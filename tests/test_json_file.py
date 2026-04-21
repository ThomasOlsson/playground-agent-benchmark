import tempfile
import unittest
from pathlib import Path

from validators import json_file


def case(**args):
    return {"validator": {"type": "json_file", "args": args}}


class TestJsonFile(unittest.TestCase):
    def test_valid_json_passes(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "o.json").write_text('{"a": 1}')
            r = json_file.validate(case(path="o.json"), Path(td))
            self.assertTrue(r["ok"])
            self.assertEqual(r["observed"], {"a": 1})

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as td:
            r = json_file.validate(case(path="o.json"), Path(td))
            self.assertFalse(r["ok"])
            self.assertIn("missing", r["detail"])

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "o.json").write_text("not json")
            r = json_file.validate(case(path="o.json"), Path(td))
            self.assertFalse(r["ok"])
            self.assertIn("JSON", r["detail"])


if __name__ == "__main__":
    unittest.main()
