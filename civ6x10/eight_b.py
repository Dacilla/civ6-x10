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

# Wildcard filler policies (one shared name/description pair in X10Text.sql).
# Wildcard cards can occupy any slot type, so one family covers all.
FILLER_COUNT = 99
FILLER_PREFIX = "POLICY_X10_FILLER_WILDCARD_"


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
    """Inert slot copies + wildcard filler policies (guarded, idempotent).

    Copies are inert by default (GovernmentSlotType=SLOT_NONE, which no
    government screen honors): module-off / invalid-k sessions keep the
    single vanilla slot. The native REPEAT kind rewrites copies N<=k to
    the real slot type. Fillers are effect-free wildcard policies so the
    end-turn check can always be satisfied.
    """
    chunks = [
        "-- GENERATED by civ6x10.eight_b from audited bonus-slot grants.",
        "-- Do not hand-edit. Regenerate: python -m civ6x10 build-8b-manifests",
        "-- Inert copies (SLOT_NONE): activated only by the native REPEAT",
        "-- kind for copies N <= integral k. Filler policies are effect-free",
        "-- wildcard cards (shared LOC in X10Text.sql) so multiplied bonus",
        "-- slots can always be filled and the turn ended.",
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
    chunks.append("-- Wildcard filler policies (effect-free, Code of Laws).")
    for i in range(1, FILLER_COUNT + 1):
        pid = f"{FILLER_PREFIX}{i:03d}"
        chunks.append(
            "INSERT INTO Types (Type, Kind)\n"
            f"SELECT '{pid}', 'KIND_POLICY'\n"
            f"WHERE NOT EXISTS (SELECT 1 FROM Types"
            f" WHERE Type = '{pid}');")
        chunks.append(
            "INSERT INTO Policies (PolicyType, Description, PrereqCivic,"
            " Name, GovernmentSlotType, ExplicitUnlock)\n"
            f"SELECT '{pid}', 'LOC_POLICY_X10_FILLER_DESCRIPTION',"
            f" 'CIVIC_CODE_OF_LAWS', 'LOC_POLICY_X10_FILLER_NAME',"
            f" 'SLOT_WILDCARD', 0\n"
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
