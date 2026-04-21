import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def run_new(*args) -> Path:
    r = subprocess.run([sys.executable, "-m", "scripts.new_run", *args],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return Path(r.stdout.strip())


def run_validate(run_dir: Path) -> None:
    subprocess.run([sys.executable, "-m", "scripts.validate", "--run", str(run_dir)],
                   cwd=REPO, capture_output=True, text=True)


def run_summarize(run_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "scripts.summarize", "--run", str(run_dir)],
                          cwd=REPO, capture_output=True, text=True)


class TestSummarize(unittest.TestCase):
    def test_summary_header_and_table(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "s", "--cases", "SMK-001", "--runs-dir", td,
                              "--frontend", "claude-code",
                              "--model", "claude-opus-4-7",
                              "--provider", "anthropic",
                              "--local-or-cloud", "cloud")
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")
            run_validate(run_dir)

            r = run_summarize(run_dir)
            self.assertEqual(r.returncode, 0, r.stderr)
            text = (run_dir / "summary.md").read_text()

            # Case table header and row
            self.assertIn("| case | status | declared validator | allowed_paths | latency_ms | notes |", text)
            self.assertIn("| SMK-001 | pass | exact_text |", text)

            # Agent block
            self.assertIn("## Agent", text)
            self.assertIn("frontend: claude-code", text)
            self.assertIn("model: claude-opus-4-7", text)
            self.assertIn("provider: anthropic", text)
            self.assertIn("local_vs_cloud: cloud", text)

            # Environment block
            self.assertIn("## Environment", text)
            self.assertIn("host:", text)
            self.assertIn("python:", text)

            self.assertIn("Totals:", text)


if __name__ == "__main__":
    unittest.main()
