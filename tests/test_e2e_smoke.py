import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def new_run(td: str, *flags) -> Path:
    r = subprocess.run([sys.executable, "-m", "scripts.new_run", "--runs-dir", td, *flags],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return Path(r.stdout.strip())


def validate(run_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "scripts.validate", "--run", str(run_dir)],
                          cwd=REPO, capture_output=True, text=True)


def summarize(run_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "scripts.summarize", "--run", str(run_dir)],
                          cwd=REPO, capture_output=True, text=True)


def populate_all_four_cases_to_pass(run_dir: Path) -> None:
    # SMK-001
    w = run_dir / "cases" / "SMK-001" / "workdir"
    (w / "out").mkdir()
    (w / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")

    # STR-001
    w = run_dir / "cases" / "STR-001" / "workdir"
    (w / "out").mkdir()
    (w / "out" / "summary.json").write_text(json.dumps({
        "name": "playground", "version": "0.1.0", "tags": ["benchmark", "tiny", "demo"]
    }))

    # RO-001
    w = run_dir / "cases" / "RO-001" / "workdir"
    (w / "out").mkdir()
    (w / "out" / "routes.json").write_text(json.dumps([
        {"method": "GET",    "path": "/users",        "handler": "UserController@index"},
        {"method": "GET",    "path": "/users/{id}",   "handler": "UserController@show"},
        {"method": "POST",   "path": "/users",        "handler": "UserController@store"},
        {"method": "PUT",    "path": "/users/{id}",   "handler": "UserController@update"},
        {"method": "DELETE", "path": "/users/{id}",   "handler": "UserController@destroy"},
        {"method": "GET",    "path": "/products",     "handler": "ProductController@index"},
    ]))

    # EDT-002 — edit README.md in place, fixing the typo
    readme = run_dir / "cases" / "EDT-002" / "workdir" / "todo-py" / "README.md"
    readme.write_text(readme.read_text().replace("recieve", "receive"))


class TestE2ESmoke(unittest.TestCase):
    def test_full_v1_pipeline_all_pass(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = new_run(td, "--label", "e2e",
                              "--cases", "SMK-001,STR-001,RO-001,EDT-002",
                              "--frontend", "claude-code",
                              "--model", "claude-opus-4-7",
                              "--provider", "anthropic",
                              "--local-or-cloud", "cloud",
                              "--notes", "e2e smoke")
            populate_all_four_cases_to_pass(run_dir)

            v = validate(run_dir)
            self.assertEqual(v.returncode, 0, v.stderr)

            s = summarize(run_dir)
            self.assertEqual(s.returncode, 0, s.stderr)

            text = (run_dir / "summary.md").read_text()
            for cid in ["SMK-001", "STR-001", "RO-001", "EDT-002"]:
                self.assertIn(f"| {cid} | pass |", text, cid)

            m = json.loads((run_dir / "manifest.json").read_text())
            self.assertEqual(m["counts"], {"total": 4, "passed": 4, "failed": 0, "error": 0})
            self.assertIsNotNone(m["finished_at"])
            self.assertEqual(m["agent"]["frontend"], "claude-code")
            self.assertEqual(m["agent"]["model"], "claude-opus-4-7")
            self.assertIn("python", m["environment"])
            self.assertEqual(m["notes"], "e2e smoke")

            # Every case has artifact references and on-disk artifacts.
            for cid in ["SMK-001", "STR-001", "RO-001", "EDT-002"]:
                case_dir = run_dir / "cases" / cid
                result = json.loads((case_dir / "result.json").read_text())
                self.assertEqual(result["artifacts"]["case_snapshot"], f"cases/{cid}/case.json")
                self.assertIn("latency_ms", result)
                self.assertTrue((case_dir / "changes.json").exists(), cid)
                self.assertTrue((case_dir / "changes.diff").exists(), cid)


if __name__ == "__main__":
    unittest.main()
