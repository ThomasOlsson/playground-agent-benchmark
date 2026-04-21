import json
import tempfile
import unittest
from pathlib import Path

from bench import loader


VALID_CASE = {
    "schema_version": 1,
    "id": "TST-001",
    "title": "Test",
    "category": "exact-output",
    "difficulty": "trivial",
    "mode": "write",
    "tags": ["smoke"],
    "fixture": None,
    "allowed_paths": ["out/x.txt"],
    "prompt": "do thing",
    "expected_output": {"kind": "file", "path": "out/x.txt"},
    "validator": {"type": "exact_text", "args": {"path": "out/x.txt", "expect": "X"}}
}


class TestValidateAgainstSchema(unittest.TestCase):
    def test_accepts_valid_case(self):
        schema = json.loads(loader.SCHEMA_PATH.read_text())
        errors = loader.validate_against_schema(VALID_CASE, schema)
        self.assertEqual(errors, [])

    def test_rejects_missing_required_field(self):
        bad = {k: v for k, v in VALID_CASE.items() if k != "id"}
        schema = json.loads(loader.SCHEMA_PATH.read_text())
        errors = loader.validate_against_schema(bad, schema)
        self.assertTrue(any("id" in e for e in errors), errors)

    def test_rejects_wrong_enum(self):
        bad = dict(VALID_CASE, mode="write-all")
        schema = json.loads(loader.SCHEMA_PATH.read_text())
        errors = loader.validate_against_schema(bad, schema)
        self.assertTrue(any("mode" in e for e in errors), errors)

    def test_rejects_bad_id_pattern(self):
        bad = dict(VALID_CASE, id="not-matching")
        schema = json.loads(loader.SCHEMA_PATH.read_text())
        errors = loader.validate_against_schema(bad, schema)
        self.assertTrue(any("id" in e for e in errors), errors)


class TestLoadCase(unittest.TestCase):
    def test_loads_valid_case_from_disk(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "c.json"
            p.write_text(json.dumps(VALID_CASE))
            case = loader.load_case(p)
            self.assertEqual(case["id"], "TST-001")

    def test_raises_on_malformed_json(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "c.json"
            p.write_text("not json")
            with self.assertRaises(loader.CaseLoadError):
                loader.load_case(p)

    def test_raises_on_schema_violation(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "c.json"
            p.write_text(json.dumps({"id": "X"}))
            with self.assertRaises(loader.CaseLoadError):
                loader.load_case(p)


if __name__ == "__main__":
    unittest.main()
