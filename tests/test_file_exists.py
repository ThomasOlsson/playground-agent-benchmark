import tempfile
import unittest
from pathlib import Path

from validators import file_exists


def case(**args):
    return {"validator": {"type": "file_exists", "args": args}}


class TestFileExists(unittest.TestCase):
    def test_exists_true_passes(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "a.txt").write_text("hi")
            r = file_exists.validate(case(path="a.txt", exists=True), Path(td))
            self.assertTrue(r["ok"])

    def test_exists_true_fails_when_missing(self):
        with tempfile.TemporaryDirectory() as td:
            r = file_exists.validate(case(path="a.txt", exists=True), Path(td))
            self.assertFalse(r["ok"])

    def test_exists_false_passes_when_missing(self):
        with tempfile.TemporaryDirectory() as td:
            r = file_exists.validate(case(path="a.txt", exists=False), Path(td))
            self.assertTrue(r["ok"])

    def test_contains_passes(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "a.txt").write_text("please receive this")
            r = file_exists.validate(case(path="a.txt", exists=True, contains="receive"), Path(td))
            self.assertTrue(r["ok"])

    def test_not_contains_passes(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "a.txt").write_text("please receive this")
            r = file_exists.validate(case(path="a.txt", exists=True, not_contains="recieve"), Path(td))
            self.assertTrue(r["ok"])

    def test_contains_fails(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "a.txt").write_text("bye")
            r = file_exists.validate(case(path="a.txt", exists=True, contains="hello"), Path(td))
            self.assertFalse(r["ok"])

    def test_not_contains_fails(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "a.txt").write_text("please recieve this")
            r = file_exists.validate(case(path="a.txt", exists=True, not_contains="recieve"), Path(td))
            self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main()
