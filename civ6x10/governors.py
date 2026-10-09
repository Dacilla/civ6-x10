"""Phase 4A: closed-world Governor / governor-promotion audit.

AUDIT ONLY. This module discovers every official Governor and governor
promotion actually present, walks the reachable modifier / argument /
requirement graph, classifies each numeric gameplay value against the
project's existing semantic vocabulary, and emits a machine-readable manifest
plus an inventory/graph dataset.

It deliberately writes NO production registry rows: the Phase 4B production
slice is a separate, reviewed decision (docs/GOVERNOR_AUDIT.md).

Discovery world (closed world, derived from the installed official database
copy plus the mode-gated Secret Societies XML that ships with the game):

  Base / Rise & Fall / Gathering Storm content  -> Governors, GovernorPromotions,
      GovernorPromotionSets, GovernorPromotionModifiers, GovernorPromotionPrereqs,
      GovernorPromotionConditions, GovernorModifiers, Governors_XP2,
      GovernorsCannotAssign, Governors.TraitType -> TraitModifiers.
  New Frontier game mode (Secret Societies)    -> SecretSocieties,
      plus the same GovernorPromotionSets / GovernorPromotions /
      GovernorPromotionModifiers tables populated by
      DLC/Ethiopia/Data/Ethiopia_SecretSocieties_MODE.xml only when
      GAMEMODE_SECRETSOCIETIES is active (hence absent from a clean DB copy).

Provenance: every discovered row is attributed to the package/file/UpdateDatabase
action that ships it (see provenance_from_install), so a future audit can tell
base content from mode-gated content without loading the game.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
from pathlib import Path

# --------------------------------------------------------------------------
# Ownership design (report only in Phase 4A - NOT implemented anywhere).
# civ6x10.production.MODULE_BITS: traits 1, policies 2, governments 4,
# pantheons 8, wonders 16. The CE writer's s_modEnabled[5] mirrors that and
# already reads an X10_MODULE_GOVERNORS config key (currently ignored).
# Next owner bit: 32 = governors (then 64 = suzerain).
# --------------------------------------------------------------------------
PROPOSED_GOVERNOR_MODULE_BIT = 32
PROPOSED_NEXT_MODULE_BIT_AFTER_GOVERNORS = 64

DEFAULT_GAME_ROOT = (
    r"C:\Program Files (x86)\Steam\steamapps\common"
    r"\Sid Meier's Civilization VI")

SECRET_SOCIETY_XML_REL = os.path.join(
    "DLC", "Ethiopia", "Data", "Ethiopia_SecretSocieties_MODE.xml")

SECRET_SOCIETY_GOVERNORS = {
    "GOVERNOR_OWLS_OF_MINERVA": "SECRETSOCIETY_OWLS_OF_MINERVA",
    "GOVERNOR_HERMETIC_ORDER": "SECRETSOCIETY_HERMETIC_ORDER",
    "GOVERNOR_VOIDSONGERS": "SECRETSOCIETY_VOIDSONGERS",
    "GOVERNOR_SANGUINE_PACT": "SECRETSOCIETY_SANGUINE_PACT",
}

# Effect types that consume their magnitude integrally at the game-effect
# layer (Phase 3F/3G proven). Phase 4B must inherit the same gate.
ENGINE_INTEGRAL_EFFECTS = {"EFFECT_ADJUST_BUILDING_YIELD_CHANGE"}

# Curated governor classification: effect_type -> (family, disposition,
# rationale). Keyed by effect (never by effect alone across carriers when the
# disposition differs - a few modifier_type-specific overrides follow below).
# Dispositions: CERTIFIED_CANDIDATE (Phase-4B-eligible), EXCLUDED,
# DECISION_REQUIRED. Anything not listed fails the closed-world test.
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
    "EFFECT_ADJUST_FEATURE_NO_IMPROVEMENT_APPEAL_GOVERNOR": ("FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat appeal per unimproved feature; appeal is float-valued"),
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
    "EFFECT_ADJUST_EXTRA_HEAL_GOVERNOR": ("PERCENT_BONUS", "CERTIFIED_CANDIDATE",
        "percent extra healing for units in city (Laying on of Hands +100%)"),
    "EFFECT_ADJUST_PLAYER_YIELD_CHANGE_PER_GREAT_PERSON_CLASS_ON_RESOURCE": ("FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat yield per great person of class (Hermetic ley lines +1)"),
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
        "city combat-strength points (Garrison Commander +5); combat transform"),
    "EFFECT_ADJUST_CITY_FRIENDLY_COMBAT_BONUS": ("COMBAT_STRENGTH_BONUS", "CERTIFIED_CANDIDATE",
        "friendly-unit combat-strength points in city (Head Falconer +5); combat transform"),
    "EFFECT_ADJUST_UNIT_AGAINST_DISTRICT_COMBAT_BONUS": ("COMBAT_STRENGTH_BONUS", "CERTIFIED_CANDIDATE",
        "combat-strength points against districts (Serasker +10); combat transform"),
    "EFFECT_ADJUST_CITY_RELIGIOUS_COMBAT_BONUS": ("COMBAT_STRENGTH_BONUS", "CERTIFIED_CANDIDATE",
        "theological-combat strength points (Grand Inquisitor +10); combat transform"),
    "EFFECT_ADJUST_CITY_AIR_DEFENSE_BONUS": ("COMBAT_STRENGTH_BONUS", "CERTIFIED_CANDIDATE",
        "city air-defense rating (Air Defense Initiative +25); combat-equivalent rating"),
    "EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER": ("COMBAT_STRENGTH_BONUS", "CERTIFIED_CANDIDATE",
        "unit combat-strength modifier (Sanguine intimidate -5); same effect as the live-proven Toqui combat transform (b_k), including negative values"),
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
    "EFFECT_ADJUST_UNIT_BUILDER_CHARGES": ("CHARGES", "DECISION_REQUIRED",
        "builder charges are whole uses (Guildmaster / vampire builds); integral gate candidate"),
    "EFFECT_ADJUST_CITY_SETTLER_CONSUME_POP": ("INDIVISIBLE_COUNT", "DECISION_REQUIRED",
        "settler population consumption is a whole-citizen flow (Expedition)"),
    # --- loyalty / identity pressure (Toqui hold class) --------------------
    "EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE": ("LOYALTY", "EXCLUDED",
        "project rule: EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE is temporarily excluded (Toqui stored-form hold, 2026-10-08); governor carriers inherit the same hold"),
    "EFFECT_ADJUST_CITY_IDENTITY_PER_TURN": ("LOYALTY", "DECISION_REQUIRED",
        "identity/loyalty gained per turn (Owls counterspies +4); same pressure class as the Toqui hold"),
    "EFFECT_ADJUST_CITY_RELIGION_PRESSURE": ("LOYALTY", "DECISION_REQUIRED",
        "religious pressure is a pressure rate (Cardinal Bishop); same class as identity pressure - needs review"),
    "EFFECT_ADJUST_CITY_RELIGIOUS_HEAL": ("FLAT_AMOUNT", "DECISION_REQUIRED",
        "religious-unit healing: percent-vs-flat unresolved (Laying on of Hands)"),
    "EFFECT_ADJUST_GOVERNOR_GRIEVENCE_SCORE": ("FLAT_AMOUNT", "DECISION_REQUIRED",
        "grievance score is a whole-point score applied for a duration (Capou Agha); score+Turns split unresolved"),
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
    "EFFECT_ADJUST_PLAYER_YIELD_CHANGE_PER_GREAT_PERSON_CLASS_ON_RESOURCE": ("FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat yield per great person of a class (Hermetic ley lines +1)"),
    "EFFECT_ADJUST_CITY_INNER_DEFENSE": ("COMBAT_STRENGTH_BONUS", "CERTIFIED_CANDIDATE",
        "city inner-defense rating (Redoubt +5); defense rating is a combat-equivalent strength value"),
    "EFFECT_ADJUST_UNIT_BUILD_CHARGES": ("CHARGES", "DECISION_REQUIRED",
        "builder charges are whole uses (Guildmaster / vampire builds); integral gate candidate"),
    "EFFECT_ADJUST_CITY_GROWTH": ("PERCENT_BONUS", "CERTIFIED_CANDIDATE",
        "percent city growth (Surplus Logistics +20%)"),
    "EFFECT_ADJUST_CITY_YIELD_MODIFIER": ("PERCENT_BONUS", "CERTIFIED_CANDIDATE",
        "percent city yield modifier (Librarian +15% science/culture); scalar per-definition (mixed-domain family excludes vector siblings)"),
    "EFFECT_ADJUST_CITY_YIELD_PER_POPULATION": ("FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat yield per citizen (Connoisseur culture +1, Researcher science +1)"),
    "EFFECT_ADJUST_CITY_EXTRA_ACCUMULATION": ("INDIVISIBLE_COUNT", "DECISION_REQUIRED",
        "extra strategic accumulation is a whole-unit flow (Defense Logistics +1)"),
    "EFFECT_ADJUST_TRADE_ROUTE_YIELD_TO_OTHERS": ("FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat yield sent to other civs on trade routes (Surplus Logistics food +2); Domestic flag is a selector"),
    # --- governor titles (shared with traits module) ----------------------
    "EFFECT_ADJUST_PLAYER_GOVERNOR_POINTS": ("GOVERNOR_TITLES", "EXCLUDED",
        "already certified under TRAITS ownership (SULEIMAN_GOVERNOR_POINTS +1, narrow Delta-on-GOVERNOR_POINTS rule); governor module must not re-own/double-scale"),
}

# modifier_type-specific overrides where the same effect behaves differently.
CURATED_MODIFIER_OVERRIDES = {
    "MODIFIER_GOVERNOR_ADJUST_DISTRICT_COMBAT_BONUS": ("SPATIAL_BUDGET", "EXCLUDED",
        "subject requirement PLOT_10_TILES_AWAY_MAX_REQUIREMENTS makes the bonus a spatial-radius effect; radius is structural scope, not a magnitude"),
}

# Families that Phase 4B could certify ADDITIVE for (audit opinion only).
ADDITIVE_CANDIDATE_FAMILIES = {
    "GOLD", "FLAT_YIELD", "FLAT_AMOUNT", "PRODUCTION_PERCENT", "PERCENT_BONUS",
    "EXPERIENCE", "HOUSING", "AMENITY", "TOURISM",
}

SELECTOR_ARG_NAMES = {
    "YieldType", "BuildingType", "DistrictType", "ImprovementType",
    "GreatWorkObjectType", "ProjectType", "ModifierId", "ResourceType",
    "UnitType", "FeatureType", "TerrainType", "EraType", "Key",
    "GreatPersonClassType", "RouteType", "ReligionType", "Domestic",
    "DomesticCities", "ForeignCities", "CanPurchase", "Enable", "Enabled",
    "Ignore", "Prevent", "Protected", "IncludeWonder",
}


# --------------------------------------------------------------------------
# XML (mode-gated Secret Societies) parsing
# --------------------------------------------------------------------------
def _xml_rows(xml_text: str, table: str) -> list[dict]:
    """Rows of <table> in either attribute-form or nested-element form."""
    m = re.search(r"<%s>(.*?)</%s>" % (table, table), xml_text, re.S)
    if not m:
        return []
    body = m.group(1)
    out: list[dict] = []
    for row in re.finditer(r"<Row(?:\s+([^>]*?))?/>|<Row(?:\s+([^>]*?))?>(.*?)</Row>",
                           body, re.S):
        if row.group(1) or (row.group(1) == "" and row.group(3) is None):
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', row.group(1) or ""))
            if attrs:
                out.append(attrs)
                continue
        inner = row.group(3) or ""
        if not inner.strip():
            continue
        attrs = dict(re.findall(r"<(\w+)>([^<]*)</\1>", inner))
        if attrs:
            out.append(attrs)
    return out


MODE_TABLES = ("Governors", "GovernorPromotionSets", "GovernorPromotions",
               "GovernorPromotionPrereqs", "GovernorPromotionConditions",
               "GovernorPromotionModifiers", "GovernorModifiers",
               "GovernorsCannotAssign", "SecretSocieties", "TraitModifiers",
               "UnitAbilities", "UnitAbilityModifiers",
               "Modifiers", "ModifierArguments", "DynamicModifiers",
               "Requirements", "RequirementSets", "RequirementSetRequirements",
               "RequirementArguments")

# Tables whose rows are definition payloads merged into the audit view when a
# clean DB copy lacks the mode-gated content.
_OVERLAY_DEF_TABLES = ("Modifiers", "ModifierArguments", "DynamicModifiers",
                       "Requirements", "RequirementSets",
                       "RequirementSetRequirements", "RequirementArguments")


def _normalise_row_keys(r: dict) -> dict:
    """Normalise typo'd attribute names in shipped XML (ModifierID->ModifierId)."""
    r = dict(r)
    if "ModifierId" not in r and "ModifierID" in r:
        r["ModifierId"] = r.pop("ModifierID")
    if "RequirementId" not in r and "RequirementID" in r:
        r["RequirementId"] = r.pop("RequirementID")
    if "RequirementSetId" not in r and "RequirementSetID" in r:
        r["RequirementSetId"] = r.pop("RequirementSetID")
    return r


def load_mode_overlay(game_root: str | Path | None = None) -> dict:
    """Full mode-gated (Secret Societies) content, definition rows included.

    The clean official DB copy does NOT contain these rows: they are inserted
    only when GAMEMODE_SECRETSOCIETIES is active, which is why they are
    discovered from the shipped XML and merged into the audit view so the
    closed world is genuinely closed for mode content too.
    """
    root = Path(game_root) if game_root else Path(DEFAULT_GAME_ROOT)
    path = root / SECRET_SOCIETY_XML_REL
    overlay = {"available": path.is_file(), "source": str(path), "rows": {},
               "typo_normalised": 0}
    if not path.is_file():
        return overlay
    text = path.read_text(encoding="utf-8")
    for table in MODE_TABLES:
        rows = [_normalise_row_keys(r) for r in _xml_rows(text, table)]
        overlay["rows"][table] = rows
    overlay["typo_normalised"] = sum(
        1 for t in ("GovernorPromotionModifiers", "RequirementSetRequirements")
        for r in overlay["rows"].get(t, [])
        if "ModifierId" not in r and "ModifierID" in r)
    return overlay


def load_secret_societies(game_root: str | Path | None = None) -> dict:
    """Mode-gated Secret Societies content, tagged with provenance."""
    overlay = load_mode_overlay(game_root)
    result = {"available": overlay["available"], "source": overlay["source"],
              "governors": {}, "promotions": {}, "sets": [], "links": [],
              "governor_rows": overlay["rows"].get("Governors", []),
              "trait_modifiers": overlay["rows"].get("TraitModifiers", []),
              "typo_normalised": overlay["typo_normalised"]}
    rows = overlay["rows"]
    for r in rows.get("SecretSocieties", []):
        gov = r.get("GovernorType")
        result["governors"][gov] = {
            "GovernorType": gov,
            "SecretSocietyType": r.get("SecretSocietyType"),
            "Name": r.get("Name"),
            "source": "New Frontier game mode (Secret Societies)",
            "source_file": SECRET_SOCIETY_XML_REL,
            "load_order": ("DLC/Ethiopia UpdateDatabase id=EthiopiaGameplayXP1_MODE "
                           "criteria=Ethiopia_Mode (GAMEMODE_SECRETSOCIETIES)"),
        }
    result["sets"] = rows.get("GovernorPromotionSets", [])
    result["prereqs"] = rows.get("GovernorPromotionPrereqs", [])
    result["conditions"] = rows.get("GovernorPromotionConditions", [])
    for r in rows.get("GovernorPromotions", []):
        r = dict(r)
        r["source"] = "New Frontier game mode (Secret Societies)"
        r["source_file"] = SECRET_SOCIETY_XML_REL
        result["promotions"][r["GovernorPromotionType"]] = r
    for r in rows.get("GovernorPromotionModifiers", []):
        if "ModifierId" in r and "GovernorPromotionType" in r:
            result["links"].append(r)
    return result


# --------------------------------------------------------------------------
# Provenance: which installed package/file/action ships each ID
# --------------------------------------------------------------------------
def provenance_from_install(ids: list[str], game_root: str | Path | None = None
                            ) -> dict:
    """Map each governor ID to its shipping package/file (best effort)."""
    root = Path(game_root) if game_root else Path(DEFAULT_GAME_ROOT)
    want = {i for i in ids if i}
    found: dict[str, dict] = {}
    if not root.is_dir() or not want:
        return found
    # load order index: base < expansions < DLC (alpha), matching the
    # engine's base -> expansion -> DLC resolution order.
    order = [("Base", root / "Base"), ("Rise & Fall", root / "DLC" / "Expansion1"),
             ("Gathering Storm", root / "DLC" / "Expansion2")]
    for d in sorted((root / "DLC").glob("*")) if (root / "DLC").is_dir() else []:
        if d.name in ("Expansion1", "Expansion2"):
            continue
        order.append((f"DLC/{d.name}", d))
    for pkg, pkg_dir in order:
        if not pkg_dir.is_dir():
            continue
        for f in pkg_dir.rglob("*.xml"):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            hit = None
            for i in want:
                if i in text:
                    hit = i
                    break
            if hit is None:
                continue
            rel = str(f.relative_to(root)).replace("\\", "/")
            prev = found.get(hit)
            if prev is None or order.index((pkg, pkg_dir)) < prev["_rank"]:
                found[hit] = {"package": pkg, "file": rel, "_rank": order.index((pkg, pkg_dir))}
    for v in found.values():
        v.pop("_rank", None)
    return found


# --------------------------------------------------------------------------
# Universe discovery
# --------------------------------------------------------------------------
def discover_universe(db_path: str | Path, game_root: str | Path | None = None
                      ) -> dict:
    """Closed-world discovery of governors, promotions and their attachments."""
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    ss = load_secret_societies(game_root)

    governors: dict[str, dict] = {}
    for r in db.execute("SELECT * FROM Governors ORDER BY GovernorType"):
        d = dict(r)
        d["source"] = "Base/Rise & Fall/Gathering Storm (official DB)"
        d["modifiers"] = []
        governors[d["GovernorType"]] = d
    xp2 = {r["GovernorType"]: dict(r) for r in db.execute("SELECT * FROM Governors_XP2")}
    for g in governors.values():
        if g["GovernorType"] in xp2:
            g["AssignToMajor"] = xp2[g["GovernorType"]].get("AssignToMajor")

    promotions: dict[str, dict] = {}
    for r in db.execute("SELECT * FROM GovernorPromotions ORDER BY GovernorPromotionType"):
        d = dict(r)
        d["source"] = "Base/Rise & Fall/Gathering Storm (official DB)"
        d["prereqs"] = []
        d["modifiers"] = []
        promotions[d["GovernorPromotionType"]] = d
    sets: list[dict] = [dict(r) for r in db.execute("SELECT * FROM GovernorPromotionSets")]
    prereqs: list[dict] = [dict(r) for r in db.execute("SELECT * FROM GovernorPromotionPrereqs")]
    conditions: list[dict] = [dict(r) for r in db.execute("SELECT * FROM GovernorPromotionConditions")]
    links: list[dict] = [dict(r) for r in db.execute("SELECT * FROM GovernorPromotionModifiers")]
    gov_mods: list[dict] = [dict(r) for r in db.execute("SELECT * FROM GovernorModifiers")]
    cannot_assign: list[dict] = [dict(r) for r in db.execute("SELECT * FROM GovernorsCannotAssign")]

    # fold the mode-gated Secret Societies content into the same structures
    overlay_governors = {r.get("GovernorType"): r for r in ss["governor_rows"]}
    for gt, g in ss["governors"].items():
        g2 = dict(g)
        g2["modifiers"] = []
        row = overlay_governors.get(gt, {})
        for k in ("IdentityPressure", "TransitionStrength", "AssignCityState",
                  "Image", "PortraitImage"):
            if k in row:
                g2[k] = row[k]
        governors[gt] = g2
    for pt, p in ss["promotions"].items():
        p2 = dict(p)
        p2["prereqs"] = []
        p2["modifiers"] = []
        promotions[pt] = p2
    sets.extend(ss["sets"])
    prereqs.extend([{"GovernorPromotionType": r["GovernorPromotionType"],
                    "PrereqGovernorPromotion": r["PrereqGovernorPromotion"]}
                   for r in ss["prereqs"]])
    conditions.extend(ss["conditions"])
    links.extend([{"GovernorPromotionType": r["GovernorPromotionType"],
                  "ModifierId": r["ModifierId"]}
                 for r in ss["links"]])
    # governor -> trait -> trait modifiers (Ibrahim: TRAIT_LEADER_SULEIMAN_
    # GOVERNOR -> SULEIMAN_GOVERNOR_POINTS; shared with the traits module).
    trait_mods = [dict(r) for r in db.execute("SELECT * FROM TraitModifiers")]
    trait_mods.extend(ss["trait_modifiers"])
    trait_link: dict[str, list[str]] = {}
    for r in trait_mods:
        trait_link.setdefault(r["TraitType"], []).append(r["ModifierId"])
    # mode-gated governor-scoped definition payloads (clean copy lacks them)
    mode_overlay = load_mode_overlay(game_root)
    db.close()

    for p in prereqs:
        if p["GovernorPromotionType"] in promotions:
            promotions[p["GovernorPromotionType"]]["prereqs"].append(p["PrereqGovernorPromotion"])
    for l in links:
        pt = l["GovernorPromotionType"]
        if pt in promotions:
            promotions[pt]["modifiers"].append(l["ModifierId"])
    for l in gov_mods:
        gt = l["GovernorType"]
        if gt in governors:
            governors[gt]["modifiers"].append(l["ModifierId"])
    # trait-attached modifiers (Ibrahim: TRAIT_LEADER_SULEIMAN_GOVERNOR ->
    # SULEIMAN_GOVERNOR_POINTS, shared with the traits module).
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

    # raw direct cells per governor (for direct_cells accounting)
    governor_direct: dict[str, dict] = {}
    for gt, g in governors.items():
        cell = {}
        for k in ("IdentityPressure", "TransitionStrength", "AssignCityState"):
            if g.get(k) is not None:
                cell[k] = g[k]
        if g.get("AssignToMajor") is not None:
            cell["AssignToMajor"] = g["AssignToMajor"]
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
        "secret_societies": {
            "available": ss["available"],
            "source": ss["source"],
            "governors": sorted(ss["governors"]),
            "promotions": sorted(ss["promotions"]),
            "typo_normalised": ss["typo_normalised"],
        },
    }
    return universe, mode_overlay


# --------------------------------------------------------------------------
# Reachability + classification
# --------------------------------------------------------------------------
def _requirement_chain(db, set_id: str | None) -> list[dict]:
    if not set_id:
        return []
    out = []
    for rsr in db.execute("SELECT RequirementId FROM RequirementSetRequirements "
                          "WHERE RequirementSetId=? ORDER BY RequirementId", (set_id,)):
        rid = rsr["RequirementId"]
        req = db.execute("SELECT * FROM Requirements WHERE RequirementId=?", (rid,)).fetchone()
        args = [dict(r) for r in db.execute(
            "SELECT Name, Value FROM RequirementArguments WHERE RequirementId=? ORDER BY Name",
            (rid,))]
        out.append({
            "requirement_set": set_id,
            "requirement_id": rid,
            "requirement_type": req["RequirementType"] if req else None,
            "inverse": bool(req["Inverse"]) if req else None,
            "arguments": [(a["Name"], a["Value"]) for a in args],
        })
    return out


def effect_engine_integral(effect_type: str | None) -> bool:
    return effect_type in ENGINE_INTEGRAL_EFFECTS


def _classify(modifier_type: str, effect_type: str, arg: str, value: str,
              req_chain: list[dict]) -> dict:
    """Classify one reachable row into the audit vocabulary."""
    if arg in SELECTOR_ARG_NAMES:
        return {"family": "SELECTOR", "disposition": "EXCLUDED",
                "reason": "selector/type argument, never a magnitude",
                "engine_integral": False}
    numeric = None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        pass
    if numeric is None:
        return {"family": "SELECTOR", "disposition": "EXCLUDED",
                "reason": "non-numeric reference value",
                "engine_integral": False}
    engine_integral = effect_type in ENGINE_INTEGRAL_EFFECTS
    fam, disp, reason = None, None, None
    ov = CURATED_MODIFIER_OVERRIDES.get(modifier_type)
    if ov is not None:
        fam, disp, reason = ov
    else:
        rule = CURATED_EFFECT_RULES.get(effect_type)
        if rule is not None:
            fam, disp, reason = rule
    if fam is None:
        fam, disp, reason = ("DECISION_REQUIRED", "DECISION_REQUIRED",
                             "no curated governor semantics for this effect")

    if engine_integral and disp == "CERTIFIED_CANDIDATE":
        reason += "; engine applies integrally -> integral gate required"
    return {"family": fam, "disposition": disp, "reason": reason,
            "engine_integral": engine_integral}

def build_reachability(db_path: str | Path, universe: dict,
                       overlay: dict | None = None,
                       game_root: str | Path | None = None) -> list[dict]:
    """Every reachable numeric row, root -> modifier -> argument/requirements.

    Definition payloads come from the official DB copy; anything the clean copy
    lacks (mode-gated Secret Societies content) is resolved from the shipped
    XML overlay and tagged as such, so the closed world stays closed.
    """
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    overlay = overlay or {"rows": {}, "available": False}
    ov_mod = {r["ModifierId"]: r for r in overlay["rows"].get("Modifiers", [])
              if r.get("ModifierId")}
    ov_args: dict[str, list[dict]] = {}
    for r in overlay["rows"].get("ModifierArguments", []):
        if r.get("ModifierId"):
            ov_args.setdefault(r["ModifierId"], []).append(r)
    ov_dyn = {r["ModifierType"]: r for r in overlay["rows"].get("DynamicModifiers", [])
              if r.get("ModifierType")}
    ov_req = {r["RequirementId"]: r for r in overlay["rows"].get("Requirements", [])
              if r.get("RequirementId")}
    ov_rsr: dict[str, list[str]] = {}
    for r in overlay["rows"].get("RequirementSetRequirements", []):
        if r.get("RequirementSetId") and r.get("RequirementId"):
            ov_rsr.setdefault(r["RequirementSetId"], []).append(r["RequirementId"])
    ov_reqargs: dict[str, list[tuple[str, str]]] = {}
    for r in overlay["rows"].get("RequirementArguments", []):
        if r.get("RequirementId"):
            ov_reqargs.setdefault(r["RequirementId"], []).append(
                (r.get("Name"), r.get("Value")))

    def ov_requirement_chain(set_id):
        if not set_id:
            return []
        out = []
        for rid in ov_rsr.get(set_id, []):
            req = ov_req.get(rid, {})
            out.append({"requirement_set": set_id, "requirement_id": rid,
                        "requirement_type": req.get("RequirementType"),
                        "inverse": str(req.get("Inverse", "0")) == "1",
                        "arguments": ov_reqargs.get(rid, [])})
        return out
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

    prov = provenance_from_install(sorted(mod_ids) + sorted(universe["promotions"]) +
                                   sorted(universe["governors"]), game_root)

    rows: list[dict] = []
    visited: set[str] = set()

    def lazy_fetch(mod_id):
        """Fetch a nested modifier's definition/args on demand."""
        if mod_id in mod_info or mod_id in ov_mod:
            return
        row = db.execute("SELECT * FROM Modifiers WHERE ModifierId=?", (mod_id,)).fetchone()
        if row is not None:
            mod_info[mod_id] = dict(row)
            for a in db.execute(
                    "SELECT * FROM ModifierArguments WHERE ModifierId=? ORDER BY Name",
                    (mod_id,)):
                args_by_mod.setdefault(mod_id, []).append(dict(a))

    def add(root_gov, root_prom, mod_id):
        lazy_fetch(mod_id)
        mi = mod_info.get(mod_id)
        def_source = "official DB"
        if mi is None and mod_id in ov_mod:
            mi = dict(ov_mod[mod_id])
            def_source = "mode overlay (Secret Societies XML)"
        if mi is None:
            rows.append({
                "root_governor": root_gov, "root_promotion": root_prom,
                "modifier_id": mod_id, "modifier_type": None, "effect_type": None,
                "collection": None, "argument": None, "value": None,
                "requirement_context": [], "family": "DECISION_REQUIRED",
                "disposition": "DECISION_REQUIRED",
                "reason": "modifier definition absent from clean DB copy and XML overlay",
                "engine_integral": False,
                "provenance": prov.get(mod_id, {}).get("file", "unresolved"),
                "package": prov.get(mod_id, {}).get("package", "unresolved"),
                "definition_source": "unresolved",
            })
            return
        mt = mi["ModifierType"]
        d = dyn.get(mt) or ov_dyn.get(mt) or {}
        chain = []
        for set_id in (mi.get("OwnerRequirementSetId"), mi.get("SubjectRequirementSetId")):
            before = len(chain)
            chain.extend(_requirement_chain(db, set_id))
            if len(chain) == before:
                chain.extend(ov_requirement_chain(set_id))
        args = args_by_mod.get(mod_id)
        arg_source = def_source
        if args is None:
            args = [dict(a) for a in ov_args.get(mod_id, [])]
            arg_source = "mode overlay (Secret Societies XML)"
        if not args:
            # capability modifiers carry no magnitude at all (copy luxuries
            # for import, copy strategics): still account for them explicitly
            # so every promotion/disposition pair is closed-world.
            rows.append({
                "root_governor": root_gov, "root_promotion": root_prom,
                "modifier_id": mod_id, "modifier_type": mt,
                "effect_type": d.get("EffectType"), "collection": d.get("CollectionType"),
                "argument": None, "value": None,
                "requirement_context": [f"{c['requirement_set']}->"
                                        f"{c['requirement_type']}" for c in chain],
                "family": "GRANT_OBJECT", "disposition": "EXCLUDED",
                "reason": "capability modifier with no magnitude arguments",
                "engine_integral": effect_engine_integral(d.get("EffectType")),
                "provenance": prov.get(mod_id, {}).get("file", "official DB"),
                "package": prov.get(mod_id, {}).get("package", "official DB"),
                "definition_source": def_source,
            })
        for a in args:
            cls = _classify(mt, d.get("EffectType"), a["Name"], a["Value"], chain)
            # EFFECT_ATTACH_MODIFIER nests another definition behind a
            # ModifierId argument: follow it once so nothing reachable from a
            # promotion root stays unaccounted for.
            if (d.get("EffectType") == "EFFECT_ATTACH_MODIFIER"
                    and a["Name"] == "ModifierId" and a["Value"]
                    and a["Value"] not in visited):
                visited.add(a["Value"])
                add(root_gov, root_prom, a["Value"])
            rows.append({
                "root_governor": root_gov, "root_promotion": root_prom,
                "modifier_id": mod_id, "modifier_type": mt,
                "effect_type": d.get("EffectType"), "collection": d.get("CollectionType"),
                "argument": a["Name"], "value": a["Value"],
                "requirement_context": [f"{c['requirement_set']}->"
                                        f"{c['requirement_type']}" for c in chain],
                "family": cls["family"], "disposition": cls["disposition"],
                "reason": cls["reason"], "engine_integral": cls["engine_integral"],
                "provenance": prov.get(mod_id, {}).get("file", "official DB"),
                "package": prov.get(mod_id, {}).get("package", "official DB"),
                "definition_source": arg_source,
            })

    for gt, g in universe["governors"].items():
        for m in g["modifiers"]:
            add(gt, None, m)
        for pt in g.get("promotions", []):
            for m in universe["promotions"].get(pt, {}).get("modifiers", []):
                add(gt, pt, m)
    # promotions with no owning governor (should not happen; closed world)
    attached = {pt for g in universe["governors"].values() for pt in g.get("promotions", [])}
    for pt, p in universe["promotions"].items():
        if pt in attached:
            continue
        for m in p["modifiers"]:
            add("(unattached)", pt, m)
    db.close()
    return rows






# --------------------------------------------------------------------------
# Manifest emission (machine-readable audit decisions)
# --------------------------------------------------------------------------
def build_manifest(audit: dict) -> dict:
    universe, rows = audit["universe"], audit["rows"]
    from collections import Counter
    ss_roots = set(universe["secret_societies"]["governors"])

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
            "level": p.get("Level"),
            "column": p.get("Column"),
            "base_ability": str(p.get("BaseAbility", "0")).lower() in ("true", "1"),
            "prereqs": p.get("prereqs", []),
            "modifiers": p.get("modifiers", []),
            "source": p.get("source"),
            "secret_society": any(r["root_governor"] in ss_roots for r in prows),
            "disposition_summary": summary(prows),
            "rows": prows,
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
            "secret_society_type": g.get("SecretSocietyType"),
            "source": g.get("source"),
            "load_order": g.get("load_order"),
            "promotions": g.get("promotions", []),
            "direct_modifiers": g.get("modifiers", []),
            "disposition_summary": summary(grows),
        }
    return {
        "audit": "Phase 4A governors (audit only; no production registry rows)",
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
        },
        "disposition_summary": {
            "reachable_rows": summary(rows),
            "direct_cells": summary(audit["direct_cells"]),
        },
        "family_summary": dict(sorted(Counter(r["family"] for r in rows).items())),
        "engine_integral_rows": [r for r in rows if r["engine_integral"]],
        "secret_societies": universe["secret_societies"],
        "registry_overlap": audit["registry_overlap"],
        "governors": governors,
        "promotions": promos,
        "direct_cells": audit["direct_cells"],
        "unit_ability_modifiers": audit["unit_ability_modifiers"],
    }


def write_manifest(manifest: dict, out: str | Path) -> None:
    import yaml
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        yaml.safe_dump(manifest, fh, sort_keys=False, allow_unicode=True,
                       width=120)

# --------------------------------------------------------------------------
# Direct numeric DB cells keyed by governor / promotion / set
# --------------------------------------------------------------------------
DIRECT_GOVERNOR_CELLS = [
    ("Governors.IdentityPressure", "loyalty/identity applied on appointment",
     "LOYALTY", "DECISION_REQUIRED",
     "identity pressure is a pressure rate; same class as the Toqui hold"),
    ("Governors.TransitionStrength", "transition strength used when a governor moves",
     "FLAT_AMOUNT", "DECISION_REQUIRED",
     "engine-internal transition weighting, not a player-facing magnitude"),
    ("Governors.AssignCityState", "whether the governor may be assigned to a city-state",
     "BOOLEAN_UNLOCK", "EXCLUDED", "boolean capability, not a magnitude"),
    ("Governors_XP2.AssignToMajor", "whether the governor may be assigned to a major city",
     "BOOLEAN_UNLOCK", "EXCLUDED", "boolean capability, not a magnitude"),
    ("GovernorPromotions.Level", "promotion tree level (0 base .. 3)",
     "INDIVISIBLE_COUNT", "EXCLUDED",
     "structural tree position, not a magnitude"),
    ("GovernorPromotions.Column", "promotion tree column",
     "INDIVISIBLE_COUNT", "EXCLUDED", "structural tree position, not a magnitude"),
    ("GovernorPromotions.BaseAbility", "base (free) ability flag",
     "BOOLEAN_UNLOCK", "EXCLUDED", "structural flag, not a magnitude"),
    ("GovernorPromotionConditions.HiddenWithoutPrereqs", "UI gating flag",
     "BOOLEAN_UNLOCK", "EXCLUDED", "UI flag, not a magnitude"),
    ("GovernorPromotionConditions.EarliestGameEra", "earliest era the promotion appears",
     "DURATION", "EXCLUDED", "era gate, not a magnitude"),
    ("SecretSocieties.DiscoverAt*BaseChance", "discovery chance percentages",
     "PROBABILITY", "EXCLUDED",
     "discovery probability: repeated-trial semantics do not apply to a one-off chance"),
]


def direct_cells(universe: dict) -> list[dict]:
    """Every direct numeric governor/promotion cell with a disposition."""
    out = []
    seen_cells = set()
    for g in universe["governors"].values():
        for cell, meaning, fam, disp, why in DIRECT_GOVERNOR_CELLS:
            table, col = cell.split(".")
            src = universe.get("governor_direct", {}).get(g["GovernorType"], {})
            if col not in src:
                continue
            v = src[col]
            if v is None or v == "" or v == "0" or v == 0:
                continue
            key = (g["GovernorType"], cell, str(v))
            if key in seen_cells:
                continue
            seen_cells.add(key)
            out.append({"root": g["GovernorType"], "cell": cell, "value": str(v),
                       "meaning": meaning, "family": fam, "disposition": disp,
                       "reason": why})
    # promotion tree structure (Level/Column/BaseAbility) summarised per level
    for pt, p in universe["promotions"].items():
        for col, meaning in (("Level", "level"), ("Column", "column")):
            v = p.get(col)
            if v is None:
                continue
            out.append({"root": pt, "cell": f"GovernorPromotions.{col}",
                       "value": str(v), "meaning": meaning,
                       "family": "INDIVISIBLE_COUNT", "disposition": "EXCLUDED",
                       "reason": "structural tree position, not a magnitude"})
        if str(p.get("BaseAbility", "0")).lower() in ("true", "1"):
            out.append({"root": pt, "cell": "GovernorPromotions.BaseAbility",
                       "value": "true", "meaning": "base ability",
                       "family": "BOOLEAN_UNLOCK", "disposition": "EXCLUDED",
                       "reason": "structural flag, not a magnitude"})
    return out


# --------------------------------------------------------------------------
# Side path: modifiers reachable only through society unit abilities
# --------------------------------------------------------------------------
def unit_ability_modifiers(overlay: dict) -> list[dict]:
    """Modifiers attached to secret-society UNIT abilities (not promotions).

    Discovered explicitly so they are documented as out-of-graph rather than
    silently dropped: they scale unit behaviour, not governor behaviour.
    """
    rows = overlay["rows"]
    args = {}
    for r in rows.get("ModifierArguments", []):
        if r.get("ModifierId"):
            args.setdefault(r["ModifierId"], []).append(r)
    dyn = {r.get("ModifierType"): r for r in rows.get("DynamicModifiers", [])
           if r.get("ModifierType")}
    mods = {r.get("ModifierId"): r for r in rows.get("Modifiers", [])
            if r.get("ModifierId")}
    abilities = {r.get("UnitAbilityType") for r in rows.get("UnitAbilities", [])
                 if r.get("UnitAbilityType")}
    out = []
    for r in rows.get("UnitAbilityModifiers", []):
        mid = r.get("ModifierId")
        if not mid:
            continue
        mi = mods.get(mid, {})
        et = (dyn.get(mi.get("ModifierType")) or {}).get("EffectType")
        for a in args.get(mid, []):
            out.append({"unit_ability": r.get("UnitAbilityType"),
                        "society_unit_ability": r.get("UnitAbilityType") in abilities,
                        "modifier_id": mid, "modifier_type": mi.get("ModifierType"),
                        "effect_type": et, "argument": a.get("Name"),
                        "value": a.get("Value"),
                        "disposition": "OUT_OF_GRAPH",
                        "reason": "unit-ability attached modifier: scales unit behaviour, not governor behaviour; audited as a side path"})
    return out


# --------------------------------------------------------------------------
# Shared-definition overlap with the existing production registry
# --------------------------------------------------------------------------
def registry_overlap(mod_ids: list[str], root: str | Path = ".") -> dict:
    """Modifier IDs already owned by traits/policies/governments/pantheons/wonders.

    Phase 4B must never double-scale a definition another module already owns;
    ownership stays with the existing module unless the audit explicitly
    recommends transfer.
    """
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


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------
INVENTORY_FIELDS = ["root_governor", "root_promotion", "modifier_id",
                    "modifier_type", "effect_type", "collection", "argument",
                    "value", "family", "disposition", "engine_integral",
                    "package", "provenance", "definition_source",
                    "requirement_context", "reason"]


def write_inventory_csv(rows: list[dict], out: str | Path) -> None:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=INVENTORY_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({**r, "requirement_context": ";".join(r["requirement_context"])})


def write_graph_json(universe: dict, rows: list[dict], out: str | Path) -> None:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    graph = {
        "governors": {},
        "promotions": {},
        "edges": rows,
    }
    for gt, g in universe["governors"].items():
        graph["governors"][gt] = {
            "name": g.get("Name"),
            "identity_pressure": g.get("IdentityPressure"),
            "transition_strength": g.get("TransitionStrength"),
            "assign_city_state": g.get("AssignCityState"),
            "trait_type": g.get("TraitType"),
            "source": g.get("source"),
            "promotions": g.get("promotions", []),
            "direct_modifiers": g.get("modifiers", []),
        }
    for pt, p in universe["promotions"].items():
        graph["promotions"][pt] = {
            "level": p.get("Level"), "column": p.get("Column"),
            "base_ability": p.get("BaseAbility"),
            "prereqs": p.get("prereqs", []),
            "modifiers": p.get("modifiers", []),
            "source": p.get("source"),
        }
    out.write_text(json.dumps(graph, indent=1, sort_keys=True), encoding="utf-8")


def build_audit(db_path: str | Path, game_root: str | Path | None = None,
               root: str | Path = ".") -> dict:
    universe, overlay = discover_universe(db_path, game_root)
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
