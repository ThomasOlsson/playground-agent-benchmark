import json
import tempfile
import unittest
from pathlib import Path

from bench import baseline


class TestWalk(unittest.TestCase):
    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(baseline.walk(Path(td)), {})

    def test_skips_bench_sidecar(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / ".bench").mkdir()
            (p / ".bench" / "x.json").write_text("{}")
            (p / "a.txt").write_text("hi")
            result = baseline.walk(p)
            self.assertEqual(list(result.keys()), ["a.txt"])

    def test_walks_nested_files(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "sub").mkdir()
            (p / "sub" / "b.txt").write_text("b")
            (p / "a.txt").write_text("a")
            result = baseline.walk(p)
            self.assertEqual(set(result), {"a.txt", "sub/b.txt"})
            self.assertEqual(result["a.txt"]["size"], 1)
            self.assertEqual(len(result["a.txt"]["sha256"]), 64)


class TestCapture(unittest.TestCase):
    def test_writes_sidecar_json(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "a.txt").write_text("hello")
            result = baseline.capture(p)
            data = json.loads((p / ".bench" / "baseline.json").read_text())
            self.assertEqual(set(data["files"]), {"a.txt"})
            self.assertEqual(result, data)
            self.assertIn("captured_at", data)


class TestDiff(unittest.TestCase):
    def test_created_modified_deleted_unchanged(self):
        base = {"same.txt": {"sha256": "A"}, "change.txt": {"sha256": "B"}, "gone.txt": {"sha256": "C"}}
        cur  = {"same.txt": {"sha256": "A"}, "change.txt": {"sha256": "X"}, "new.txt": {"sha256": "Z"}}
        d = baseline.diff(base, cur)
        self.assertEqual(d["unchanged"], ["same.txt"])
        self.assertEqual(d["modified"], ["change.txt"])
        self.assertEqual(d["deleted"], ["gone.txt"])
        self.assertEqual(d["created"], ["new.txt"])
        self.assertEqual(d["unsupported"], [])

    def test_unsupported_flagged(self):
        base = {}
        cur  = {"weird.lnk": {"sha256": "__unsupported__"}}
        d = baseline.diff(base, cur)
        self.assertEqual(d["unsupported"], ["weird.lnk"])


if __name__ == "__main__":
    unittest.main()
