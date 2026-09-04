from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_baseline


class EvaluateBaselineTests(unittest.TestCase):
    def test_score_text_preserves_sensitive_characters(self) -> None:
        result = evaluate_baseline.score_text("A01\nCode()\n", "A00\nCode()\n")
        self.assertEqual(result["reference_characters"], 11)
        self.assertEqual(result["edit_distance"], 1)
        self.assertEqual(result["cer_denominator"], "reference_characters")

    def test_full_result_path_is_used_instead_of_preview(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            (run_dir / "result.txt").write_text("right\n", encoding="utf-8")
            (run_dir / "run.json").write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "exit_code": 0,
                        "result_path": "result.txt",
                        "result_text": "wrong preview",
                    }
                ),
                encoding="utf-8",
            )
            sample = {
                "sample_id": "synthetic",
                "reference_version": "synthetic-1",
                "review_status": "confirmed",
                "cer_eligible": True,
                "regions": [],
                "evaluation_text": "right\n",
            }
            result = evaluate_baseline.evaluate_sample(sample, run_dir / "run.json")
            self.assertEqual(result["status"], "scored")
            self.assertEqual(result["text"]["cer"], 0)

    def test_uncertain_reference_is_coverage_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            (run_dir / "result.txt").write_text("visible\nuncertain\n", encoding="utf-8")
            (run_dir / "run.json").write_text(
                json.dumps({"status": "passed", "exit_code": 0, "result_path": "result.txt"}),
                encoding="utf-8",
            )
            sample = {
                "sample_id": "fuzzy",
                "reference_version": "draft-1",
                "review_status": "pending_user_review",
                "cer_eligible": False,
                "uncertain_region_ids": ["fuzzy-r02"],
                "regions": [],
            }
            result = evaluate_baseline.evaluate_sample(sample, run_dir / "run.json")
            self.assertEqual(result["status"], "coverage_only")
            self.assertEqual(result["text"]["status"], "not_eligible_due_to_uncertain_or_missing_reference")

    def test_correction_reports_allowed_item_and_delta(self) -> None:
        reference = "This is a duplicate record.\n"
        result = evaluate_baseline.score_correction(
            "This is a dup1icate record.\n",
            reference,
            reference,
            [
                {
                    "repair_id": "fix-1",
                    "source": "dup1icate",
                    "target": "duplicate",
                }
            ],
        )
        self.assertEqual(result["corrected"]["cer"], 0)
        self.assertEqual(result["original"]["edit_distance"], 1)
        self.assertEqual(result["fixed_error_estimate"], 1)
        self.assertTrue(result["allowed_repairs"][0]["source_present_in_original"])

    def test_lines_report_missing_and_duplicate(self) -> None:
        result = evaluate_baseline.line_checks("one\none\n", ["one", "two"])
        self.assertEqual(result["missing_lines"], ["two"])
        self.assertEqual(result["repeated_lines"], {"one": 2})


if __name__ == "__main__":
    unittest.main()
