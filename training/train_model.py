from __future__ import annotations
import argparse, json, logging, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ["وضعیت سیر قبل (۱=سالم، ۰=خراب)", "روز از آخرین خرابی در سیر", "زمان تعمیرات امروز (ساعت)", "هزینه تعمیر (یورو)"]
TARGET = "قابلیت سیر امروز"

def setup_logging():
    folder = ROOT / "logs"
    folder.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(folder / "training.log", encoding="utf-8")], force=True)

def train(path: Path):
    setup_logging()
    logging.info("TRAIN_START | dataset=%s", path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}. Copy LocomotivDataSet.xlsx into training/data/.")
    frame = pd.read_excel(path, sheet_name="گزارش روزانه")
    logging.info("DATASET_LOADED | rows=%d columns=%d", len(frame), len(frame.columns))
    missing = [c for c in FEATURES + [TARGET] if c not in frame.columns]
    if missing:
        raise ValueError(f"Required columns missing: {missing}")
    data = frame[FEATURES + [TARGET]].copy()
    for col in FEATURES + [TARGET]:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    before = len(data)
    data = data.dropna()
    logging.info("DATA_VALIDATED | rows=%d dropped=%d", len(data), before-len(data))
    if data.empty:
        raise ValueError("No valid numeric rows found.")
    x = data[FEATURES].astype(np.float32)
    y = data[TARGET].astype(np.float32)
    if not x[FEATURES[0]].isin([0, 1]).all():
        raise ValueError("Previous running status must be 0 or 1.")
    if ((y < 0) | (y > 1)).any():
        raise ValueError("Target capability must be between 0 and 1.")
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)
    model = RandomForestRegressor(n_estimators=160, min_samples_leaf=2, random_state=42, n_jobs=-1)
    logging.info("MODEL_FIT_START | algorithm=RandomForestRegressor")
    model.fit(x_train, y_train)
    pred = model.predict(x_test)
    mae = float(mean_absolute_error(y_test, pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
    r2 = float(r2_score(y_test, pred))
    logging.info("EVALUATION | test_rows=%d mae=%.6f rmse=%.6f r2=%.6f", len(x_test), mae, rmse, r2)
    out = ROOT / "public" / "models"
    out.mkdir(parents=True, exist_ok=True)
    onx = convert_sklearn(model, initial_types=[("features", FloatTensorType([None, 4]))], target_opset=17, options={id(model): {"zipmap": False}})
    model_path = out / "locomotive_model.onnx"
    model_path.write_bytes(onx.SerializeToString())
    metadata = {"model_name":"locomotive-capability-regressor","model_version":"0.1.0","created_at_utc":datetime.now(timezone.utc).isoformat(),"algorithm":"RandomForestRegressor","features":FEATURES,"target":TARGET,"input_name":"features","training_rows":int(len(x_train)),"test_rows":int(len(x_test)),"metrics":{"mae":mae,"rmse":rmse,"r2":r2},"dataset_file":path.name,"dataset_is_synthetic":True,"warning":"Workbook documentation describes this dataset as synthetic/random; metrics do not establish real-world predictive validity."}
    (out / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info("MODEL_EXPORTED | path=%s bytes=%d", model_path, model_path.stat().st_size)
    logging.info("TRAIN_COMPLETE | status=success")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=ROOT / "training" / "data" / "LocomotivDataSet.xlsx")
    args = parser.parse_args()
    try:
        train(args.dataset.resolve())
        return 0
    except Exception:
        logging.exception("TRAIN_FAILED")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
