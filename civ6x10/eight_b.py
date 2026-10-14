"""Phase 8B manifest construction (Playtest-1 closure coverage expansion).

Builds new machine-readable manifests + SQL from the official DB copy and
patches vector rows in the existing wonders/traits manifests. Every row
carries human-certified confidence + provenance; the certification gate
(civ6x10.certification) still admits or refuses each row independently --
this module proposes, the gate disposes. Anything the gate cannot certify
fails the generation loudly (SemanticConflict), never silently.

Manifests written here (all gitignored local inputs to generate-registry):
  manifests/slots.yml       REPEAT slot-copy rows (module wonders/traits)
  manifests/envoys.yml      token-gated envoy-tier leaves (module suzerain)
  manifests/promotions.yml  promotion/ability magnitudes (module promotions)
  manifests/dedications.yml commemoration magnitudes (module dedications)
  manifests/modes.yml       game-mode magnitudes (module modes)

SQL written here (committed controller content, regenerated):
  controller/X10/Config/X10SlotCopies.sql   inert slot copies + fillers

Patches applied to existing manifests (re-applied after any regen):
  wonders.yml / traits.yml vector Amount rows -> vector_multiply
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "local" / "DebugGameplay_official.sqlite"

# SSO inline capacity (chars) from the native profile (X10Compat.h:
# ssoInlineThreshold 0x10). SsoWrite refuses longer replacements, so a
# scaled vector that cannot fit at high k can never apply at any k.
SSO_INLINE_CAP = 16

INERT_SLOT = "SLOT_NONE"


def open_db() -> sqlite3.Connection:
    if not DB_PATH.is_file():
        raise FileNotFoundError(
            f"official DB copy unavailable: {DB_PATH} (local-only)")
    db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def base_covered_keys() -> tuple[set, dict]:
    """(modifier_id, argument) keys already owned by base manifests.

    A mode/sweep/promotion row repeating a base-covered key is the SAME
    official definition, not new coverage: the base module owns it, so the
    new row is skipped (recorded) instead of unioning owners (which would
    wrongly gate base behavior behind the new module). Genuine disagreements
    (same key, different official) still fail loud in production.
    """
    import yaml
    keys: set = set()
    owners: dict = {}
    for module in ("traits", "policies", "governments", "pantheons",
                   "wonders", "governors", "suzerain"):
        path = ROOT / "manifests" / f"{module}.yml"
        if not path.is_file():
            continue
        doc = yaml.safe_load(open(path, encoding="utf-8"))
        for r in doc[module]:
            keys.add((r["modifier_id"], r["argument_name"]))
            owners[(r["modifier_id"], r["argument_name"])] = module
    return keys, owners


def manifest_rows_for_modifier(db: sqlite3.Connection, modifier_id: str,
                               object_id: str) -> list[dict]:
    """Raw inventory rows (one per ModifierArgument) for a ModifierId."""
    m = db.execute(
        "SELECT ModifierType FROM Modifiers WHERE ModifierId = ?",
        (modifier_id,)).fetchone()
    if m is None:
        raise KeyError(f"unknown ModifierId: {modifier_id}")
    effs = db.execute(
        "SELECT EffectType FROM DynamicModifiers WHERE ModifierType = ?",
        (m["ModifierType"],)).fetchall()
    effect = effs[0]["EffectType"] if effs else "UNKNOWN_NO_DYNAMIC"
    rows = []
    for a in db.execute(
            "SELECT Name,Value FROM ModifierArguments WHERE ModifierId = ?",
            (modifier_id,)).fetchall():
        rows.append({
            "object_id": object_id,
            "modifier_id": modifier_id,
            "modifier_type": m["ModifierType"],
            "effect_type": effect,
            "argument_name": a["Name"],
            "official_value": a["Value"],
            "argument_value": a["Value"],
        })
    return rows


# --------------------------------------------------------------------------
# Vectors: patch Amount rows in wonders.yml / traits.yml.
# --------------------------------------------------------------------------

VECTOR_FAMILY_BY_EFFECT = {
    "EFFECT_ADJUST_PLOT_YIELD": "FLAT_YIELD",
    "EFFECT_ADJUST_CITY_YIELD_MODIFIER": "PERCENT_BONUS",
    "EFFECT_ADJUST_PLAYER_INTERNATIONAL_TRADE_ROUTE_YIELD_MODIFIER":
        "PERCENT_BONUS",
}

VECTOR_AMOUNT_IDS = {
    "PETRA_YIELD_MODIFIER",
    "HALICARNASSUS_MAUSOLEUM_YIELD_MODIFIER",
    "CLEOPATRA_FLOODPLAINS_RESOURCE_YIELD",
    "TRAIT_SULEIMAN_ALT_SCIENCE_CULTURE_GOLDEN_AGE",
    "TRAIT_SAME_CONTINENT_YIELD",
    "TRAIT_FOREIGN_CONTINENT_YIELD",
    "TRAIT_LEADER_NEARBY_CITIES_GAIN_YIELDS",
    "TRAIT_LEADER_NEARBY_CITIES_LOSE_YIELDS",
    "TRAIT_INTERNATIONAL_TRADE_GAIN_ALL_YIELDS",
    "TOKUGAWA_NEGATIVE_INTERNATIONAL_YIELDS",
}


def patch_vector_manifests() -> dict:
    """Set vector Amount rows to the vector_multiply pipeline.

    Six-element vectors are patched uniformly but the gate excludes them
    (value:vector-too-long): their high-k output cannot fit the SSO inline
    capacity, so they can never apply at any k. Short vectors certify.
    Returns counts per manifest.
    """
    import yaml
    from .transforms import vector_multiply
    counts = {}
    for manifest, key in (("wonders", "wonders"), ("traits", "traits")):
        path = ROOT / "manifests" / f"{manifest}.yml"
        doc = yaml.safe_load(open(path, encoding="utf-8"))
        n = 0
        for r in doc[key]:
            if r["modifier_id"] in VECTOR_AMOUNT_IDS \
                    and r["argument_name"] == "Amount":
                fam = VECTOR_FAMILY_BY_EFFECT.get(r["effect_type"],
                                                  "FLAT_YIELD")
                r["semantic_family"] = fam
                r["transformation"] = "vector_multiply"
                r["generated_value"] = vector_multiply(
                    r["official_value"], 10.0)
                r["status"] = "ok"
                r["confidence"] = "human_certified_8b_vector"
                n += 1
        counts[manifest] = n
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            yaml.safe_dump(doc, fh, sort_keys=False, allow_unicode=True)
    return counts


# Base slot grants: (base_modifier_id, slot_type, attach_kind, attach_id,
# module). GREATPERSON_ECONOMIC_POLICY_SLOT is an orphan (no attach row in
# any link table) and is skipped with reason in docs/PHASE_8B.md.
SLOT_BASES = [
    ("POTALA_PALACE_DIPLOMATIC_GOVERNMENT_SLOT", "SLOT_DIPLOMATIC",
     "building", "BUILDING_POTALA_PALACE", "wonders"),
    ("FORBIDDEN_CITY_WILDCARD_GOVERNMENT_SLOT", "SLOT_WILDCARD",
     "building", "BUILDING_FORBIDDEN_CITY", "wonders"),
    ("ALHAMBRA_MILITARY_GOVERNMENT_SLOT", "SLOT_MILITARY",
     "building", "BUILDING_ALHAMBRA", "wonders"),
    ("BIG_BEN_ECONOMIC_GOVERNMENT_SLOT", "SLOT_ECONOMIC",
     "building", "BUILDING_BIG_BEN", "wonders"),
    ("TRAIT_ECONOMIC_GOVERNMENT_SLOT", "SLOT_ECONOMIC",
     "trait", "TRAIT_LEADER_KUBLAI", "traits"),
    ("TRAIT_MILITARY_GOVERNMENT_SLOT", "SLOT_MILITARY",
     "trait", "TRAIT_LEADER_HOLY_ROMAN_EMPEROR", "traits"),
    ("TRAIT_WILDCARD_GOVERNMENT_SLOT", "SLOT_WILDCARD",
     "trait", "TRAIT_CIVILIZATION_PLATOS_REPUBLIC", "traits"),
]

SLOT_MODIFIER_TYPE = "MODIFIER_PLAYER_CULTURE_ADJUST_GOVERNMENT_SLOTS_MODIFIER"
SLOT_EFFECT = "EFFECT_ADJUST_PLAYER_GOVERNMENT_SLOT_TYPE"

# Copies N=2..100: at integral k, copies with N<=k activate (base + N-1
# copies = N slots); fractional k activates none (single vanilla slot).
SLOT_COPY_MAX = 100

# Typed filler policies (Phase 8B.1 correction of the 8B wildcard error).
#
# GovernmentSlots.AllowsAnyPolicy is SLOT-side: a WILDCARD slot accepts any
# card, but a SLOT_WILDCARD policy fits ONLY wildcard slots. The 8B comment
# claiming "wildcard cards can occupy any slot type" was backwards: 99
# wildcard fillers could never fill Potala diplomatic, Alhambra military,
# or Big Ben economic bonus slots. Fillers are therefore typed per slot;
# a typed card fills its own slot type plus wildcard slots.
#
# Counts cover the maximum simultaneous bonus slots per type at every
# supported preset with zero real cards assumed (absolute worst case):
# military 2 sources (Alhambra + HRE) x100 = 200, diplomatic 1 source
# (Potala) x100 = 100, economic 2 sources (Big Ben + Kublai) x100 = 200,
# wildcard 2 sources (Forbidden City + Plato) x100 = 200.
#
# Phase 8B.4 (P0B hard fail: 700 Code-of-Laws cards flood the picker):
# fillers ship DORMANT -- ExplicitUnlock=1 with NO civic prerequisite
# (NULL PrereqCivic has 22 official precedents: government/special
# policies unlocked by other means). Nothing unlocks them except the
# X10 on-demand slot manager (controller/X10/UI/X10SlotManager.lua),
# which unlocks only the deficit for the player's CURRENT slots.
# One shared name/description pair (LOC_POLICY_X10_FILLER_NAME/DESC,
# loaded InGame via X10GameText.sql).
FILLER_COUNTS = {
    "SLOT_MILITARY": 200,
    "SLOT_DIPLOMATIC": 100,
    "SLOT_ECONOMIC": 200,
    "SLOT_WILDCARD": 200,
}
FILLER_PREFIX = "POLICY_X10_FILLER_"


def slot_copy_id(base: str, n: int) -> str:
    return f"{base}_X10R{n:03d}"


def build_slot_manifest_rows() -> list[dict]:
    """REPEAT manifest rows for every inert slot copy."""
    rows = []
    for base, slot, kind, attach_id, module in SLOT_BASES:
        obj = attach_id
        for n in range(2, SLOT_COPY_MAX + 1):
            rows.append({
                "object_id": obj,
                "modifier_id": slot_copy_id(base, n),
                "modifier_type": SLOT_MODIFIER_TYPE,
                "effect_type": SLOT_EFFECT,
                "argument_name": "GovernmentSlotType",
                "official_value": INERT_SLOT,
                "semantic_family": "STRUCTURAL_SLOT",
                "transformation": "repeat_count",
                "generated_value": "10",
                "status": "ok",
                "confidence": "human_certified_8b_slots",
                "certification_source": "phase8b-slots-audit",
                "module": module,
                "copy_index": n,
                "repeat_target": slot,
                "slot_base": base,
            })
    return rows


def write_slots_manifest(rows: list[dict]) -> Path:
    import yaml
    path = ROOT / "manifests" / "slots.yml"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump({"slots": rows}, fh, sort_keys=False,
                       allow_unicode=True)
    return path


def emit_slot_sql() -> str:
    """Inert slot copies + typed filler policies (guarded, idempotent).

    Copies are inert by default (GovernmentSlotType=SLOT_NONE, a
    ModifierArguments value no government screen honors): module-off /
    invalid-k sessions keep the single vanilla slot. The native REPEAT
    kind rewrites copies N<=k to the real slot type. SLOT_NONE tolerance
    (engine ignores the unknown slot value without granting anything) is
    covered by the Playtest-2 P0 boot smoke; see docs/PHASE_8B.md.
    Fillers are effect-free typed policies, dormant by default
    (ExplicitUnlock, no civic): the on-demand slot manager unlocks only
    the deficit for the player's current slots, so the confirm gate
    (all slots must be filled before policies can be confirmed) can
    always be satisfied without flooding the picker.
    """
    chunks = [
        "-- GENERATED by civ6x10.eight_b from audited bonus-slot grants.",
        "-- Do not hand-edit. Regenerate: python -m civ6x10 build-8b-manifests",
        "-- Inert copies (SLOT_NONE): activated only by the native REPEAT",
        "-- kind for copies N <= integral k. Filler policies are effect-free",
        "-- typed cards (shared LOC in X10Text.sql) so multiplied bonus",
        "-- slots can always be filled and policies confirmed.",
        "",
    ]
    for base, slot, kind, attach_id, module in SLOT_BASES:
        link_table = "BuildingModifiers" if kind == "building" \
            else "TraitModifiers"
        link_col = "BuildingType" if kind == "building" else "TraitType"
        chunks.append(f"-- {base} ({slot}): 99 inert copies")
        for n in range(2, SLOT_COPY_MAX + 1):
            cid = slot_copy_id(base, n)
            guard = (
                f"EXISTS (SELECT 1 FROM Modifiers WHERE ModifierId = '{base}')"
                f"\n  AND EXISTS (SELECT 1 FROM {link_table}"
                f" WHERE {link_col} = '{attach_id}'"
                f" AND ModifierId = '{base}')")
            chunks.append(
                "INSERT INTO Modifiers (ModifierId, ModifierType, RunOnce,"
                " NewOnly, Permanent, Repeatable)\n"
                f"SELECT '{cid}', '{SLOT_MODIFIER_TYPE}', 0, 0, 0, 0\n"
                f"WHERE NOT EXISTS (SELECT 1 FROM Modifiers"
                f" WHERE ModifierId = '{cid}')\n  AND {guard};")
            chunks.append(
                f"INSERT INTO {link_table} ({link_col}, ModifierId)\n"
                f"SELECT '{attach_id}', '{cid}'\n"
                f"WHERE NOT EXISTS (SELECT 1 FROM {link_table}"
                f" WHERE {link_col} = '{attach_id}'"
                f" AND ModifierId = '{cid}')\n  AND {guard};")
            chunks.append(
                "INSERT INTO ModifierArguments (ModifierId, Name, Type,"
                " Value)\n"
                f"SELECT '{cid}', 'GovernmentSlotType', 'ARGTYPE_IDENTITY',"
                f" '{INERT_SLOT}'\n"
                f"WHERE NOT EXISTS (SELECT 1 FROM ModifierArguments"
                f" WHERE ModifierId = '{cid}'"
                f" AND Name = 'GovernmentSlotType')\n  AND {guard};")
        chunks.append("")
    chunks.append("-- Typed filler policies (DORMANT: ExplicitUnlock, no civic).")
    for slot, count in FILLER_COUNTS.items():
        short = slot.replace("SLOT_", "")
        chunks.append(f"-- {short}: {count} fillers")
        for i in range(1, count + 1):
            pid = f"{FILLER_PREFIX}{short}_{i:03d}"
            chunks.append(
                "INSERT INTO Types (Type, Kind)\n"
                f"SELECT '{pid}', 'KIND_POLICY'\n"
                f"WHERE NOT EXISTS (SELECT 1 FROM Types"
                f" WHERE Type = '{pid}');")
            chunks.append(
                "INSERT INTO Policies (PolicyType, Description, PrereqCivic,"
                " Name, GovernmentSlotType, ExplicitUnlock)\n"
                f"SELECT '{pid}', 'LOC_POLICY_X10_FILLER_DESC',"
                f" NULL, 'LOC_POLICY_X10_FILLER_NAME',"
                f" '{slot}', 1\n"
                f"WHERE NOT EXISTS (SELECT 1 FROM Policies"
                f" WHERE PolicyType = '{pid}');")
    chunks.append("")
    return "\n".join(chunks)


def write_slot_sql() -> Path:
    path = ROOT / "controller" / "X10" / "Config" / "X10SlotCopies.sql"
    path.write_text(emit_slot_sql(), encoding="utf-8", newline="\n")
    return path


# Generic city-state type traits: 1/3/6-envoy tier wrappers attach leaf
# magnitudes. Minor-owned always-on rows (district-production 500,
# send-trade-route bonus) are NOT player envoy rewards and are never
# swept in (documented in docs/PHASE_8B.md).
ENVOY_TYPE_TRAITS = (
    "MINOR_CIV_TRADE_TRAIT",
    "MINOR_CIV_SCIENTIFIC_TRAIT",
    "MINOR_CIV_CULTURAL_TRAIT",
    "MINOR_CIV_INDUSTRIAL_TRAIT",
    "MINOR_CIV_MILITARISTIC_TRAIT",
    "MINOR_CIV_RELIGIOUS_TRAIT",
)

# Wrapper gates proving an envoy tier (subject requirement sets).
ENVOY_TIER_BY_SET = {
    "PLAYER_HAS_SMALL_INFLUENCE": 1,
    "PLAYER_HAS_MEDIUM_INFLUENCE": 3,
    "PLAYER_HAS_LARGE_INFLUENCE": 6,
    "PLAYER_HAS_LARGE_INFLUENCE_AND_PAPAL_PRIMACY": 6,
}


def build_envoy_manifest_rows(db) -> tuple[list[dict], list[str]]:
    """Leaf rows for token-gated envoy tiers + notes for review.

    Only wrappers whose subject set is an envoy-tier gate are followed;
    the wrapper itself (ATTACH + ModifierId arg) is attach metadata, never
    a magnitude. Returns (rows, notes) where notes record every skipped
    wrapper/leaf and why.
    """
    from .modules import build_manifest
    rows: list[dict] = []
    notes: list[str] = []
    for trait in ENVOY_TYPE_TRAITS:
        wrappers = db.execute(
            "SELECT ModifierId FROM TraitModifiers WHERE TraitType = ?",
            (trait,)).fetchall()
        for (wid,) in wrappers:
            m = db.execute(
                "SELECT ModifierType,SubjectRequirementSetId"
                " FROM Modifiers WHERE ModifierId = ?", (wid,)).fetchone()
            if m is None:
                notes.append(f"{trait}: wrapper {wid} has no Modifiers row")
                continue
            if m["ModifierType"] != "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER":
                notes.append(
                    f"{trait}: non-wrapper {wid} ({m['ModifierType']})"
                    " is minor-owned, not a player envoy reward")
                continue
            tier = ENVOY_TIER_BY_SET.get(m["SubjectRequirementSetId"] or "")
            if tier is None:
                notes.append(
                    f"{trait}: wrapper {wid} gate "
                    f"{m['SubjectRequirementSetId']} is not an envoy tier")
                continue
            target = db.execute(
                "SELECT Value FROM ModifierArguments WHERE ModifierId = ?"
                " AND Name = 'ModifierId'", (wid,)).fetchone()
            if target is None:
                notes.append(f"{trait}: wrapper {wid} has no target")
                continue
            leaf = target["Value"]
            raws = manifest_rows_for_modifier(db, leaf, trait)
            for r in raws:
                r["envoy_tier"] = tier
                r["root_trait"] = trait
                r["root_wrapper"] = wid
            for h in build_manifest(raws, "object_id"):
                if h["transformation"] == "unchanged":
                    continue  # attach metadata / selectors
                if h["status"] != "ok":
                    notes.append(
                        f"{trait}: leaf {leaf} arg {h['argument_name']} "
                        f"status {h['status']} (left out)")
                    continue
                h["module"] = "suzerain"
                h["confidence"] = "human_certified_8b_envoy"
                h["certification_source"] = "phase8b-envoy-audit"
                rows.append(h)
    return rows, notes


def write_envoy_manifest(rows: list[dict]) -> Path:
    import yaml
    path = ROOT / "manifests" / "envoys.yml"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump({"envoys": rows}, fh, sort_keys=False,
                       allow_unicode=True)
    return path


# (effect, argument) -> (family, transformation) patches applied to
# build_manifest output for rows the heuristic leaves undecided. Only
# reviewed magnitudes are listed; everything else undecided stays out,
# and boolean flags are normalized to unchanged (reviewed, not scaled).
PROMOTION_PATCHES = {
    # Spy chances/times: curated probability/discount evidence.
    ("EFFECT_ADJUST_UNIT_SPY_OPERATION_CHANCE", "Amount"):
        ("PROBABILITY", "repeated_probability"),
    ("EFFECT_ADJUST_UNIT_SPY_OPERATION_TIME", "ReductionPercent"):
        ("DISCOUNT", "compound_discount"),
    ("EFFECT_ADJUST_UNIT_SPY_ESTABLISH_TIME", "ReductionPercent"):
        ("DISCOUNT", "compound_discount"),
    ("EFFECT_ADJUST_UNIT_SPY_OFFENSIVE_OPERATION_TIME", "ReductionPercent"):
        ("DISCOUNT", "compound_discount"),
    # Post-combat percent yields share the reviewed percent semantics.
    ("EFFECT_ADJUST_UNIT_POST_COMBAT_YIELD", "PercentDefeatedStrength"):
        ("DEFEATED_STRENGTH_SCALING", "canonical_x10_multiply"),
    # WMD protection percents are flat magnitudes.
    ("EFFECT_ADJUST_UNIT_WMD_PROTECTION", "Blast"):
        ("PERCENT_BONUS", "canonical_x10_multiply"),
    ("EFFECT_ADJUST_UNIT_WMD_PROTECTION", "Fallout"):
        ("PERCENT_BONUS", "canonical_x10_multiply"),
    # Coastal-raid loot gold is a flat magnitude.
    ("EFFECT_ADJUST_UNIT_RAIDING", "Bonus"):
        ("FLAT_AMOUNT", "canonical_x10_multiply"),
    # Tourism-bomb range penalty is a flat magnitude (SPATIAL floor is
    # the range filter, reviewed 8B).
    ("EFFECT_ADJUST_UNIT_TOURISM_BOMB_RANGE", "Modifier"):
        ("FLAT_AMOUNT", "canonical_x10_multiply"),
    # Great-People-points per kill are whole points (count-like).
    ("EFFECT_ADJUST_GREAT_PEOPLE_POINTS_PER_KILL_BY_DEFEATED_STRENGTH",
     "Amount"):
        ("GREAT_PERSON_POINTS", "canonical_x10_multiply"),
}

# Status-ok rows that must stay unscaled (reviewed non-magnitudes the
# heuristic calls ok, e.g. spy Offensive flags).
FORCE_UNCHANGED = {
    ("EFFECT_ADJUST_UNIT_SPY_OPERATION_CHANCE", "Offensive"),
}

# Reviewed non-magnitudes (boolean/capability flags, era filters):
# normalized to unchanged so the ledger records the decision instead of
# "undecided".
NON_MAGNITUDE_ARGS = {
    "Ignore", "Exert", "CanMove", "CanAttack", "CanFight", "CanRaid",
    "CanCapture", "CanDrop", "CanSee", "SeeHidden", "Hidden", "Disable",
    "Enable", "Bypass", "Enter", "Converts", "Convert", "NoSpread",
    "NoReduction", "UseAdvancedPillaging", "UseAdvancedCoastalRaid",
    "LandVictorySpread", "Offensive", "Defense", "EscortMobility",
    "ForceRetreat", "RelicSource", "AllowUniqueOverride",
    "StartEra", "EndEra", "IsWonder", "BoostsWonders", "EntireCity",
    "Key", "Max", "ForeignCities", "NotSpecialty", "Intercontinental",
    "Neutralize", "KeepOverflow", "UniqueOverride", "DistanceChange",
    "SpreadMultiplier", "TechEnabledSpreadMultiplier",
}

# Mode magnitudes with reviewed per-modifier disposition. PROPERTY-keyed
# mechanics (resurrect flags, teleport enables, favor multipliers) are
# capabilities/settings, never magnitudes; hero era-strength progression
# is a base combat stat, never a bonus.
MODE_FORCE_UNCHANGED_IDS = {
    "POLICY_POPULAR_FRONT_ALLIANCE_FAVOR",
    "SECRET_SOCIETIES_ATTACH_PLAYER_CASTLES_TELEPORT",
    "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_1_ENVOY_FROM_TRADE_ROUTE",
    "MODIFIER_QUESTING_KNIGHT_ERA_STRENGTH",
    "MODIFIER_HUNAHPU_RESURRECT_KILL",
    "MODIFIER_MULAN_FORTIFY",
    "TRAIT_GOLDEN_AGE_UNLOCK_DARK_POLICIES",
    "POLICY_SAKDINA_PROJECT_POINTS_MULTIPLIER",
}

MODE_PATCHES = {
    # Dramatic-age wonder tourism factor shares the reviewed percent
    # semantics of the base-game tourism factor.
    ("EFFECT_ADJUST_CITY_TOURISM", "ScalingFactor"):
        ("PERCENT_BONUS", "canonical_x10_multiply"),
}

# Base unit stats and ambiguous progression knobs: excluded with reason
# (documented in docs/PHASE_8B.md), never patched in.
PROMOTION_EXCLUDED_MODIFIERS = {
    # Base combat strength is a stat, not a bonus (§8/§10).
    "MODIFIER_UNIT_ADJUST_BASE_COMBAT_STRENGTH",
}


def _promotion_name(db, link_table, modifier_id):
    id_col = "UnitPromotionType" if "Promotion" in link_table \
        else "UnitAbilityType"
    name_col = "UnitPromotionType" if "Promotion" in link_table \
        else "UnitAbilityType"
    rows = db.execute(
        f"SELECT {id_col} FROM {link_table} WHERE ModifierId = ?",
        (modifier_id,)).fetchall()
    return sorted(r[0] for r in rows)


def build_promotion_manifest_rows(db) -> tuple[list[dict], list[str]]:
    """Sweep promotion + ability modifiers with per-row disposition."""
    from .modules import build_manifest, apply_transform, apply_dynamic
    rows: list[dict] = []
    notes: list[str] = []
    seen_mods: dict[str, str] = {}
    for link in ("UnitPromotionModifiers", "UnitAbilityModifiers"):
        for (mid,) in db.execute(
                f"SELECT DISTINCT ModifierId FROM {link}").fetchall():
            try:
                raws = manifest_rows_for_modifier(db, mid, link)
            except KeyError:
                notes.append(f"{link}: {mid} has no Modifiers row (skip)")
                continue
            mtype = raws[0]["modifier_type"] if raws else "?"
            if mtype in PROMOTION_EXCLUDED_MODIFIERS:
                notes.append(
                    f"{link}: {mid} ({mtype}) excluded: base unit stat")
                continue
            names = _promotion_name(db, link, mid)
            for r in raws:
                r["promotion_names"] = names
                r["promotion_link"] = link
            for h in build_manifest(raws, "object_id"):
                key = (h["effect_type"], h["argument_name"])
                if key in PROMOTION_PATCHES:
                    # Reviewed disposition overrides the heuristic, even
                    # when the heuristic already yields status ok (e.g.
                    # Wolin GPP-per-kill is GREAT_PERSON_POINTS, not a
                    # defeated-strength factor).
                    fam, tr = PROMOTION_PATCHES[key]
                    h["semantic_family"] = fam
                    h["transformation"] = tr
                    h["generated_value"], h["status"] = \
                        apply_transform(tr, h["official_value"])
                    h["confidence"] = "human_certified_8b_promotion"
                    h["module"] = "promotions"
                    if h["status"] == "ok":
                        rows.append(h)
                        continue
                    notes.append(f"{link}: {mid} {key} patch failed (out)")
                    continue
                if key in FORCE_UNCHANGED and h["status"] == "ok":
                    h["transformation"] = "unchanged"
                    h["generated_value"] = h["official_value"]
                    h["confidence"] = "human_certified_8b_reviewed"
                    h["module"] = "promotions"
                    rows.append(h)
                    continue
                if key == ("EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER",
                           "Amount") and h["status"] != "ok":
                    # Negative combat officials are debuff magnitudes: the
                    # tenfold formula is undefined for them, so they scale
                    # flat (certified ADDITIVE by the negative-combat gate).
                    try:
                        neg = float(h["official_value"]) < 0
                    except (TypeError, ValueError):
                        neg = False
                    if neg:
                        h["semantic_family"] = "FLAT_AMOUNT"
                        h["transformation"] = "canonical_x10_multiply"
                        h["generated_value"], h["status"] = \
                            apply_transform("canonical_x10_multiply",
                                            h["official_value"])
                        h["confidence"] = "human_certified_8b_promotion"
                        h["module"] = "promotions"
                        if h["status"] == "ok":
                            rows.append(h)
                            continue
                        notes.append(f"{link}: {mid} {key} patch failed")
                        continue
                if h["transformation"] == "unchanged":
                    h["confidence"] = "human_certified_8b_reviewed"
                    h["module"] = "promotions"
                    rows.append(h)
                    continue
                if h["status"] != "ok":
                    if h["argument_name"] in NON_MAGNITUDE_ARGS:
                        h["transformation"] = "unchanged"
                        h["generated_value"] = h["official_value"]
                        h["status"] = "ok"
                        h["confidence"] = \
                            "human_certified_8b_boolean"
                        h["module"] = "promotions"
                        rows.append(h)
                        continue
                    notes.append(
                        f"{link}: {mid} {key} status {h['status']} (out)")
                    continue
                h["module"] = "promotions"
                if h["confidence"] == "auto_rule":
                    h["confidence"] = "human_certified_8b_promotion"
                rows.append(h)
    return rows, notes


def write_promotion_manifest(rows: list[dict]) -> Path:
    import yaml
    path = ROOT / "manifests" / "promotions.yml"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump({"promotions": rows}, fh, sort_keys=False,
                       allow_unicode=True)
    return path


DEDICATION_PATCHES = {
    # Wonder-tourism scaling factor is percent-scale (reviewed 8B).
    ("EFFECT_ADJUST_CITY_TOURISM", "ScalingFactor"):
        ("PERCENT_BONUS", "canonical_x10_multiply"),
    # Spy time reductions share the promotion disposition.
    ("EFFECT_ADJUST_UNIT_SPY_ESTABLISH_TIME", "ReductionPercent"):
        ("DISCOUNT", "compound_discount"),
    ("EFFECT_ADJUST_UNIT_SPY_OFFENSIVE_OPERATION_TIME", "ReductionPercent"):
        ("DISCOUNT", "compound_discount"),
}

# Commemoration ATTACH wrappers resolve one hop to their leaf magnitudes.
# Wrappers themselves are attach metadata, never magnitudes.
DEDICATION_ATTACH_TABLE = "CommemorationModifiers"


def build_dedication_manifest_rows(db) -> tuple[list[dict], list[str]]:
    """Sweep commemoration modifiers (+ one ATTACH hop) with disposition."""
    from .modules import build_manifest, apply_transform
    rows: list[dict] = []
    notes: list[str] = []
    mids = [r[0] for r in db.execute(
        "SELECT DISTINCT ModifierId FROM CommemorationModifiers").fetchall()]
    # One ATTACH hop: wrapper targets join the sweep with provenance.
    extra: dict[str, str] = {}
    for mid in list(mids):
        m = db.execute(
            "SELECT ModifierType FROM Modifiers WHERE ModifierId = ?",
            (mid,)).fetchone()
        if m is None:
            continue
        eff = db.execute(
            "SELECT EffectType FROM DynamicModifiers WHERE ModifierType = ?",
            (m["ModifierType"],)).fetchall()
        if any(e[0] == "EFFECT_ATTACH_MODIFIER" for e in eff):
            tgt = db.execute(
                "SELECT Value FROM ModifierArguments WHERE ModifierId = ?"
                " AND Name = 'ModifierId'", (mid,)).fetchone()
            if tgt is not None:
                extra[tgt["Value"]] = mid
    # Sweep each modifier (wrappers resolve via `extra` provenance below).
    for mid in mids + [t for t in extra if t not in mids]:
        try:
            raws = manifest_rows_for_modifier(db, mid, "Commemoration")
        except KeyError:
            notes.append(f"dedications: {mid} has no Modifiers row (skip)")
            continue
        ctype = db.execute(
            "SELECT CommemorationType FROM CommemorationModifiers"
            " WHERE ModifierId = ?", (mid,)).fetchone()
        ctype = ctype[0] if ctype else f"attach-target-of-{extra.get(mid, '?')}"
        for r in raws:
            r["root_commemoration"] = ctype
        for h in build_manifest(raws, "object_id"):
            key = (h["effect_type"], h["argument_name"])
            if key in DEDICATION_PATCHES:
                fam, tr = DEDICATION_PATCHES[key]
                h["semantic_family"] = fam
                h["transformation"] = tr
                h["generated_value"], h["status"] = \
                    apply_transform(tr, h["official_value"])
                h["confidence"] = "human_certified_8b_dedication"
                h["module"] = "dedications"
                if h["status"] == "ok":
                    rows.append(h)
                    continue
                notes.append(f"dedications: {mid} {key} patch failed")
                continue
            if h["transformation"] == "unchanged":
                h["confidence"] = "human_certified_8b_reviewed"
                h["module"] = "dedications"
                rows.append(h)
                continue
            if h["status"] != "ok":
                if h["argument_name"] in NON_MAGNITUDE_ARGS:
                    h["transformation"] = "unchanged"
                    h["generated_value"] = h["official_value"]
                    h["status"] = "ok"
                    h["confidence"] = "human_certified_8b_boolean"
                    h["module"] = "dedications"
                    rows.append(h)
                    continue
                notes.append(
                    f"dedications: {mid} {key} status {h['status']} (out)")
                continue
            h["module"] = "dedications"
            if h["confidence"] == "auto_rule":
                h["confidence"] = "human_certified_8b_dedication"
            rows.append(h)
    return rows, notes


def write_dedication_manifest(rows: list[dict]) -> Path:
    import yaml
    path = ROOT / "manifests" / "dedications.yml"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump({"dedications": rows}, fh, sort_keys=False,
                       allow_unicode=True)
    return path


import re
import xml.etree.ElementTree as ET
from pathlib import Path

# Civ VI install root (read-only parsing of shipped mode overlays).
INSTALL_ROOT = Path(
    "C:/Program Files (x86)/Steam/steamapps/common"
    "/Sid Meier's Civilization VI")

# Mode overlay files actually parsed (from spike/8a-frontier/modes.json;
# Data-layer gameplay files only, not Text/UI).
MODE_FILES = {
    "monopolies": [
        "DLC/KublaiKhan_Vietnam/Data/KublaiKhan_Vietnam_Monopolies_MODE.xml",
        "DLC/KublaiKhan_Vietnam/Data/KublaiKhan_Vietnam_Monopolies_XP1_MODE.xml",
        "DLC/KublaiKhan_Vietnam/Data/KublaiKhan_Vietnam_Monopolies_XP2_MODE.xml",
        "DLC/KublaiKhan_Vietnam/Data/KublaiKhan_Vietnam_Monopolies_GranColombiaMaya_MODE.xml",
    ],
    "heroes": [
        "DLC/Babylon/Data/Babylon_Heroes_MODE.xml",
        "DLC/Babylon/Data/Babylon_Heroes_XP1_MODE.xml",
        "DLC/Babylon/Data/Babylon_Heroes_XP2_MODE.xml",
        "DLC/Babylon/Data/Babylon_Heroes_IndonesiaKhmer_MODE.xml",
        "DLC/Babylon/Data/Babylon_Heroes_IndonesiaKhmer_XP1_MODE.xml",
        "DLC/Babylon/Data/Babylon_Heroes_IndonesiaKhmer_XP2_MODE.xml",
        "DLC/Babylon/Data/Babylon_Heroes_Poland_MODE.xml",
        "DLC/Babylon/Data/Babylon_Heroes_SecretSocieties_MODE.xml",
    ],
    "dramatic": [
        "DLC/Byzantium_Gaul/Data/Byzantium_Gaul_DramaticAges_MODE.xml",
        "DLC/Byzantium_Gaul/Data/Byzantium_Gaul_DramaticAges_Georgia_MODE.xml",
        "DLC/Byzantium_Gaul/Data/Byzantium_Gaul_DramaticAges_Expansion1_MODE.xml",
        "DLC/Byzantium_Gaul/Data/Byzantium_Gaul_DramaticAges_Expansion2_MODE.xml",
    ],
    "secretsocieties": [
        "DLC/Ethiopia/Data/Ethiopia_SecretSocieties_MODE.xml",
        "DLC/Ethiopia/Data/Ethiopia_SecretSocieties_Expansion1_MODE.xml",
        "DLC/Ethiopia/Data/Ethiopia_SecretSocieties_Expansion2_MODE.xml",
        "DLC/Ethiopia/Data/Ethiopia_SecretSocieties_GranColombiaMaya_MODE.xml",
        "DLC/Byzantium_Gaul/Data/Byzantium_Gaul_SecretSocieties_MODE.xml",
    ],
    "apocalypse": [
        "DLC/GranColombia_Maya/Data/GranColombia_Maya_Emergencies_MODE.xml",
        "DLC/GranColombia_Maya/Data/GranColombia_Maya_RandomEvents_MODE.xml",
        "DLC/GranColombia_Maya/Data/GranColombia_Maya_RandomEvents_Vikings_MODE.xml",
        "DLC/GranColombia_Maya/Data/GranColombia_Maya_UnitOperations_MODE.xml",
        "DLC/GranColombia_Maya/Data/GranColombia_Maya_UnitPromotions_MODE.xml",
        "DLC/GranColombia_Maya/Data/GranColombia_Maya_Units_MODE.xml",
    ],
    "zombie": [
        "DLC/VikingsLandmarks/Data/VikingsLandmarks_TowerDefense_MODE.xml",
    ],
    "barbarians": [
        "DLC/Portugal/Data/Portugal_Barbarians_MODE.xml",
    ],
    "shuffle": [
        "DLC/TreeRandomizer/Data/TreeRandomizer_Technologies_MODE.xml",
        "DLC/TreeRandomizer/Data/TreeRandomizer_Civics_MODE.xml",
        "DLC/TreeRandomizer/Data/TreeRandomizer_Expansion2_MODE.xml",
    ],
}

# Attach tables swept for mode magnitudes (link table -> object id column).
MODE_ATTACH_TABLES = {
    "BuildingModifiers": "BuildingType",
    "PolicyModifiers": "PolicyType",
    "TraitModifiers": "TraitType",
    "ProjectCompletionModifiers": "ProjectType",
    "GreatWorkModifiers": "GreatWorkType",
    "UnitAbilityModifiers": "UnitAbilityType",
    "GameModifiers": "Game",
}


def _row_dict(elem):
    out = {}
    # Attribute-style rows (<Row ModifierId="..." .../>) and element-style
    # rows (<Row><ModifierId>...</ModifierId></Row>) both occur in shipped
    # overlays; attributes win on collision (they carry the full row).
    for k, v in elem.attrib.items():
        out[k] = v.strip()
    # Attribute casing varies by file (ModifierID vs ModifierId).
    if "ModifierID" in out and "ModifierId" not in out:
        out["ModifierId"] = out.pop("ModifierID")
    for child in elem:
        tag = child.tag
        if tag in ("Row", "Update", "Delete", "Replace"):
            continue
        text = child.text.strip() if child.text and child.text.strip() \
            else ""
        out.setdefault(tag, text)
    return out


def parse_mode_file(relpath):
    """Parse one overlay file into modifier tables (read-only)."""
    path = INSTALL_ROOT / relpath
    if not path.is_file():
        return None
    try:
        root = ET.parse(str(path)).getroot()
    except ET.ParseError:
        return None
    data = {"modifiers": {}, "args": {}, "dynamic": {}, "attach": {}}
    gameinfo = root.find("GameInfo")
    if gameinfo is None:
        gameinfo = root
    for table in gameinfo:
        name = table.tag
        if name == "Modifiers":
            for row in list(table.findall("Row")) + \
                    list(table.findall("Update")):
                d = _row_dict(row)
                if d.get("ModifierId"):
                    data["modifiers"][d["ModifierId"]] = d
        elif name == "ModifierArguments":
            for row in list(table.findall("Row")) + \
                    list(table.findall("Update")):
                d = _row_dict(row)
                if d.get("ModifierId"):
                    data["args"].setdefault(
                        d["ModifierId"], []).append(d)
        elif name == "DynamicModifiers":
            for row in table.findall("Row"):
                d = _row_dict(row)
                if d.get("ModifierType"):
                    data["dynamic"][d["ModifierType"]] = d
        elif name in MODE_ATTACH_TABLES:
            for row in table.findall("Row"):
                d = _row_dict(row)
                if d.get("ModifierId"):
                    data["attach"].setdefault(
                        d["ModifierId"], []).append(
                            (name, d))
    return data


def collect_mode_data():
    """Parse all configured overlay files -> per-mode data bundles."""
    bundle = {}
    for mode, files in MODE_FILES.items():
        mods, args, dyn, attach = {}, {}, {}, {}
        for rel in files:
            data = parse_mode_file(rel)
            if data is None:
                continue
            mods.update(data["modifiers"])
            for k, v in data["args"].items():
                args.setdefault(k, []).extend(v)
            dyn.update(data["dynamic"])
            for k, v in data["attach"].items():
                attach.setdefault(k, []).extend(v)
        bundle[mode] = {"modifiers": mods, "args": args, "dynamic": dyn,
                        "attach": attach}
    return bundle


def mode_official_leak(db, modifier_ids):
    """ModifierIds that ALSO exist in the clean official DB (leak risk)."""
    leaked = []
    for mid in modifier_ids:
        if db.execute("SELECT 1 FROM Modifiers WHERE ModifierId = ?",
                      (mid,)).fetchone():
            leaked.append(mid)
    return leaked


def build_mode_manifest_rows(db, bundle) -> tuple[list[dict], list[str]]:
    """Manifest rows for mode magnitudes with explicit disposition."""
    from .modules import build_manifest, apply_transform
    rows: list[dict] = []
    notes: list[str] = []
    for mode, data in bundle.items():
        leaked = set(mode_official_leak(db, data["modifiers"]))
        for mid, m in data["modifiers"].items():
            if mid in leaked:
                notes.append(
                    f"modes/{mode}: {mid} shared with standard game "
                    "(excluded: mode leakage risk)")
                continue
            mtype = m.get("ModifierType", "")
            dyn = data["dynamic"].get(mtype, {})
            effect = dyn.get("EffectType", "")
            if not effect:
                # Unknown carrier (base-game DynamicModifiers may define
                # it): resolve from the clean DB when possible.
                base = db.execute(
                    "SELECT EffectType FROM DynamicModifiers"
                    " WHERE ModifierType = ?", (mtype,)).fetchone()
                effect = base[0] if base else ""
            if not effect:
                notes.append(
                    f"modes/{mode}: {mid} carrier {mtype} has no known "
                    "EffectType (out)")
                continue
            obj = f"mode:{mode}"
            att = data["attach"].get(mid)
            if att:
                table, link = att[0]
                idcol = MODE_ATTACH_TABLES[table]
                obj = link.get(idcol, obj)
            raws = []
            for a in data["args"].get(mid, []):
                raws.append({
                    "object_id": obj,
                    "modifier_id": mid,
                    "modifier_type": mtype,
                    "effect_type": effect,
                    "argument_name": a.get("Name", ""),
                    "official_value": a.get("Value", ""),
                    "argument_value": a.get("Value", ""),
                    "mode": mode,
                    "mode_subject": m.get("SubjectRequirementSetId", ""),
                })
            for h in build_manifest(raws, "object_id"):
                key = (h["effect_type"], h["argument_name"])
                if key in MODE_PATCHES:
                    fam, tr = MODE_PATCHES[key]
                    h["semantic_family"] = fam
                    h["transformation"] = tr
                    h["generated_value"], h["status"] = \
                        apply_transform(tr, h["official_value"])
                    h["confidence"] = "human_certified_8b_mode"
                if mid in MODE_FORCE_UNCHANGED_IDS and h["status"] == "ok":
                    h["transformation"] = "unchanged"
                    h["generated_value"] = h["official_value"]
                    h["confidence"] = "human_certified_8b_mode_excluded"
                if key == ("EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER",
                           "Amount") and h["status"] != "ok":
                    # Negative combat officials are debuff magnitudes
                    # (Intimidate -5 scales flat, like promotions).
                    try:
                        neg = float(h["official_value"]) < 0
                    except (TypeError, ValueError):
                        neg = False
                    if neg:
                        h["semantic_family"] = "FLAT_AMOUNT"
                        h["transformation"] = "canonical_x10_multiply"
                        h["generated_value"], h["status"] = \
                            apply_transform("canonical_x10_multiply",
                                            h["official_value"])
                        h["confidence"] = "human_certified_8b_mode"
                h["module"] = "modes"
                if h["confidence"] == "auto_rule":
                    h["confidence"] = "human_certified_8b_mode"
                h["certification_source"] = f"phase8b-mode-audit:{mode}"
                if h["transformation"] == "unchanged":
                    rows.append(h)
                    continue
                if h["status"] != "ok":
                    if h["argument_name"] in NON_MAGNITUDE_ARGS:
                        h["transformation"] = "unchanged"
                        h["generated_value"] = h["official_value"]
                        h["status"] = "ok"
                        rows.append(h)
                        continue
                    notes.append(
                        f"modes/{mode}: {mid} "
                        f"({h['effect_type']}, {h['argument_name']}) "
                        f"status {h['status']} (out)")
                    continue
                rows.append(h)
    return rows, notes


def write_mode_manifest(rows: list[dict]) -> Path:
    import yaml
    # Modes manifest keeps magnitudes only: mode overlays duplicate base
    # definitions (same ModifierId, selector arguments), and unchanged
    # rows would fake multi-module ownership at the manifest level while
    # never entering production. The disposition notes file keeps the
    # reviewed-but-unscaled record.
    rows = [r for r in rows if r.get("transformation") != "unchanged"]
    path = ROOT / "manifests" / "modes.yml"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump({"modes": rows}, fh, sort_keys=False,
                       allow_unicode=True)
    return path


def write_sweep_manifest(rows: list[dict]) -> Path:
    import yaml
    path = ROOT / "manifests" / "sweep.yml"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump({"sweep": rows}, fh, sort_keys=False,
                       allow_unicode=True)
    return path


def build_all(write: bool = True) -> dict:
    """Run every 8B manifest/SQL builder. Returns step -> counts/paths.

    Patches existing wonders/traits vector rows in place (re-run after any
    base-manifest regen), then writes slots/envoys/promotions/dedications/
    modes/sweep manifests + the slot-copies SQL.
    """
    from .bridge import collect_registry_rows  # noqa (cycle guard note)
    db = open_db()
    report: dict = {}
    report["vectors"] = patch_vector_manifests()
    slot_rows = build_slot_manifest_rows()
    report["slots_sql"] = str(write_slot_sql())
    envoy_rows, envoy_notes = build_envoy_manifest_rows(db)
    report["envoys_notes"] = len(envoy_notes)
    promo_rows, promo_notes = build_promotion_manifest_rows(db)
    report["promotions_notes"] = len(promo_notes)
    dedi_rows, dedi_notes = build_dedication_manifest_rows(db)
    report["dedications_notes"] = len(dedi_notes)
    bundle = collect_mode_data()
    mode_rows, mode_notes = build_mode_manifest_rows(db, bundle)
    report["modes_notes"] = len(mode_notes)
    # Phase 8B.1: Game Modes owns ALL Secret Society-specific bonuses.
    # The 4A.1-audit + 6B-backlog society rows (previously governors-owned)
    # join the modes manifest here with module=modes; magnitudes,
    # transforms, and certification sources are byte-identical, only
    # ownership moves (bit 32 -> 512).
    from .governors import build_secret_society_mode_rows
    ss_rows = build_secret_society_mode_rows(
        ROOT / "civ6x10" / "rules" / "governor_audit.yml",
        backlog_path=ROOT / "civ6x10" / "rules" / "semantic_backlog.yml")
    report["modes_secret_society_rows"] = len(ss_rows)
    # The overlay sweep independently reaches most society keys (same
    # definitions, heuristic provenance). The governor-audit rows are the
    # reviewed authority for these keys, so colliding overlay rows are
    # dropped here: production dedup would otherwise merge them (fragile)
    # or fail on any metadata drift.
    ss_keys = {(r["modifier_id"], r["argument_name"]) for r in ss_rows}
    superseded = [r for r in mode_rows
                  if (r["modifier_id"], r["argument_name"]) in ss_keys]
    report["modes_overlay_superseded_by_society"] = len(superseded)
    mode_rows = [r for r in mode_rows
                 if (r["modifier_id"], r["argument_name"]) not in ss_keys]
    mode_rows.extend(ss_rows)
    sweep_rows, sweep_notes = build_core_sweep_rows(db)
    covered, _owners = base_covered_keys()
    for name, rowset in (("slots", slot_rows), ("envoys", envoy_rows),
                         ("promotions", promo_rows),
                         ("dedications", dedi_rows), ("modes", mode_rows),
                         ("sweep", sweep_rows)):
        kept = [h for h in rowset
                if (h["modifier_id"], h["argument_name"]) not in covered]
        report[f"{name}_base_covered_skipped"] = len(rowset) - len(kept)
        if name == "slots":
            slot_rows = kept
        elif name == "envoys":
            envoy_rows = kept
        elif name == "promotions":
            promo_rows = kept
        elif name == "dedications":
            dedi_rows = kept
        elif name == "modes":
            mode_rows = kept
        elif name == "sweep":
            sweep_rows = kept
    report["slots_manifest"] = str(write_slots_manifest(slot_rows))
    report["slots_rows"] = len(slot_rows)
    report["envoys_manifest"] = str(write_envoy_manifest(envoy_rows))
    report["envoys_rows"] = len(envoy_rows)
    report["promotions_manifest"] = str(
        write_promotion_manifest(promo_rows))
    report["promotions_rows"] = len(promo_rows)
    report["dedications_manifest"] = str(
        write_dedication_manifest(dedi_rows))
    report["dedications_rows"] = len(dedi_rows)
    report["modes_manifest"] = str(write_mode_manifest(mode_rows))
    report["modes_rows"] = len(mode_rows)
    report["sweep_manifest"] = str(write_sweep_manifest(sweep_rows))
    report["sweep_rows"] = len(sweep_rows)
    report["sweep_notes"] = len(sweep_notes)
    if write:
        report["envoy_notes_file"] = str(_write_notes("envoys", envoy_notes))
        report["promotion_notes_file"] = str(
            _write_notes("promotions", promo_notes))
        report["dedication_notes_file"] = str(
            _write_notes("dedications", dedi_notes))
        report["mode_notes_file"] = str(_write_notes("modes", mode_notes))
        report["sweep_notes_file"] = str(_write_notes("sweep", sweep_notes))
    db.close()
    return report


def _write_notes(name: str, notes: list[str]) -> Path:
    path = ROOT / "spike" / "8b" / f"{name}_disposition.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"# Phase 8B {name} disposition notes (reviewed exclusions)\n")
        for n in sorted(set(notes)):
            fh.write(f"- {n}\n")
    return path


# attach table -> (id column, module tag, provenance label)
SWEEP_TABLES = {
    "BeliefModifiers": ("BeliefType", "religion", "belief"),
    "GreatPersonIndividualActionModifiers": ("GreatPersonIndividualType",
                                             "greatpeople",
                                             "greatperson-active"),
    "GreatPersonIndividualBirthModifiers": ("GreatPersonIndividualType",
                                            "greatpeople",
                                            "greatperson-birth"),
    "ProjectCompletionModifiers": ("ProjectType", "projects", "project"),
}

# Reviewed sweep patches (family, transformation) by (effect, argument).
SWEEP_PATCHES = {
    ("EFFECT_ADJUST_RELIGIOUS_COMBAT_LOSS", "ReductionPercent"):
        ("DISCOUNT", "compound_discount"),
    ("EFFECT_GRANT_PLAYER_YIELD_PERCENT_UNIT_COST", "UnitCostPercent"):
        ("PERCENT_BONUS", "canonical_x10_multiply"),
}


def _belief_class(db, belief):
    r = db.execute("SELECT BeliefClassType FROM Beliefs WHERE BeliefType = ?",
                   (belief,)).fetchone()
    return r[0] if r else ""


def build_core_sweep_rows(db) -> tuple[list[dict], list[str]]:
    """Sweep belief/great-person/project modifiers with disposition."""
    from .modules import build_manifest, apply_transform
    rows: list[dict] = []
    notes: list[str] = []
    for table, (idcol, module, label) in SWEEP_TABLES.items():
        try:
            links = db.execute(
                f"SELECT {idcol}, ModifierId FROM {table}").fetchall()
        except Exception as e:
            notes.append(f"sweep: {table} unreadable ({e})")
            continue
        for (obj, mid) in links:
            if table == "BeliefModifiers" and \
                    _belief_class(db, obj) == "BELIEF_CLASS_PANTHEON":
                continue  # pantheons module owns these already
            # One ATTACH hop: belief/founder wrappers (Tithe, Defender,
            # Choral Music) carry the magnitude on a leaf modifier.
            sweep_ids = [(mid, None)]
            mtype = db.execute(
                "SELECT ModifierType FROM Modifiers WHERE ModifierId = ?",
                (mid,)).fetchone()
            if mtype is not None:
                effs = db.execute(
                    "SELECT EffectType FROM DynamicModifiers"
                    " WHERE ModifierType = ?", (mtype[0],)).fetchall()
                if any(e[0] == "EFFECT_ATTACH_MODIFIER" for e in effs):
                    tgt = db.execute(
                        "SELECT Value FROM ModifierArguments"
                        " WHERE ModifierId = ? AND Name = 'ModifierId'",
                        (mid,)).fetchone()
                    if tgt is not None:
                        sweep_ids.append((tgt[0], mid))
            for sid, wrapper in sweep_ids:
                try:
                    raws = manifest_rows_for_modifier(db, sid, obj)
                except KeyError:
                    notes.append(
                        f"sweep: {sid} has no Modifiers row (skip)")
                    continue
                if wrapper is not None:
                    for r in raws:
                        r["root_wrapper"] = wrapper
                for h in build_manifest(raws, "object_id"):
                    h["sweep_table"] = table
                    h["sweep_label"] = label
                    key = (h["effect_type"], h["argument_name"])
                    if key in SWEEP_PATCHES:
                        fam, tr = SWEEP_PATCHES[key]
                        h["semantic_family"] = fam
                        h["transformation"] = tr
                        h["generated_value"], h["status"] = \
                            apply_transform(tr, h["official_value"])
                        h["confidence"] = "human_certified_8b_sweep"
                        h["module"] = module
                        if h["status"] == "ok":
                            rows.append(h)
                            continue
                        notes.append(
                            f"sweep: {obj} {sid} {key} patch failed")
                        continue
                    h["module"] = module
                    if h["transformation"] == "unchanged":
                        h["confidence"] = "human_certified_8b_reviewed"
                        rows.append(h)
                        continue
                    if h["status"] != "ok":
                        if h["argument_name"] in NON_MAGNITUDE_ARGS:
                            h["transformation"] = "unchanged"
                            h["generated_value"] = h["official_value"]
                            h["status"] = "ok"
                            h["confidence"] = "human_certified_8b_reviewed"
                            rows.append(h)
                            continue
                        notes.append(
                            f"sweep: {obj} {sid} ({h['effect_type']}, "
                            f"{h['argument_name']}) status {h['status']} (out)")
                        continue
                    rows.append(h)
    return rows, notes
