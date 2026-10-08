"""CLI: inventory / review / generate / verify."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cmd_inventory(args) -> int:
    from .inventory import inventory
    inv = inventory(Path(args.db))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(inv, indent=2), encoding="utf-8")
    print(json.dumps(inv, indent=1))
    return 0


def cmd_review(args) -> int:
    from .review import run_review
    audit_data = Path(args.audit_data)
    summary = run_review(audit_data, ROOT / "data", ROOT / "reports",
                         ROOT / "manifests")
    print(json.dumps({k: summary[k] for k in
                      ("global_rows", "global_needs_review", "release1_rows",
                       "release1_needs_review", "reviewed_by_family",
                       "ambiguous_rows")}, indent=1))
    return 0


def cmd_generate(args) -> int:
    import yaml
    from .generator import statements_for_manifest
    man = yaml.safe_load(open(ROOT / "manifests" / f"{args.module}.yml", encoding="utf-8"))
    rows = man[args.module]
    stmts = statements_for_manifest(rows)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    header = (f"-- X10 {args.module} (clean-room, deterministic)\n"
              f"-- {len(stmts)} idempotent absolute-SET statements\n")
    out.write_text(header + "\n".join(stmts) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(stmts)} statements)")
    return 0


def cmd_inventory_pantheons(args) -> int:
    from .pantheon import build_pantheon_inventory, write_csv
    rows = build_pantheon_inventory(args.db)
    write_csv(rows, args.out)
    print(f"wrote {args.out} ({len(rows)} rows)")
    return 0


def cmd_inventory_wonders(args) -> int:
    from .wonder import build_wonder_inventory, write_csv
    rows = build_wonder_inventory(args.db)
    write_csv(rows, args.out)
    print(f"wrote {args.out} ({len(rows)} rows)")
    return 0


def cmd_generate_registry(args) -> int:
    import json
    import yaml
    from .production import build_production_registry, emit_cxx
    rows: list[dict] = []
    for module in ("traits", "policies", "governments", "pantheons", "wonders"):
        man = yaml.safe_load(
            open(ROOT / "manifests" / f"{module}.yml", encoding="utf-8"))
        for r in man[module]:
            r = dict(r)
            r["module"] = module
            rows.append(r)
    entries, report = build_production_registry(rows)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(emit_cxx(entries), encoding="utf-8")
    rep = Path(str(out) + ".coverage.json")
    ledger = report.pop("conflict_ledger")
    rep.write_text(json.dumps(report, indent=2), encoding="utf-8")
    import csv
    with open(Path(str(out) + ".conflicts.csv"), "w", encoding="utf-8",
               newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "modifier_id", "effect_type", "argument", "sem_family",
            "proposed_family", "proposed_transform", "cert_source",
            "resolution"])
        w.writeheader()
        w.writerows(ledger)
    print(f"wrote {out} ({len(entries)} entries)")
    print(json.dumps(report, indent=1))
    return 0


def cmd_verify(args) -> int:
    import yaml
    from .validation import validate
    man = yaml.safe_load(open(ROOT / "manifests" / f"{args.module}.yml", encoding="utf-8"))
    rows = man[args.module]
    from .generator import statements_for_manifest
    stmts = statements_for_manifest(rows)
    result = validate(stmts, Path(args.db), rows)
    print(json.dumps({k: v for k, v in result.items()
                      if k != "zero_row_statements"}, indent=1)[:2000])
    if result["zero_row_statements"]:
        print(f"zero-row: {len(result['zero_row_statements'])}")
    return 0 if result["verdict"] == "PASS" else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="civ6x10")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("inventory")
    p.add_argument("--db", required=True)
    p.add_argument("--out", default=str(ROOT / "data" / "inventory.json"))
    p.set_defaults(fn=cmd_inventory)
    p = sub.add_parser("review")
    p.add_argument("--scope", default="release1")
    p.add_argument("--audit-data", default=str(ROOT / "data" / "local"))
    p.set_defaults(fn=cmd_review)
    p = sub.add_parser("generate")
    p.add_argument("--module", required=True, choices=["traits", "policies", "governments", "pantheons", "wonders"])
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_generate)
    p = sub.add_parser("inventory-pantheons")
    p.add_argument("--db", required=True,
                   help="official Gameplay SQLite COPY (never the live install)")
    p.add_argument("--out", default=str(ROOT / "data" / "local" / "pantheon_effects.csv"))
    p.set_defaults(fn=cmd_inventory_pantheons)
    p = sub.add_parser("inventory-wonders")
    p.add_argument("--db", required=True,
                   help="official Gameplay SQLite COPY (never the live install)")
    p.add_argument("--out", default=str(ROOT / "data" / "local" / "wonder_effects.csv"))
    p.set_defaults(fn=cmd_inventory_wonders)
    p = sub.add_parser("generate-registry")
    p.add_argument("--out", default=str(ROOT / "build" / "X10ProductionRegistry.inc"))
    p.set_defaults(fn=cmd_generate_registry)
    p = sub.add_parser("verify")
    p.add_argument("--module", required=True, choices=["traits", "policies", "governments", "pantheons", "wonders"])
    p.add_argument("--db", required=True)
    p.set_defaults(fn=cmd_verify)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
