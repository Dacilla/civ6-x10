"""Pantheon manifest builder (phase 2)."""
from __future__ import annotations

from . import build_manifest


def build(rows: list[dict]) -> list[dict]:
    return build_manifest(rows, "belief_type")
