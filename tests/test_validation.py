"""Validation fixture: deliberate mismatch + idempotence proof on a toy DB."""
from __future__ import annotations

import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sqlite3
import tempfile
import unittest
from pathlib import Path


def make_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE ModifierArguments (ModifierId TEXT, Name TEXT, Value TEXT)")
    con.execute("INSERT INTO ModifierArguments VALUES ('M_FLAT','Amount','7')")
    con.execute("INSERT INTO ModifierArguments VALUES ('M_SEL','YieldType','YIELD_SCIENCE')")
    con.commit()
    con.close()


class TestValidation(unittest.TestCase):
    def test_verify_passes_and_is_idempotent(self):
        from civ6x10.generator import statements_for_manifest
        from civ6x10.validation import validate
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "off.sqlite"
            make_db(db)
            manifest = [
                {"object_id": "T", "modifier_id": "M_FLAT", "modifier_type": "MT",
                 "effect_type": "ET", "argument_name": "Amount",
                 "official_value": "7", "semantic_family": "FLAT_AMOUNT",
                 "transformation": "canonical_x10_multiply",
                 "generated_value": "70", "status": "ok", "confidence": "reviewed"},
                {"object_id": "T", "modifier_id": "M_SEL", "modifier_type": "MT",
                 "effect_type": "ET", "argument_name": "YieldType",
                 "official_value": "YIELD_SCIENCE", "semantic_family": "SELECTOR",
                 "transformation": "unchanged",
                 "generated_value": "YIELD_SCIENCE", "status": "ok",
                 "confidence": "reviewed"},
            ]
            stmts = statements_for_manifest(manifest)
            # only the magnitude emits; the selector is unchanged by design
            self.assertEqual(len(stmts), 1)
            self.assertIn("70", stmts[0])
            result = validate(stmts, db, manifest)
            self.assertEqual(result["verdict"], "PASS")
            self.assertTrue(result["idempotent_reapply"])
            self.assertEqual(result["unexpected_targets"], [])

    def test_stale_id_detected(self):
        from civ6x10.validation import validate
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "off.sqlite"
            make_db(db)
            manifest = [
                {"object_id": "T", "modifier_id": "M_NOPE", "modifier_type": "MT",
                 "effect_type": "ET", "argument_name": "Amount",
                 "official_value": "7", "semantic_family": "FLAT_AMOUNT",
                 "transformation": "canonical_x10_multiply",
                 "generated_value": "70", "status": "ok", "confidence": "reviewed"},
            ]
            stmts = ["UPDATE ModifierArguments SET Value = 70 "
                     "WHERE ModifierId = 'M_NOPE' AND Name = 'Amount';"]
            result = validate(stmts, db, manifest)
            self.assertEqual(result["verdict"], "FAIL")
            self.assertTrue(result["errors"] or result["zero_row_statements"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
