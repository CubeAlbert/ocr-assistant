from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_baseline


class RunBaselineTests(unittest.TestCase):
    def test_nonzero_subprocess_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_baseline.run_process(
                [sys.executable, "-c", "raise SystemExit(3)"],
                output_dir=Path(directory),
                cwd=ROOT,
                timeout_seconds=2,
                sample_interval_seconds=0.05,
            )
            self.assertEqual(result["exit_code"], 3)
            self.assertFalse(result["timed_out"])

    def test_timeout_is_recorded_and_process_is_terminated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_baseline.run_process(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                output_dir=Path(directory),
                cwd=ROOT,
                timeout_seconds=0.2,
                sample_interval_seconds=0.05,
            )
            self.assertTrue(result["timed_out"])
            self.assertIsNotNone(result["exit_code"])

    def test_empty_full_result_does_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            (run_dir / "result.txt").write_text("\n", encoding="utf-8")
            (run_dir / "run.json").write_text(
                json.dumps({"status": "passed", "exit_code": 0, "result_path": "result.txt"}),
                encoding="utf-8",
            )
            status, info = run_baseline.validate_run_record(run_dir)
            self.assertEqual(status, "empty_full_result")
            self.assertEqual(info["result_path"], str(run_dir / "result.txt"))


if __name__ == "__main__":
    unittest.main()
