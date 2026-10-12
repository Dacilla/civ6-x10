"""Phase 8B envoys: token-gated generic tier leaves (module suzerain)."""

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
