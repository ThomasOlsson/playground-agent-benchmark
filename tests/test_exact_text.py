import tempfile
import unittest
from pathlib import Path

from validators import exact_text


def case(**args):
    return {"validator": {"type": "exact_text", "args": args}}


def write(td: Path, name: str, data: bytes) -> None:
    (td / name).write_bytes(data)


class TestExactText(unittest.TestCase):
    def test_exact_match_no_trailing_newline(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write(td, "o.txt", b"HELLO")
            r = exact_text.validate(case(path="o.txt", expect="HELLO", trailing_newline=False), td)
            self.assertTrue(r["ok"], r)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as td:
            r = exact_text.validate(case(path="o.txt", expect="HELLO"), Path(td))
            self.assertFalse(r["ok"])
            self.assertIn("missing", r["detail"])

    def test_rejects_trailing_newline_when_forbidden(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write(td, "o.txt", b"HELLO\n")
            r = exact_text.validate(case(path="o.txt", expect="HELLO", trailing_newline=False), td)
            self.assertFalse(r["ok"])

    def test_requires_trailing_newline_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write(td, "o.txt", b"HELLO")
            r = exact_text.validate(case(path="o.txt", expect="HELLO"), td)
            self.assertFalse(r["ok"])

    def test_content_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write(td, "o.txt", b"BYE")
            r = exact_text.validate(case(path="o.txt", expect="HELLO", trailing_newline=False), td)
            self.assertFalse(r["ok"])
            self.assertEqual(r["observed"], "BYE")
            self.assertEqual(r["expected"], "HELLO")

    def test_strip(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write(td, "o.txt", b"  HELLO  ")
            r = exact_text.validate(case(path="o.txt", expect="HELLO", trailing_newline=False, strip=True), td)
            self.assertTrue(r["ok"], r)


if __name__ == "__main__":
    unittest.main()
