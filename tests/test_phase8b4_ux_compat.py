"""Phase 8B.4 policy-UX + display-compatibility gates.

Covers what is statically provable without a game boot:

- BRS compat data generated from the SAME registry the native engine
  consumes (minus REPEAT), with native kind ids and owner bits;
- Lua structural lint for the two shipped scripts (no interpreter is
  available locally; logic is human-gated in P0C/P1);
- Python twins of the Lua deficit algorithm and the Lua Apply mirror,
  tested against transforms.py on the P1 witness values (the Lua ports
  are line-reviewed against these twins);
- filler dormancy (ExplicitUnlock, no civic) + InGame text loading;
- modinfo UI wiring (compat data before compat code; manager script).

Anything requiring the game runtime (UnlockPolicy behavior, RMA cache
mutation, EPC rendering) is human-gated in P0C/P1, never asserted here.
"""
from __future__ import annotations

import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

X10ROOT = ROOT / "controller" / "X10"


# --------------------------------------------------------------------------
# Python twins of X10SlotManager.lua source-driven targets (port target).
# --------------------------------------------------------------------------

def twin_copies(k) -> int | None:
    """Python twin of ResolveCopiesAndMask k-branch (mask omitted).

    None = disarmed/unresolvable (fail closed). Integral armed k gives
    k-1 extra slots per active source; fractional k gives 0 (native
    REPEAT refuses, vanilla single slot).
    """
    if k is None or not isinstance(k, (int, float)):
        return None
    if isinstance(k, bool) or not 0 < k <= 100:
        return None
    if k != math.floor(k):
        return 0
    return int(k) - 1


def twin_targets(sources: list, active: set, copies: int,
                 enabled: set) -> dict:
    """sources: [(base, slot, module)]. active/enabled: base/module sets."""
    targets: dict = {}
    for base, slot, module in sources:
        if base in active and module in enabled:
            targets[slot] = targets.get(slot, 0) + copies
    return targets


def twin_reconcile(targets: dict, have: dict, pool: dict) -> tuple:
    """One reconcile: unlock min(deficit, remaining pool) per type.
    Returns (unlocked_this_round, new_have)."""
    have = dict(have)
    unlocked = 0
    for slot, want in targets.items():
        deficit = max(0, want - have.get(slot, 0))
        take = min(deficit, pool.get(slot, 0) - have.get(slot, 0))
        take = max(0, take)
        have[slot] = have.get(slot, 0) + take
        unlocked += take
    return unlocked, have


class TestDeficitTwin(unittest.TestCase):
    # (source-driven targets; the matching-based cases were removed
    # with the CanSlotPolicy matcher in 8B.4.4.)
    pass


# --------------------------------------------------------------------------
# Python twin of X10BRSCompat.lua ApplyEntry (port target for review).
# --------------------------------------------------------------------------

def twin_round_half_away(v: float) -> int:
    return math.floor(v + 0.5) if v >= 0 else math.ceil(v - 0.5)


def twin_half_ulp(x: float) -> float:
    if x == 0:
        return 0.0
    _, e = math.frexp(abs(x))
    return 2.0 ** (e - 25)


def twin_count_applies(official: float, k: float, kerr: float,
                       is_delta: bool) -> bool:
    v = official * ((k - 1.0) if is_delta else k)
    r = twin_round_half_away(v)
    tol = abs(official) * kerr + 1e-9 * max(1.0, abs(v))
    return tol < 0.5 and abs(v - r) <= tol


def twin_apply(kind: int, official: float, k: float,
               count_like: bool) -> str | None:
    from civ6x10 import transforms as T
    kerr = twin_half_ulp(k)
    if count_like and not twin_count_applies(
            official, k, kerr, kind == 5):
        return None
    if kind == 0:
        return "%.6g" % (official * k)
    if kind == 1:
        if official < 0:
            return "%.6g" % (official * k)
        inner = k * math.exp(official / 25.0) - (k - 1.0)
        if inner <= 0:
            return None
        return format(25.0 * math.log(inner), ".2f")
    if kind == 2:
        pct = abs(official) > 1.0
        frac = official / 100.0 if pct else official
        if not 0.0 <= frac <= 1.0:
            return None
        out = 1.0 - (1.0 - frac) ** k
        return "%.6g" % (out * 100.0 if pct else out)
    if kind == 3:
        d = abs(official) / 100.0
        if not 0.0 <= d <= 1.0:
            return None
        out = (1.0 - (1.0 - d) ** k) * 100.0
        return "%.6g" % (-out if official < 0 else out)
    if kind == 4:
        raise AssertionError("vectors use string officials in tests")
    if kind == 5:
        return "%.6g" % (official * (k - 1.0))
    return None


class TestBrsDataGenerated(unittest.TestCase):
    def test_data_matches_registry(self):
        import yaml
        from civ6x10.bridge import collect_registry_rows
        from civ6x10.production import build_production_registry
        from civ6x10.brsdata import build_brs_entries, NATIVE_KIND_ID
        try:
            entries, _ = build_production_registry(
                collect_registry_rows(ROOT))
        except FileNotFoundError:
            raise unittest.SkipTest("local-only registry inputs unavailable")
        text = (ROOT / "controller" / "X10" / "X10BRSData.lua").read_text(
            encoding="utf-8")
        self.assertTrue(text.startswith("-- GENERATED by civ6x10.brsdata"))
        # Every non-REPEAT registry entry appears exactly once.
        wanted = sorted(
            (e["modifier_id"], e["argument"]) for e in entries
            if e["kind"] != "REPEAT")
        found = re.findall(
            r'\{ id = "([^"]+)", arg = "([^"]+)", official = "([^"]*)",'
            r" kind = (\d), countLike = (\d), owners = (\d+) \},", text)
        self.assertEqual(len(wanted), 1788)
        self.assertEqual(sorted((i, a) for i, a, _, _, _, _ in found),
                         wanted)
        by_key = {(e["modifier_id"], e["argument"]): e for e in entries}
        for i, a, off, kind, cl, owners in found:
            e = by_key[(i, a)]
            self.assertEqual(off, e["official"], i)
            self.assertEqual(kind, str(NATIVE_KIND_ID[e["kind"]]), i)
            self.assertEqual(cl, "1" if e["count_like"] else "0", i)
            self.assertEqual(owners, str(e["owners"]), i)
        # God King pair present with policies ownership.
        gk = [f for f in found if f[0] in ("GOD_KING_GOLD", "GOD_KING_FAITH")]
        self.assertEqual(len(gk), 2)
        for _, _, off, kind, _, owners in gk:
            self.assertEqual((off, kind, owners), ("1", "0", "2"))

    def test_no_repeat_rows_in_data(self):
        text = (ROOT / "controller" / "X10" / "X10BRSData.lua").read_text(
            encoding="utf-8")
        self.assertNotIn("_X10R", text)


class TestSourceTargets(unittest.TestCase):
    """Phase 8B.4.4 source-driven targets (replaces matching tests)."""

    SOURCES = [
        ("POTALA_PALACE_DIPLOMATIC_GOVERNMENT_SLOT", "SLOT_DIPLOMATIC",
         "wonders"),
        ("FORBIDDEN_CITY_WILDCARD_GOVERNMENT_SLOT", "SLOT_WILDCARD",
         "wonders"),
        ("ALHAMBRA_MILITARY_GOVERNMENT_SLOT", "SLOT_MILITARY", "wonders"),
        ("BIG_BEN_ECONOMIC_GOVERNMENT_SLOT", "SLOT_ECONOMIC", "wonders"),
        ("TRAIT_ECONOMIC_GOVERNMENT_SLOT", "SLOT_ECONOMIC", "traits"),
        ("TRAIT_MILITARY_GOVERNMENT_SLOT", "SLOT_MILITARY", "traits"),
        ("TRAIT_WILDCARD_GOVERNMENT_SLOT", "SLOT_WILDCARD", "traits"),
    ]
    POOL = {"SLOT_MILITARY": 200, "SLOT_DIPLOMATIC": 100,
            "SLOT_ECONOMIC": 200, "SLOT_WILDCARD": 200}

    def test_all_seven_sources_mapped(self):
        from civ6x10.eight_b import SLOT_BASES
        want = {(base, slot, module) for base, slot, _, _, module
                in SLOT_BASES}
        got = {(b, s, m) for b, s, m in self.SOURCES}
        self.assertEqual(got, want)

    def test_lua_sources_match_manifest(self):
        import re
        text = (ROOT / "controller" / "X10" / "UI"
                / "X10SlotManager.lua").read_text(encoding="utf-8")
        for base, slot, module in self.SOURCES:
            self.assertIn(f'base = "{base}"', text)
        # Seven base entries, no more.
        self.assertEqual(len(re.findall(r"base = ", text)), 7)

    def test_preset_target_counts(self):
        for k, want in ((2, 1), (3, 2), (5, 4), (10, 9), (20, 19),
                        (50, 49), (100, 99)):
            self.assertEqual(twin_copies(k), want, k)
            got = twin_targets(self.SOURCES,
                               {b for b, _, _ in self.SOURCES},
                               want, {"wonders", "traits"})
            # All seven active: per-type sums of k-1.
            self.assertEqual(
                got, {"SLOT_DIPLOMATIC": want, "SLOT_WILDCARD": 2 * want,
                      "SLOT_MILITARY": 2 * want, "SLOT_ECONOMIC": 2 * want})

    def test_integer_custom(self):
        self.assertEqual(twin_copies(7), 6)

    def test_fractional_custom_zero(self):
        from civ6x10 import transforms as T
        self.assertEqual(twin_copies(T.stored_float32(7.3)), 0)
        self.assertEqual(twin_copies(7.5), 0)

    def test_off_invalid_zero_or_none(self):
        self.assertIsNone(twin_copies(0))
        self.assertIsNone(twin_copies(-1))
        self.assertIsNone(twin_copies(101))
        self.assertIsNone(twin_copies(None))

    def test_module_off_zero(self):
        got = twin_targets(self.SOURCES,
                           {b for b, _, _ in self.SOURCES},
                           9, {"traits"})
        self.assertNotIn("SLOT_DIPLOMATIC", got)
        self.assertEqual(got.get("SLOT_MILITARY"), 9)
        self.assertEqual(
            twin_targets(self.SOURCES, set(), 9, {"wonders", "traits"}),
            {})

    def test_same_type_accumulates(self):
        got = twin_targets(
            self.SOURCES,
            {"POTALA_PALACE_DIPLOMATIC_GOVERNMENT_SLOT",
             "FORBIDDEN_CITY_WILDCARD_GOVERNMENT_SLOT"}, 9,
            {"wonders", "traits"})
        self.assertEqual(got, {"SLOT_DIPLOMATIC": 9, "SLOT_WILDCARD": 9})

    def test_reconcile_constant_and_pool_bounded(self):
        # Potala x10 across three reconciles: 9 then 0, 0.
        have = {}
        seen = []
        for _ in range(3):
            unlocked, have = twin_reconcile({"SLOT_DIPLOMATIC": 9},
                                            have, self.POOL)
            seen.append(unlocked)
        self.assertEqual(seen, [9, 0, 0])
        self.assertEqual(have, {"SLOT_DIPLOMATIC": 9})
        # Existing unlocked fillers respected (no over-unlock).
        unlocked, have = twin_reconcile(
            {"SLOT_DIPLOMATIC": 9}, {"SLOT_DIPLOMATIC": 9}, self.POOL)
        self.assertEqual((unlocked, have["SLOT_DIPLOMATIC"]), (0, 9))

    def test_no_civic_mass_unlock(self):
        import re
        text = (ROOT / "civ6x10" / "eight_b.py").read_text(encoding="utf-8")
        self.assertNotIn("CIVIC_CODE_OF_LAWS', 'LOC_POLICY_X10_FILLER_NAME",
                         text.replace(' NULL, ', ''))
        # Source-driven Lua: no active sources => empty targets => no
        # unlocks (ordinary Code of Laws stays clean).
        self.assertEqual(
            twin_targets(self.SOURCES, set(), 9, {"wonders", "traits"}), {})
        unlocked, have = twin_reconcile({}, {}, self.POOL)
        self.assertEqual((unlocked, have), (0, {}))

    def test_potala_x10_target_nine(self):
        # THE P0C case: Potala x10 => 9 Diplomatic Reserves, then 0, 0.
        copies = twin_copies(10)
        self.assertEqual(copies, 9)
        got = twin_targets(
            self.SOURCES, {"POTALA_PALACE_DIPLOMATIC_GOVERNMENT_SLOT"},
            copies, {"wonders", "traits"})
        self.assertEqual(got, {"SLOT_DIPLOMATIC": 9})
        have = {}
        seen = []
        for _ in range(3):
            unlocked, have = twin_reconcile(got, have, self.POOL)
            seen.append(unlocked)
        self.assertEqual(seen, [9, 0, 0])
        # Second x10 Diplomatic source would accumulate (9 + 9 = 18);
        # with only Potala active the target stays 9 (bounded supply).

    def test_no_matcher_remains_in_lua(self):
        text = (ROOT / "controller" / "X10" / "UI"
                / "X10SlotManager.lua").read_text(encoding="utf-8")
        # No functional gameplay-side legality matcher may remain.
        # (History comments may name the removed APIs; calls must not.)
        for needle in ("CanSlotPolicy(", ":CanSlotPolicy(",
                       "GetSlotType(", "MaximumMatching(",
                       "DeficitFromUnmatched(", "CurrentSlots(",
                       "Kuhn(", "IsPolicyObsolete("):
            self.assertNotIn(needle, text, needle)
        # Unlock path is target-count only.
        self.assertIn("UnlockToTarget", text)
        self.assertIn("PlayerTargets", text)

    def test_hooks_pruned_in_lua(self):
        text = (ROOT / "controller" / "X10" / "UI"
                / "X10SlotManager.lua").read_text(encoding="utf-8")
        for banned in ("PlayerTurnStarted", "PlayerDoTurn",
                       "GovernmentPolicyChanged", "GovernmentChanged",
                       "CivicCompleted"):
            self.assertNotIn(banned, text, banned)
        for required in ('name = "WonderCompleted"',
                         'name = "TurnBegin"',
                         'name = "LoadScreenClose"',
                         'ReconcileAll("init")'):
            self.assertIn(required, text, required)


def twin_resolve(preset, custom):
    """Python twin of the Lua k-resolution (both compat + manager).

    Returns armed k or None (disarmed). Native parity: Custom 0 (and
    any 0-equivalent blank) normalizes to DISARMED like preset Off.
    """
    if preset is not None:
        if preset == 0:
            return None
        if preset == 101:
            if not isinstance(custom, (int, float)) or isinstance(
                    custom, bool) or not 0 < custom <= 100:
                return None
            return custom
        if preset in (2, 3, 5, 10, 20, 50, 100):
            return preset
        return None
    if not isinstance(custom, (int, float)) or isinstance(
            custom, bool) or not 0 < custom <= 100:
        return None
    return custom


def twin_human_majors(ids_api, objs_api, scan_ids, humans):
    """Python twin of X10SlotManager HumanMajors stage logic.

    ids_api: 'missing' | 'throw' | list (numbers AND/OR opaque objects,
        modeling GetAliveMajorIDs returning Player objects by mistake).
    objs_api: 'missing' | 'throw' | list of fake players {id, human}.
    scan_ids: ids visible to the bounded scan. humans: human-major ids.
    Returns (resolved_ids, stage_used).
    """
    out, seen = [], set()

    def consider(i):
        if isinstance(i, bool) or not isinstance(i, int):
            return
        if i in seen or i not in humans:
            return
        seen.add(i)
        out.append(i)

    n0 = len(out)
    if ids_api != "missing":
        if ids_api != "throw":
            for i in ids_api:
                consider(i)
        if len(out) > n0:
            return out, "ids"
    if objs_api != "missing":
        if objs_api != "throw":
            for p in objs_api:
                consider(p.get("id"))
        if len(out) > n0:
            return out, "objects"
    for i in scan_ids:
        consider(i)
    return out, "scan"


class TestEnumerationTwin(unittest.TestCase):
    def test_ids_api_preferred(self):
        got, stage = twin_human_majors([0, 2], "missing", [], {0, 2})
        self.assertEqual((got, stage), ([0, 2], "ids"))

    def test_object_shape_falls_through(self):
        # THE 8B.4 BUG: GetAliveMajors-style Player objects are not
        # numbers, so the IDs stage must yield ZERO (not stop), and
        # the object stage must resolve via GetID.
        objs = [{"id": 0, "human": True}, {"id": 1, "human": False}]
        got, stage = twin_human_majors(
            [{"opaque": "player"}, {"opaque": "player2"}],
            objs, [], {0})
        self.assertEqual((got, stage), ([0], "objects"))

    def test_empty_ids_falls_through(self):
        got, stage = twin_human_majors(
            [], [{"id": 3, "human": True}], [], {3})
        self.assertEqual((got, stage), ([3], "objects"))

    def test_both_missing_uses_scan(self):
        got, stage = twin_human_majors(
            "missing", "missing", [0, 1, 2], {1})
        self.assertEqual((got, stage), ([1], "scan"))

    def test_no_duplicate_ids(self):
        got, _ = twin_human_majors([0, 0, 2], "missing", [0, 2], {0, 2})
        self.assertEqual(sorted(got), [0, 2])


class TestReconcileIdempotenceTwin(unittest.TestCase):
    """Phase 8B.4.3 matching-universe idempotence (HISTORICAL).

    Characterizes the REMOVED 8B.4 matcher for review; 8B.4.4 replaces
    matching with source-driven targets (see TestSourceTargets).
    Kept so the 8/16/24 flood shape cannot be reintroduced unnoticed.
    """

    def _rounds(self, n_slots, n_real, pool, rounds=3):
        unlocked = 0
        deficits = []
        for _ in range(rounds):
            # Maximum match size = min(slots, real + unlocked).
            matched = min(n_slots, n_real + unlocked)
            deficit = n_slots - matched
            deficits.append(deficit)
            take = min(deficit, pool - unlocked)
            unlocked += take
        return deficits, unlocked

    def test_case_a_fresh_deficit_8(self):
        deficits, unlocked = self._rounds(10, 2, 100, rounds=1)
        self.assertEqual(deficits, [8])
        self.assertEqual(unlocked, 8)

    def test_case_b_satisfied_stays_zero(self):
        # 2 real + 8 unlocked fillers already cover 10 slots.
        deficits, unlocked = self._rounds(10, 2, 100, rounds=1)
        self.assertEqual(deficits, [8])
        # Second round starts from 8 unlocked (Case B input state).
        deficits2, unlocked2 = self._rounds(10, 2 + 8, 100 - 8, rounds=1)
        self.assertEqual(deficits2, [0])
        self.assertEqual(unlocked2, 0)

    def test_case_c_larger_demand(self):
        deficits, unlocked = self._rounds(20, 2 + 8, 100 - 8, rounds=1)
        self.assertEqual(deficits, [10])
        self.assertEqual(unlocked, 10)

    def test_case_d_no_repeated_unlock(self):
        # Three reconciliations after Case A: total stays 8, deficits
        # after the first round are 0 (the old code produced 8,8,8 and
        # unlocked 24).
        deficits, unlocked = self._rounds(10, 2, 100, rounds=3)
        self.assertEqual(deficits, [8, 0, 0])
        self.assertEqual(unlocked, 8)

    def test_old_exclusion_shape_would_flood(self):
        # Documents the bug: excluding unlocked fillers from matching
        # re-computes the full deficit every round.
        deficits = []
        unlocked = 0
        for _ in range(3):
            matched = min(10, 2)  # BUG: unlocked fillers invisible
            deficits.append(10 - matched)
            unlocked += min(10 - matched, 100 - unlocked)
        self.assertEqual(deficits, [8, 8, 8])
        self.assertEqual(unlocked, 24)


class TestRetryLogTwin(unittest.TestCase):
    """pcall returns (execution_ok, return_value): only (True, True)
    may log wrapper-active."""

    @staticmethod
    def twin_should_log(outcome):
        # outcome: ("return", value) | ("throw", None)
        if outcome[0] == "throw":
            ok, installed = False, None
        else:
            ok, installed = True, outcome[1]
        return bool(ok and installed)

    def test_true_logs(self):
        self.assertTrue(self.twin_should_log(("return", True)))

    def test_false_stays_silent(self):
        # THE BUG: old code logged on bare pcall truthiness here.
        self.assertFalse(self.twin_should_log(("return", False)))
        self.assertFalse(self.twin_should_log(("return", None)))

    def test_throw_stays_silent(self):
        self.assertFalse(self.twin_should_log(("throw", None)))

    def test_lua_pattern_corrected(self):
        text = (ROOT / "controller" / "X10" / "X10BRSCompat.lua").read_text(
            encoding="utf-8")
        self.assertIn("local ok, installed = pcall(Install);", text)
        self.assertIn("if ok and installed then", text)
        self.assertNotIn("if pcall(Install) then", text)


class TestKResolutionTwin(unittest.TestCase):
    def test_standard_presets(self):
        for k in (2, 3, 5, 10, 20, 50, 100):
            self.assertEqual(twin_resolve(k, None), k)

    def test_off_and_zero_disarm(self):
        self.assertIsNone(twin_resolve(0, None))
        self.assertIsNone(twin_resolve(101, 0))
        self.assertIsNone(twin_resolve(None, 0))

    def test_custom_valid_and_73(self):
        self.assertEqual(twin_resolve(101, 7.3), 7.3)
        self.assertEqual(twin_resolve(None, 10), 10)
        self.assertEqual(twin_resolve(101, 100), 100)

    def test_invalid_disarms(self):
        self.assertIsNone(twin_resolve(101, -1))
        self.assertIsNone(twin_resolve(101, 101))
        self.assertIsNone(twin_resolve(101, None))
        self.assertIsNone(twin_resolve(101, "abc"))
        self.assertIsNone(twin_resolve(None, None))
        self.assertIsNone(twin_resolve(999, None))
        self.assertIsNone(twin_resolve(None, -5))


class TestApplyTwin(unittest.TestCase):
    def test_p1_witness_values(self):
        # God King / Urban Planning flat magnitudes.
        self.assertEqual(twin_apply(0, 1.0, 10.0, False), "10")
        # Discipline nonlinear combat (NOT +50, NOT +5).
        got = twin_apply(1, 5.0, 10.0, False)
        self.assertEqual(got, "29.19")
        self.assertNotIn(got, ("50", "5"))
        # Panama delta at 7.3 applies (10 x 6.3 = 63); Stonehenge-style
        # inexact deltas refuse.
        from civ6x10 import transforms as T
        kf = T.stored_float32(7.3)
        self.assertEqual(twin_apply(5, 10.0, kf, True), "63")
        self.assertIsNone(twin_apply(5, 2.0, kf, True))
        self.assertIsNone(twin_apply(0, 6.0, kf, True))
        # Exact count-like applies.
        self.assertEqual(twin_apply(0, 10.0, kf, True), "73")

    def test_twin_agrees_with_native_conventions(self):
        from civ6x10 import transforms as T
        self.assertEqual(twin_apply(0, 2.0, 10.0, False),
                         "%.6g" % T.scale_flat(2.0, 10.0))
        self.assertEqual(twin_apply(2, 50.0, 10.0, False),
                         "%.6g" % T.repeated_probability_for_multiplier(
                             50.0, 10.0))
        self.assertEqual(twin_apply(3, 50.0, 10.0, False),
                         "%.6g" % T.compound_discount_for_multiplier(
                             50.0, 10.0))
        self.assertEqual(twin_apply(5, 2.0, 10.0, False),
                         "%.6g" % T.bridge_delta(2.0, 10.0))
        # Negative combat scales flat (native negative-combat-flat).
        self.assertEqual(twin_apply(1, -5.0, 10.0, False), "-50")


class TestFillerDormancyAndText(unittest.TestCase):
    def test_every_gameplay_loc_tag_has_ingame_text(self):
        import re
        slot_sql = (ROOT / "controller" / "X10" / "Config"
                    / "X10SlotCopies.sql").read_text(encoding="utf-8")
        tags = set(re.findall(r"LOC_POLICY_X10_[A-Z_]+", slot_sql))
        self.assertEqual(tags, {"LOC_POLICY_X10_FILLER_DESC",
                                "LOC_POLICY_X10_FILLER_NAME"})
        text = (ROOT / "controller" / "X10" / "Config"
                / "X10Text.sql").read_text(encoding="utf-8")
        for tag in tags:
            self.assertIn(f"'{tag}'", text, tag)

    def test_text_loaded_in_both_contexts(self):
        import xml.etree.ElementTree as ET
        m = ET.parse(str(ROOT / "controller" / "X10"
                         / "X10.modinfo")).getroot()
        fe = [f.text for a in m.find("FrontEndActions")
              for f in a.iter("File")]
        self.assertIn("Config/X10Text.sql", fe)
        ig_text = [f.text for a in m.find("InGameActions")
                   if a.tag == "UpdateText" for f in a.iter("File")]
        self.assertIn("Config/X10Text.sql", ig_text)

    def test_ui_wiring(self):
        import xml.etree.ElementTree as ET
        m = ET.parse(str(ROOT / "controller" / "X10"
                         / "X10.modinfo")).getroot()
        files = [f.text for f in m.find("Files").iter("File")]
        for rel in ("X10BRSData.lua", "X10BRSCompat.lua",
                    "X10BRSCompat.xml", "UI/X10SlotManager.lua"):
            self.assertIn(rel, files, rel)
        ig = {a.get("id"): [f.text for f in a.iter("File")]
              for a in m.find("InGameActions")}
        # Data loads before the compat layer that consumes it.
        self.assertEqual(ig["X10BRSCompat"],
                         ["X10BRSData.lua", "X10BRSCompat.lua"])
        self.assertEqual(ig["X10SlotManager"], ["UI/X10SlotManager.lua"])


class TestBrsContextWiring(unittest.TestCase):
    """The compat script must EXECUTE in an AddUserInterfaces context:
    ImportFiles alone only exposes files to the VFS."""

    def _actions(self):
        import xml.etree.ElementTree as ET
        m = ET.parse(str(ROOT / "controller" / "X10"
                         / "X10.modinfo")).getroot()
        return m

    def test_add_user_interfaces_context(self):
        m = self._actions()
        uis = [(a.get("id"),
                a.find("Properties/Context").text
                if a.find("Properties/Context") is not None else None,
                [f.text for f in a.iter("File")])
               for a in m.find("InGameActions")
               if a.tag == "AddUserInterfaces"]
        self.assertEqual(len(uis), 1, uis)
        aid, context, files = uis[0]
        # Shared InGame host context (the BRS RealModifierAnalysis
        # pattern); the Lua-basename unit, not the Context, is ours.
        self.assertEqual(context, "InGame")
        self.assertEqual(files, ["X10BRSCompat.xml"])
        for needle in ("GovernmentScreen", "reportscreen", "BRSPage"):
            self.assertNotIn(needle, aid + context + "".join(files))

    def test_xml_lua_basename_parity(self):
        # Same-basename .xml/.lua is the execution mechanism (the BRS
        # RealModifierAnalysis pattern): the context xml causes its lua
        # to run. ImportFiles exposure alone executes nothing.
        self.assertTrue(
            (ROOT / "controller" / "X10" / "X10BRSCompat.xml").is_file())
        self.assertTrue(
            (ROOT / "controller" / "X10" / "X10BRSCompat.lua").is_file())

    def test_data_explicitly_included(self):
        # Do not assume importing executes: the executing file must
        # explicitly include the data by the proven bare-name form.
        text = (ROOT / "controller" / "X10" / "X10BRSCompat.lua").read_text(
            encoding="utf-8")
        self.assertRegex(text, r'pcall\(include,\s*"X10BRSData"\)')
        self.assertIn("[X10BRSCompat] context loaded", text)
        self.assertIn("generated data loaded:", text)
        self.assertIn("RMA found", text)
        self.assertIn("RMA deferred", text)
        self.assertIn("[X10BRSCompat] installed", text)

    def test_covered_object_families(self):
        # Exactly the audited CalculateModifierEffect call sites:
        # BRSPage_Policy Policy/Belief, BRSPage_Minor Trait (x2),
        # EPC GovernmentScreen Policy.
        text = (ROOT / "controller" / "X10" / "X10BRSCompat.lua").read_text(
            encoding="utf-8")
        for fam in ("Policy = { table = \"PolicyModifiers\"",
                    "Belief = { table = \"BeliefModifiers\"",
                    "Trait = { table = \"TraitModifiers\""):
            self.assertIn(fam, text, fam)

    def test_slot_manager_content_markers(self):
        text = (ROOT / "controller" / "X10" / "UI"
                / "X10SlotManager.lua").read_text(encoding="utf-8")
        # Source-driven targets (8B.4.4): safe enumeration survives
        # (IDs API preferred, Player objects via GetID, bounded scan
        # last), target machinery present, failed matcher gone.
        for needle in ("PlayerManager.GetAliveMajorIDs",
                       "PlayerManager.GetAliveMajors",
                       "GetID", "PlayerTargets", "UnlockToTarget",
                       "AlreadyUnlockedByType", "WonderOwned",
                       "PlayerHasTrait", "ResolveCopiesAndMask"):
            self.assertIn(needle, text, needle)
        self.assertNotIn("#Players", text)


class TestLuaLint(unittest.TestCase):
    # No Lua interpreter is available locally; this catches gross
    # structural typos only. Logic is human-gated (P0C/P1).
    def _lint(self, rel):
        text = (ROOT / "controller" / "X10" / rel).read_text(
            encoding="utf-8")
        stripped = []
        for line in text.splitlines():
            s = line.split("--", 1)[0]
            out, quote = "", None
            for ch in s:
                if quote is not None:
                    if ch == quote:
                        quote = None
                    continue
                if ch in "\"'":
                    quote = ch
                    continue
                out += ch
            stripped.append(out)
        code = "\n".join(stripped)
        for a, b in ("()", "[]", "{}"):
            self.assertEqual(code.count(a), code.count(b), (rel, a))
        # `do` belongs to for/while (no separate end); standalone
        # do-blocks are not used in these files.
        opens = len(re.findall(
            r"\b(function|if|for|while)\b", code))
        closes = len(re.findall(r"\bend\b", code))
        self.assertEqual(opens, closes, rel)
        # Lua 5.1-compatible subset only (unknown Civ VI Lua version):
        # no bitwise ops, integer division, goto, string.pack.
        # (`~=` inequality is fine; bare `~` never appears outside it.)
        for bad in ("&", "|", "<<", ">>", "//", "goto",
                    "string.pack"):
            self.assertNotIn(bad, code, (rel, bad))
        self.assertNotRegex(code, r"(?<![~=])~(?![=])", rel)

    def test_slot_manager_lints(self):
        self._lint("UI/X10SlotManager.lua")

    def test_brs_compat_lints(self):
        self._lint("X10BRSCompat.lua")

    def test_brs_data_lints(self):
        self._lint("X10BRSData.lua")


if __name__ == "__main__":
    unittest.main(verbosity=2)
