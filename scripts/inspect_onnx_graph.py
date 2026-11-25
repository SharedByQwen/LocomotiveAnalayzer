from __future__ import annotations

import collections
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "backend" / "models" / "model_bundle.zip"
OUT_DIR = ROOT / "diagnostics"
MODEL = OUT_DIR / "graph_inspection_model.onnx"


def extract_model() -> None:
    if not ZIP_PATH.is_file():
        raise FileNotFoundError(f"Model bundle not found: {ZIP_PATH}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH) as archive:
        candidates = [
            item for item in archive.infolist()
            if not item.is_dir() and Path(item.filename).name.lower() == "locomotive_model.onnx"
        ]
        if not candidates:
            raise FileNotFoundError("locomotive_model.onnx was not found inside model_bundle.zip")
        item = min(candidates, key=lambda value: len(value.filename))
        print(f"MODEL_ENTRY={item.filename}", flush=True)
        print(f"MODEL_UNCOMPRESSED_BYTES={item.file_size}", flush=True)
        started = time.perf_counter()
        print("EXTRACT_BEGIN", flush=True)
        with archive.open(item) as source, MODEL.open("wb") as target:
            while chunk := source.read(8 * 1024 * 1024):
                target.write(chunk)
        print(f"EXTRACT_DONE bytes={MODEL.stat().st_size} elapsed={time.perf_counter()-started:.2f}s", flush=True)


def main() -> int:
    try:
        extract_model()
    except Exception as exc:
        print(f"EXTRACT_ERROR={type(exc).__name__}: {exc}", flush=True)
        return 2

    try:
        import onnx
    except ImportError:
        print("ONNX_PARSER_MISSING", flush=True)
        print("Install with: .venv\\Scripts\\python.exe -m pip install onnx", flush=True)
        return 3

    print(f"ONNX_PARSER_VERSION={onnx.__version__}", flush=True)
    print(f"FILE_SIZE={MODEL.stat().st_size}", flush=True)
    start = time.perf_counter()
    print("PARSE_BEGIN (ONNX graph parse only; no ONNX Runtime session)", flush=True)
    model = onnx.load(str(MODEL), load_external_data=False)
    print(f"PARSE_DONE elapsed={time.perf_counter()-start:.2f}s", flush=True)
    graph = model.graph
    print(f"IR_VERSION={model.ir_version}", flush=True)
    print(f"OPSETS={[(x.domain, x.version) for x in model.opset_import]}", flush=True)
    print(f"GRAPH_NAME={graph.name}", flush=True)
    print(f"NODE_COUNT={len(graph.node)}", flush=True)
    print(f"INITIALIZER_COUNT={len(graph.initializer)}", flush=True)
    print(f"INITIALIZER_BYTES={sum(len(x.raw_data) for x in graph.initializer):,}", flush=True)
    print(f"INPUTS={[(x.name, x.type) for x in graph.input]}", flush=True)
    print(f"OUTPUTS={[(x.name, x.type) for x in graph.output]}", flush=True)
    op_counts = collections.Counter((node.domain or "ai.onnx", node.op_type) for node in graph.node)
    print("OPERATOR_COUNTS_BEGIN", flush=True)
    for (domain, op), count in op_counts.most_common():
        print(f"OP {domain}::{op} count={count}", flush=True)
    print("OPERATOR_COUNTS_END", flush=True)
    for node in graph.node:
        if node.op_type == "TreeEnsembleRegressor":
            attrs = {}
            for attribute in node.attribute:
                try:
                    value = onnx.helper.get_attribute_value(attribute)
                    attrs[attribute.name] = len(value) if isinstance(value, (list, tuple)) else str(value)[:160]
                except Exception as exc:
                    attrs[attribute.name] = f"attribute_read_error:{exc}"
            print(f"TREE_ENSEMBLE_NODE name={node.name!r} attributes={attrs}", flush=True)
    print("DIAGNOSTIC_PARSE_COMPLETE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
