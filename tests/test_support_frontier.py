"""Phase 8A: support-frontier accounting tests.

Reads ONLY the committed discovery artifact
(`civ6x10/rules/support_frontier.yml`) plus production sources.
CI-safe: accounting tests run everywhere; live cross-checks against the
private baseline DB / generated manifests skip when unavailable.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YML = ROOT / "civ6x10" / "rules" / "support_frontier.yml"

TAXONOMY = [
    "ALREADY_SUPPORTED",
    "EXISTING_AUDIT_EXCLUDED",
    "STRONG_CANDIDATE",
    "CANDIDATE_COUNT_LIKE",
    "CANDIDATE_NEEDS_NEW_TRANSFORM",
    "NEEDS_SEMANTIC_RESEARCH",
    "NEEDS_PRODUCT_DECISION",
    "GLOBAL_OR_CROSS_PLAYER_LEAKAGE",
    "STRUCTURAL_OR_FILTER",
    "COST_OR_PRICE",
    "TIMER_OR_DURATION",
    "BASE_STAT_NOT_BONUS",
    "MODE_SYSTEM_MECHANIC",
    "NO_MEANINGFUL_MULTIPLIER_TARGET",
]

DIRECT_ROLES = [
    "bonus_magnitude",
    "base_stat",
    "cost",
    "duration_timer",
    "chance",
    "cap",
    "requirement_filter",
    "selector",
    "ai_weight",
    "progression_threshold",
    "global_intensity",
    "structural_internal",
]

EXPECTED_MODES = [
    "apocalypse",
    "secret_societies",
    "tech_civic_shuffle",
    "dramatic_ages",
    "heroes_legends",
    "monopolies_corporations",
    "barbarian_clans",
    "zombie_defense",
]


def frontier():
    import yaml
    return yaml.safe_load(YML.read_text(encoding="utf-8"))


class TestFrontierArtifact(unittest.TestCase):
    def test_yml_loads_and_version(self):
        doc = frontier()
        self.assertEqual(doc["version"], 2)
        self.assertEqual(doc["phase"], "8B")
        for key in ("baseline_db", "production", "taxonomy", "game_modes",
                    "modifier_roots", "direct_tables", "beyond_request",
                    "discovery"):
            self.assertIn(key, doc, key)

    def test_taxonomy_exact(self):
        self.assertEqual(frontier()["taxonomy"], TAXONOMY)

    def test_production_block_matches_freeze(self):
        prod = frontier()["production"]
        self.assertEqual(
            (prod["entries"], prod["unique"], prod["shared"],
             prod["unconditional"], prod["count_like"]),
            (2481, 2475, 26, 1333, 1148))
        self.assertEqual(prod["ce_commit"], "86be003")
        self.assertEqual(
            prod["dll_sha256"],
            "85ea875229ba644a65f00a96373162a8311e0d9f0d12281d7b407bd264c38507")

    def test_roots_accounted(self):
        doc = frontier()
        roots = doc["modifier_roots"]
        disc = doc["discovery"]
        # every schema modifier-reference table examined is dispositioned
        self.assertEqual(len(roots), disc["modifier_tables_examined"])
        seen = set()
        total_pairs = 0
        for r in roots:
            self.assertTrue(r["table"] and r["table"] not in seen)
            seen.add(r["table"])
            self.assertTrue(r["role"], r["table"])
            pairs = r.get("pairs", [])
            self.assertEqual(r["numeric_pairs"], len(pairs), r["table"])
            self.assertEqual(
                r["in_registry"] + r["uncovered"], r["numeric_pairs"],
                r["table"])
            for p in pairs:
                self.assertIn(p["disposition"], TAXONOMY,
                              (r["table"], p))
                self.assertTrue(p["modifier"] and p["argument"],
                                (r["table"], p))
            total_pairs += len(pairs)
        self.assertEqual(total_pairs, disc["total_numeric_pairs"])

    def test_no_pair_disappears(self):
        doc = frontier()
        counted = {}
        for r in doc["modifier_roots"]:
            for p in r.get("pairs", []):
                counted[p["disposition"]] = counted.get(
                    p["disposition"], 0) + 1
        self.assertEqual(counted, doc["disposition_totals"])

    def test_modes_dispositioned(self):
        doc = frontier()
        modes = doc["game_modes"]
        self.assertTrue(modes)
        found = set()
        for m in modes:
            self.assertTrue(m["id"] and m["name"], m)
            found.add(m["id"])
            self.assertTrue(m["disposition"], m["id"])
            self.assertTrue(m["configuration_id"], m["id"])
            self.assertTrue(m["dlc"], m["id"])
            self.assertIsInstance(m.get("overlay_files", []), list)
        sanity = doc.get("mode_sanity_check", {})
        missing = [e for e in EXPECTED_MODES if e not in found]
        extra = [f for f in found if f not in EXPECTED_MODES]
        if missing or extra:
            self.assertTrue(sanity.get("discrepancies"),
                            (missing, extra))
        self.assertEqual(sorted(sanity.get("expected_8", [])),
                         sorted(EXPECTED_MODES))

    def test_direct_tables_dispositioned(self):
        for t in frontier()["direct_tables"]:
            self.assertTrue(t["table"] and t["field"], t)
            self.assertIn(t["role"], DIRECT_ROLES, t)
            self.assertIn(t["disposition"], TAXONOMY, t)

    def test_beyond_request_recorded(self):
        doc = frontier()
        self.assertIsInstance(doc["beyond_request"], list)
        self.assertTrue(doc["discovery"].get("beyond_request_method"),
                        "record how beyond-request systems were searched")

    def test_production_code_ignores_frontier(self):
        # the frontier artifact must never feed production loaders; the
        # only sanctioned mention is the release-surface inventory entry
        # (same standing as the other private audit YAMLs)
        hits = []
        for py in (ROOT / "civ6x10").glob("*.py"):
            if "support_frontier" in py.read_text(encoding="utf-8"):
                hits.append(py.name)
        self.assertEqual(hits, ["release_surface.py"])
        export_src = (ROOT / "release" / "export_public_source.py"
                      ).read_text(encoding="utf-8")
        self.assertNotIn("support_frontier", export_src)

    def test_no_lua_in_production_tree(self):
        # any custom-validation prototype must stay disposable under
        # spike/8a-frontier/; production ships zero Lua
        lua = [str(p) for d in ("controller", "dependencies")
               for p in (ROOT / d).rglob("*.lua")]
        self.assertEqual(lua, [])

    def test_frontier_files_classified_private(self):
        from civ6x10.release_surface import classify
        for rel in ("civ6x10/rules/support_frontier.yml",
                    "docs/SUPPORT_FRONTIER.md",
                    "spike/8a-frontier/db_scan.json"):
            surface = classify(rel)[0]
            self.assertEqual(surface, "private", rel)

    def test_three_metrics_defined(self):
        doc = frontier()
        fig = doc["roadmap_figures"]
        for key in ("units_root_occurrences", "units_unique_definitions",
                    "units_proposed_production"):
            self.assertTrue(fig[key], key)
        self.assertEqual(
            fig["actionable_definitions"],
            fig["unique_definition_totals"].get("STRONG_CANDIDATE", 0)
            + fig["unique_definition_totals"].get(
                "CANDIDATE_COUNT_LIKE", 0))
        # root occurrences and unique definitions are different units:
        # dedup can only shrink counts, never grow them
        for disp, n_root in fig["root_occurrence_totals"].items():
            self.assertGreaterEqual(
                n_root, fig["unique_definition_totals"].get(disp, 0),
                disp)

    def test_civic_award_conflict_regression(self):
        doc = frontier()
        proj = {(p["modifier"], p["argument"]): p
                for p in doc["definition_projection"]}
        key = ("CIVIC_AWARD_ONE_INFLUENCE_TOKEN", "Amount")
        self.assertIn(key, proj)
        p = proj[key]
        self.assertFalse(p["roots_agree"])
        self.assertEqual(
            sorted(p["dispositions"]),
            ["CANDIDATE_COUNT_LIKE", "NEEDS_PRODUCT_DECISION"])
        self.assertEqual(p["final_disposition"], "NEEDS_PRODUCT_DECISION")

    def test_no_candidate_hides_conflict(self):
        doc = frontier()
        bad = [(p["modifier"], p["argument"], p["dispositions"])
               for p in doc["definition_projection"]
               if p["final_disposition"] in ("STRONG_CANDIDATE",
                                             "CANDIDATE_COUNT_LIKE")
               and not p["roots_agree"]]
        self.assertEqual(bad, [])

    def test_cross_root_duplicates_complete(self):
        doc = frontier()
        by_table = {}
        for r in doc["modifier_roots"]:
            for q in r["pairs"]:
                if q["disposition"] == "ALREADY_SUPPORTED":
                    continue
                by_table.setdefault(
                    (q["modifier"], q["argument"]), set()).add(r["table"])
        expected = sorted(k for k, v in by_table.items() if len(v) > 1)
        recorded = sorted((d["modifier"], d["argument"])
                          for d in doc["cross_root_duplicates"])
        self.assertEqual(recorded, expected)
        for d in doc["cross_root_duplicates"]:
            self.assertTrue(d["roots"] and d["dispositions"])
            self.assertIn(d["final_disposition"], TAXONOMY)

    def test_mode_counts_not_labelled_candidates(self):
        doc = frontier()
        for g in doc["game_modes"]:
            self.assertIn(g["candidate_status"],
                          ("PENDING", "NONE_NO_TARGET"), g["id"])
            self.assertTrue(g["verdict_meaning"], g["id"])
            self.assertLessEqual(
                g["numeric_scalar_pairs"] + g["structural_selector_pairs"],
                g["unique_pairs"], g["id"])
        md = (ROOT / "docs" / "SUPPORT_FRONTIER.md").read_text(
            encoding="utf-8")
        for banned in ("125 scalable magnitudes",
                       "176 scalable magnitudes",
                       "163 scalable magnitudes",
                       "149 scalable magnitudes",
                       "every overlay pair is ready for production",
                       "370 candidate magnitudes"):
            self.assertNotIn(banned, md, banned)

    def test_generated_tables_verbatim_in_md(self):
        frag = (ROOT / "spike" / "8a-frontier" / "generated_tables.md"
                ).read_text(encoding="utf-8")
        md = (ROOT / "docs" / "SUPPORT_FRONTIER.md").read_text(
            encoding="utf-8")
        blocks = [b.strip() for b in frag.split("### Table")[1:]]
        self.assertTrue(blocks)
        for b in blocks:
            self.assertIn("### Table " + b, md)


def _mode_manifest_pairs():
    """(modifier_id, argument) pairs owned by the modes manifest.

    Mode-overlay definitions are parsed from shipped overlays and are
    absent from the no-overlay baseline snapshot by construction.
    """
    import yaml
    p = ROOT / "manifests" / "modes.yml"
    if not p.is_file():
        raise unittest.SkipTest("modes manifest unavailable")
    man = yaml.safe_load(p.read_text(encoding="utf-8"))
    return {(r["modifier_id"], r["argument_name"]) for r in man["modes"]}


class TestFrontierLiveCrossCheck(unittest.TestCase):
    """Needs private inputs; skips in CI and clean checkouts."""

    def _production_pairs(self):
        from civ6x10.bridge import collect_registry_rows
        from civ6x10.production import build_production_registry
        entries, _ = build_production_registry(collect_registry_rows(ROOT))
        pairs = {(e["modifier_id"], e["argument"]) for e in entries}
        return entries, pairs

    def test_production_pairs_live(self):
        import sqlite3
        db = ROOT / "data" / "local" / "DebugGameplay_official.sqlite"
        if not db.is_file():
            raise unittest.SkipTest("baseline DB unavailable")
        if not (ROOT / "manifests" / "traits.yml").is_file():
            raise unittest.SkipTest("generated manifests unavailable")
        entries, pairs = self._production_pairs()
        self.assertEqual(len(entries), 2481)
        doc = frontier()
        self.assertEqual(doc["pair_overlap"]["production_pairs_total"],
                         len(pairs))
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            db_args = set()
            tables = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")]
            for t in tables:
                cols = [c[1] for c in con.execute(
                    f'PRAGMA table_info("{t}")')]
                if "ModifierId" not in cols or \
                        "ModifierArgument" not in cols and \
                        "ArgumentName" not in cols and "Name" not in cols:
                    continue
                # best-effort mirror of the scanner's pair extraction:
                # every candidate argument column is checked
                for acol in ("ModifierArgument", "ArgumentName", "Name",
                             "Argument", "Value"):
                    if acol in cols:
                        try:
                            for mid, arg in con.execute(
                                    f'SELECT ModifierId, "{acol}" '
                                    f'FROM "{t}"'):
                                db_args.add((mid, arg))
                        except Exception:
                            pass
        finally:
            con.close()
        missing = {(m, a) for (m, a) in pairs if (m, a) not in db_args}
        # Absent from official data by construction (all documented):
        # - X10_ synthetic bridge helpers (wonder-direct bridge);
        # - *_X10R### inert slot copies (slot-copy SQL, Phase 8B);
        # - mode-overlay pairs (module modes, parsed from shipped mode
        #   overlays, absent from the no-overlay baseline snapshot);
        # - artifact-documented overlay pairs (governor mode remainder).
        # Anything else unexplained fails.
        doc = frontier()
        overlay = set()
        for m in doc["game_modes"]:
            for p in m.get("overlay_pairs", []):
                overlay.add((p[0], p[1]))
        mode_pairs = _mode_manifest_pairs()
        unexplained = {(m, a) for (m, a) in missing
                       if not (isinstance(m, str) and m.startswith("X10_"))
                       and not (isinstance(m, str) and "_X10R" in m)
                       and (m, a) not in overlay
                       and (m, a) not in mode_pairs}
        self.assertEqual(unexplained, set())

    def test_baseline_db_matches(self):
        import hashlib
        db = ROOT / "data" / "local" / "DebugGameplay_official.sqlite"
        if not db.is_file():
            raise unittest.SkipTest("baseline DB unavailable")
        doc = frontier()
        self.assertEqual(doc["baseline_db"]["bytes"], db.stat().st_size)
        h = hashlib.sha256()
        with open(db, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        self.assertEqual(doc["baseline_db"]["sha256"], h.hexdigest())

    def test_no_overlay_leak_into_production(self):
        # Mode-overlay-only modifiers must not appear in production
        # RUNTIME files (setup config, wonder bridge, dummies, engine
        # redirect, modinfo action/file references). Generated manifests
        # are audit workspace, not runtime, so they are out of scope.
        runtime_rels = [
            "controller/X10/Config/X10Config.sql",
            "controller/X10/Config/X10Text.sql",
            "controller/X10/Config/X10WonderBridge.sql",
            "controller/X10/Config/Dummy.sql",
            "controller/X10/X10.modinfo",
            "dependencies/CE-X10/Config/EngineRedirect.sql",
            "dependencies/CE-X10/Config/Dummy.sql",
            "dependencies/CE-X10/CE-X10.modinfo",
        ]
        for rel in runtime_rels:
            self.assertTrue((ROOT / rel).is_file(), rel)
        prod_ids = set()
        for rel in runtime_rels:
            text = (ROOT / rel).read_text(encoding="utf-8")
            prod_ids |= set(re.findall(r"[A-Z][A-Z0-9_]{5,}", text))
        doc = frontier()
        leaked = []
        for m in doc["game_modes"]:
            for mid in m.get("mode_only_modifiers", []):
                if mid in prod_ids:
                    leaked.append((m["id"], mid))
        self.assertEqual(leaked, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
