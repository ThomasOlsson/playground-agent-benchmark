import unittest
from pathlib import Path

from bench import loader

CASES_DIR = Path(__file__).resolve().parent.parent / "cases"
EXPECTED_IDS = {"SMK-001", "STR-001", "RO-001", "EDT-002"}


class TestCaseFiles(unittest.TestCase):
    def setUp(self):
        self.files = sorted(CASES_DIR.rglob("*.json"))

    def test_four_cases_on_disk(self):
        self.assertEqual(len(self.files), 4, [p.name for p in self.files])

    def test_all_cases_load_against_schema(self):
        ids = set()
        for f in self.files:
            case = loader.load_case(f)
            ids.add(case["id"])
        self.assertEqual(ids, EXPECTED_IDS)

    def test_smk_001_shape(self):
        case = loader.load_case(CASES_DIR / "smoke" / "SMK-001.json")
        self.assertEqual(case["mode"], "write")
        self.assertEqual(case["validator"]["type"], "exact_text")
        self.assertEqual(case["allowed_paths"], ["out/banner.txt"])

    def test_str_001_shape(self):
        case = loader.load_case(CASES_DIR / "structured" / "STR-001.json")
        self.assertEqual(case["validator"]["type"], "keys_present")
        self.assertIn("smoke", case["tags"])
        self.assertIn("structured-output", case["tags"])

    def test_ro_001_shape(self):
        case = loader.load_case(CASES_DIR / "structured" / "RO-001.json")
        self.assertEqual(case["mode"], "read-only")
        self.assertEqual(case["fixture"], "routes-php")

    def test_edt_002_shape(self):
        case = loader.load_case(CASES_DIR / "bounded-edit" / "EDT-002.json")
        self.assertEqual(case["fixture"], "todo-py")
        self.assertIn("todo-py/README.md", case["allowed_paths"])


if __name__ == "__main__":
    unittest.main()
