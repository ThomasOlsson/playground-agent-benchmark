import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class TestCompareStub(unittest.TestCase):
    def test_help_works(self):
        r = subprocess.run([sys.executable, "-m", "scripts.compare", "--help"],
                           cwd=REPO, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("deferred to v1.1", r.stdout + r.stderr)

    def test_invocation_exits_nonzero(self):
        r = subprocess.run([sys.executable, "-m", "scripts.compare", "--a", "x", "--b", "y"],
                           cwd=REPO, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
