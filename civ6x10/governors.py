"""Phase 4A/4A.1: closed-world Governor / governor-promotion audit.

AUDIT ONLY. Discovers every official Governor and governor promotion that is
actually present, walks the reachable modifier / argument / requirement graph,
classifies each numeric gameplay value against the project's semantic
vocabulary, and emits a machine-readable manifest + inventory + graph.

Phase 4A.1 hardening over 4A:

* **Schema-driven discovery** - governor tables are found by scanning the real
  SQLite schema for any column whose name contains "Governor" (plus
  `RequiredGovernor`-style columns), instead of a curated table list. This is
  what pulls in `GovernorReplaces` and `GreatWorks_MODE`.
* **Action-aware mode discovery** - the Secret Societies payload is resolved
  from the Ethiopia modinfo's own UpdateDatabase actions/criteria for the
  configured ruleset, not from a single hard-coded file, and records the exact
  file + action + criteria + SHA-256 provenance per row.
* **Machine-accounted structural data** - discovery chances, appointment cap,
  cannot-assign rows, great-work governor requirements and governor-replace
  rows are emitted as dispositioned direct cells.
* **Corrected dispositions** - appeal ratings are integral-gated, a structural
  radius requirement no longer excludes the unrelated combat magnitude, and
  negative combat strength is decision-required (the canonical transform is
  undefined there).
* **Reproducible** - explicit `--game-root` / `CIV6_GAME_ROOT`, source-file
  hashes recorded in provenance, and CI-safe skips when mode sources are
  absent.

It writes NO production registry rows: the Phase 4B production slice is a
separate, reviewed decision.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path

# --------------------------------------------------------------------------
# Ownership design (report only - NOT implemented anywhere in Phase 4A).
# civ6x10.production.MODULE_BITS: traits 1, policies 2, governments 4,
# pantheons 8, wonders 16; Phase 4B implemented the next value (32 =
# governors) and (since Phase 5B) the CE writer arms s_modEnabled[7] with
# seven flags (traits, policies, governments, pantheons, wonders, governors,
# suzerain=bit 64),
# reading X10_MODULE_GOVERNORS as a supported module (default ON).
# --------------------------------------------------------------------------
PROPOSED_GOVERNOR_MODULE_BIT = 32
PROPOSED_NEXT_MODULE_BIT_AFTER_GOVERNORS = 64

DEFAULT_GAME_ROOTS = [
    os.environ.get("CIV6_GAME_ROOT") or "",
    os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 "Steam", "steamapps", "common",
                 "Sid Meier's Civilization VI"),
]

# New Frontier Pass: the pack that carries the Secret Societies game mode.
MODE_MODINFO_REL = os.path.join("DLC", "Ethiopia", "Ethiopia.modinfo")
MODE_PACKAGE = "New Frontier Pass (Ethiopia/Philippines pack)"

# Effect types that consume their magnitude integrally at the game-effect
# layer (Phase 3F/3G proven). Phase 4B must inherit the same gate.
ENGINE_INTEGRAL_EFFECTS = {"EFFECT_ADJUST_BUILDING_YIELD_CHANGE"}
# Appeal ratings are whole levels in this project's existing certification
# (count_like_effects: FEATURE_APPEAL_MODIFIER / CITY_APPEAL).
ENGINE_INTEGRAL_APPEAL_EFFECTS = {
    "EFFECT_ADJUST_FEATURE_NO_IMPROVEMENT_APPEAL_GOVERNOR",
    "EFFECT_ADJUST_PLOT_APPEAL",
    "EFFECT_ADJUST_CITY_APPEAL",
}

# Cross-check only. The authoritative set is DERIVED from the shipped
# SecretSocieties rows (see secret_society_governor_types) so a renamed or
# newly added society cannot be missed, and so the old misspelling
# (a misspelled governor/society name) cannot silently drop one.
SECRET_SOCIETY_GOVERNOR_TYPES = {
    "GOVERNOR_OWLS_OF_MINERVA", "GOVERNOR_HERMETIC_ORDER",
    "GOVERNOR_VOIDSINGERS", "GOVERNOR_SANGUINE_PACT",
}


def secret_society_governor_types(universe: dict) -> set:
    """Governor types bound by a SecretSocieties row (data-derived)."""
    found = {r["GovernorType"] for r in universe.get("secret_societies", [])
             if r.get("GovernorType")}
    if not found:
        # no SecretSocieties rows loaded (clean DB without the mode payload)
        return set()
    return found


# --------------------------------------------------------------------------
# Generic XML row parsing (attribute form and nested-element form)
# --------------------------------------------------------------------------
def normalise_row_keys(r: dict) -> tuple[dict, bool]:
    """Normalise typo'd shipped attribute names.

    Returns (row, normalised). The official Ethiopia Secret Societies XML
    contains at least one `ModifierID` (capital D) where the schema expects
    `ModifierId`; dropping it would silently remove a reachable effect from
    the closed world.
    """
    r = dict(r)
    changed = False
    for good, bad in (("ModifierId", "ModifierID"), ("RequirementId", "RequirementID"),
                      ("RequirementSetId", "RequirementSetID")):
        if good not in r and bad in r:
            r[good] = r.pop(bad)
            changed = True
    return r, changed


def _xml_rows(xml_text: str, table: str) -> list[dict]:
    """Rows of <table> in either attribute or nested-element form."""
    m = re.search(r"<%s>(.*?)</%s>" % (table, table), xml_text, re.S)
    if not m:
        return []
    body = m.group(1)
    out: list[dict] = []
    for row in re.finditer(
            r"<Row(?:\s+([^>]*?))?/>|<Row(?:\s+([^>]*?))?>(.*?)</Row>", body, re.S):
        if row.group(1) is not None and row.group(3) is None:
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', row.group(1) or ""))
            if attrs:
                r, _ = normalise_row_keys(attrs)
                out.append(r)
            continue
        inner = row.group(3) or ""
        if not inner.strip():
            continue
        attrs = dict(re.findall(r"<(\w+)>([^<]*)</\1>", inner))
        if attrs:
            r, _ = normalise_row_keys(attrs)
            out.append(r)
    return out


def _xml_rows_with_typo_count(xml_text: str, table: str) -> tuple[list[dict], int]:
    """Rows plus the number of typo-normalised rows (counted BEFORE fix-up)."""
    m = re.search(r"<%s>(.*?)</%s>" % (table, table), xml_text, re.S)
    if not m:
        return [], 0
    out: list[dict] = []
    typos = 0
    for row in re.finditer(
            r"<Row(?:\s+([^>]*?))?/>|<Row(?:\s+([^>]*?))?>(.*?)</Row>", m.group(1), re.S):
        raw = None
        if row.group(1) is not None and row.group(3) is None:
            raw = dict(re.findall(r'(\w+)="([^"]*)"', row.group(1) or ""))
        elif row.group(3):
            inner = (row.group(3) or "").strip()
            if inner:
                raw = dict(re.findall(r"<(\w+)>([^<]*)</\1>", inner))
        if not raw:
            continue
        fixed, changed = normalise_row_keys(raw)
        if changed:
            typos += 1
        out.append(fixed)
    return out, typos


# --------------------------------------------------------------------------
# Schema-driven governor-table discovery
# --------------------------------------------------------------------------
def discover_governor_tables(db) -> list[dict]:
    """Every table whose schema references a governor, found by column name."""
    tables = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    out = []
    for t in tables:
        cols = [c[1] for c in db.execute(f'PRAGMA table_info("{t}")')]
        gov_cols = [c for c in cols if "governor" in c.lower()]
        if not gov_cols:
            continue
        n = db.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        out.append({"table": t, "columns": cols, "governor_columns": gov_cols,
                    "rows": n, "source": "official DB schema scan"})
    return out


# --------------------------------------------------------------------------
# Action-aware Secret Societies (game mode) discovery
# --------------------------------------------------------------------------
def _parse_modinfo_actions(modinfo_text: str) -> list[dict]:
    """UpdateDatabase actions with their criteria and files, in file order."""
    criteria: dict[str, str] = {}
    for m in re.finditer(r'<Criteria id="([^"]+)"([^>]*)>(.*?)</Criteria>',
                         modinfo_text, re.S):
        criteria[m.group(1)] = m.group(3).strip()
    actions = []
    for m in re.finditer(
            r'<UpdateDatabase id="([^"]+)"([^>]*)>(.*?)</UpdateDatabase>',
            modinfo_text, re.S):
        files = re.findall(r"<File(?: [^>]*)?>([^<]+)</File>", m.group(3))
        crit = re.search(r'criteria="([^"]+)"', m.group(2) or "")
        actions.append({
            "id": m.group(1),
            "criteria": crit.group(1) if crit else "",
            "criteria_body": criteria.get(crit.group(1) if crit else "", ""),
            "files": files,
        })
    return actions


def _ruleset_actions(actions: list[dict], criteria_suffix: str) -> list[dict]:
    """Actions whose criteria target the given ruleset/mode combination."""
    return [a for a in actions
            if criteria_suffix in a["criteria"]]


def resolve_mode_payload(game_root: str | Path | None = None,
                         ruleset: str = "Expansion2",
                         conditional_overlays: bool = True) -> dict:
    """Resolve the Secret Societies payload the way the engine would.

    `ruleset` selects the Expansion1/Expansion2 criteria branch;
    `conditional_overlays` includes the Gran Colombia/Maya overlay (present
    whenever that civ content is installed).
    """
    roots = [game_root] if game_root else [r for r in DEFAULT_GAME_ROOTS if r]
    for root in roots:
        root = Path(root)
        modinfo = root / MODE_MODINFO_REL
        if not modinfo.is_file():
            continue
        text = modinfo.read_text(encoding="utf-8")
        actions = _parse_modinfo_actions(text)
        wanted = []
        for a in _ruleset_actions(actions, ruleset):
            if "GranColombia_Maya" in a["criteria"]:
                continue  # conditional overlay, handled below
            wanted.append(a)
        if conditional_overlays:
            wanted.extend(_ruleset_actions(actions, "GranColombia_Maya"))
        files = []
        seen = set()
        mod_dir = modinfo.parent
        for a in wanted:
            for rel in a["files"]:
                if rel in seen:
                    continue
                seen.add(rel)
                p = mod_dir / rel
                entry = {
                    "file": ("DLC/Ethiopia/" + rel).replace("\\", "/"),
                    "mod_relative_path": rel.replace("\\", "/"),
                    "package": MODE_PACKAGE,
                    "action_id": a["id"],
                    "criteria": a["criteria"],
                    "criteria_body": a["criteria_body"][:200],
                    "exists": p.is_file(),
                    "sha256": None,
                    "bytes": None,
                }
                if p.is_file():
                    data = p.read_bytes()
                    entry["sha256"] = hashlib.sha256(data).hexdigest()
                    entry["bytes"] = len(data)
                files.append(entry)
        return {"available": True, "root": str(root), "ruleset": ruleset,
                "files": files}
    return {"available": False, "root": None, "ruleset": ruleset, "files": []}


MODE_TABLES = (
    "Governors", "GovernorPromotionSets", "GovernorPromotions",
    "GovernorPromotionPrereqs", "GovernorPromotionConditions",
    "GovernorPromotionModifiers", "GovernorModifiers", "GovernorsCannotAssign",
    "SecretSocieties", "TraitModifiers", "GovernorReplaces", "GreatWorks_MODE",
    "Modifiers", "ModifierArguments", "DynamicModifiers", "Requirements",
    "RequirementSets", "RequirementSetRequirements", "RequirementArguments",
    "UnitAbilities", "UnitAbilityModifiers", "GlobalParameters",
)


def load_mode_overlay(game_root=None, ruleset: str = "Expansion2",
                      conditional_overlays: bool = True) -> dict:
    """Full mode payload, per-file provenance and row source included."""
    payload = resolve_mode_payload(game_root, ruleset, conditional_overlays)
    overlay = {"available": payload["available"], "root": payload["root"],
               "ruleset": payload["ruleset"], "files": payload["files"],
               "rows": {}, "typo_normalised": 0, "sources": {}}
    if not payload["available"]:
        return overlay
    for entry in payload["files"]:
        if not entry["exists"]:
            continue
        p = Path(payload["root"]) / "DLC" / "Ethiopia" / entry["mod_relative_path"]
        text = p.read_text(encoding="utf-8")
        for table in MODE_TABLES:
            rows, typos = _xml_rows_with_typo_count(text, table)
            overlay["typo_normalised"] += typos
            if not rows:
                continue
            tag = f"{entry['file']} [{entry['action_id']}/{entry['criteria']}]"
            overlay["rows"].setdefault(table, [])
            for r in rows:
                r = dict(r)
                r["_source_file"] = entry["file"]
                r["_source_action"] = entry["action_id"]
                r["_source_criteria"] = entry["criteria"]
                r["_source_sha256"] = entry["sha256"]
                overlay["rows"][table].append(r)
            overlay["sources"][tag] = overlay["sources"].get(tag, 0) + len(rows)
    # MAX_GOVERNOR_APPOINTMENTS and friends come from <GlobalParameters>
    for entry in payload["files"]:
        if not entry["exists"]:
            continue
        p = Path(payload["root"]) / entry["file"]
        text = p.read_text(encoding="utf-8")
        for m in re.finditer(r"<Where Name=\"(MAX_[A-Z_]+)\"/>", text):
            overlay["rows"].setdefault("GlobalParameters", []).append({
                "Name": m.group(1), "_source_file": entry["file"],
                "_source_action": entry["action_id"],
                "_source_criteria": entry["criteria"],
                "_source_sha256": entry["sha256"]})
    return overlay


# --------------------------------------------------------------------------
# Curated governor classification
# --------------------------------------------------------------------------
CURATED_EFFECT_RULES = {
    # --- additive flat magnitudes (float-safe in the engine) --------------
    "EFFECT_ADJUST_BUILDING_YIELD_CHANGE": ("FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat building yield; ENGINE-INTEGRAL application (Phase 3F/3G evidence) - integral gate required"),
    "EFFECT_ADJUST_CITY_YIELD_PER_DISTRICT": ("FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat yield per matching district (Cardinal Bishop: faith per holy site); city yield, float-safe"),
    "EFFECT_ADJUST_CITY_RESOURCE_HARVEST_BONUS": ("PERCENT_BONUS", "CERTIFIED_CANDIDATE",
        "percent bonus to harvest yields (Groundbreaker +50%)"),
    "EFFECT_ADJUST_CITY_YIELD_FROM_FOREIGN_TRADE_ROUTES_PASSING_THROUGH": ("GOLD", "CERTIFIED_CANDIDATE",
        "flat gold from foreign trade routes passing through (Foreign Exchange +3)"),
    "EFFECT_ADJUST_CITY_GOLD_FROM_CITIZENS": ("GOLD", "CERTIFIED_CANDIDATE",
        "flat gold from citizens (Tax Collector +2)"),
    "EFFECT_ADJUST_PLOT_YIELD": ("FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat plot yield (Forestry gold, Renewable Energy gold); subject requirement filters the plot, never scaled"),
    "EFFECT_ADJUST_FEATURE_NO_IMPROVEMENT_APPEAL_GOVERNOR": ("APPEAL", "CERTIFIED_CANDIDATE",
        "appeal per unimproved feature (Forestry Management); project treats appeal ratings as WHOLE LEVELS - ENGINE-INTEGRAL gate required (1 x 7.3 must refuse)"),
    "EFFECT_ADJUST_DISTRICT_YIELD_MODIFIER": ("PERCENT_BONUS", "CERTIFIED_CANDIDATE",
        "percent adjacency yield modifier (Harbormaster +100% commercial hub/harbor adjacency)"),
    "EFFECT_ADJUST_CITY_YIELD_MODIFIER_FROM_FAITH": ("PERCENT_BONUS", "CERTIFIED_CANDIDATE",
        "percent yield from faith output (Voidsingers ley lines +20%)"),
    "EFFECT_ADJUST_CITY_GREAT_PERSON_POINTS_MODIFIER": ("PERCENT_BONUS", "CERTIFIED_CANDIDATE",
        "percent great-person-point modifier (Educator Grants +100%); project already excludes this effect from count-like"),
    "EFFECT_GOVERNOR_ADJUST_CITY_TOKENS_GRANTED_MODIFIER": ("PERCENT_BONUS", "CERTIFIED_CANDIDATE",
        "percent envoy modifier (Puppeteer +100% envoys in city)"),
    "EFFECT_ADJUST_PLAYER_GOLD_INTEREST_PERCENT": ("PERCENT_BONUS", "CERTIFIED_CANDIDATE",
        "percent treasury interest (Owls of Minerva +3%)"),
    "EFFECT_ADJUST_EXTRA_HEAL_GOVERNOR": ("FLAT_AMOUNT", "DECISION_REQUIRED",
        "governor healing (Laying on of Hands +100): flat HP vs percent vs cap/sentinel unresolved until engine semantics are established"),
    "EFFECT_ADJUST_CITY_RELIGIOUS_HEAL": ("FLAT_AMOUNT", "DECISION_REQUIRED",
        "religious-unit healing (Laying on of Hands +100): flat HP vs percent vs cap/sentinel unresolved until engine semantics are established"),
    "EFFECT_ADJUST_PLAYER_YIELD_CHANGE_PER_GREAT_PERSON_CLASS_ON_RESOURCE": ("FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat yield per great person of a class on a resource (Hermetic ley lines +1, incl. Gran Colombia/Maya Comandante General overlay)"),
    "EFFECT_ADJUST_TRAIT_AMENITY": ("AMENITY", "CERTIFIED_CANDIDATE",
        "amenity from counterspies (Owls +1); project treats amenities as float-valued"),
    # --- production / project percentages ---------------------------------
    "EFFECT_ADJUST_ALL_DISTRICTS_PRODUCTION": ("PRODUCTION_PERCENT", "CERTIFIED_CANDIDATE",
        "percent district production rate (Zoning Commissioner +20%)"),
    "EFFECT_ADJUST_PROJECT_PRODUCTION": ("PRODUCTION_PERCENT", "CERTIFIED_CANDIDATE",
        "percent project production (Arms Race Proponent)"),
    "EFFECT_ADJUST_SPACE_RACE_PROJECTS_PRODUCTION": ("PRODUCTION_PERCENT", "CERTIFIED_CANDIDATE",
        "percent space-race project production (Space Initiative)"),
    "EFFECT_ADJUST_CITY_ALL_MILITARY_UNITS_PRODUCTION": ("PRODUCTION_PERCENT", "CERTIFIED_CANDIDATE",
        "percent military-unit production (Pasha +20%)"),
    "EFFECT_ADJUST_CITY_CULTURE_BORDER_EXPANSION": ("PRODUCTION_PERCENT", "CERTIFIED_CANDIDATE",
        "percent culture border expansion (Land Acquisition)"),
    # --- housing / amenities ----------------------------------------------
    "EFFECT_ADJUST_DISTRICT_HOUSING": ("HOUSING", "CERTIFIED_CANDIDATE",
        "district housing (Water Works +2); housing scales as a magnitude"),
    "EFFECT_ADJUST_DISTRICT_AMENITY": ("AMENITY", "CERTIFIED_CANDIDATE",
        "district amenity (Water Works canal/dam +1)"),
    # --- combat-equivalent transform (b_k formula) ------------------------
    "EFFECT_ADJUST_CITY_COMBAT_BONUS": ("COMBAT_STRENGTH_BONUS", "CERTIFIED_CANDIDATE",
        "city combat-strength points (Garrison Commander +5); combat transform; requirement scope stays excluded"),
    "EFFECT_ADJUST_CITY_FRIENDLY_COMBAT_BONUS": ("COMBAT_STRENGTH_BONUS", "CERTIFIED_CANDIDATE",
        "friendly-unit combat-strength points in city (Head Falconer +5); combat transform"),
    "EFFECT_ADJUST_UNIT_AGAINST_DISTRICT_COMBAT_BONUS": ("COMBAT_STRENGTH_BONUS", "CERTIFIED_CANDIDATE",
        "combat-strength points against districts (Serasker +10): the 10-tile requirement is a FILTER (excluded), the Amount is the magnitude (combat transform)"),
    "EFFECT_ADJUST_CITY_RELIGIOUS_COMBAT_BONUS": ("COMBAT_STRENGTH_BONUS", "CERTIFIED_CANDIDATE",
        "theological-combat strength points (Grand Inquisitor +10); combat transform"),
    "EFFECT_ADJUST_CITY_AIR_DEFENSE_BONUS": ("COMBAT_STRENGTH_BONUS", "CERTIFIED_CANDIDATE",
        "city air-defense rating (Air Defense Initiative +25); combat-equivalent rating"),
    "EFFECT_ADJUST_CITY_INNER_DEFENSE": ("COMBAT_STRENGTH_BONUS", "CERTIFIED_CANDIDATE",
        "city inner-defense rating (Redoubt +5); defense rating is a combat-equivalent strength value"),
    "EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER": ("COMBAT_STRENGTH_BONUS", "DECISION_REQUIRED",
        "unit combat-strength modifier (Sanguine intimidate -5): the canonical b_k transform is UNDEFINED for negative strengths (25*ln(k*(exp(b/25)-1)+1) has a negative argument at k=7.3 and k=10); refused by the existing implementation rather than given a new negative formula"),
    # --- indivisible counts / integral-gate candidates --------------------
    "EFFECT_ADJUST_CITY_SPY_BONUS": ("INDIVISIBLE_COUNT", "DECISION_REQUIRED",
        "spy operation bonus in whole levels (Local Informants +3); integral gate candidate"),
    "EFFECT_ADJUST_GOVERNOR_ALLIANCE_POINTS": ("INDIVISIBLE_COUNT", "DECISION_REQUIRED",
        "alliance points are whole points (Khass Oda Bashi +2); integral gate candidate"),
    "EFFECT_ADJUST_CITY_ATTACKS_PER_TURN": ("INDIVISIBLE_COUNT", "DECISION_REQUIRED",
        "attacks per turn is a capability count (Embrasure +1); scaling changes city defense structure"),
    "EFFECT_ADJUST_RESOURCE_POWER_PROVIDED_GOVERNOR": ("INDIVISIBLE_COUNT", "DECISION_REQUIRED",
        "power provided per turn is a whole-unit flow (Industrialist +1); integral gate candidate"),
    "EFFECT_ADJUST_CITY_RELIGION_EXTRA_PROMOTIONS": ("INDIVISIBLE_COUNT", "DECISION_REQUIRED",
        "extra unit promotions are whole promotions (Patron Saint +1)"),
    "EFFECT_ADJUST_UNIT_BUILD_CHARGES": ("CHARGES", "DECISION_REQUIRED",
        "builder charges are whole uses (Guildmaster / vampire builds); integral gate candidate"),
    "EFFECT_ADJUST_CITY_SETTLER_CONSUME_POP": ("INDIVISIBLE_COUNT", "DECISION_REQUIRED",
        "settler population consumption is a whole-citizen flow (Expedition)"),
    "EFFECT_ADJUST_CITY_EXTRA_ACCUMULATION": ("INDIVISIBLE_COUNT", "DECISION_REQUIRED",
        "extra strategic accumulation is a whole-unit flow (Defense Logistics +1)"),
    # --- loyalty / identity pressure (Toqui hold class) --------------------
    "EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE": ("LOYALTY", "EXCLUDED",
        "project rule: EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE is temporarily excluded (Toqui stored-form hold, 2026-10-08); governor carriers inherit the same hold"),
    "EFFECT_ADJUST_CITY_IDENTITY_PER_TURN": ("LOYALTY", "DECISION_REQUIRED",
        "identity/loyalty gained per turn (Owls counterspies +4); same pressure class as the Toqui hold"),
    "EFFECT_ADJUST_CITY_RELIGION_PRESSURE": ("LOYALTY", "DECISION_REQUIRED",
        "religious pressure is a pressure rate (Cardinal Bishop); same class as identity pressure - needs review"),
    # --- grants / object creation -----------------------------------------
    "EFFECT_ADJUST_CITY_ALLOWED_IMPROVEMENT": ("GRANT_OBJECT", "EXCLUDED",
        "unlocks an improvement (Aquaculture fishery, Parks city park); structural grant"),
    "EFFECT_GOVERNOR_ADJUST_CITY_TOKENS_GRANTED": ("GRANT_OBJECT", "EXCLUDED",
        "grants envoys (Messenger +2); envoy objects are DECISION_REQUIRED in project rules"),
    "EFFECT_ADJUST_PLAYER_TOKEN_ON_TRADE_ROUTE_STARTED": ("GRANT_OBJECT", "EXCLUDED",
        "grants an envoy per trade route started (Owls); envoy object grant"),
    "EFFECT_GRANT_SPY": ("GRANT_OBJECT", "EXCLUDED",
        "grants spies (Owls spy capacity +2); object grant"),
    "EFFECT_GRANT_UNIT_IN_CITY": ("GRANT_OBJECT", "EXCLUDED",
        "grants units in the capital (Sanguine Pact vampires); object grant"),
    "EFFECT_ADJUST_PLAYER_VALID_BUILDING": ("GRANT_OBJECT", "EXCLUDED",
        "unlocks a society building (Gilded Vault, Alchemical Society); structural grant"),
    "EFFECT_ADJUST_IMPROVEMENT_PROPERTY": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "improvement property unlock (Owls castle teleport); structural property"),
    "EFFECT_ADJUST_PLAYER_GOVERNMENT_SLOT_TYPE": ("SLOT_CAPACITY", "EXCLUDED",
        "government/wildcard policy slot modifier (Owls economic + wildcard slots); slot capacity is structural"),
    # --- boolean / structural ---------------------------------------------
    "EFFECT_ADJUST_CITY_CAN_PURCHASE_DISTRICTS": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "district purchase unlock (Contractor); boolean"),
    "EFFECT_ADJUST_CAN_FAITH_PURCHASE_DISTRICTS": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "faith district purchase unlock (Divine Architect); boolean"),
    "EFFECT_ADJUST_CITY_ALLOWED_INCOMING_REGIONAL_STACKING": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "incoming regional yield stacking unlock (Vertical Integration); boolean"),
    "EFFECT_ADJUST_CITY_SIEGE_PROTECTION": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "siege protection flag (Defense Logistics); boolean"),
    "EFFECT_ADJUST_CITY_RELIGION_IGNORE_PRESSURE": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "religious pressure immunity flag (Citadel of God); boolean"),
    "EFFECT_ADJUST_CITY_RELIGION_IGNORE_COMBAT": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "theological combat immunity flag (Citadel of God); boolean"),
    "EFFECT_ADJUST_IGNORE_IDENTITY_PRESSURE": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "identity pressure immunity flag (Grand Vizier); boolean"),
    "EFFECT_ADJUST_PREVENT_STRUCTURAL_DAMAGE": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "structural damage prevention flag (Reinforced Infrastructure); boolean"),
    "EFFECT_ADJUST_UNIT_GRANT_EXPERIENCE": ("EXPERIENCE", "EXCLUDED",
        "project rule: sentinel Amount=-1 (Embrasure free promotions) is not a magnitude"),
    "EFFECT_ATTACH_MODIFIER": ("GRANT_OBJECT", "EXCLUDED",
        "attaches a nested modifier (Guildmaster builder charges); the nested definition is audited via ModifierId traversal"),
    # --- multiplicative factors / unresolved percent semantics ------------
    "EFFECT_ADJUST_CITY_STRATEGIC_RESOURCE_REQUIREMENT_MODIFIER": ("MULTIPLICATIVE_FACTOR", "DECISION_REQUIRED",
        "percent reduction of strategic-resource requirement (Black Marketeer -80%); multiplicative factor on a requirement, not a magnitude"),
    "EFFECT_ADJUST_PLAYER_TARGET_CITY_SPY_YIELD_PERCENT": ("PERCENT_BONUS", "DECISION_REQUIRED",
        "percent of another city's yield from spy missions (Owls +50%); percent-of-foreign-yield semantics unresolved"),
    "EFFECT_GRANT_CITY_YIELD_PERCENT_BUILDING_CREATED_COST": ("PERCENT_BONUS", "DECISION_REQUIRED",
        "percent of building production cost granted as yield (Citadel of God +25%, IncludeWonder selector); grant-on-completion semantics unresolved"),
    "EFFECT_ADJUST_CITY_TOURISM": ("MULTIPLICATIVE_FACTOR", "DECISION_REQUIRED",
        "tourism ScalingFactor=200 (Curator): percent-vs-factor scaling unresolved (same precedent as Cristo/St. Basil's)"),
    "EFFECT_ADJUST_GOVERNOR_GRIEVENCE_SCORE": ("FLAT_AMOUNT", "DECISION_REQUIRED",
        "grievance score is a whole-point score applied for a duration (Capou Agha); score+Turns split unresolved"),
    "EFFECT_ADJUST_CITY_YIELD_PER_POPULATION": ("FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat yield per citizen (Connoisseur culture +1, Researcher science +1)"),
    "EFFECT_ADJUST_CITY_YIELD_MODIFIER": ("PERCENT_BONUS", "CERTIFIED_CANDIDATE",
        "percent city yield modifier (Librarian +15% science/culture); scalar per-definition (mixed-domain family excludes vector siblings)"),
    "EFFECT_ADJUST_CITY_GROWTH": ("PERCENT_BONUS", "CERTIFIED_CANDIDATE",
        "percent city growth (Surplus Logistics +20%)"),
    "EFFECT_ADJUST_TRADE_ROUTE_YIELD_TO_OTHERS": ("FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat yield sent to other civs on trade routes (Surplus Logistics food +2); Domestic flag is a selector"),
    "EFFECT_ADJUST_CITY_EXTRA_ACCUMULATION": ("INDIVISIBLE_COUNT", "DECISION_REQUIRED",
        "extra strategic accumulation is a whole-unit flow (Defense Logistics +1)"),
    # --- mode-only (Secret Societies) effects ------------------------------
    "EFFECT_ATTACH_PERMANENT_MODIFIER_TO_PLOT_UNITS": ("GRANT_OBJECT", "EXCLUDED",
        "permanently attaches a modifier to units on a tile (Sanguine combat-result chain); structural attach, followed via ModifierId"),
    "EFFECT_ATTACH_PERMANENT_MODIFIER_TO_ADJACENT_PLOT_UNITS": ("GRANT_OBJECT", "EXCLUDED",
        "permanently attaches a modifier to units on adjacent tiles (Sanguine); structural attach, followed via ModifierId"),
    "EFFECT_ADJUST_UNIT_PROPERTY": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "unit property unlock (Owls castle teleport / unit properties); structural"),
    "EFFECT_ADD_PLAYER_PROJECT_AVAILABILITY": ("GRANT_OBJECT", "EXCLUDED",
        "unlocks a project (Voidsingers); structural availability grant"),
    "EFFECT_GRANT_IMPROVEMENT_ADJACENT_YIELDS": ("GRANT_OBJECT", "EXCLUDED",
        "grants adjacency yields to an improvement (Hermetic); structural yield grant"),
    "EFFECT_GRANT_YIELD_PER_RESOURCE_IN_CITY": ("FLAT_YIELD", "DECISION_REQUIRED",
        "yield per resource type in city (Hermetic); per-resource multiplier semantics unresolved"),
    "EFFECT_ADJUST_UNIT_ADVANCED_PILLAGING": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "advanced pillaging capability (Owls); boolean capability"),
    "EFFECT_ADJUST_UNIT_DIRECT_LOYALTY_DAMAGE": ("LOYALTY", "DECISION_REQUIRED",
        "direct loyalty damage from a unit ability (Voidsinger spread dissent); loyalty class, Toqui-hold semantics"),
    "EFFECT_ADJUST_PLAYER_YIELD_CHANGE": ("FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat player yield change (society yield modifier); additive magnitude"),
    "EFFECT_DIPLOMACY_SIMPLE_EFFECT": ("GRANT_OBJECT", "EXCLUDED",
        "diplomatic simple modifier between same/different society members; diplomatic effect, not a magnitude"),
    "EFFECT_ADJUST_UNIT_RELIC_UPON_DEATH": ("GRANT_OBJECT", "EXCLUDED",
        "grants a relic when a unit dies (cultist relic); object grant"),
    "EFFECT_ADJUST_PLAYER_VALID_UNIT_BUILD": ("GRANT_OBJECT", "EXCLUDED",
        "unlocks a unit for the player (society units); structural availability grant"),
    "EFFECT_GRANT_FREE_RESOURCE_VISIBILITY": ("GRANT_OBJECT", "EXCLUDED",
        "reveals a resource type; object/visibility grant"),
    "EFFECT_ADJUST_UNIT_HEALING_MODIFIERS": ("PERCENT_BONUS", "DECISION_REQUIRED",
        "percent healing modifier for all units (Voidsingers); heal semantics (flat HP vs percent vs cap) unresolved"),
    # --- governor titles (shared with traits module) ----------------------
    "EFFECT_ADJUST_PLAYER_GOVERNOR_POINTS": ("GOVERNOR_TITLES", "EXCLUDED",
        "already certified under TRAITS ownership (SULEIMAN_GOVERNOR_POINTS +1, narrow Delta-on-GOVERNOR_POINTS rule); governor module must not re-own/double-scale"),
    # --- society building mirror effects (Gran Colombia/Maya overlay) -----
    "EFFECT_ADJUST_DISTRICT_YIELD_BASED_ON_ADJACENCY_BONUS": ("MULTIPLICATIVE_FACTOR", "DECISION_REQUIRED",
        "yield mirrors another district's yield (Alchemical Society / Gilded Vault); multiplicative mirror semantics unresolved"),
    "EFFECT_ADJUST_TRADE_ROUTE_CAPACITY": ("INDIVISIBLE_COUNT", "DECISION_REQUIRED",
        "trade route capacity is a whole-route allowance (Gilded Vault +1)"),
}

CURATED_MODIFIER_OVERRIDES = {}

ADDITIVE_CANDIDATE_FAMILIES = {
    "GOLD", "FLAT_YIELD", "FLAT_AMOUNT", "PRODUCTION_PERCENT", "PERCENT_BONUS",
    "EXPERIENCE", "HOUSING", "AMENITY", "TOURISM", "APPEAL",
}

# Arguments that name a type/target and are therefore never magnitudes.
SELECTOR_ARG_NAMES = {
    "YieldType", "BuildingType", "DistrictType", "ImprovementType",
    "GreatWorkObjectType", "ProjectType", "ModifierId", "ResourceType",
    "UnitType", "FeatureType", "TerrainType", "EraType", "Key",
    "GreatPersonClassType", "RouteType", "ReligionType", "Domestic",
    "DomesticCities", "ForeignCities", "CanPurchase", "Enable", "Enabled",
    "Ignore", "Prevent", "Protected", "IncludeWonder", "GovernmentSlotType",
    "BuildingTypeToReplace", "YieldTypeToGrant", "YieldTypeToMirror",
    "GreatWorkType", "UniqueGovernorType", "ReplacesGovernorType",
    "SecretSocietyType", "GovernorType", "GovernorPromotionType",
    "RequiredGovernor", "PrereqGovernorPromotion", "Name", "Value",
}


def effect_engine_integral(effect_type: str | None) -> bool:
    return (effect_type in ENGINE_INTEGRAL_EFFECTS
            or effect_type in ENGINE_INTEGRAL_APPEAL_EFFECTS)


def _classify(modifier_type: str, effect_type: str, arg: str, value: str):
    """Classify one reachable argument into the audit vocabulary."""
    if arg in SELECTOR_ARG_NAMES:
        return {"family": "SELECTOR", "disposition": "EXCLUDED",
                "reason": "selector/type/reference argument, never a magnitude",
                "engine_integral": False}
    # requirement-set arguments are filters, never magnitudes, regardless of
    # which modifier the set is attached to
    try:
        float(value)
    except (TypeError, ValueError):
        return {"family": "SELECTOR", "disposition": "EXCLUDED",
                "reason": "non-numeric reference value",
                "engine_integral": False}
    fam, disp, reason = CURATED_EFFECT_RULES.get(
        effect_type, ("DECISION_REQUIRED", "DECISION_REQUIRED",
                      "no curated governor semantics for this effect"))
    integral = effect_engine_integral(effect_type)
    if integral and disp == "CERTIFIED_CANDIDATE":
        reason += "; engine applies integrally -> integral gate required"
    return {"family": fam, "disposition": disp, "reason": reason,
            "engine_integral": integral}


# --------------------------------------------------------------------------
# Universe discovery (DB + action-aware mode payload)
# --------------------------------------------------------------------------
def discover_governor_tables_from_db(db) -> list[dict]:
    """Every governor-keyed table, discovered from the real SQLite schema."""
    tables = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    out = []
    for tname in tables:
        cols = [c[1] for c in db.execute(f'PRAGMA table_info("{tname}")')]
        gov_cols = [c for c in cols if "governor" in c.lower()]
        if not gov_cols:
            continue
        n = db.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
        out.append({"table": tname, "columns": cols,
                    "governor_columns": gov_cols, "rows": n,
                    "source": "official DB schema scan"})
    return out


def discover_universe(db_path: str | Path, game_root=None,
                      ruleset: str = "Expansion2",
                      conditional_overlays: bool = True) -> tuple[dict, dict]:
    """Closed-world discovery of governors, promotions and their attachments."""
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    overlay = load_mode_overlay(game_root, ruleset, conditional_overlays)
    gov_tables = discover_governor_tables_from_db(db)

    governors: dict[str, dict] = {}
    for r in db.execute("SELECT * FROM Governors ORDER BY GovernorType"):
        d = dict(r)
        d["source"] = "official DB (Base/Rise & Fall/Gathering Storm)"
        d["modifiers"] = []
        governors[d["GovernorType"]] = d
    for r in db.execute("SELECT * FROM Governors_XP2"):
        gt = r["GovernorType"]
        if gt in governors:
            governors[gt]["AssignToMajor"] = r["AssignToMajor"]
    for r in overlay["rows"].get("Governors", []):
        gt = r.get("GovernorType")
        if not gt:
            continue
        d = {k: v for k, v in r.items() if not k.startswith("_")}
        d["source"] = ("mode overlay: %s [%s/%s]"
                       % (r.get("_source_file"), r.get("_source_action"),
                          r.get("_source_criteria")))
        d["modifiers"] = []
        governors[gt] = d

    promotions: dict[str, dict] = {}
    for r in db.execute("SELECT * FROM GovernorPromotions ORDER BY GovernorPromotionType"):
        d = dict(r)
        d["source"] = "official DB"
        d["prereqs"] = []
        d["modifiers"] = []
        promotions[d["GovernorPromotionType"]] = d
    for r in overlay["rows"].get("GovernorPromotions", []):
        pt = r.get("GovernorPromotionType")
        if not pt:
            continue
        d = {k: v for k, v in r.items() if not k.startswith("_")}
        d["source"] = ("mode overlay: %s [%s/%s]"
                       % (r.get("_source_file"), r.get("_source_action"),
                          r.get("_source_criteria")))
        d["prereqs"] = []
        d["modifiers"] = []
        promotions[pt] = d

    sets = [dict(r) for r in db.execute("SELECT * FROM GovernorPromotionSets")]
    sets += [{k: v for k, v in r.items() if not k.startswith("_")}
             for r in overlay["rows"].get("GovernorPromotionSets", [])]
    prereqs = [dict(r) for r in db.execute("SELECT * FROM GovernorPromotionPrereqs")]
    prereqs += [{k: v for k, v in r.items() if not k.startswith("_")}
                for r in overlay["rows"].get("GovernorPromotionPrereqs", [])]
    conditions = [dict(r) for r in db.execute("SELECT * FROM GovernorPromotionConditions")]
    conditions += [{k: v for k, v in r.items() if not k.startswith("_")}
                   for r in overlay["rows"].get("GovernorPromotionConditions", [])]
    links = [dict(r) for r in db.execute("SELECT * FROM GovernorPromotionModifiers")]
    links += [{k: v for k, v in r.items() if not k.startswith("_")}
              for r in overlay["rows"].get("GovernorPromotionModifiers", [])]
    gov_mods = [dict(r) for r in db.execute("SELECT * FROM GovernorModifiers")]
    gov_mods += [{k: v for k, v in r.items() if not k.startswith("_")}
                 for r in overlay["rows"].get("GovernorModifiers", [])]
    cannot_assign = [dict(r) for r in db.execute("SELECT * FROM GovernorsCannotAssign")]
    cannot_assign += [{k: v for k, v in r.items() if not k.startswith("_")}
                      for r in overlay["rows"].get("GovernorsCannotAssign", [])]
    replaces = [dict(r) for r in db.execute("SELECT * FROM GovernorReplaces")]
    replaces += [{k: v for k, v in r.items() if not k.startswith("_")}
                 for r in overlay["rows"].get("GovernorReplaces", [])]
    gw_mode = [dict(r) for r in db.execute("SELECT * FROM GreatWorks_MODE")]
    gw_mode += [{k: v for k, v in r.items() if not k.startswith("_")}
                for r in overlay["rows"].get("GreatWorks_MODE", [])]
    societies = [dict(r) for r in db.execute("SELECT * FROM SecretSocieties")]
    societies += [{k: v for k, v in r.items() if not k.startswith("_")}
                  for r in overlay["rows"].get("SecretSocieties", [])]
    trait_mods = [dict(r) for r in db.execute("SELECT * FROM TraitModifiers")]
    trait_mods += [{k: v for k, v in r.items() if not k.startswith("_")}
                   for r in overlay["rows"].get("TraitModifiers", [])]
    global_params = [{k: v for k, v in r.items() if not k.startswith("_")}
                     for r in overlay["rows"].get("GlobalParameters", [])]

    trait_link: dict[str, list[str]] = {}
    for r in trait_mods:
        trait_link.setdefault(r["TraitType"], []).append(r["ModifierId"])

    for p in prereqs:
        if p["GovernorPromotionType"] in promotions:
            promotions[p["GovernorPromotionType"]]["prereqs"].append(
                p["PrereqGovernorPromotion"])
    for l in links:
        pt = l["GovernorPromotionType"]
        if pt in promotions:
            promotions[pt]["modifiers"].append(l["ModifierId"])
    for l in gov_mods:
        gt = l["GovernorType"]
        if gt in governors:
            governors[gt]["modifiers"].append(l["ModifierId"])
    for gt, g in governors.items():
        tt = g.get("TraitType")
        if tt and tt in trait_link:
            g["modifiers"].extend(sorted(set(trait_link[tt])))

    by_gov: dict[str, list[str]] = {}
    for s in sets:
        by_gov.setdefault(s["GovernorType"], []).append(s["GovernorPromotion"])
    for gt, promos in by_gov.items():
        if gt in governors:
            governors[gt]["promotions"] = sorted(promos)
    for g in governors.values():
        g.setdefault("promotions", [])
        g["cannot_assign"] = sorted(
            r["GovernorType"] for r in cannot_assign
            if r["GovernorType"] == g["GovernorType"]
            and str(r.get("CannotAssign", "")).lower() in ("true", "1"))
        g["secret_society_type"] = next(
            (r.get("SecretSocietyType") for r in societies
             if r.get("GovernorType") == g["GovernorType"]), None)
        g["discovery_chances"] = {
            k.replace("DiscoverAt", "").replace("BaseChance", ""): v
            for r in societies if r.get("GovernorType") == g["GovernorType"]
            for k, v in r.items()
            if k.startswith("DiscoverAt") and k.endswith("BaseChance")}

    governor_direct: dict[str, dict] = {}
    for gt, g in governors.items():
        cell = {}
        for k in ("IdentityPressure", "TransitionStrength", "AssignCityState"):
            if g.get(k) is not None:
                cell[k] = g[k]
        if g.get("AssignToMajor") is not None:
            cell["AssignToMajor"] = g["AssignToMajor"]
        for k, v in g.get("discovery_chances", {}).items():
            cell["DiscoverAt%sBaseChance" % k] = v
        governor_direct[gt] = cell

    universe = {
        "governor_direct": governor_direct,
        "governors": governors,
        "promotions": promotions,
        "sets": sets,
        "prereqs": prereqs,
        "conditions": conditions,
        "promotion_modifiers": links,
        "governor_modifiers": gov_mods,
        "governors_cannot_assign": cannot_assign,
        "governor_replaces": replaces,
        "great_works_mode": gw_mode,
        "secret_societies": societies,
        "global_parameters": global_params,
        "governor_tables": gov_tables,
        "mode": overlay,
        "secret_society_governors": sorted(
            secret_society_governor_types({
                "secret_societies": societies}) | SECRET_SOCIETY_GOVERNOR_TYPES
            if societies else SECRET_SOCIETY_GOVERNOR_TYPES),
    }
    db.close()
    return universe, overlay


# --------------------------------------------------------------------------
# Reachability
# --------------------------------------------------------------------------
def _requirement_chain(db, set_id, overlay):
    if not set_id:
        return []
    out = []
    for rsr in db.execute("SELECT RequirementId FROM RequirementSetRequirements "
                          "WHERE RequirementSetId=? ORDER BY RequirementId", (set_id,)):
        rid = rsr["RequirementId"]
        req = db.execute("SELECT * FROM Requirements WHERE RequirementId=?",
                         (rid,)).fetchone()
        args = [dict(r) for r in db.execute(
            "SELECT Name, Value FROM RequirementArguments WHERE RequirementId=? ORDER BY Name",
            (rid,))]
        out.append({"requirement_set": set_id, "requirement_id": rid,
                    "requirement_type": req["RequirementType"] if req else None,
                    "inverse": bool(req["Inverse"]) if req else None,
                    "arguments": [(a["Name"], a["Value"]) for a in args],
                    "source": "official DB"})
    if out:
        return out
    ov_rsr = [r for r in overlay["rows"].get("RequirementSetRequirements", [])
              if r.get("RequirementSetId") == set_id]
    ov_req = {r.get("RequirementId"): r
              for r in overlay["rows"].get("Requirements", [])}
    ov_args: dict[str, list] = {}
    for r in overlay["rows"].get("RequirementArguments", []):
        if r.get("RequirementId"):
            ov_args.setdefault(r["RequirementId"], []).append(
                (r.get("Name"), r.get("Value")))
    for r in ov_rsr:
        rid = r["RequirementId"]
        req = ov_req.get(rid, {})
        out.append({"requirement_set": set_id, "requirement_id": rid,
                    "requirement_type": req.get("RequirementType"),
                    "inverse": str(req.get("Inverse", "0")) == "1",
                    "arguments": ov_args.get(rid, []),
                    "source": "mode overlay"})
    return out


def build_reachability(db_path, universe, overlay, game_root=None) -> list[dict]:
    """Every reachable numeric row: root -> modifier -> argument/requirements."""
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    ov_mod = {r["ModifierId"]: r for r in overlay["rows"].get("Modifiers", [])
              if r.get("ModifierId")}
    ov_args: dict[str, list[dict]] = {}
    for r in overlay["rows"].get("ModifierArguments", []):
        if r.get("ModifierId"):
            ov_args.setdefault(r["ModifierId"], []).append(r)
    ov_dyn = {r["ModifierType"]: r for r in overlay["rows"].get("DynamicModifiers", [])
              if r.get("ModifierType")}
    mod_ids = sorted({m for p in universe["promotions"].values() for m in p["modifiers"]} |
                     {m for g in universe["governors"].values() for m in g["modifiers"]})
    mod_info: dict[str, dict] = {}
    if mod_ids:
        q = ("SELECT * FROM Modifiers WHERE ModifierId IN (%s)"
             % ",".join("?" * len(mod_ids)))
        for r in db.execute(q, tuple(mod_ids)):
            mod_info[r["ModifierId"]] = dict(r)
    dyn: dict[str, dict] = {}
    for r in db.execute("SELECT ModifierType, CollectionType, EffectType FROM DynamicModifiers"):
        dyn[r["ModifierType"]] = dict(r)
    args_by_mod: dict[str, list[dict]] = {}
    if mod_ids:
        q = ("SELECT * FROM ModifierArguments WHERE ModifierId IN (%s) ORDER BY ModifierId, Name"
             % ",".join("?" * len(mod_ids)))
        for r in db.execute(q, tuple(mod_ids)):
            args_by_mod.setdefault(r["ModifierId"], []).append(dict(r))

    def provenance_of(mod_id):
        ov = ov_mod.get(mod_id, {})
        if ov and ov.get("_source_file"):
            return {"file": ov["_source_file"], "action": ov.get("_source_action"),
                    "criteria": ov.get("_source_criteria"),
                    "sha256": ov.get("_source_sha256")}
        row = db.execute("SELECT 1 FROM Modifiers WHERE ModifierId=?",
                         (mod_id,)).fetchone()
        if row:
            return {"file": "official DB copy", "action": None,
                    "criteria": None, "sha256": None}
        return None

    rows: list[dict] = []
    visited: set[str] = set()

    def add(root_gov, root_prom, mod_id, depth=0):
        if depth > 2:
            return
        lazy_fetch(mod_id)
        mi = mod_info.get(mod_id)
        def_source = "official DB"
        if mi is None and mod_id in ov_mod:
            mi = dict(ov_mod[mod_id])
            def_source = "mode overlay"
        if mi is None:
            rows.append({"root_governor": root_gov, "root_promotion": root_prom,
                         "modifier_id": mod_id, "modifier_type": None,
                         "effect_type": None, "collection": None, "argument": None,
                         "value": None, "requirement_context": [],
                         "family": "DECISION_REQUIRED",
                         "disposition": "DECISION_REQUIRED",
                         "reason": "modifier definition absent from DB copy and mode overlay",
                         "engine_integral": False, "provenance": None,
                         "package": "unresolved", "definition_source": "unresolved"})
            return
        mt = mi["ModifierType"]
        d = dyn.get(mt) or ov_dyn.get(mt) or {}
        chain = []
        for set_id in (mi.get("OwnerRequirementSetId"),
                       mi.get("SubjectRequirementSetId")):
            before = len(chain)
            chain.extend(_requirement_chain(db, set_id, overlay))
            if len(chain) == before:
                pass
        args = args_by_mod.get(mod_id)
        arg_source = def_source
        if args is None:
            args = [dict(a) for a in ov_args.get(mod_id, [])]
            arg_source = "mode overlay"
        prov = provenance_of(mod_id)
        req_ctx = ["%s->%s(%s)" % (c["requirement_set"], c["requirement_type"],
                                   ",".join("%s=%s" % a for a in c["arguments"]))
                   for c in chain]
        # requirement-set arguments are filters, never magnitudes: emit them
        # explicitly so a structural radius can never be mistaken for (or
        # contaminate) the modifier's own magnitude.
        for c in chain:
            for (aname, avalue) in c["arguments"]:
                rows.append({
                    "root_governor": root_gov, "root_promotion": root_prom,
                    "modifier_id": mod_id, "modifier_type": mt,
                    "effect_type": "REQUIREMENT:" + (c["requirement_type"] or ""),
                    "collection": None,
                    "argument": "%s.%s" % (c["requirement_set"], aname),
                    "value": avalue,
                    "requirement_context": req_ctx,
                    "family": "SPATIAL_BUDGET" if "Distance" in aname else "THRESHOLD",
                    "disposition": "EXCLUDED",
                    "reason": "requirement/filter argument (inverse=%s): scopes which plots/districts the effect applies to; never scaled" % c.get("inverse"),
                    "engine_integral": False,
                    "provenance": prov,
                    "package": (prov or {}).get("file", "official DB"),
                    "definition_source": c.get("source", "official DB"),
                })
        if not args:
            rows.append({"root_governor": root_gov, "root_promotion": root_prom,
                         "modifier_id": mod_id, "modifier_type": mt,
                         "effect_type": d.get("EffectType"),
                         "collection": d.get("CollectionType"), "argument": None,
                         "value": None, "requirement_context": req_ctx,
                         "family": "GRANT_OBJECT", "disposition": "EXCLUDED",
                         "reason": "capability modifier with no magnitude arguments",
                         "engine_integral": effect_engine_integral(d.get("EffectType")),
                         "provenance": prov, "package": prov["file"] if prov else "official DB",
                         "definition_source": def_source})
        for a in args:
            cls = _classify(mt, d.get("EffectType"), a.get("Name"), a.get("Value"))
            rows.append({"root_governor": root_gov, "root_promotion": root_prom,
                         "modifier_id": mod_id, "modifier_type": mt,
                         "effect_type": d.get("EffectType"),
                         "collection": d.get("CollectionType"),
                         "argument": a.get("Name"), "value": a.get("Value"),
                         "requirement_context": req_ctx,
                         "family": cls["family"], "disposition": cls["disposition"],
                         "reason": cls["reason"],
                         "engine_integral": cls["engine_integral"],
                         "provenance": prov,
                         "package": prov["file"] if prov else "official DB",
                         "definition_source": (def_source if args is args_by_mod.get(mod_id)
                                               else arg_source)})
            if (d.get("EffectType") == "EFFECT_ATTACH_MODIFIER"
                    and a.get("Name") == "ModifierId" and a.get("Value")
                    and a["Value"] not in visited):
                visited.add(a["Value"])
                add(root_gov, root_prom, a["Value"], depth + 1)
            if (d.get("EffectType") in ("EFFECT_ATTACH_PERMANENT_MODIFIER_TO_PLOT_UNITS",
                                        "EFFECT_ATTACH_PERMANENT_MODIFIER_TO_ADJACENT_PLOT_UNITS")
                    and a.get("Name") == "ModifierId" and a.get("Value")
                    and a["Value"] not in visited):
                visited.add(a["Value"])
                add(root_gov, root_prom, a["Value"], depth + 1)

    def lazy_fetch(mod_id):
        if mod_id in mod_info or mod_id in ov_mod:
            return
        row = db.execute("SELECT * FROM Modifiers WHERE ModifierId=?",
                         (mod_id,)).fetchone()
        if row is not None:
            mod_info[mod_id] = dict(row)
            for a in db.execute("SELECT * FROM ModifierArguments WHERE ModifierId=? "
                                "ORDER BY Name", (mod_id,)):
                args_by_mod.setdefault(mod_id, []).append(dict(a))

    for gt, g in universe["governors"].items():
        for m in g["modifiers"]:
            add(gt, None, m)
        for pt in g.get("promotions", []):
            for m in universe["promotions"].get(pt, {}).get("modifiers", []):
                add(gt, pt, m)
    attached = {pt for g in universe["governors"].values()
                for pt in g.get("promotions", [])}
    for pt, p in universe["promotions"].items():
        if pt in attached:
            continue
        for m in p["modifiers"]:
            add("(unattached)", pt, m)
    db.close()
    return rows


# --------------------------------------------------------------------------
# Direct / structural cells
# --------------------------------------------------------------------------
DIRECT_CELL_RULES = {
    "IdentityPressure": ("LOYALTY", "DECISION_REQUIRED",
        "identity pressure applied on appointment; loyalty class (Toqui hold)"),
    "TransitionStrength": ("FLAT_AMOUNT", "DECISION_REQUIRED",
        "engine-internal transition weighting when a governor moves"),
    "AssignCityState": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "boolean capability: may the governor be assigned to a city-state"),
    "AssignToMajor": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "boolean capability: may the governor be assigned to a major city"),
    "Level": ("INDIVISIBLE_COUNT", "EXCLUDED", "structural promotion-tree level"),
    "Column": ("INDIVISIBLE_COUNT", "EXCLUDED", "structural promotion-tree column"),
    "BaseAbility": ("BOOLEAN_UNLOCK", "EXCLUDED", "structural base-ability flag"),
    "HiddenWithoutPrereqs": ("BOOLEAN_UNLOCK", "EXCLUDED", "UI gating flag"),
    "EarliestGameEra": ("DURATION", "EXCLUDED", "era gate, not a magnitude"),
    "CannotAssign": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "boolean capability: governor cannot be assigned (secret societies are leader-bound)"),
    "RequiredGovernor": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "great work requires a specific governor (Voidsinger relics); selective/structural"),
    "UniqueGovernorType": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "governor uniqueness/replacement mapping; structural"),
    "ReplacesGovernorType": ("BOOLEAN_UNLOCK", "EXCLUDED",
        "governor replacement target; structural"),
    "DiscoverAtCityStateBaseChance": ("PROBABILITY", "EXCLUDED",
        "one-off game-mode discovery configuration; NOT a repeated-chance magnitude"),
    "DiscoverAtNaturalWonderBaseChance": ("PROBABILITY", "EXCLUDED",
        "one-off game-mode discovery configuration; NOT a repeated-chance magnitude"),
    "DiscoverAtGoodyHutBaseChance": ("PROBABILITY", "EXCLUDED",
        "one-off game-mode discovery configuration; NOT a repeated-chance magnitude"),
    "DiscoverAtBarbarianCampBaseChance": ("PROBABILITY", "EXCLUDED",
        "one-off game-mode discovery configuration; NOT a repeated-chance magnitude"),
}


def direct_cells(universe: dict) -> list[dict]:
    """Every direct numeric/structural governor/promotion/mode cell."""
    out = []
    seen = set()

    def emit(root, cell, value, source):
        fam, disp, why = DIRECT_CELL_RULES.get(
            cell, ("FLAT_AMOUNT", "DECISION_REQUIRED", "unclassified direct cell"))
        key = (root, cell, str(value), source)
        if key in seen or value is None or value == "":
            return
        seen.add(key)
        out.append({"root": root, "cell": cell, "value": str(value),
                    "family": fam, "disposition": disp, "reason": why,
                    "source": source})

    for gt, cell in universe["governor_direct"].items():
        for k, v in cell.items():
            emit(gt, k, v, "official DB / mode overlay")
    for pt, p in universe["promotions"].items():
        for col in ("Level", "Column"):
            emit(pt, col, p.get(col), p.get("source", "official DB"))
        if str(p.get("BaseAbility", "0")).lower() in ("true", "1"):
            emit(pt, "BaseAbility", "true", p.get("source", "official DB"))
    for c in universe["conditions"]:
        if c.get("HiddenWithoutPrereqs") not in (None, ""):
            emit(c["GovernorPromotionType"], "HiddenWithoutPrereqs",
                 c["HiddenWithoutPrereqs"], "official DB / mode overlay")
        if c.get("EarliestGameEra") not in (None, "", "NO_ERA"):
            emit(c["GovernorPromotionType"], "EarliestGameEra",
                 c["EarliestGameEra"], "official DB / mode overlay")
    for r in universe["governors_cannot_assign"]:
        emit(r["GovernorType"], "CannotAssign", r.get("CannotAssign"),
             "official DB / mode overlay")
    for r in universe["great_works_mode"]:
        emit(r.get("RequiredGovernor"), "RequiredGovernor",
             r.get("GreatWorkType"), "official DB / mode overlay")
    for r in universe["governor_replaces"]:
        emit(r.get("UniqueGovernorType"), "UniqueGovernorType",
             r.get("ReplacesGovernorType"), "official DB / mode overlay")
    for r in universe["global_parameters"]:
        out.append({"root": "(game mode)", "cell": "GlobalParameters.%s" % r["Name"],
                    "value": "raised by mode payload",
                    "family": "INDIVISIBLE_COUNT", "disposition": "EXCLUDED",
                    "reason": "mode-raised governor appointment cap (MAX_GOVERNOR_APPOINTMENTS=9): game-mode configuration, not a scalable magnitude",
                    "source": r.get("_source_file", "mode overlay")})
    return out


# --------------------------------------------------------------------------
# Side path: modifiers reachable only through unit abilities
# --------------------------------------------------------------------------
def unit_ability_modifiers(overlay: dict) -> list[dict]:
    rows = overlay["rows"]
    args: dict[str, list] = {}
    for r in rows.get("ModifierArguments", []):
        if r.get("ModifierId"):
            args.setdefault(r["ModifierId"], []).append(r)
    dyn = {r.get("ModifierType"): r for r in rows.get("DynamicModifiers", [])}
    mods = {r.get("ModifierId"): r for r in rows.get("Modifiers", [])}
    out = []
    for r in rows.get("UnitAbilityModifiers", []):
        mid = r.get("ModifierId")
        if not mid:
            continue
        mi = mods.get(mid, {})
        et = (dyn.get(mi.get("ModifierType")) or {}).get("EffectType")
        for a in args.get(mid, []):
            out.append({"unit_ability": r.get("UnitAbilityType"),
                        "modifier_id": mid, "modifier_type": mi.get("ModifierType"),
                        "effect_type": et, "argument": a.get("Name"),
                        "value": a.get("Value"),
                        "disposition": "OUT_OF_GRAPH",
                        "reason": "unit-ability attached modifier: scales unit behaviour, not governor behaviour; audited as a documented side path"})
    return out


# --------------------------------------------------------------------------
# Registry overlap
# --------------------------------------------------------------------------
def registry_overlap(mod_ids, root=".") -> dict:
    root = Path(root)
    out = {"available": False, "shared": [], "count": 0}
    try:
        from .bridge import collect_registry_rows
        rows = collect_registry_rows(root)
    except FileNotFoundError:
        return out
    reg = {r["modifier_id"] for r in rows}
    shared = sorted(m for m in mod_ids if m in reg)
    out.update({"available": True, "shared": shared, "count": len(shared)})
    return out


def build_audit(db_path, game_root=None, ruleset="Expansion2",
               conditional_overlays=True, root=".") -> dict:
    universe, overlay = discover_universe(db_path, game_root, ruleset,
                                          conditional_overlays)
    rows = build_reachability(db_path, universe, overlay, game_root)
    mod_ids = sorted({r["modifier_id"] for r in rows})
    return {
        "universe": universe,
        "rows": rows,
        "overlay": overlay,
        "direct_cells": direct_cells(universe),
        "unit_ability_modifiers": unit_ability_modifiers(overlay),
        "registry_overlap": registry_overlap(mod_ids, root),
    }




# --------------------------------------------------------------------------
# Phase 4B: production manifest derived from the audited candidate set
# --------------------------------------------------------------------------
GOVERNOR_MODULE = "governors"
GOVERNOR_MODULE_BIT = 32

# Audited families -> production transform. Combat uses the canonical combat
# formula; everything else is the additive magnitude transform. The audited
# family is preserved verbatim (never relabelled to satisfy the gate).
FAMILY_TRANSFORM = {
    "COMBAT_STRENGTH_BONUS": "canonical_combat_bonus",
}


def _fmt(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    s = f"{f:.2f}".rstrip("0").rstrip(".")
    return s


def audited_governor_candidates(audit_path) -> list[dict]:
    """Exactly the CERTIFIED_CANDIDATE rows from the checked-in audit."""
    import yaml
    doc = yaml.safe_load(Path(audit_path).read_text(encoding="utf-8"))
    out = []
    for pt, p in (doc.get("promotions") or {}).items():
        for r in p.get("rows", []):
            if r.get("disposition") != "CERTIFIED_CANDIDATE":
                continue
            out.append({
                "root_promotion": pt,
                "modifier_id": r["modifier_id"],
                "modifier_type": r.get("modifier_type"),
                "effect_type": r.get("effect_type"),
                "argument_name": r.get("argument"),
                "official_value": str(r.get("value")),
                "semantic_family": r.get("family"),
                "engine_integral": bool(r.get("engine_integral")),
                "root_governor": r.get("root_governor"),
            })
    out.sort(key=lambda r: r["modifier_id"])
    return out


def build_governor_manifest(audit_path, module: str = GOVERNOR_MODULE) -> dict:
    """Production manifest rows for exactly the audited governor candidates.

    Mechanically derived from `civ6x10/rules/governor_audit.yml` so the
    production input stays reproducible without the gitignored inventory CSV.
    Nothing is hand-maintained, no DECISION_REQUIRED / EXCLUDED / direct /
    structural / discovery-chance / requirement-filter / unit-ability row can
    enter, and the audited semantic family is preserved as-is.
    """
    cands = audited_governor_candidates(audit_path)
    rows = []
    for r in cands:
        family = r["semantic_family"]
        transform = FAMILY_TRANSFORM.get(family, "canonical_x10_multiply")
        try:
            gen = float(r["official_value"]) * 10.0
            generated = _fmt(gen)
        except (TypeError, ValueError):
            generated = r["official_value"]
        rows.append({
            "object_id": r["root_promotion"],
            "modifier_id": r["modifier_id"],
            "modifier_type": r["modifier_type"],
            "effect_type": r["effect_type"],
            "argument_name": r["argument_name"],
            "official_value": r["official_value"],
            "semantic_family": family,
            "transformation": transform,
            "generated_value": generated,
            "status": "ok",
            "confidence": "human_certified",
            "certification_source": "phase4a.1-governor-audit",
            "engine_integral": r["engine_integral"],
            "root_governor": r["root_governor"],
            "multiplier": 10.0,
        })
    return {module: rows}


def write_governor_manifest(manifest: dict, out) -> None:
    import yaml
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        yaml.safe_dump(manifest, fh, sort_keys=False, allow_unicode=True,
                       width=120)


# --------------------------------------------------------------------------
# Manifest emission (machine-readable audit decisions)
# --------------------------------------------------------------------------
def build_manifest(audit: dict) -> dict:
    universe, rows = audit["universe"], audit["rows"]
    from collections import Counter
    ss_roots = set(universe["secret_society_governors"])
    if not ss_roots:
        ss_roots = {r.get("GovernorType")
                    for r in universe.get("secret_societies", [])
                    if r.get("GovernorType")}

    def summary(items):
        c = Counter(i["disposition"] for i in items)
        return {"total": len(items),
                "CERTIFIED_CANDIDATE": c.get("CERTIFIED_CANDIDATE", 0),
                "EXCLUDED": c.get("EXCLUDED", 0),
                "DECISION_REQUIRED": c.get("DECISION_REQUIRED", 0),
                "OUT_OF_GRAPH": c.get("OUT_OF_GRAPH", 0)}

    promos = {}
    for pt, p in universe["promotions"].items():
        prows = [r for r in rows if r["root_promotion"] == pt]
        promos[pt] = {
            "level": p.get("Level"), "column": p.get("Column"),
            "base_ability": str(p.get("BaseAbility", "0")).lower() in ("true", "1"),
            "prereqs": p.get("prereqs", []),
            "modifiers": p.get("modifiers", []),
            "source": p.get("source"),
            "secret_society": p.get("GovernorPromotionType", pt) and any(
                r["root_governor"] in ss_roots for r in prows),
            "disposition_summary": summary(prows), "rows": prows,
        }
    governors = {}
    for gt, g in universe["governors"].items():
        grows = [r for r in rows if r["root_governor"] == gt]
        governors[gt] = {
            "name": g.get("Name"),
            "identity_pressure": g.get("IdentityPressure"),
            "transition_strength": g.get("TransitionStrength"),
            "assign_city_state": g.get("AssignCityState"),
            "trait_type": g.get("TraitType"),
            "secret_society": gt in ss_roots,
            "secret_society_type": g.get("secret_society_type"),
            "discovery_chances": g.get("discovery_chances", {}),
            "cannot_assign": g.get("cannot_assign", []),
            "source": g.get("source"), "load_order": g.get("source"),
            "promotions": g.get("promotions", []),
            "direct_modifiers": g.get("modifiers", []),
            "disposition_summary": summary(grows),
        }
    return {
        "audit": "Phase 4A.1 governors (audit only; no production registry rows)",
        "proposed_owner_bit": PROPOSED_GOVERNOR_MODULE_BIT,
        "proposed_next_bit_after": PROPOSED_NEXT_MODULE_BIT_AFTER_GOVERNORS,
        "counts": {
            "governors": len(governors),
            "governors_base": sum(1 for g in governors.values()
                                  if not g["secret_society"]),
            "governors_secret_society": sum(1 for g in governors.values()
                                            if g["secret_society"]),
            "promotions": len(promos),
            "promotions_base": sum(1 for p in promos.values()
                                   if not p["secret_society"]),
            "promotions_secret_society": sum(1 for p in promos.values()
                                             if p["secret_society"]),
            "reachable_rows": len(rows),
            "direct_cells": len(audit["direct_cells"]),
            "unit_ability_side_path": len(audit["unit_ability_modifiers"]),
            "typo_normalised": audit["overlay"].get("typo_normalised", 0),
        },
        "disposition_summary": {
            "reachable_rows": summary(rows),
            "direct_cells": summary(audit["direct_cells"]),
        },
        "family_summary": dict(sorted(Counter(r["family"] for r in rows).items())),
        "engine_integral_rows": [r for r in rows if r["engine_integral"]],
        "governor_tables": audit["universe"]["governor_tables"],
        "mode_files": [{"file": f["file"], "action": f["action_id"],
                        "criteria": f["criteria"], "sha256": f["sha256"],
                        "bytes": f["bytes"], "exists": f["exists"],
                        "package": f["package"]}
                       for f in audit["overlay"].get("files", [])],
        "mode_sources": audit["overlay"].get("sources", {}),
        "registry_overlap": audit["registry_overlap"],
        "governors": governors,
        "promotions": promos,
        "direct_cells": audit["direct_cells"],
        "unit_ability_modifiers": audit["unit_ability_modifiers"],
    }


def write_manifest(manifest: dict, out) -> None:
    import yaml
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        yaml.safe_dump(manifest, fh, sort_keys=False, allow_unicode=True,
                       width=120)


INVENTORY_FIELDS = ["root_governor", "root_promotion", "modifier_id",
                    "modifier_type", "effect_type", "collection", "argument",
                    "value", "family", "disposition", "engine_integral",
                    "package", "definition_source", "requirement_context",
                    "reason"]


def write_inventory_csv(rows, out) -> None:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=INVENTORY_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({**r,
                        "requirement_context": ";".join(r["requirement_context"])})


def write_graph_json(universe, rows, out) -> None:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    graph = {"governors": {}, "promotions": {}, "edges": rows}
    for gt, g in universe["governors"].items():
        graph["governors"][gt] = {
            "name": g.get("Name"),
            "identity_pressure": g.get("IdentityPressure"),
            "transition_strength": g.get("TransitionStrength"),
            "assign_city_state": g.get("AssignCityState"),
            "trait_type": g.get("TraitType"),
            "secret_society_type": g.get("secret_society_type"),
            "source": g.get("source"),
            "promotions": g.get("promotions", []),
            "direct_modifiers": g.get("modifiers", []),
        }
    for pt, p in universe["promotions"].items():
        graph["promotions"][pt] = {
            "level": p.get("Level"), "column": p.get("Column"),
            "base_ability": p.get("BaseAbility"),
            "prereqs": p.get("prereqs", []), "modifiers": p.get("modifiers", []),
            "source": p.get("source"),
        }
    out.write_text(json.dumps(graph, indent=1, sort_keys=True,
                              default=str), encoding="utf-8")
