"""CLI: inventory / review / generate / verify."""
from __future__ import annotations

import argparse
import csv
import json
import os
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


def cmd_inventory_wonder_direct(args) -> int:
    from .bridge import build_wonder_direct, write_direct_csv
    rows = build_wonder_direct(args.db)
    write_direct_csv(rows, args.out)
    print(f"wrote {args.out} ({len(rows)} rows)")
    return 0


def cmd_generate_bridge_sql(args) -> int:
    from .bridge import emit_bridge_sql, load_direct_csv
    rows = load_direct_csv(args.csv)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(emit_bridge_sql(rows), encoding="utf-8")
    print(f"wrote {out} ({len(rows)} bridged cells)")
    return 0


def cmd_generate_registry(args) -> int:
    import json
    from .bridge import collect_registry_rows
    from .production import build_production_registry, emit_cxx
    rows = collect_registry_rows(ROOT)
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


def cmd_generate_governor_manifest(args) -> int:
    from .governors import build_governor_manifest, write_governor_manifest
    manifest = build_governor_manifest(args.audit, args.module)
    rows = manifest[args.module]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_governor_manifest(manifest, out)
    from collections import Counter
    fams = Counter(r["semantic_family"] for r in rows)
    print(f"wrote {out} ({len(rows)} certified rows, "
          f"{len({r['modifier_id'] for r in rows})} distinct modifier ids)")
    print(json.dumps({
        "families": dict(sorted(fams.items())),
        "combat_rows": sum(1 for r in rows
                           if r["transformation"] == "canonical_combat_bonus"),
        "engine_integral_rows": sum(1 for r in rows if r["engine_integral"]),
    }, indent=1))
    return 0


def cmd_audit_governors(args) -> int:
    from .governors import (build_audit, build_manifest, write_manifest,
                            write_inventory_csv, write_graph_json)
    root = args.game_root or os.environ.get("CIV6_GAME_ROOT") or None
    audit = build_audit(args.db, game_root=root, ruleset=args.ruleset,
                        conditional_overlays=not args.no_conditional_overlays,
                        root=ROOT)
    manifest = build_manifest(audit)
    man_out = Path(args.manifest)
    man_out.parent.mkdir(parents=True, exist_ok=True)
    write_manifest(manifest, man_out)
    write_inventory_csv(audit["rows"], args.inventory)
    write_graph_json(audit["universe"], audit["rows"], args.graph)
    c = manifest["counts"]
    d = manifest["disposition_summary"]
    print(f"wrote {man_out} (governors={c['governors']} "
          f"[base {c['governors_base']} / secret-society {c['governors_secret_society']}], "
          f"promotions={c['promotions']} "
          f"[base {c['promotions_base']} / secret-society {c['promotions_secret_society']}])")
    print(f"wrote {args.inventory} ({c['reachable_rows']} reachable rows)")
    print(json.dumps({
        "counts": c,
        "reachable_dispositions": d["reachable_rows"],
        "direct_cell_dispositions": d["direct_cells"],
        "family_summary": manifest["family_summary"],
        "engine_integral_rows": len(manifest["engine_integral_rows"]),
        "registry_overlap": manifest["registry_overlap"],
        "mode_files": [{"file": f["file"], "sha256": f["sha256"],
                        "action": f["action_id"], "criteria": f["criteria"],
                        "exists": f["exists"]} for f in manifest["mode_files"]],
    }, indent=1))
    return 0


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
    p.add_argument("--module", required=True, choices=["traits", "policies", "governments", "pantheons", "wonders",
                 "governors"])
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
    p = sub.add_parser("inventory-wonder-direct")
    p.add_argument("--db", required=True,
                   help="official Gameplay SQLite COPY (never the live install)")
    p.add_argument("--out", default=str(ROOT / "data" / "local" / "wonder_direct.csv"))
    p.set_defaults(fn=cmd_inventory_wonder_direct)
    p = sub.add_parser("generate-bridge-sql")
    p.add_argument("--csv", default=str(ROOT / "data" / "local" / "wonder_direct.csv"))
    p.add_argument("--out", default=str(ROOT / "controller" / "X10" / "Config" / "X10WonderBridge.sql"))
    p.set_defaults(fn=cmd_generate_bridge_sql)
    p = sub.add_parser("generate-governor-manifest")
    p.add_argument("--audit", default=str(ROOT / "civ6x10" / "rules" /
                                          "governor_audit.yml"),
                   help="checked-in Phase-4A.1 governor audit manifest")
    p.add_argument("--module", default="governors", choices=["governors"])
    p.add_argument("--out", default=str(ROOT / "manifests" / "governors.yml"))
    p.set_defaults(fn=cmd_generate_governor_manifest)
    p = sub.add_parser("generate-registry")
    p.add_argument("--out", default=str(ROOT / "build" / "X10ProductionRegistry.inc"))
    p.set_defaults(fn=cmd_generate_registry)
    p = sub.add_parser("verify")
    p.add_argument("--module", required=True, choices=["traits", "policies", "governments", "pantheons", "wonders",
                 "governors"])
    p.add_argument("--db", required=True)
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("audit-governors")
    p.add_argument("--db", required=True,
                   help="official Gameplay SQLite COPY (never the live install)")
    p.add_argument("--game-root", default=None,
                   help="installed Civ VI root (mode-gated Secret Societies XML); "
                        "falls back to CIV6_GAME_ROOT")
    p.add_argument("--ruleset", default="Expansion2",
                   choices=["Expansion1", "Expansion2"],
                   help="ruleset whose mode payload should be loaded")
    p.add_argument("--no-conditional-overlays", action="store_true",
                   help="exclude the Gran Colombia/Maya conditional overlay")
    p.add_argument("--manifest",
                   default=str(ROOT / "civ6x10" / "rules" / "governor_audit.yml"))
    p.add_argument("--inventory",
                   default=str(ROOT / "data" / "local" / "governor_effects.csv"))
    p.add_argument("--graph",
                   default=str(ROOT / "data" / "local" / "governor_graph.json"))
    p.set_defaults(fn=cmd_audit_governors)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
