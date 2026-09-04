#!/usr/bin/env python3
"""Run one parameterized local model smoke test and write a trace record."""

from __future__ import annotations

import argparse
import hashlib
import json

import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROUTES = ("paddleocr-vl", "qwen3-text", "qwen3-vl")
DEFAULT_TEXT = (
    "Correct only the obvious OCR spelling error in this sentence. "
    "Return only the corrected sentence: This is a dup1icate record."
)
DEFAULT_VL_PROMPT = "Transcribe all visible text in reading order. Preserve spelling, punctuation, numbers, and code symbols. Return only the complete transcription."


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def absolute_path(path: Path) -> Path:
    return path.expanduser().resolve()


def file_fingerprint(path: Path) -> dict[str, Any]:
    """Return per-file SHA-256 values and a stable manifest digest."""

    if not path.exists():
        raise FileNotFoundError(f"model path does not exist: {path}")
    files = [path] if path.is_file() else [item for item in path.rglob("*") if item.is_file()]
    if not files:
        raise FileNotFoundError(f"model path contains no files: {path}")

    entries: list[dict[str, Any]] = []
    manifest_lines: list[str] = []
    for item in sorted(files, key=lambda item: item.as_posix()):
        digest = hashlib.sha256()
        with item.open("rb") as stream:
            for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        relative = item.name if path.is_file() else item.relative_to(path).as_posix()
        file_digest = digest.hexdigest()
        size = item.stat().st_size
        entries.append({"path": relative, "size_bytes": size, "sha256": file_digest})
        manifest_lines.append(f"{relative}	{size}	{file_digest}")

    manifest_digest = hashlib.sha256("\n".join(manifest_lines).encode("utf-8")).hexdigest()
    return {
        "algorithm": "sha256",
        "manifest_sha256": manifest_digest,
        "files": entries,
    }


def model_identity(model_path: Path, revision: str | None) -> dict[str, Any]:
    is_immutable = bool(revision and revision not in {"master", "main", "latest"})
    if revision and not is_immutable:
        note = "The supplied revision is mutable; the SHA-256 file manifest is the local identity."
    elif not revision:
        note = "No immutable revision was supplied; the SHA-256 file manifest is the local identity."
    else:
        note = "Revision was supplied by the caller and is recorded alongside the file manifest."
    return {
        "path": str(model_path),
        "revision": revision,
        "revision_is_immutable": is_immutable,
        "revision_note": note,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", required=True, choices=ROUTES)
    parser.add_argument(
        "--model-path",
        required=True,
        type=Path,
        help="Local model directory. For PaddleOCR this is the VL recognition model directory.",
    )
    parser.add_argument(
        "--layout-model-path",
        type=Path,
        help="PaddleOCR layout model directory. Required for the PaddleOCR-VL route so it can be hashed.",
    )
    parser.add_argument("--image", type=Path, help="Input image for PaddleOCR-VL and Qwen3-VL.")
    parser.add_argument("--input-text", default=DEFAULT_TEXT, help="Text prompt for the Qwen3 text route.")

    parser.add_argument(
        "--input-text-file",
        type=Path,
        help="UTF-8 text input file for the Qwen3 text route; takes precedence over --input-text.",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        help="UTF-8 prompt file for the Qwen3-VL route; takes precedence over its default prompt.",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Runtime device, for example cpu, cuda, cuda:0, gpu, or gpu:0.",
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--max-new-tokens", type=int, default=None)
    parser.add_argument(
        "--model-revision",
        help="Optional source revision label; a SHA-256 manifest is always recorded.",
    )
    parser.add_argument(
        "--layout-model-revision",
        help="Optional source revision label for the PaddleOCR layout model; its SHA-256 manifest is always recorded.",
    )
    args = parser.parse_args()
    if args.route in {"paddleocr-vl", "qwen3-vl"} and args.image is None:
        parser.error(f"--image is required for route {args.route}")
    if args.route == "paddleocr-vl" and args.layout_model_path is None:
        parser.error("--layout-model-path is required for route paddleocr-vl")
    if args.image is not None and not args.image.is_file():
        parser.error(f"image does not exist or is not a file: {args.image}")
    if args.layout_model_path is not None and not args.layout_model_path.is_dir():
        parser.error(f"layout model path does not exist or is not a directory: {args.layout_model_path}")
    if args.input_text_file is not None and not args.input_text_file.is_file():
        parser.error(f"input text file does not exist or is not a file: {args.input_text_file}")
    if args.prompt_file is not None and not args.prompt_file.is_file():
        parser.error(f"prompt file does not exist or is not a file: {args.prompt_file}")
    if args.max_new_tokens is not None and args.max_new_tokens < 1:
        parser.error("--max-new-tokens must be positive")
    return args


def torch_device_map(requested: str) -> str | dict[str, str]:
    normalized = requested.lower()
    if normalized == "cpu":
        return "cpu"
    if normalized == "auto":
        return "auto"
    if normalized == "cuda":
        return {"": "cuda:0"}
    if normalized.startswith("cuda:"):
        return {"": requested}
    raise ValueError(f"Qwen routes support cpu, auto, cuda, or cuda:N; got {requested!r}")


def parameter_device(model: Any) -> str:
    try:
        return str(next(model.parameters()).device)
    except (AttributeError, StopIteration):
        return str(getattr(model, "device", "unknown"))


def effective_max_new_tokens(args: argparse.Namespace) -> int | None:
    if args.max_new_tokens is not None:
        return args.max_new_tokens
    if args.route == "qwen3-text":
        return 32
    if args.route == "qwen3-vl":
        return 64
    return None



def read_utf8(path: Path) -> str:
    value = path.read_text(encoding="utf-8")
    if not value.strip():
        raise ValueError(f"UTF-8 input file is empty: {path}")
    return value


def route_text_input(args: argparse.Namespace) -> str:
    if args.input_text_file is not None:
        return read_utf8(args.input_text_file)
    if args.route == "qwen3-vl" and args.prompt_file is not None:
        return read_utf8(args.prompt_file)
    if args.route == "qwen3-vl":
        return DEFAULT_VL_PROMPT
    return args.input_text


def image_dimensions(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        from PIL import Image

        with Image.open(absolute_path(path)) as image:
            return {"width": image.width, "height": image.height, "mode": image.mode}
    except Exception:
        return None


def script_context() -> dict[str, Any]:
    project_root = Path(__file__).resolve().parent.parent
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



def run_paddle(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    child_script = Path(__file__).with_name("paddleocr_child.py").resolve()
    if not child_script.is_file():
        raise FileNotFoundError(f"PaddleOCR child runner was not found: {child_script}")
    metadata_path = output_dir / "paddleocr-child.json"
    command = [
        str(Path(sys.executable).resolve()),
        str(child_script),
        "--image",
        str(absolute_path(args.image)),
        "--device",
        args.device,
        "--output-dir",
        str(output_dir),
        "--metadata-path",
        str(metadata_path),
        "--vl-rec-model-dir",
        str(absolute_path(args.model_path)),
        "--layout-model-dir",
        str(absolute_path(args.layout_model_path)),
    ]
    if args.max_new_tokens is not None:
        command.extend(["--max_new_tokens", str(args.max_new_tokens)])

    started = time.perf_counter()
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    elapsed = time.perf_counter() - started
    (output_dir / "paddleocr.stdout.log").write_text(completed.stdout, encoding="utf-8")
    (output_dir / "paddleocr.stderr.log").write_text(completed.stderr, encoding="utf-8")

    child_metadata: dict[str, Any] | None = None
    if metadata_path.is_file():
        try:
            loaded_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if isinstance(loaded_metadata, dict):
                child_metadata = loaded_metadata
        except (OSError, json.JSONDecodeError):
            child_metadata = None

    output_files = sorted(
        item
        for item in output_dir.iterdir()
        if item.is_file() and item.name not in {"run.json", metadata_path.name}
    )
    text_candidates = [
        item for item in output_files if item.suffix.lower() in {".md", ".txt", ".json"}
    ]
    output_text = ""
    for candidate in text_candidates:
        try:
            value = candidate.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if value.strip():
            output_text = value
            break

    if completed.returncode != 0:
        raise RuntimeError(f"PaddleOCR child exited with status {completed.returncode}")
    if not output_text.strip():
        raise RuntimeError("PaddleOCR produced no non-empty text output")
    if not child_metadata:
        raise RuntimeError("PaddleOCR child did not write its device record")
    result_path = output_dir / "result.txt"
    result_path.write_text(output_text, encoding="utf-8")
    actual_device = child_metadata.get("actual_device_after_predict")
    if not actual_device or actual_device == "unknown":
        raise RuntimeError("PaddleOCR child did not report its actual device")
    return {
        "command": command,
        "child_exit_code": completed.returncode,
        "actual_device": actual_device,
        "actual_device_source": "paddleocr-child.json written by the child after PaddleOCRVL prediction",
        "child_device_record": child_metadata,
        "stage_timing_seconds": {
            "child_total": child_metadata.get("timing_seconds", {}).get("total"),
            "load": child_metadata.get("timing_seconds", {}).get("load"),
            "preprocess": child_metadata.get("timing_seconds", {}).get("preprocess"),
            "generation": child_metadata.get("timing_seconds", {}).get("generation"),
            "save": child_metadata.get("timing_seconds", {}).get("save"),
            "parent_wall": elapsed,
        },
        "output_files": [str(item.relative_to(output_dir)) for item in output_dir.iterdir() if item.is_file()],
        "result_path": "result.txt",
        "input_token_count": None,
        "generated_token_count": child_metadata.get("generated_token_count"),
        "result_text": output_text[:20000],
        "result_text_preview": output_text[:20000],
    }



def run_qwen_text(args: argparse.Namespace, output_dir: Path, input_text: str) -> dict[str, Any]:
    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_path = str(absolute_path(args.model_path))
    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        dtype="auto",
        device_map=torch_device_map(args.device),
        local_files_only=True,
    )
    loaded_seconds = time.perf_counter() - started
    preprocessing_started = time.perf_counter()
    messages = [{"role": "user", "content": input_text}]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    model_inputs = tokenizer([prompt], return_tensors="pt")
    target_device = next(model.parameters()).device
    model_inputs = {key: value.to(target_device) for key, value in model_inputs.items()}
    preprocessing_seconds = time.perf_counter() - preprocessing_started
    input_token_count = int(model_inputs["input_ids"].shape[-1])
    generated_started = time.perf_counter()
    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=args.max_new_tokens or 32,
        do_sample=False,
    )
    generated_seconds = time.perf_counter() - generated_started
    content = tokenizer.decode(
        generated_ids[0][input_token_count:],
        skip_special_tokens=True,
    ).strip()
    if not content:
        raise RuntimeError("Qwen3 text generation returned empty output")
    saving_started = time.perf_counter()
    result_path = output_dir / "result.txt"
    result_path.write_text(content + "\n", encoding="utf-8")
    saving_seconds = time.perf_counter() - saving_started
    return {
        "actual_device": parameter_device(model),
        "stage_timing_seconds": {
            "load": loaded_seconds,
            "preprocess": preprocessing_seconds,
            "generation": generated_seconds,
            "save": saving_seconds,
        },
        "output_files": ["result.txt"],
        "result_path": "result.txt",
        "input_token_count": input_token_count,
        "generated_token_count": int(generated_ids.shape[-1] - input_token_count),
        "result_text": content[:20000],
        "result_text_preview": content[:20000],
    }


def run_qwen_vl(args: argparse.Namespace, output_dir: Path, prompt_text: str) -> dict[str, Any]:
    from PIL import Image
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

    model_path = str(absolute_path(args.model_path))
    started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(model_path, local_files_only=True)
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_path,
        dtype="auto",
        device_map=torch_device_map(args.device),
        local_files_only=True,
    )
    loaded_seconds = time.perf_counter() - started
    preprocessing_started = time.perf_counter()
    image = Image.open(absolute_path(args.image)).convert("RGB")
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {
                    "type": "text",
                    "text": prompt_text,
                },
            ],
        }
    ]
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    )
    target_device = next(model.parameters()).device
    inputs = {key: value.to(target_device) if hasattr(value, "to") else value for key, value in inputs.items()}
    preprocessing_seconds = time.perf_counter() - preprocessing_started
    input_token_count = int(inputs["input_ids"].shape[-1])
    generated_started = time.perf_counter()
    generated_ids = model.generate(
        **inputs,
        max_new_tokens=args.max_new_tokens or 64,
        do_sample=False,
    )
    generated_token_count = int(generated_ids.shape[-1] - input_token_count)
    generated_seconds = time.perf_counter() - generated_started
    trimmed = [out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs["input_ids"], generated_ids)]
    content = processor.batch_decode(
        trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0].strip()
    if not content:
        raise RuntimeError("Qwen3-VL generation returned empty output")
    saving_started = time.perf_counter()
    result_path = output_dir / "result.txt"
    result_path.write_text(content + "\n", encoding="utf-8")
    saving_seconds = time.perf_counter() - saving_started
    return {
        "actual_device": parameter_device(model),
        "stage_timing_seconds": {
            "load": loaded_seconds,
            "preprocess": preprocessing_seconds,
            "generation": generated_seconds,
            "save": saving_seconds,
        },
        "output_files": ["result.txt"],
        "result_path": "result.txt",
        "input_token_count": input_token_count,
        "generated_token_count": generated_token_count,
        "result_text": content[:20000],
        "result_text_preview": content[:20000],
    }


def execute(args: argparse.Namespace) -> int:
    output_dir = absolute_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = absolute_path(args.model_path)
    started_at = utc_now()
    started = time.perf_counter()
    record: dict[str, Any] = {
        "route_input": route_text_input(args),
        "schema_version": 1,
        "started_at_utc": started_at,
        "route": args.route,
        "argv": sys.argv,
        "model": model_identity(model_path, args.model_revision),
        "model_components": {},
        "input": {
            "image": str(absolute_path(args.image)) if args.image is not None else None,
            "image_sha256": None,
            "image_size": image_dimensions(args.image),
            "text": route_text_input(args) if args.route == "qwen3-text" else None,
            "text_file": str(absolute_path(args.input_text_file)) if args.input_text_file else None,
            "text_file_sha256": None,
            "prompt_file": str(absolute_path(args.prompt_file)) if args.prompt_file else None,
            "prompt_file_sha256": None,
        },
        "script_context": script_context(),
        "parameters": {
            "requested_device": args.device,
            "max_new_tokens": effective_max_new_tokens(args),
            "do_sample": False,
            "dtype": "auto" if args.route != "paddleocr-vl" else "fp32-default",
            "layout_model_path": (
                str(absolute_path(args.layout_model_path)) if args.layout_model_path is not None else None
            ),
            "layout_model_revision": args.layout_model_revision,
        },
    }
    if args.layout_model_path is not None:
        record["model_components"]["layout_detection"] = model_identity(
            absolute_path(args.layout_model_path),
            args.layout_model_revision,
        )
    try:
        fingerprint_started = time.perf_counter()
        record["model"]["file_fingerprint"] = file_fingerprint(model_path)
        for component in record["model_components"].values():
            component["file_fingerprint"] = file_fingerprint(Path(component["path"]))
        if args.image is not None:
            record["input"]["image_sha256"] = hashlib.sha256(
                absolute_path(args.image).read_bytes()
            ).hexdigest()
        if args.input_text_file is not None:
            record["input"]["text_file_sha256"] = hashlib.sha256(
                absolute_path(args.input_text_file).read_bytes()
            ).hexdigest()
        if args.prompt_file is not None:
            record["input"]["prompt_file_sha256"] = hashlib.sha256(
                absolute_path(args.prompt_file).read_bytes()
            ).hexdigest()
            pass
        record["timing_seconds"] = {"fingerprint": time.perf_counter() - fingerprint_started}
        if args.route == "paddleocr-vl":
            result = run_paddle(args, output_dir)
        elif args.route == "qwen3-text":
            result = run_qwen_text(args, output_dir, route_text_input(args))
        else:
            result = run_qwen_vl(args, output_dir, route_text_input(args))
        record["timing_seconds"].update(result.pop("stage_timing_seconds", {}))
        record.update(result)
        record["status"] = "passed"
        record["exit_code"] = 0
    except Exception as exc:
        record["status"] = "failed"
        record["exit_code"] = 1
        record["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    record.setdefault("timing_seconds", {})["total"] = time.perf_counter() - started
    record["finished_at_utc"] = utc_now()
    record_path = output_dir / "run.json"
    record["record_path"] = str(record_path)
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return int(record["exit_code"])


def main() -> int:
    return execute(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())