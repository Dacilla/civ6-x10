"""Government manifest builder (release 1)."""
from __future__ import annotations

from . import build_manifest


def build(rows: list[dict]) -> list[dict]:
    return build_manifest(rows, "government")
