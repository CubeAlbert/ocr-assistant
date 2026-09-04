#!/usr/bin/env python3
"""Run one model route over a reference sample manifest, one sample per process."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def git_context(project_root: Path) -> dict[str, Any]:
    revision = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    status = subprocess.run(
        ["git", "-C", str(project_root), "status", "--short"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "revision": revision.stdout.strip() if revision.returncode == 0 else None,
        "workspace_dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
    }


def process_tree_rss(process: psutil.Process) -> int:
    total = 0
    for item in [process, *process.children(recursive=True)]:
        try:
            total += item.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return total


def terminate_process_tree(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
        return
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except ProcessLookupError:
        pass


def run_process(
    command: list[str],
    *,
    output_dir: Path,
    timeout_seconds: float,
    cwd: Path | None = None,
    sample_interval_seconds: float = 0.25,
) -> dict[str, Any]:
    stdout_path = output_dir / "process.stdout.log"
    stderr_path = output_dir / "process.stderr.log"
    started = time.perf_counter()
    max_rss = 0
    timed_out = False
    with stdout_path.open("w", encoding="utf-8", errors="replace") as stdout, stderr_path.open(
        "w", encoding="utf-8", errors="replace"
    ) as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, cwd=cwd)
        process_info = psutil.Process(process.pid)
        while process.poll() is None:
            try:
                max_rss = max(max_rss, process_tree_rss(process_info))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            if time.perf_counter() - started > timeout_seconds:
                timed_out = True
                terminate_process_tree(process)
                break
            time.sleep(max(0.05, sample_interval_seconds))
        try:
            return_code = process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            terminate_process_tree(process)
            return_code = process.wait(timeout=10)
        try:
            max_rss = max(max_rss, process_tree_rss(process_info))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return {
        "exit_code": return_code,
        "timed_out": timed_out,
        "duration_seconds": time.perf_counter() - started,
        "max_rss_bytes_estimate": max_rss or None,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }


def validate_run_record(sample_dir: Path) -> tuple[str, dict[str, Any]]:
    run_path = sample_dir / "run.json"
    if not run_path.is_file():
        return "missing_run_record", {"run_record": str(run_path)}
    try:
        record = load_json(run_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return "invalid_run_record", {"message": str(exc)}
    if record.get("status") != "passed" or record.get("exit_code") != 0:
        return "model_run_failed", {"run_record": str(run_path), "model_status": record.get("status")}
    result_path_value = record.get("result_path")
    if not result_path_value:
        return "missing_full_result_path", {"run_record": str(run_path)}
    result_path = Path(str(result_path_value))
    if not result_path.is_absolute():
        result_path = sample_dir / result_path
    if not result_path.is_file():
        return "missing_full_result", {"result_path": str(result_path)}
    if not result_path.read_text(encoding="utf-8").strip():
        return "empty_full_result", {"result_path": str(result_path)}
    return "passed", {"run_record": str(run_path), "result_path": str(result_path)}


def resolve_sample_path(manifest_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (manifest_path.parent / path).resolve()


def build_command(args: argparse.Namespace, sample: dict[str, Any], sample_dir: Path, image: Path) -> list[str]:
    runner = args.runner.expanduser().resolve()
    command = [
        str(Path(sys.executable).resolve()),
        str(runner),
        "--route",
        args.route,
        "--model-path",
        str(args.model_path.expanduser().resolve()),
        "--image",
        str(image),
        "--device",
        args.device,
        "--output-dir",
        str(sample_dir),
    ]
    if args.layout_model_path:
        command.extend(["--layout-model-path", str(args.layout_model_path.expanduser().resolve())])
    if args.model_revision:
        command.extend(["--model-revision", args.model_revision])
    if args.layout_model_revision:
        command.extend(["--layout-model-revision", args.layout_model_revision])
    if args.max_new_tokens is not None:
        command.extend(["--max-new-tokens", str(args.max_new_tokens)])
    prompt_file_value = sample.get("prompt_file")
    if prompt_file_value is None and args.prompt_file:
        prompt_file_value = str(args.prompt_file.expanduser().resolve())
    if prompt_file_value:
        prompt_file = resolve_sample_path(args.manifest, str(prompt_file_value))
        command.extend(["--prompt-file", str(prompt_file)])
    input_file_value = sample.get("input_text_file")
    if input_file_value is None and args.input_text_file:
        input_file_value = str(args.input_text_file.expanduser().resolve())
    if input_file_value:
        input_file = resolve_sample_path(args.manifest, str(input_file_value))
        command.extend(["--input-text-file", str(input_file)])
    elif sample.get("input_text") is not None:
        input_file = sample_dir / "input.txt"
        input_file.write_text(str(sample["input_text"]), encoding="utf-8")
        command.extend(["--input-text-file", str(input_file)])
    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--route", required=True, choices=("paddleocr-vl", "qwen3-text", "qwen3-vl"))
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--layout-model-path", type=Path)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--runner", type=Path, default=Path(__file__).with_name("validate_model.py"))
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--input-text-file", type=Path)
    parser.add_argument("--model-revision")
    parser.add_argument("--layout-model-revision")
    parser.add_argument("--max-new-tokens", type=int)
    parser.add_argument("--timeout-seconds", type=float, default=1800)
    parser.add_argument("--sample-id", help="Run only one sample for a bounded smoke; omit for the full manifest.")
    parser.add_argument("--sample-interval-seconds", type=float, default=0.25)
    return parser.parse_args()


def execute(args: argparse.Namespace) -> int:
    args.manifest = args.manifest.expanduser().resolve()
    manifest = load_json(args.manifest)
    samples = manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("manifest must contain a non-empty samples list")
    if args.sample_id is not None:
        samples = [sample for sample in samples if str(sample.get("sample_id")) == args.sample_id]
        if not samples:
            raise ValueError(f"sample_id not found in manifest: {args.sample_id}")
    if args.route == "paddleocr-vl" and args.layout_model_path is None:
        raise ValueError("--layout-model-path is required for paddleocr-vl")
    if args.route == "qwen3-vl" and args.max_new_tokens is None:
        raise ValueError("qwen3-vl baseline requires explicit --max-new-tokens")
    if args.timeout_seconds <= 0:
        raise ValueError("--timeout-seconds must be positive")
    output_root = args.output_dir.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    project_root = Path(__file__).resolve().parent.parent
    baseline_record: dict[str, Any] = {
        "schema_version": 1,
        "started_at_utc": utc_now(),
        "manifest": str(args.manifest),
        "manifest_sha256": sha256_file(args.manifest),
        "route": args.route,
        "requested_device": args.device,
        "model_path": str(args.model_path.expanduser().resolve()),
        "sample_id_filter": args.sample_id,
        "runner": str(args.runner.expanduser().resolve()),
        "parameters": {
            "max_new_tokens": args.max_new_tokens,
            "timeout_seconds": args.timeout_seconds,
            "sample_interval_seconds": args.sample_interval_seconds,
        },
        "script_context": git_context(project_root),
        "samples": [],
    }
    for sample in samples:
        sample_id = str(sample.get("sample_id", ""))
        if not sample_id or Path(sample_id).name != sample_id:
            raise ValueError(f"sample_id must be a simple directory name: {sample_id!r}")
        sample_dir = output_root / sample_id
        sample_dir.mkdir(parents=True, exist_ok=False)
        image = resolve_sample_path(args.manifest, str(sample["image"]))
        if not image.is_file():
            entry = {"sample_id": sample_id, "status": "missing_image", "image": str(image)}
            (sample_dir / "baseline.json").write_text(json.dumps(entry, indent=2) + "\n", encoding="utf-8")
            baseline_record["samples"].append(entry)
            continue
        expected_hash = sample.get("image_sha256")
        actual_hash = sha256_file(image)
        if expected_hash and str(expected_hash).lower() != actual_hash.lower():
            entry = {
                "sample_id": sample_id,
                "status": "image_hash_mismatch",
                "image": str(image),
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash,
            }
            (sample_dir / "baseline.json").write_text(json.dumps(entry, indent=2) + "\n", encoding="utf-8")
            baseline_record["samples"].append(entry)
            continue
        command = build_command(args, sample, sample_dir, image)
        (sample_dir / "command.json").write_text(
            json.dumps(command, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        process = run_process(
            command,
            output_dir=sample_dir,
            cwd=project_root,
            timeout_seconds=args.timeout_seconds,
            sample_interval_seconds=args.sample_interval_seconds,
        )
        if process["timed_out"]:
            model_status, model_info = "timed_out", {"run_record": str(sample_dir / "run.json")}
        elif process["exit_code"] == 0:
            model_status, model_info = validate_run_record(sample_dir)
        else:
            model_status, model_info = "model_run_failed", {"run_record": str(sample_dir / "run.json")}
        entry = {
            "sample_id": sample_id,
            "image": str(image),
            "image_sha256": actual_hash,
            "reference_version": sample.get("reference_version"),
            "command": command,
            "process": process,
            "model": model_info,
            "status": model_status,
        }
        (sample_dir / "baseline.json").write_text(
            json.dumps(entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        baseline_record["samples"].append(entry)
    baseline_record["finished_at_utc"] = utc_now()
    baseline_record["status"] = (
        "passed" if all(item.get("status") == "passed" for item in baseline_record["samples"]) else "partial_or_failed"
    )
    (output_root / "baseline.json").write_text(
        json.dumps(baseline_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(baseline_record, ensure_ascii=False, indent=2))
    return 0 if baseline_record["status"] == "passed" else 1


def main() -> int:
    try:
        return execute(parse_args())
    except Exception as exc:
        print(json.dumps({"status": "failed", "type": type(exc).__name__, "message": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
