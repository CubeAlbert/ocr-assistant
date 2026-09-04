#!/usr/bin/env python3
"""Execute PaddleOCR-VL in a child process and record its own device."""

from __future__ import annotations

import argparse
import json
import traceback
import time
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--device", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--metadata-path", required=True, type=Path)
    parser.add_argument("--vl-rec-model-dir", required=True, type=Path)
    parser.add_argument("--layout-model-dir", required=True, type=Path)
    parser.add_argument("--max_new_tokens", type=int)
    return parser.parse_args()


def write_metadata(path: Path, metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    child_started = time.perf_counter()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    load_started = time.perf_counter()
    from paddleocr import PaddleOCRVL
    import paddle

    paddle.set_device(args.device)
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "requested_device": args.device,
        "actual_device_after_set_device": str(paddle.get_device()),
        "max_new_tokens": args.max_new_tokens,
    }
    write_metadata(args.metadata_path, metadata)
    metadata["timing_seconds"] = {"load": None, "preprocess": None, "generation": None, "save": 0.0}

    pipeline = None
    try:
        pipeline = PaddleOCRVL(
            device=args.device,
            vl_rec_model_dir=str(args.vl_rec_model_dir.resolve()),
            layout_detection_model_dir=str(args.layout_model_dir.resolve()),
        )
        metadata["timing_seconds"]["load"] = time.perf_counter() - load_started
        metadata["actual_device_after_pipeline_init"] = str(paddle.get_device())
        write_metadata(args.metadata_path, metadata)

        result_count = 0
        generation_started = time.perf_counter()
        for result in pipeline.predict_iter(
            str(args.image.resolve()),
            max_new_tokens=args.max_new_tokens,
        ):
            save_started = time.perf_counter()
            result.print()
            result.save_all(str(args.output_dir))
            metadata["timing_seconds"]["save"] += time.perf_counter() - save_started
            result_count += 1
        metadata["timing_seconds"]["generation"] = time.perf_counter() - generation_started

        metadata["result_count"] = result_count
        metadata["actual_device_after_predict"] = str(paddle.get_device())
    except Exception as exc:
        metadata["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        raise
    finally:
        if pipeline is not None:
            pipeline.close()
        metadata.setdefault("actual_device_after_predict", str(paddle.get_device()))
        metadata["timing_seconds"]["total"] = time.perf_counter() - child_started
        write_metadata(args.metadata_path, metadata)

    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())