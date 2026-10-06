"""Determinism: regeneration is byte-identical (release-1 exit criterion)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


class TestDeterminism(unittest.TestCase):
    def test_manifest_regeneration_stable(self):
        from civ6x10.modules import build_manifest
        rows = [{"trait_type": "T_FX", "modifier_id": "M_FX_A1",
                 "modifier_type": "MODIFIER_FX_FLAT",
                 "effect_type": "EFFECT_FX_YIELD",
                 "argument_name": "Amount", "official_value": "7"}]
        self.assertEqual(build_manifest(rows, "trait_type"),
                         build_manifest(rows, "trait_type"))

    def test_scope_stable(self):
        import shutil
        import tempfile
        from civ6x10.scope import build_release1_scope
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "fx"
            d.mkdir()
            for src, dst in [("fx_effect_semantics.csv", "effect_semantics.csv"),
                             ("fx_official_traits.csv", "official_traits.csv"),
                             ("fx_policy_effects.csv", "policy_effects.csv"),
                             ("fx_government_effects.csv", "government_effects.csv")]:
                shutil.copy2(ROOT / "data" / "fixtures" / src, d / dst)
            _, a = build_release1_scope(d)
            _, b = build_release1_scope(d)
            self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
