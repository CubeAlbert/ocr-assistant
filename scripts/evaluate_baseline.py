#!/usr/bin/env python3
"""Score saved OCR baseline outputs against a versioned reference manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def normalize_line_endings(value: str) -> str:
    """Normalize only line endings; preserve case, punctuation, digits and spaces."""

    return value.replace("\r\n", "\n").replace("\r", "\n")


def levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def score_text(output: str, reference: str) -> dict[str, Any]:
    output = normalize_line_endings(output)
    reference = normalize_line_endings(reference)
    distance = levenshtein_distance(output, reference)
    denominator = len(reference)
    return {
        "status": "scored",
        "edit_distance": distance,
        "reference_characters": denominator,
        "output_characters": len(output),
        "cer": (distance / denominator) if denominator else None,
        "cer_denominator": "reference_characters",
    }


def line_checks(output: str, expected_lines: list[str]) -> dict[str, Any]:
    lines = normalize_line_endings(output).splitlines()
    non_empty_lines = [line for line in lines if line]
    repeated = {
        line: count
        for line in dict.fromkeys(non_empty_lines)
        if (count := non_empty_lines.count(line)) > 1
    }
    missing = [line for line in expected_lines if line and line not in non_empty_lines]
    return {
        "output_line_count": len(lines),
        "expected_line_count": len(expected_lines),
        "missing_lines": missing,
        "repeated_lines": repeated,
    }


def structure_checks(output: str, checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = normalize_line_endings(output)
    output_lines = normalized.splitlines()
    results: list[dict[str, Any]] = []
    for check in checks:
        kind = check.get("kind")
        expected = check.get("expected")
        if kind == "contains":
            passed = expected in normalized
            result = {"id": check.get("id"), "kind": kind, "expected": expected, "passed": passed}
        elif kind == "contains_all" and isinstance(expected, list):
            missing = [item for item in expected if item not in normalized]
            result = {"id": check.get("id"), "kind": kind, "missing": missing, "passed": not missing}
        elif kind == "line_count":
            actual_count = len(output_lines)
            result = {
                "id": check.get("id"),
                "kind": kind,
                "expected": expected,
                "actual": actual_count,
                "passed": actual_count == expected,
            }
        else:
            result = {
                "id": check.get("id"),
                "kind": kind,
                "passed": False,
                "status": "unsupported_check",
            }
        results.append(result)
    return results


def reference_text(sample: dict[str, Any], *, corrected: bool = False) -> str | None:
    if corrected and sample.get("evaluation_text_after_repairs") is not None:
        return str(sample["evaluation_text_after_repairs"])
    if not sample.get("cer_eligible", True):
        return None
    if sample.get("evaluation_text") is not None:
        return str(sample["evaluation_text"])
    regions = [
        region
        for region in sample.get("regions", [])
        if region.get("status") in {"confirmed", "eligible"} and not region.get("uncertain", False)
    ]
    if not regions:
        return None
    ordered = sorted(regions, key=lambda region: region.get("order", 0))
    return "\n".join(str(region.get("text", "")) for region in ordered) + "\n"


def apply_expected_repairs(text: str, repairs: list[dict[str, Any]]) -> str:
    result = text
    for repair in repairs:
        source = str(repair.get("source", ""))
        target = str(repair.get("target", ""))
        if source:
            result = result.replace(source, target, 1)
    return result


def score_correction(
    original_output: str,
    corrected_output: str,
    reference: str,
    repairs: list[dict[str, Any]],
) -> dict[str, Any]:
    original_score = score_text(original_output, reference)
    corrected_score = score_text(corrected_output, reference)
    expected_corrected = apply_expected_repairs(reference, repairs)
    out_of_scope_distance = levenshtein_distance(
        normalize_line_endings(corrected_output), normalize_line_endings(expected_corrected)
    )
    applied: list[dict[str, Any]] = []
    for repair in repairs:
        source = str(repair.get("source", ""))
        target = str(repair.get("target", ""))
        applied.append(
            {
                "repair_id": repair.get("repair_id"),
                "source_present_in_original": bool(source and source in original_output),
                "target_present_in_corrected": bool(target and target in corrected_output),
            }
        )
    original_distance = int(original_score["edit_distance"])
    corrected_distance = int(corrected_score["edit_distance"])
    return {
        "status": "scored",
        "original": original_score,
        "corrected": corrected_score,
        "fixed_error_estimate": max(0, original_distance - corrected_distance),
        "new_error_estimate": max(0, corrected_distance - original_distance),
        "out_of_scope_edit_distance": out_of_scope_distance,
        "allowed_repairs": applied,
        "expected_corrected_text": expected_corrected,
    }


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def load_result_text(run_path: Path) -> tuple[str | None, dict[str, Any]]:
    record = load_json(run_path)
    if record.get("status") != "passed" or record.get("exit_code") != 0:
        return None, {"status": "run_failed", "run_record": str(run_path)}
    result_path_value = record.get("result_path")
    if not result_path_value:
        return None, {"status": "missing_full_result_path", "run_record": str(run_path)}
    result_path = Path(str(result_path_value))
    if not result_path.is_absolute():
        result_path = run_path.parent / result_path
    if not result_path.is_file():
        return None, {"status": "missing_full_result", "result_path": str(result_path)}
    output = result_path.read_text(encoding="utf-8")
    if not output.strip():
        return None, {"status": "empty_full_result", "result_path": str(result_path)}
    return output, {"status": "loaded", "result_path": str(result_path)}


def evaluate_sample(sample: dict[str, Any], run_path: Path, corrected_run_path: Path | None = None) -> dict[str, Any]:
    output, result_info = load_result_text(run_path)
    result: dict[str, Any] = {
        "sample_id": sample.get("sample_id"),
        "reference_version": sample.get("reference_version"),
        "review_status": sample.get("review_status"),
        "reference_coverage": {
            "region_count": len(sample.get("regions", [])),
            "uncertain_region_ids": sample.get("uncertain_region_ids", []),
            "cer_eligible": bool(sample.get("cer_eligible", True)),
        },
        "run": result_info,
    }
    if output is None:
        result["status"] = "not_scored"
        return result

    reference = reference_text(sample)
    result["status"] = "scored" if reference is not None else "coverage_only"
    if reference is not None:
        expected_lines = [line for line in normalize_line_endings(reference).splitlines() if line]
        result["text"] = score_text(output, reference)
        result["lines"] = line_checks(output, expected_lines)
    else:
        result["text"] = {"status": "not_eligible_due_to_uncertain_or_missing_reference"}
        result["lines"] = line_checks(output, [])
    result["structure"] = structure_checks(output, sample.get("structure_checks", []))

    if corrected_run_path is not None and reference is not None:
        corrected_output, corrected_info = load_result_text(corrected_run_path)
        result["corrected_run"] = corrected_info
        if corrected_output is not None:
            result["correction"] = score_correction(
                output,
                corrected_output,
                reference,
                sample.get("allowed_word_level_repairs", []),
            )
        else:
            result["correction"] = {"status": "not_scored"}
    return result


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# OCR Baseline Evaluation",
        "",
        f"- Reference manifest: {report['reference_manifest']}",
        f"- Reference version: {report.get('reference_version')}",
        f"- Results root: {report['results_root']}",
        "- run.json.result_text is intentionally not used; scoring reads result_path.",
        "",
        "| Sample | Status | CER | Missing lines | Repeated lines | Review |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for item in report.get("samples", []):
        text_result = item.get("text", {})
        cer = text_result.get("cer") if isinstance(text_result, dict) else None
        missing = len(item.get("lines", {}).get("missing_lines", []))
        repeated = len(item.get("lines", {}).get("repeated_lines", {}))
        lines.append(
            f"| {item.get('sample_id')} | {item.get('status')} | "
            f"{cer if cer is not None else 'n/a'} | {missing} | {repeated} | {item.get('review_status')} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- CER uses reference characters as its denominator.",
            "- Uncertain or mixed regions are reported for coverage but are excluded from CER when cer_eligible is false.",
            "- A failed, empty, missing, or suspected-truncated run is not a quality pass.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-manifest", required=True, type=Path)
    parser.add_argument("--results-root", required=True, type=Path)
    parser.add_argument("--corrected-root", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def execute(args: argparse.Namespace) -> int:
    manifest_path = args.reference_manifest.expanduser().resolve()
    manifest = load_json(manifest_path)
    samples: list[dict[str, Any]] = manifest.get("samples", [])
    if not isinstance(samples, list) or not samples:
        raise ValueError("reference manifest must contain a non-empty samples list")
    results_root = args.results_root.expanduser().resolve()
    corrected_root = args.corrected_root.expanduser().resolve() if args.corrected_root else None
    evaluated: list[dict[str, Any]] = []
    for sample in samples:
        sample_id = str(sample["sample_id"])
        run_path = results_root / sample_id / "run.json"
        corrected_run_path = corrected_root / sample_id / "run.json" if corrected_root else None
        if not run_path.is_file():
            evaluated.append({"sample_id": sample_id, "status": "missing_run_record"})
        else:
            evaluated.append(evaluate_sample(sample, run_path, corrected_run_path))
    report = {
        "schema_version": 1,
        "reference_manifest": str(manifest_path),
        "reference_version": manifest.get("reference_version"),
        "results_root": str(results_root),
        "corrected_root": str(corrected_root) if corrected_root else None,
        "samples": evaluated,
    }
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "evaluation.md").write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    try:
        return execute(parse_args())
    except Exception as exc:
        print(
            json.dumps({"status": "failed", "type": type(exc).__name__, "message": str(exc)}, ensure_ascii=False)
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
