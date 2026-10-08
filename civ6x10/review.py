"""Review pipeline: scope RELEASE_1, infer families, write ledger + manifests."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from .modules import build_manifest, load_csv
from .modules import governments as mod_gov
from .modules import pantheons as mod_pan
from .modules import policies as mod_pol
from .modules import traits as mod_traits
from .modules import wonders as mod_won
from .scope import build_release1_scope
from .semantics import infer_family

AUDIT = Path(__file__).resolve().parents[2] / "audit"


def _values_for(key: tuple[str, str], pools: list[list[dict]],
                val_keys: tuple[str, ...] = ("official_value", "argument_value", "db_value")) -> list[str]:
    vals: list[str] = []
    for pool in pools:
        for r in pool:
            if (r.get("modifier_type", "").strip(), r.get("argument_name", "").strip()) == key:
                for k in val_keys:
                    if r.get(k):
                        vals.append(str(r[k]))
                        break
    return sorted(set(vals))[:25]


def run_review(audit_data: Path, out_data: Path, out_reports: Path,
               out_manifests: Path) -> dict:
    scoped, stats = build_release1_scope(audit_data)
    traits_rows = load_csv(audit_data / "official_traits.csv")
    pol_rows = load_csv(audit_data / "policy_effects.csv")
    gov_rows = load_csv(audit_data / "government_effects.csv")
    pan_rows = load_csv(audit_data / "pantheon_effects.csv")
    won_rows = load_csv(audit_data / "wonder_effects.csv")

    # decision ledger over scoped registry rows with inspected official values
    ledger: list[dict] = []
    for r in scoped:
        key = (r["modifier_type"].strip(), r["argument_name"].strip())
        vals = _values_for(key, [traits_rows, pol_rows, gov_rows, pan_rows])
        family, transform, conf = infer_family(
            r.get("modifier_type", ""), r.get("effect_type", ""),
            r.get("argument_name", ""),
            vals if vals else [r.get("evidence", "")])
        # evidence text is display-only: appending it to the inference
        # input would poison numeric families with non-numeric prose.
        display_vals = list(vals)
        if r.get("evidence") and len(display_vals) < 25:
            display_vals = sorted(set(display_vals + [r["evidence"][:40]]))[:25]
        ledger.append({
            "modifier_type": r["modifier_type"],
            "effect_type": r.get("effect_type", ""),
            "argument_name": r["argument_name"],
            "sources": r.get("release1_source", ""),
            "registry_family": r.get("semantic_family", ""),
            "registry_confidence": r.get("confidence", ""),
            "review_family": family,
            "review_transform": transform,
            "review_confidence": conf,
            "sample_values": "|".join(display_vals[:8]),
        })

    out_data.mkdir(parents=True, exist_ok=True)
    with open(out_data / "release1_semantics.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ledger[0].keys()))
        w.writeheader()
        w.writerows(ledger)

    # per-object manifests
    out_manifests.mkdir(parents=True, exist_ok=True)
    manifests = {
        "traits": mod_traits.build(_join_effect(traits_rows, scoped)),
        "policies": mod_pol.build(_join_effect(pol_rows, scoped)),
        "governments": mod_gov.build(_join_effect(gov_rows, scoped)),
        "pantheons": mod_pan.build(_join_effect(pan_rows, scoped)),
        "wonders": mod_won.build(_join_effect(won_rows, scoped)),
    }
    for name, rows in manifests.items():
        import yaml
        with open(out_manifests / f"{name}.yml", "w", encoding="utf-8") as fh:
            yaml.safe_dump({name: rows}, fh, sort_keys=False, allow_unicode=True)

    summary = _summarize(ledger, manifests, stats)
    (out_data / "release1_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    _write_review_report(out_reports / "RELEASE1_SEMANTIC_REVIEW.md", summary, ledger)
    for name, fname in (("policies", "POLICY_DECISIONS.md"),
                        ("governments", "GOVERNMENT_DECISIONS.md"),
                        ("traits", "TRAIT_DECISIONS.md"),
                        ("pantheons", "PANTHEON_DECISIONS.md"),
                        ("wonders", "WONDER_DECISIONS.md")):
        _write_module_report(out_reports / fname,
                             name, manifests[name])
    return summary


def _join_effect(rows: list[dict], scoped: list[dict]) -> list[dict]:
    eff = {(r["modifier_type"].strip(), r["argument_name"].strip()):
           r.get("effect_type", "") for r in scoped}
    out = []
    for r in rows:
        r = dict(r)
        r.setdefault("effect_type", eff.get(
            (r.get("modifier_type", "").strip(), r.get("argument_name", "").strip()), ""))
        out.append(r)
    return out


def _summarize(ledger, manifests, stats) -> dict:
    fam = Counter(r["review_family"] for r in ledger)
    auto = sum(1 for r in ledger if r["review_confidence"] == "auto_rule")
    ambig = [r for r in ledger if r["review_confidence"] == "needs_human"]
    mod_stats = {}
    for name, rows in manifests.items():
        c = Counter(r["status"] for r in rows)
        mod_stats[name] = {
            "rows": len(rows),
            "ok": c.get("ok", 0),
            "refused": c.get("refused", 0),
            "undecided": c.get("undecided", 0),
        }
    return {
        **stats,
        "reviewed_by_family": auto,
        "ambiguous_rows": len(ambig),
        "family_histogram": dict(sorted(fam.items())),
        "manifests": mod_stats,
        "ambiguous_keys": [
            [r["modifier_type"], r["effect_type"], r["argument_name"]] for r in ambig[:60]],
    }


def _write_review_report(path: Path, summary: dict, ledger: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fam_lines = "\n".join(f"| {k} | {v} |" for k, v in
                          sorted(summary["family_histogram"].items(), key=lambda kv: -kv[1]))
    ambig = [r for r in ledger if r["review_confidence"] == "needs_human"][:40]
    amb_lines = "\n".join(
        f"| `{r['modifier_type']}` | `{r['effect_type']}` | `{r['argument_name']}` | {r['sample_values'][:60]} |"
        for r in ambig) or "_none_"
    path.write_text(f"""# RELEASE_1 Semantic Review

Deterministically scoped from the official inventories: a registry row is in
RELEASE_1 iff its (modifier_type, argument_name) occurs in official traits,
policies, governments, pantheons, or wonders. Counts derived, never hard-coded.

## Scope

| Measure | Count |
|---|---:|
| Global registry rows | {summary['global_rows']} |
| Global NEEDS_REVIEW | {summary['global_needs_review']} |
| RELEASE_1 rows | {summary['release1_rows']} |
| RELEASE_1 NEEDS_REVIEW (before review) | {summary['release1_needs_review']} |
| Auto-ruled this pass (heuristics: NOT certified, never production-eligible alone) | {summary['reviewed_by_family']} |
| Remaining ambiguous | {summary['ambiguous_rows']} |

Machine-readable: `data/release1_semantics.csv` (decision ledger),
`data/release1_summary.json`.

## Review families

| Family | Rows |
|---|---:|
{fam_lines}

Family rules live in `civ6x10/semantics.py`; transforms in
`civ6x10/rules/transformations.yml`. Every auto-accepted row traces to its
rule via `review_family`/`review_transform` in the ledger.

## Ambiguous queue (first {min(40, summary['ambiguous_rows'])} of {summary['ambiguous_rows']})

| ModifierType | EffectType | Argument | Sample values |
|---|---|---|---|
{amb_lines}

Full queue: filter `data/release1_semantics.csv` on
`review_confidence = needs_human`.
""", encoding="utf-8")


def _write_module_report(path: Path, name: str, rows: list[dict]) -> None:
    from collections import Counter
    c = Counter(r["status"] for r in rows)
    q = [r for r in rows if r["status"] != "ok"][:40]
    q_lines = "\n".join(
        f"| `{r['object_id']}` | `{r['modifier_id']}` | `{r['argument_name']}` | {r['official_value']} | {r['semantic_family']} | {r['status']} |"
        for r in q) or "_none_"
    # Preserve hand-curated sections appended after the marker.
    curated = ""
    if path.is_file():
        old = path.read_text(encoding="utf-8")
        if "<!-- CURATED-BELOW" in old:
            curated = "<!-- CURATED-BELOW" + old.split("<!-- CURATED-BELOW", 1)[1]
    path.write_text(f"""# {name.capitalize()} Decisions

Manifest: `manifests/{name}.yml` ({len(rows)} rows: """
f"""{c.get('ok', 0)} ok, {c.get('refused', 0)} refused, """
f"""{c.get('undecided', 0)} undecided).

| Object | Modifier | Argument | Official | Family | Decision |
|---|---|---|---|---|---|
{q_lines}

Full manifest is machine-readable; this report shows only rows needing humans.
Refused rows are never emitted as SQL (boolean unlocks, structural slots).
Undecided rows are the short human queue — no silent enhancements.

{curated}""", encoding="utf-8")
