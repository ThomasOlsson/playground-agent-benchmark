import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from bench import runs


class TestRuns(unittest.TestCase):
    def test_new_run_id_shape(self):
        now = datetime(2026, 4, 21, 18, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(runs.new_run_id("local-llama", now=now), "20260421-180000-local-llama")

    def test_new_run_dir_created(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            d = runs.new_run_dir(root, "x")
            self.assertTrue(d.exists())
            self.assertTrue(d.name.endswith("-x"))

    def test_manifest_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            m = {"run_id": "r1", "label": "x"}
            runs.write_manifest(Path(td), m)
            self.assertEqual(runs.read_manifest(Path(td))["run_id"], "r1")

    def test_result_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            runs.write_result(Path(td), {"case_id": "C", "status": "pass"})
            self.assertEqual(runs.read_result(Path(td))["status"], "pass")

    def test_list_cases(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "a").mkdir()
            (td / "a" / "X.json").write_text("{}")
            (td / "b").mkdir()
            (td / "b" / "Y.json").write_text("{}")
            (td / "README.md").write_text("skip")
            found = sorted(p.name for p in runs.list_cases(td))
            self.assertEqual(found, ["X.json", "Y.json"])

    def test_filter_by_suite_tag(self):
        cases = [
            {"id": "A", "tags": ["smoke", "no-fixture"]},
            {"id": "B", "tags": ["bounded-edit"]},
            {"id": "C", "tags": ["smoke", "structured-output"]},
        ]
        ids = [c["id"] for c in runs.filter_by_suite(cases, suite="smoke", explicit_ids=None)]
        self.assertEqual(sorted(ids), ["A", "C"])

    def test_filter_explicit_ids_overrides(self):
        cases = [{"id": "A", "tags": ["smoke"]}, {"id": "B", "tags": ["bounded-edit"]}]
        ids = [c["id"] for c in runs.filter_by_suite(cases, suite="smoke", explicit_ids=["B"])]
        self.assertEqual(ids, ["B"])

    def test_collect_environment_shape(self):
        env = runs.collect_environment()
        for key in ("host", "os", "python", "arch"):
            self.assertIn(key, env)
            self.assertIsInstance(env[key], str)
            self.assertNotEqual(env[key], "")

    def test_collect_hardware_shape(self):
        hw = runs.collect_hardware()
        for key in ("cpu_cores", "memory_gb", "gpu"):
            self.assertIn(key, hw)
        self.assertTrue(hw["cpu_cores"] is None or isinstance(hw["cpu_cores"], int))
        self.assertTrue(hw["memory_gb"] is None or isinstance(hw["memory_gb"], (int, float)))
        self.assertTrue(hw["gpu"] is None or isinstance(hw["gpu"], str))

    def test_collect_hardware_gpu_override(self):
        hw = runs.collect_hardware(gpu="RTX 4090")
        self.assertEqual(hw["gpu"], "RTX 4090")

    def test_utc_now_iso_format(self):
        import re
        s = runs.utc_now_iso()
        self.assertRegex(s, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


if __name__ == "__main__":
    unittest.main()
