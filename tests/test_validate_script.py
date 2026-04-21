import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def run_new(*args) -> Path:
    r = subprocess.run(
        [sys.executable, "-m", "scripts.new_run", *args],
        cwd=REPO, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    return Path(r.stdout.strip())


def run_validate(run_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "scripts.validate", "--run", str(run_dir)],
        cwd=REPO, capture_output=True, text=True,
    )


class TestValidateScript(unittest.TestCase):
    def test_pass_case_smk_001(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")

            r = run_validate(run_dir)
            self.assertEqual(r.returncode, 0, r.stderr)
            result = json.loads((run_dir / "cases" / "SMK-001" / "result.json").read_text())
            self.assertEqual(result["status"], "pass")
            self.assertTrue(result["allowed_paths_check"]["ok"])

    def test_fail_case_when_content_wrong(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"WRONG")

            r = run_validate(run_dir)
            self.assertEqual(r.returncode, 1)
            result = json.loads((run_dir / "cases" / "SMK-001" / "result.json").read_text())
            self.assertEqual(result["status"], "fail")

    def test_fail_on_scope_violation(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")
            (workdir / "rogue.txt").write_text("nope")

            r = run_validate(run_dir)
            self.assertEqual(r.returncode, 1)
            result = json.loads((run_dir / "cases" / "SMK-001" / "result.json").read_text())
            self.assertEqual(result["status"], "fail")
            self.assertFalse(result["allowed_paths_check"]["ok"])

    def test_manifest_counts_and_finished_at_updated(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")

            run_validate(run_dir)
            m = json.loads((run_dir / "manifest.json").read_text())
            self.assertEqual(m["counts"], {"total": 1, "passed": 1, "failed": 0, "error": 0})
            self.assertIsNotNone(m["finished_at"])

    def test_result_has_artifacts_and_latency(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")

            run_validate(run_dir)
            result = json.loads((run_dir / "cases" / "SMK-001" / "result.json").read_text())
            self.assertIn("latency_ms", result)
            self.assertIsNone(result["latency_ms"])
            artifacts = result["artifacts"]
            self.assertEqual(artifacts["case_snapshot"], "cases/SMK-001/case.json")
            self.assertEqual(artifacts["workdir"],       "cases/SMK-001/workdir")
            self.assertEqual(artifacts["changes_json"],  "cases/SMK-001/changes.json")
            self.assertEqual(artifacts["changes_diff"],  "cases/SMK-001/changes.diff")
            self.assertEqual(artifacts["transcript"],    "cases/SMK-001/transcript.txt")

    def test_changes_json_written(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")

            run_validate(run_dir)
            changes = json.loads((run_dir / "cases" / "SMK-001" / "changes.json").read_text())
            self.assertEqual(changes["created"], ["out/banner.txt"])
            self.assertEqual(changes["modified"], [])
            self.assertEqual(changes["deleted"], [])

    def test_changes_diff_written_for_new_text_file(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")

            run_validate(run_dir)
            diff_text = (run_dir / "cases" / "SMK-001" / "changes.diff").read_text()
            self.assertIn("HELLO-BENCHMARK-V1", diff_text)
            self.assertIn("+++ ", diff_text)

    def test_changes_diff_present_even_on_scope_violation(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")
            (workdir / "rogue.txt").write_text("nope\n")
            run_validate(run_dir)
            self.assertTrue((run_dir / "cases" / "SMK-001" / "changes.diff").exists())
            self.assertTrue((run_dir / "cases" / "SMK-001" / "changes.json").exists())

    def test_missing_sidecar_surfaces_in_result(self):
        """Operator visibility: if the .bench sidecar is missing, result.json must
        carry the reason in allowed_paths_check.detail and status must be 'fail'."""
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")
            # Simulate a corrupted run by wiping the sidecar directory
            shutil.rmtree(workdir / ".bench")

            r = run_validate(run_dir)
            self.assertEqual(r.returncode, 1)
            result = json.loads((run_dir / "cases" / "SMK-001" / "result.json").read_text())
            self.assertEqual(result["status"], "fail")
            self.assertFalse(result["allowed_paths_check"]["ok"])
            self.assertIn("missing sidecar file", result["allowed_paths_check"]["detail"])


if __name__ == "__main__":
    unittest.main()
