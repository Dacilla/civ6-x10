"""Wonder manifest builder (phase 3)."""
from __future__ import annotations

from . import build_manifest


def build(rows: list[dict]) -> list[dict]:
    return build_manifest(rows, "building_type")
