"""Setup-configuration multiplier parsing (pure logic, testable without the game).

A game configuration value flows: Advanced Setup Parameter ->
GameConfiguration.GetValue() -> validated per-module multiplier ->
semantic transformation. This module owns parsing/validation only.
"""
from __future__ import annotations

import math

MIN_MULTIPLIER = 0.0
MAX_MULTIPLIER = 100.0

# Data-driven component registry. Modules register here; the config parser
# accepts only registered components. New gameplay components (pantheons,
# governors, wonders, suzerain, beliefs, ...) register without code changes.
_COMPONENTS: dict[str, dict] = {
    "traits": {"label": "Civilization & leader traits"},
    "policies": {"label": "Policy cards"},
    "governments": {"label": "Governments"},
    "pantheons": {"label": "Pantheons"},
}


def register_component(name: str, label: str = "") -> None:
    if not name or not name.replace("-", "").replace("_", "").isalnum():
        raise ValueError(f"invalid component name: {name!r}")
    _COMPONENTS[name] = {"label": label or name}


def registered_components() -> list[str]:
    return sorted(_COMPONENTS)


def parse_multiplier(raw) -> float:
    """Parse a setup value into a validated multiplier.

    Accepts numbers and numeric strings. Rejects NaN/inf/negatives/over-max.
    0 means Off. Raises ValueError with a Lua-surfaceable message otherwise.
    """
    try:
        k = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"multiplier is not a number: {raw!r}")
    if not math.isfinite(k):
        raise ValueError(f"multiplier must be finite: {raw!r}")
    if k < MIN_MULTIPLIER or k > MAX_MULTIPLIER:
        raise ValueError(
            f"multiplier {k} outside range {MIN_MULTIPLIER}..{MAX_MULTIPLIER}")
    # normalize near-integers so 7.3000000001 from a slider behaves as 7.3
    if abs(k - round(k)) < 1e-9:
        k = float(round(k))
    return k


def parse_module_config(values: dict) -> dict[str, float]:
    """Validate a {module: raw_value} mapping against the registry."""
    out: dict[str, float] = {}
    for module, raw in values.items():
        if module not in _COMPONENTS:
            raise ValueError(
                f"unknown module: {module} (registered: {registered_components()})")
        out[module] = parse_multiplier(raw)
    return out


def reconstruction_key(module: str = "", modifier_id: str = "",
                       argument_name: str = "", official_value: str = "",
                       multiplier: float = 0.0) -> str:
    """Globally-unique save/reload identity for one derived value.

    Derived state = f(module, modifier, argument, official value, k).
    Keeps the old 2-arg call shape working positionally is NOT guaranteed;
    callers pass keywords.
    """
    return (f"{module}|{modifier_id}|{argument_name}|"
            f"{official_value}@{multiplier:g}")
