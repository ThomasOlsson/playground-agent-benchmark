import json
import tempfile
import unittest
from pathlib import Path

from bench import baseline
from validators import allowed_paths_check


def setup_workdir(files: dict[str, bytes], allowed: list[str]) -> Path:
    td = Path(tempfile.mkdtemp(prefix="tmp_test_apc_"))
    for rel, data in files.items():
        p = td / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    baseline.capture(td)
    (td / ".bench" / "allowed_paths.json").write_text(json.dumps(allowed))
    return td


class TestAllowedPathsCheck(unittest.TestCase):
    def test_no_changes_passes(self):
        td = setup_workdir({"fix/a.py": b"x"}, ["out/"])
        r = allowed_paths_check.validate({}, td)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["counts"]["unchanged"], 1)

    def test_allowed_create_passes(self):
        td = setup_workdir({"fix/a.py": b"x"}, ["out/", "out/banner.txt"])
        (td / "out").mkdir()
        (td / "out" / "banner.txt").write_text("HI")
        r = allowed_paths_check.validate({}, td)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["counts"]["created"], 1)

    def test_disallowed_create_violates(self):
        td = setup_workdir({"fix/a.py": b"x"}, ["out/banner.txt"])
        (td / "rogue.txt").write_text("nope")
        r = allowed_paths_check.validate({}, td)
        self.assertFalse(r["ok"])
        self.assertEqual([v["path"] for v in r["violations"]], ["rogue.txt"])
        self.assertEqual(r["violations"][0]["kind"], "created")

    def test_disallowed_modify_violates(self):
        td = setup_workdir({"fix/a.py": b"x"}, ["out/"])
        (td / "fix" / "a.py").write_text("CHANGED")
        r = allowed_paths_check.validate({}, td)
        self.assertFalse(r["ok"])
        kinds = {v["path"]: v["kind"] for v in r["violations"]}
        self.assertEqual(kinds["fix/a.py"], "modified")

    def test_delete_default_violates(self):
        td = setup_workdir({"fix/a.py": b"x"}, ["fix/a.py"])
        (td / "fix" / "a.py").unlink()
        r = allowed_paths_check.validate({}, td)
        self.assertFalse(r["ok"])
        self.assertEqual(r["violations"][0]["kind"], "deleted")

    def test_delete_with_allow_deletions(self):
        td = setup_workdir({"fix/a.py": b"x"}, ["fix/a.py"])
        (td / "fix" / "a.py").unlink()
        case = {"allow_deletions": True}
        r = allowed_paths_check.validate(case, td)
        self.assertTrue(r["ok"])

    def test_unsupported_flagged(self):
        td = setup_workdir({}, [])
        # Create a symlink pointing at non-existent target — still a non-regular file
        (td / "s").symlink_to("nowhere")
        r = allowed_paths_check.validate({}, td)
        self.assertFalse(r["ok"])
        kinds = {v["kind"] for v in r["violations"]}
        self.assertIn("unsupported", kinds)


if __name__ == "__main__":
    unittest.main()
