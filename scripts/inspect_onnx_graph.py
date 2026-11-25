from __future__ import annotations

import collections
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "diagnostics" / "diagnostic_model.onnx"


def main() -> int:
    if not MODEL.is_file():
        print(f"Model file not found: {MODEL}", flush=True)
        print("Run scripts\\diagnose_model_load.bat first to extract it.", flush=True)
        return 2
    try:
        import onnx
    except ImportError:
        print("Missing ONNX parser. Install it with:", flush=True)
        print(f'"{ROOT / ".venv" / "Scripts" / "python.exe"}" -m pip install onnx', flush=True)
        return 3

    print(f"ONNX_PARSER_VERSION={onnx.__version__}", flush=True)
    print(f"FILE_SIZE={MODEL.stat().st_size}", flush=True)
    start = time.perf_counter()
    print("PARSE_BEGIN (load graph without creating an ORT session)", flush=True)
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
                    if isinstance(value, (list, tuple)):
                        attrs[attribute.name] = len(value)
                    else:
                        attrs[attribute.name] = str(value)[:160]
                except Exception as exc:
                    attrs[attribute.name] = f"attribute_read_error:{exc}"
            print(f"TREE_ENSEMBLE_NODE name={node.name!r} attributes={attrs}", flush=True)
    print("DIAGNOSTIC_PARSE_COMPLETE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
