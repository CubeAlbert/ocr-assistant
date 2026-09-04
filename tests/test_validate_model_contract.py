from __future__ import annotations

import argparse
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import validate_model


class ValidateModelContractTests(unittest.TestCase):
    def test_text_file_takes_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.txt"
            path.write_text("file input\n", encoding="utf-8")
            args = argparse.Namespace(
                input_text_file=path,
                prompt_file=None,
                route="qwen3-text",
                input_text="inline input",
            )
            self.assertEqual(validate_model.route_text_input(args), "file input\n")

    def test_qwen_vl_has_non_concise_default_prompt(self) -> None:
        args = argparse.Namespace(input_text_file=None, prompt_file=None, route="qwen3-vl", input_text="")
        self.assertIn("complete transcription", validate_model.route_text_input(args))


if __name__ == "__main__":
    unittest.main()
