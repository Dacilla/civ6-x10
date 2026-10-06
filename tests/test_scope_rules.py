"""Scope, selector/binary refusal, and technical-clamp policy tests."""
from __future__ import annotations

import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestScope(unittest.TestCase):
    def _fxdir(self, tmp):
        import shutil
        d = Path(tmp) / "fx"
        d.mkdir()
        pairs = [("fx_effect_semantics.csv", "effect_semantics.csv"),
                 ("fx_official_traits.csv", "official_traits.csv"),
                 ("fx_policy_effects.csv", "policy_effects.csv"),
                 ("fx_government_effects.csv", "government_effects.csv")]
        for src, dst in pairs:
            shutil.copy2(ROOT / "data" / "fixtures" / src, d / dst)
        return d

    def test_release1_scope_is_deterministic(self):
        import tempfile
        from civ6x10.scope import build_release1_scope
        with tempfile.TemporaryDirectory() as td:
            fx = self._fxdir(td)
            s1, st1 = build_release1_scope(fx)
            s2, st2 = build_release1_scope(fx)
            self.assertEqual(st1, st2)
            self.assertEqual(len(s1), len(s2))
            # fixture truth: 5 global rows / 4 NEEDS_REVIEW; 4 scoped / 3 scoped NEEDS
            self.assertEqual(st1["global_rows"], 5)
            self.assertEqual(st1["global_needs_review"], 4)
            self.assertEqual(st1["release1_rows"], 4)
            self.assertEqual(st1["release1_needs_review"], 3)

    def test_release1_local_integration(self):
        """Needs the private official inputs in data/local/; skipped in CI."""
        local = ROOT / "data" / "local"
        if not (local / "effect_semantics.csv").is_file():
            self.skipTest("official inputs unavailable (data/local/)")
        from civ6x10.scope import build_release1_scope
        _, st = build_release1_scope(local)
        self.assertEqual(st["global_rows"], 1495)
        self.assertEqual(st["global_needs_review"], 843)


class TestRefusals(unittest.TestCase):
    def test_selector_unchanged(self):
        from civ6x10.modules import build_manifest
        rows = build_manifest([{
            "policy": "P", "modifier_id": "M",
            "modifier_type": "MODIFIER_X", "effect_type": "EFFECT_X",
            "argument_name": "YieldType", "official_value": "YIELD_SCIENCE",
        }], "policy")
        self.assertEqual(rows[0]["transformation"], "unchanged")
        self.assertEqual(rows[0]["generated_value"], "YIELD_SCIENCE")

    def test_binary_refused(self):
        from civ6x10.generator import statements_for_manifest
        rows = [{"object_id": "P", "modifier_id": "M", "modifier_type": "T",
                 "effect_type": "E", "argument_name": "IsWonder",
                 "official_value": "1", "semantic_family": "BOOLEAN_UNLOCK",
                 "transformation": "refused_no_multiplier",
                 "generated_value": "", "status": "refused", "confidence": "needs_human"}]
        self.assertEqual(statements_for_manifest(rows), [])

    def test_no_technical_clamp_without_evidence(self):
        import yaml
        rules = yaml.safe_load(open(ROOT / "civ6x10" / "rules" / "transformations.yml",
                                    encoding="utf-8"))
        clamps = [k for k, v in rules["transforms"].items()
                  if v.get("kind") == "TECHNICAL_CLAMP"]
        self.assertEqual(clamps, [])

    def test_fractional_k_leaves_counts_undecided(self):
        from civ6x10.modules import build_manifest
        rows = build_manifest([{
            "trait_type": "T", "modifier_id": "M",
            "modifier_type": "MODIFIER_X", "effect_type": "EFFECT_X",
            "argument_name": "Charges", "official_value": "3",
        }], "trait_type", k=7.3)
        self.assertEqual(rows[0]["status"], "undecided")
        self.assertEqual(rows[0]["confidence"], "needs_human")
        # integer k stays exact and certified
        rows10 = build_manifest([{
            "trait_type": "T", "modifier_id": "M",
            "modifier_type": "MODIFIER_X", "effect_type": "EFFECT_X",
            "argument_name": "Charges", "official_value": "3",
        }], "trait_type", k=10.0)
        self.assertEqual(rows10[0]["status"], "ok")
        self.assertEqual(rows10[0]["generated_value"], "30")

    def test_ce_capability_inventory_is_one_to_one(self):
        import json
        inv = json.loads((ROOT / "spike" / "ce_capabilities.json").read_text(encoding="utf-8"))
        entries = inv["entries"]
        by_class: dict[str, int] = {}
        for e in entries:
            by_class[e["class"]] = by_class.get(e["class"], 0) + 1
        for cls, n in inv["counts"].items():
            if cls in ("lua_callable_functions",):
                continue
            self.assertEqual(by_class.get(cls, 0), n, cls)
        self.assertEqual(inv["counts"]["lua_callable_functions"], len(entries))
        self.assertEqual(inv["modifiers_mutators_exposed"], [])

    def test_no_relative_transforms_emitted(self):
        from civ6x10.generator import statements_for_manifest
        rows = [{"object_id": "T", "modifier_id": "M_FX_A1",
                 "modifier_type": "MODIFIER_FX_FLAT", "effect_type": "EFFECT_FX_YIELD",
                 "argument_name": "Amount", "official_value": "7",
                 "semantic_family": "FLAT_AMOUNT",
                 "transformation": "canonical_x10_multiply",
                 "generated_value": "70", "status": "ok",
                 "confidence": "reviewed"}]
        stmts = statements_for_manifest(rows)
        self.assertEqual(len(stmts), 1)
        for s in stmts:
            self.assertNotIn("Value * 10", s)
            self.assertNotIn("Value*10", s)
            self.assertIn("70", s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
