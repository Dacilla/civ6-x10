"""Inventory: derive release-1 object counts from the official DB (never hard-coded)."""
from __future__ import annotations

from pathlib import Path

from .database import OfficialDb


def inventory(db_path: Path) -> dict:
    with OfficialDb(db_path) as db:
        policies = db.count("Policies")
        govs = db.query("SELECT COUNT(*) AS n FROM Governments")[0]["n"] \
            if _has(db, "Governments") else 0
        traits = db.query("SELECT COUNT(DISTINCT TraitType) AS n FROM TraitModifiers")[0]["n"]
        leaders = db.query(
            "SELECT COUNT(*) AS n FROM CivilizationLeaders WHERE LeaderType NOT LIKE 'LEADER_MINOR_CIV%'"
        )[0]["n"]
        return {
            "policies": policies,
            "governments": govs,
            "traits": traits,
            "playable_leaders": leaders,
            "db": str(db_path),
        }


def _has(db: OfficialDb, table: str) -> bool:
    return bool(db.query(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)))
