import json
import unittest
from pathlib import Path

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"

class TestSchemas(unittest.TestCase):
    def test_case_schema_loads(self):
        data = json.loads((SCHEMAS_DIR / "case.schema.json").read_text())
        self.assertEqual(data["$id"], "case.schema.json")
        self.assertEqual(data["schema_version"], 1)
        self.assertIn("id", data["required"])
        self.assertIn("validator", data["required"])

    def test_manifest_schema_loads(self):
        data = json.loads((SCHEMAS_DIR / "run-manifest.schema.json").read_text())
        self.assertEqual(data["$id"], "run-manifest.schema.json")
        self.assertIn("run_id", data["required"])

    def test_result_schema_loads(self):
        data = json.loads((SCHEMAS_DIR / "case-result.schema.json").read_text())
        self.assertEqual(data["$id"], "case-result.schema.json")
        self.assertIn("case_id", data["required"])
