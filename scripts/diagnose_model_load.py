from __future__ import annotations

import ctypes
import json
import os
import platform
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "backend" / "models" / "model_bundle.zip"
OUT_DIR = ROOT / "diagnostics"
TIMEOUT_SECONDS = 40


def log(message: str, path: Path) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def memory_info() -> dict:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]
    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(status)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return {
            "ram_total_gb": round(status.ullTotalPhys / 1024**3, 2),
            "ram_available_gb": round(status.ullAvailPhys / 1024**3, 2),
            "memory_load_percent": status.dwMemoryLoad,
            "pagefile_total_gb": round(status.ullTotalPageFile / 1024**3, 2),
            "pagefile_available_gb": round(status.ullAvailPageFile / 1024**3, 2),
        }
    return {}


def child_trial(model_path: Path, mode: str) -> int:
    import onnxruntime as ort

    print(f"TRIAL_START mode={mode}", flush=True)
    print(f"ORT_VERSION={ort.__version__}", flush=True)
    print(f"PROVIDERS={ort.get_available_providers()}", flush=True)
    options = ort.SessionOptions()
    if mode == "no_optimization":
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    elif mode == "basic":
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    elif mode == "single_thread":
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    started = time.perf_counter()
    print(f"SESSION_CREATE_BEGIN mode={mode}", flush=True)
    session = ort.InferenceSession(str(model_path), sess_options=options, providers=["CPUExecutionProvider"])
    elapsed = time.perf_counter() - started
    print(f"SESSION_CREATE_SUCCESS seconds={elapsed:.2f}", flush=True)
    print(f"INPUTS={[(x.name, x.shape, x.type) for x in session.get_inputs()]}", flush=True)
    print(f"OUTPUTS={[(x.name, x.shape, x.type) for x in session.get_outputs()]}", flush=True)
    return 0


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "--trial":
        return child_trial(Path(sys.argv[2]), sys.argv[3])

    OUT_DIR.mkdir(exist_ok=True)
    log_path = OUT_DIR / "model_load_diagnostics.log"
    if log_path.exists():
        log_path.unlink()
    log("DIAGNOSTIC_START", log_path)
    log(f"OS={platform.platform()}", log_path)
    log(f"PYTHON={sys.version}", log_path)
    log(f"CPU={platform.processor()}", log_path)
    log(f"LOGICAL_CPUS={os.cpu_count()}", log_path)
    log(f"MEMORY={json.dumps(memory_info())}", log_path)

    if not ZIP_PATH.is_file():
        log(f"ERROR model ZIP not found: {ZIP_PATH}", log_path)
        return 2

    try:
        import onnxruntime as ort
        log(f"ONNXRUNTIME_VERSION={ort.__version__}", log_path)
        log(f"AVAILABLE_PROVIDERS={ort.get_available_providers()}", log_path)
    except Exception as exc:
        log(f"ERROR importing onnxruntime: {type(exc).__name__}: {exc}", log_path)
        return 2

    log(f"ZIP_SIZE_BYTES={ZIP_PATH.stat().st_size}", log_path)
    try:
        with zipfile.ZipFile(ZIP_PATH) as archive:
            candidates = [x for x in archive.infolist() if not x.is_dir() and Path(x.filename).name.lower() == "locomotive_model.onnx"]
            if not candidates:
                log("ERROR locomotive_model.onnx not found in ZIP", log_path)
                return 2
            item = min(candidates, key=lambda x: len(x.filename))
            log(f"MODEL_ENTRY={item.filename}", log_path)
            log(f"MODEL_UNCOMPRESSED_BYTES={item.file_size}", log_path)
            model_path = OUT_DIR / "diagnostic_model.onnx"
            log("EXTRACT_BEGIN", log_path)
            with archive.open(item) as source, model_path.open("wb") as target:
                while True:
                    chunk = source.read(8 * 1024 * 1024)
                    if not chunk:
                        break
                    target.write(chunk)
            log(f"EXTRACT_DONE bytes={model_path.stat().st_size}", log_path)
    except Exception as exc:
        log(f"ERROR extracting model: {type(exc).__name__}: {exc}", log_path)
        return 2

    modes = ["default", "no_optimization", "single_thread"]
    for mode in modes:
        trial_log = OUT_DIR / f"trial_{mode}.log"
        if trial_log.exists():
            trial_log.unlink()
        log(f"TRIAL_BEGIN mode={mode} timeout_seconds={TIMEOUT_SECONDS}", log_path)
        started = time.perf_counter()
        with trial_log.open("w", encoding="utf-8") as output:
            process = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "--trial", str(model_path), mode],
                cwd=str(ROOT), stdout=output, stderr=subprocess.STDOUT,
            )
            try:
                code = process.wait(timeout=TIMEOUT_SECONDS)
                result = f"exit_code={code}"
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                result = f"TIMEOUT_after_{TIMEOUT_SECONDS}s"
        elapsed = time.perf_counter() - started
        tail = trial_log.read_text(encoding="utf-8", errors="replace").splitlines()[-8:]
        log(f"TRIAL_END mode={mode} elapsed={elapsed:.1f}s result={result}", log_path)
        for line in tail:
            log(f"  {line}", log_path)

    try:
        model_path.unlink(missing_ok=True)
    except OSError:
        pass
    log("DIAGNOSTIC_COMPLETE", log_path)
    log(f"FULL_LOG={log_path}", log_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
