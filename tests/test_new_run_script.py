import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def run(*args, **kwargs) -> subprocess.CompletedProcess:
    env = kwargs.pop("env", None)
    return subprocess.run(
        [sys.executable, "-m", "scripts.new_run", *args],
        cwd=REPO, capture_output=True, text=True, env=env, **kwargs,
    )


class TestNewRun(unittest.TestCase):
    def test_creates_run_dir_for_smoke_suite(self):
        with tempfile.TemporaryDirectory() as td:
            r = run("--label", "unit", "--suite", "smoke", "--runs-dir", td)
            self.assertEqual(r.returncode, 0, r.stderr)
            run_dir = Path(td)
            children = list(run_dir.iterdir())
            self.assertEqual(len(children), 1)
            d = children[0]
            self.assertTrue(d.name.endswith("-unit"))
            self.assertTrue((d / "manifest.json").exists())

            manifest = json.loads((d / "manifest.json").read_text())
            self.assertEqual(manifest["label"], "unit")
            self.assertEqual(manifest["suite"], "smoke")
            self.assertEqual(sorted(manifest["cases"]), ["SMK-001", "SMK-005", "STR-001"])

            for cid in manifest["cases"]:
                workdir = d / "cases" / cid / "workdir"
                self.assertTrue(workdir.exists(), cid)
                self.assertTrue((workdir / ".bench" / "baseline.json").exists())
                self.assertTrue((workdir / ".bench" / "allowed_paths.json").exists())
                self.assertTrue((d / "cases" / cid / "case.json").exists())

    def test_manifest_has_full_v1_shape(self):
        with tempfile.TemporaryDirectory() as td:
            r = run("--label", "u", "--cases", "SMK-001", "--runs-dir", td,
                    "--frontend", "claude-code",
                    "--model", "claude-opus-4-7",
                    "--provider", "anthropic",
                    "--local-or-cloud", "cloud",
                    "--runtime-base-url", "",
                    "--agent-notes", "test run",
                    "--notes", "first smoke",
                    "--gpu", "none")
            self.assertEqual(r.returncode, 0, r.stderr)
            m = json.loads((next(Path(td).iterdir()) / "manifest.json").read_text())

            # Top-level required fields present
            for key in ("schema_version", "run_id", "timestamp", "started_at", "finished_at",
                        "label", "suite", "cases", "agent", "environment", "hardware",
                        "counts", "notes"):
                self.assertIn(key, m, f"missing top-level field: {key}")

            # Timestamps populated at scaffold time
            self.assertIsNotNone(m["timestamp"])
            self.assertIsNotNone(m["started_at"])
            self.assertIsNone(m["finished_at"])
            self.assertEqual(m["timestamp"], m["started_at"])

            # Agent populated from CLI
            self.assertEqual(m["agent"]["frontend"], "claude-code")
            self.assertEqual(m["agent"]["model"], "claude-opus-4-7")
            self.assertEqual(m["agent"]["provider"], "anthropic")
            self.assertEqual(m["agent"]["local_vs_cloud"], "cloud")
            self.assertIsNone(m["agent"]["runtime_base_url"])   # empty string normalizes to null
            self.assertEqual(m["agent"]["notes"], "test run")

            # Environment auto-populated
            for key in ("host", "os", "python", "arch"):
                self.assertIn(key, m["environment"])
                self.assertIsInstance(m["environment"][key], str)

            # Hardware: cpu_cores always populated; gpu from CLI
            self.assertIsInstance(m["hardware"]["cpu_cores"], int)
            self.assertEqual(m["hardware"]["gpu"], "none")

            # Counts start at zero
            self.assertEqual(m["counts"], {"total": 1, "passed": 0, "failed": 0, "error": 0})
            self.assertEqual(m["notes"], "first smoke")

    def test_manifest_defaults_when_flags_omitted(self):
        with tempfile.TemporaryDirectory() as td:
            r = run("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            self.assertEqual(r.returncode, 0, r.stderr)
            m = json.loads((next(Path(td).iterdir()) / "manifest.json").read_text())
            self.assertEqual(m["agent"]["frontend"], "")
            self.assertEqual(m["agent"]["model"], "")
            self.assertEqual(m["agent"]["provider"], "")
            self.assertEqual(m["agent"]["local_vs_cloud"], "unknown")
            self.assertIsNone(m["agent"]["runtime_base_url"])
            self.assertEqual(m["agent"]["notes"], "")
            self.assertEqual(m["notes"], "")
            self.assertIsNone(m["hardware"]["gpu"])

    def test_fixture_gets_copied_for_ro_001(self):
        with tempfile.TemporaryDirectory() as td:
            r = run("--label", "x", "--cases", "RO-001", "--runs-dir", td)
            self.assertEqual(r.returncode, 0, r.stderr)
            d = next(Path(td).iterdir())
            workdir = d / "cases" / "RO-001" / "workdir"
            self.assertTrue((workdir / "routes-php" / "routes" / "web.php").exists())

    def test_no_fixture_case_has_empty_baseline(self):
        with tempfile.TemporaryDirectory() as td:
            r = run("--label", "x", "--cases", "SMK-001", "--runs-dir", td)
            self.assertEqual(r.returncode, 0, r.stderr)
            d = next(Path(td).iterdir())
            baseline = json.loads((d / "cases" / "SMK-001" / "workdir" / ".bench" / "baseline.json").read_text())
            self.assertEqual(baseline["files"], {})


if __name__ == "__main__":
    unittest.main()
