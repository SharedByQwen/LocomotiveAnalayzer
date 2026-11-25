from __future__ import annotations

import io
import json
import os
import time
import traceback
import zipfile
from pathlib import Path
from threading import RLock
from typing import Any

import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = Path(__file__).resolve().parent / "models"
BUNDLE_PATH = MODEL_DIR / "model_bundle.zip"
MODEL_PATH = MODEL_DIR / "locomotive_model.onnx"
METADATA_PATH = MODEL_DIR / "metadata.json"
MAX_UPLOAD_BYTES = 300 * 1024 * 1024
EXPECTED_FEATURES = 4

app = FastAPI(title="Locomotive Analyzer API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_state: dict[str, Any] = {"session": None, "metadata": None, "model_bytes": None}
_lock = RLock()


class PredictionRequest(BaseModel):
    records: list[list[float]] = Field(min_length=1)


def _validate_model(model_bytes: bytes, metadata: dict[str, Any]):
    started = time.perf_counter()
    print(f"[LocomotiveAnalyzer] Validating ONNX model ({len(model_bytes):,} bytes)...", flush=True)
    if len(model_bytes) < 16:
        raise ValueError("ONNX model file is empty or invalid.")
    features = metadata.get("features")
    if not isinstance(features, list) or len(features) != EXPECTED_FEATURES:
        raise ValueError("metadata.json must declare exactly four model features.")
    print("[LocomotiveAnalyzer] Creating ONNX Runtime session (this may take a while)...", flush=True)
    session = ort.InferenceSession(model_bytes, providers=["CPUExecutionProvider"])
    print(f"[LocomotiveAnalyzer] ONNX session created in {time.perf_counter() - started:.1f}s.", flush=True)
    inputs = session.get_inputs()
    outputs = session.get_outputs()
    if len(inputs) != 1 or len(outputs) != 1:
        raise ValueError("The ONNX model must have exactly one input and one output.")
    return session


def _load_bundle_bytes(bundle_bytes: bytes, persist: bool) -> dict[str, Any]:
    started = time.perf_counter()
    print(f"[LocomotiveAnalyzer] Opening model ZIP ({len(bundle_bytes):,} bytes)...", flush=True)
    with zipfile.ZipFile(io.BytesIO(bundle_bytes)) as archive:
        files = [item for item in archive.infolist() if not item.is_dir()]
        model_items = [item for item in files if Path(item.filename).name.lower() == "locomotive_model.onnx"]
        metadata_items = [item for item in files if Path(item.filename).name.lower() == "metadata.json"]
        if not model_items:
            raise ValueError("ZIP does not contain locomotive_model.onnx.")
        if not metadata_items:
            raise ValueError("ZIP does not contain metadata.json.")
        model_info = min(model_items, key=lambda item: len(item.filename))
        metadata_info = min(metadata_items, key=lambda item: len(item.filename))
        if model_info.file_size > 500 * 1024 * 1024:
            raise ValueError("ONNX model inside ZIP exceeds 500 MB.")
        print(f"[LocomotiveAnalyzer] Extracting ONNX: {model_info.filename} ({model_info.file_size:,} bytes)...", flush=True)
        model_bytes = archive.read(model_info)
        print(f"[LocomotiveAnalyzer] ONNX extracted; reading metadata: {metadata_info.filename}", flush=True)
        metadata = json.loads(archive.read(metadata_info).decode("utf-8-sig"))
        if not isinstance(metadata, dict):
            raise ValueError("metadata.json must contain a JSON object.")

    print("[LocomotiveAnalyzer] ZIP contents validated. Starting ONNX load...", flush=True)
    session = _validate_model(model_bytes, metadata)
    if persist:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        temp_model = MODEL_PATH.with_suffix(".onnx.tmp")
        temp_metadata = METADATA_PATH.with_suffix(".json.tmp")
        temp_bundle = BUNDLE_PATH.with_suffix(".zip.tmp")
        temp_model.write_bytes(model_bytes)
        temp_metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_bundle.write_bytes(bundle_bytes)
        os.replace(temp_model, MODEL_PATH)
        os.replace(temp_metadata, METADATA_PATH)
        os.replace(temp_bundle, BUNDLE_PATH)

    with _lock:
        _state.update(session=session, metadata=metadata, model_bytes=model_bytes)
    print(f"[LocomotiveAnalyzer] Model loaded successfully in {time.perf_counter() - started:.1f}s.", flush=True)

    return metadata


def _load_existing() -> None:
    print(f"[LocomotiveAnalyzer] Startup model search: {BUNDLE_PATH}", flush=True)
    if BUNDLE_PATH.is_file():
        print(f"[LocomotiveAnalyzer] ZIP found ({BUNDLE_PATH.stat().st_size:,} bytes). Loading...", flush=True)
        try:
            _load_bundle_bytes(BUNDLE_PATH.read_bytes(), persist=False)
            return
        except Exception as exc:
            print(f"[LocomotiveAnalyzer] Saved ZIP could not be loaded: {exc}", flush=True)
            traceback.print_exc()
    if MODEL_PATH.is_file() and METADATA_PATH.is_file():
        try:
            model_bytes = MODEL_PATH.read_bytes()
            metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
            session = _validate_model(model_bytes, metadata)
            with _lock:
                _state.update(session=session, metadata=metadata, model_bytes=model_bytes)
        except Exception as exc:
            print(f"[LocomotiveAnalyzer] Saved ONNX model could not be loaded: {exc}", flush=True)
            traceback.print_exc()


@app.on_event("startup")
def startup() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print("[LocomotiveAnalyzer] Backend startup initiated.", flush=True)
    if os.getenv("LOCOMOTIVE_SKIP_MODEL_LOAD", "").strip() == "1":
        print("[LocomotiveAnalyzer] Model loading skipped by LOCOMOTIVE_SKIP_MODEL_LOAD=1. API/UI-only mode.", flush=True)
    else:
        _load_existing()
    print("[LocomotiveAnalyzer] Backend startup complete.", flush=True)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/model/status")
def model_status():
    with _lock:
        metadata = _state["metadata"]
        session = _state["session"]
    if session is None or metadata is None:
        return {"loaded": False, "message": "No model is installed on the backend."}
    return {
        "loaded": True,
        "model_name": metadata.get("model_name"),
        "model_version": metadata.get("model_version"),
        "algorithm": metadata.get("algorithm"),
        "training_rows": metadata.get("training_rows", metadata.get("final_fit_rows")),
        "features": metadata.get("features"),
        "metrics": metadata.get("metrics"),
    }


@app.post("/api/model/upload")
async def upload_model(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload the Colab ZIP bundle.")
    bundle_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(bundle_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="ZIP file exceeds the 300 MB upload limit.")
    try:
        metadata = _load_bundle_bytes(bundle_bytes, persist=True)
    except (zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid model ZIP: {exc}") from exc
    return {
        "loaded": True,
        "model_version": metadata.get("model_version"),
        "algorithm": metadata.get("algorithm"),
        "training_rows": metadata.get("training_rows", metadata.get("final_fit_rows")),
    }


@app.post("/api/predict")
def predict(request: PredictionRequest):
    values = request.records
    if any(len(row) != EXPECTED_FEATURES for row in values):
        raise HTTPException(status_code=422, detail="Each record must contain exactly four feature values.")
    matrix = np.asarray(values, dtype=np.float32)
    if not np.isfinite(matrix).all():
        raise HTTPException(status_code=422, detail="Feature values must be finite numbers.")
    if np.any(matrix < 0):
        raise HTTPException(status_code=422, detail="Feature values must not be negative.")
    if not np.isin(matrix[:, 0], [0, 1]).all():
        raise HTTPException(status_code=422, detail="Previous running status must be 0 or 1.")

    with _lock:
        session = _state["session"]
    if session is None:
        raise HTTPException(status_code=503, detail="No ONNX model is loaded. Upload the Colab ZIP first.")

    try:
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        raw = session.run([output_name], {input_name: matrix})[0]
        predictions = np.asarray(raw).reshape(-1).astype(float).tolist()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ONNX inference failed: {exc}") from exc
    if len(predictions) != len(values) or not np.isfinite(predictions).all():
        raise HTTPException(status_code=500, detail="ONNX model returned invalid predictions.")
    return {"predictions": predictions}
