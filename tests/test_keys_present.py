import json
import tempfile
import unittest
from pathlib import Path

from validators import keys_present


def case(**args):
    return {"validator": {"type": "keys_present", "args": args}}


def write_json(td: Path, name: str, obj) -> None:
    (td / name).write_text(json.dumps(obj))


class TestKeysPresent(unittest.TestCase):
    def test_object_required_pass(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write_json(td, "o.json", {"name": "x", "version": "1.0.0", "tags": ["a", "b", "c"]})
            r = keys_present.validate(case(
                path="o.json",
                required=["name", "version", "tags"],
                constraints={
                    "name":    {"type": "string"},
                    "version": {"type": "string", "regex": r"^\d+\.\d+\.\d+$"},
                    "tags":    {"type": "array",  "len": 3, "items_regex": "^[a-z][a-z0-9-]*$"},
                },
            ), td)
            self.assertTrue(r["ok"], r)

    def test_missing_required_key(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write_json(td, "o.json", {"name": "x"})
            r = keys_present.validate(case(path="o.json", required=["name", "version"]), td)
            self.assertFalse(r["ok"])
            self.assertIn("version", r["detail"])

    def test_regex_fail(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write_json(td, "o.json", {"version": "not-semver"})
            r = keys_present.validate(case(
                path="o.json", required=["version"],
                constraints={"version": {"type": "string", "regex": r"^\d+\.\d+\.\d+$"}},
            ), td)
            self.assertFalse(r["ok"])

    def test_array_top_type_min_len(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write_json(td, "o.json", [
                {"method": "GET",  "path": "/a", "handler": "A@a"},
                {"method": "POST", "path": "/b", "handler": "B@b"},
            ])
            r = keys_present.validate(case(
                path="o.json",
                top_type="array",
                min_len=2,
                each_item={
                    "required": ["method", "path", "handler"],
                    "constraints": {
                        "method":  {"type": "string", "enum": ["GET", "POST"]},
                        "path":    {"type": "string", "regex": "^/"},
                        "handler": {"type": "string", "regex": "^[A-Z][A-Za-z]*@[a-z][A-Za-z]*$"},
                    },
                },
            ), td)
            self.assertTrue(r["ok"], r)

    def test_array_min_len_violation(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write_json(td, "o.json", [])
            r = keys_present.validate(case(path="o.json", top_type="array", min_len=1), td)
            self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main()
