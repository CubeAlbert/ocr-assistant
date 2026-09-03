#!/usr/bin/env python3
"""Collect host, Python, dependency, and framework-device evidence."""

from __future__ import annotations

import argparse
import ctypes
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_DISTRIBUTIONS = (
    "accelerate",
    "paddleocr",
    "paddlepaddle",
    "python-docx",
    "qwen-vl-utils",
    "torch",
    "torchvision",
    "transformers",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def memory_bytes() -> int | None:
    if sys.platform == "win32":
        class MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatusEx()
        status.dwLength = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.ullTotalPhys)
        return None

    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    return None


def windows_gpu_info() -> tuple[list[dict[str, Any]], str | None]:
    if platform.system() != "Windows":
        return [], None

    powershell = shutil.which("powershell")
    if powershell is None:
        return [], "PowerShell executable was not found"

    query = (
        "Get-CimInstance Win32_VideoController | "
        "Select-Object Name,AdapterRAM,DriverVersion,PNPDeviceID | "
        "ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-Command", query],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        return [], completed.stderr.strip() or "Win32_VideoController query failed"
    if not completed.stdout.strip():
        return [], None

    raw = json.loads(completed.stdout)
    entries = raw if isinstance(raw, list) else [raw]
    return [dict(entry) for entry in entries], None


def dependency_versions() -> tuple[dict[str, str | None], list[str]]:
    versions: dict[str, str | None] = {}
    missing: list[str] = []
    for distribution in REQUIRED_DISTRIBUTIONS:
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[distribution] = None
            missing.append(distribution)
    return versions, missing


def framework_devices() -> tuple[dict[str, Any], list[str]]:
    devices: dict[str, Any] = {}
    errors: list[str] = []

    try:
        import torch

        cuda_available = bool(torch.cuda.is_available())
        cuda_count = int(torch.cuda.device_count())
        devices["torch"] = {
            "version": torch.__version__,
            "cuda_available": cuda_available,
            "cuda_device_count": cuda_count,
            "cuda_devices": [torch.cuda.get_device_name(i) for i in range(cuda_count)],
            "default_device": "cuda:0" if cuda_available else "cpu",
        }
    except Exception as exc:
        devices["torch"] = {"error": f"{type(exc).__name__}: {exc}"}
        errors.append(f"torch device check failed: {type(exc).__name__}: {exc}")

    try:
        import paddle

        devices["paddle"] = {
            "version": paddle.__version__,
            "compiled_with_cuda": bool(paddle.is_compiled_with_cuda()),
            "current_device": paddle.get_device(),
        }
    except Exception as exc:
        devices["paddle"] = {"error": f"{type(exc).__name__}: {exc}"}
        errors.append(f"paddle device check failed: {type(exc).__name__}: {exc}")

    return devices, errors


def collect_report() -> tuple[dict[str, Any], int]:
    versions, missing = dependency_versions()
    framework, framework_errors = framework_devices()
    gpu_info, gpu_error = windows_gpu_info()
    errors = [f"missing distribution: {name}" for name in missing]
    errors.extend(framework_errors)
    if gpu_error:
        errors.append(f"system GPU query: {gpu_error}")

    total_memory = memory_bytes()
    report: dict[str, Any] = {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "system": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_implementation": platform.python_implementation(),
        },
        "cpu": {
            "name": platform.processor(),
            "logical_cpu_count": os.cpu_count(),
        },
        "memory": {
            "total_bytes": total_memory,
            "total_gib": round(total_memory / 1024**3, 2) if total_memory else None,
        },
        "system_gpus": gpu_info,
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "prefix": sys.prefix,
        },
        "dependencies": versions,
        "framework_devices": framework,
        "errors": errors,
    }
    return report, 1 if errors else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional directory for environment.json; stdout always receives the report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report, exit_code = collect_report()
    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        report_path = args.output_dir / "environment.json"
        report["report_path"] = str(report_path.resolve())
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())