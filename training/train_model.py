from __future__ import annotations

import argparse
import json
import logging
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn import __version__ as sklearn_version
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

ROOT = Path(__file__).resolve().parents[1]
FEATURES = [
    "وضعیت سیر قبل (۱=سالم، ۰=خراب)",
    "روز از آخرین خرابی در سیر",
    "زمان تعمیرات امروز (ساعت)",
    "هزینه تعمیر (یورو)",
]
TARGET = "قابلیت سیر امروز"
SHEET = "گزارش روزانه"
RANDOM_STATE = 42
TEST_SIZE = 0.20


def make_model() -> RandomForestRegressor:
    # A deliberately compact forest: bounded depth/leaf count keeps ONNX
    # graph size and CPU session-initialization time practical on older laptops.
    return RandomForestRegressor(
        n_estimators=80,
        max_depth=14,
        min_samples_leaf=8,
        max_leaf_nodes=128,
        max_features=1.0,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


def setup_logging() -> None:
    log_dir = ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "training.log", encoding="utf-8"),
        ],
        force=True,
    )


def calculate_metrics(actual: pd.Series, predicted: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "r2": float(r2_score(actual, predicted)),
    }



def update_training_readme(report: dict, metadata: dict, model_path: Path, bundle_path: Path) -> None:
    """Refresh the generated experiment section without overwriting the guide."""
    readme_path = ROOT / "training" / "README.md"
    content = readme_path.read_text(encoding="utf-8") if readme_path.exists() else "# Training\n"
    start = "<!-- AUTO-TRAINING-REPORT:START -->"
    end = "<!-- AUTO-TRAINING-REPORT:END -->"
    params = metadata["model_parameters"]
    metrics = report["model"]["metrics"]
    baseline = report["baseline"]["metrics"]
    libraries = {
        "Python": sys.version.split()[0],
        "NumPy": np.__version__,
        "Pandas": pd.__version__,
        "scikit-learn": sklearn_version,
        "skl2onnx": __import__("skl2onnx").__version__,
        "ONNX": __import__("onnx").__version__,
    }
    parameter_lines = "\n".join(f"| \`{key}\` | \`{value}\` |" for key, value in params.items())
    library_lines = "\n".join(f"| {name} | \`{version}\` |" for name, version in libraries.items())
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    section = f"""{start}
## آخرین گزارش آموزش (تولید خودکار)

> این بخش پس از هر آموزش موفق به‌روزرسانی می‌شود. زمان گزارش: **{updated_at}**

### داده و تقسیم‌بندی
- فایل داده: \`{report['dataset_file']}\` — شیت \`{report['worksheet']}\`
- تعداد ردیف معتبر: **{report['usable_rows']:,}**
- نسبت آموزش به آزمون: **{(1-report['test_size'])*100:.0f}% / {report['test_size']*100:.0f}%**
- تعداد ردیف آموزش: **{report['evaluation_train_rows']:,}**
- تعداد ردیف آزمون: **{report['evaluation_test_rows']:,}**
- روش تقسیم: \`{report['evaluation_method']}\` — seed: \`{report['random_state']}\`

### الگوریتم و پارامترهای مدل
- الگوریتم: **{metadata['algorithm']}**
- نوع مدل: مدل یادگیری ماشین مبتنی بر درخت؛ **شبکه عصبی استفاده نشده است**.
- ورودی‌ها: {len(metadata['features'])} ویژگی عددی
- خروجی هدف: \`{metadata['target']}\`

| پارامتر | مقدار |
|---|---:|
{parameter_lines}

### معیارهای ارزیابی روی داده آزمون
| معیار | مدل | خط پایه (میانگین) |
|---|---:|---:|
| MAE | {metrics['mae']:.6f} | {baseline['mae']:.6f} |
| RMSE | {metrics['rmse']:.6f} | {baseline['rmse']:.6f} |
| R² | {metrics['r2']:.6f} | {baseline['r2']:.6f} |

### کتابخانه‌ها و نسخه‌ها
| کتابخانه | نسخه |
|---|---:|
{library_lines}

### خروجی استقرار
- فایل ONNX: \`{model_path.relative_to(ROOT).as_posix()}\` — **{model_path.stat().st_size:,} bytes**
- بسته ZIP: \`{bundle_path.relative_to(ROOT).as_posix()}\` — **{bundle_path.stat().st_size:,} bytes**
- تعداد ردیف استفاده‌شده برای آموزش مدل نهایی: **{metadata['final_fit_rows']:,}**

### تفسیر و محدودیت
- این معیارها فقط روی بخش آزمون همین دیتاست محاسبه شده‌اند؛ برای مقایسه نسخه‌ها مفیدند اما جای آزمون زمانی یا اعتبارسنجی مستقل را نمی‌گیرند.
- مستندات دیتاست فعلی آن را مصنوعی/تصادفی توصیف می‌کند؛ بنابراین این نتایج اثبات‌کننده دقت پیش‌بینی خرابی واقعی لکوموتیو نیستند.
{end}"""
    if start in content and end in content:
        before, remainder = content.split(start, 1)
        _, after = remainder.split(end, 1)
        content = before + section + after
    else:
        content = content.rstrip() + "\n\n" + section + "\n"
    readme_path.write_text(content, encoding="utf-8")

def train(dataset_path: Path) -> None:
    setup_logging()
    logging.info("TRAIN_START | dataset=%s", dataset_path)

    if not dataset_path.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {dataset_path}. "
            "Copy LocomotivDataSet.xlsx into training/data/."
        )

    frame = pd.read_excel(dataset_path, sheet_name=SHEET)
    logging.info(
        "DATASET_LOADED | rows=%d columns=%d sheet=%s",
        len(frame), len(frame.columns), SHEET,
    )

    missing = [column for column in FEATURES + [TARGET] if column not in frame.columns]
    if missing:
        raise ValueError(f"Required columns missing from worksheet: {missing}")

    data = frame[FEATURES + [TARGET]].copy()
    for column in FEATURES + [TARGET]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    original_rows = len(data)
    data = data.replace([np.inf, -np.inf], np.nan).dropna()
    logging.info(
        "DATA_VALIDATED | usable_rows=%d dropped_rows=%d",
        len(data), original_rows - len(data),
    )

    if len(data) < 10:
        raise ValueError(
            f"At least 10 valid rows are required for a train/test evaluation; got {len(data)}."
        )

    x = data[FEATURES].astype(np.float32)
    y = data[TARGET].astype(np.float32)

    if not x[FEATURES[0]].isin([0, 1]).all():
        raise ValueError("Previous running status must contain only 0 or 1.")
    if (x < 0).any().any():
        raise ValueError("Input features must not contain negative values.")
    if ((y < 0) | (y > 1)).any():
        raise ValueError("Target capability must be between 0 and 1.")

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
    )

    # Evaluation model: it never sees the held-out test rows during fitting.
    evaluation_model = make_model()
    logging.info(
        "EVALUATION_FIT_STARTED | algorithm=RandomForestRegressor train_rows=%d test_rows=%d",
        len(x_train), len(x_test),
    )
    evaluation_model.fit(x_train, y_train)
    test_predictions = evaluation_model.predict(x_test)
    model_metrics = calculate_metrics(y_test, test_predictions)

    # A simple mean-only baseline helps show whether the model beats a trivial predictor.
    baseline = DummyRegressor(strategy="mean")
    baseline.fit(x_train, y_train)
    baseline_predictions = baseline.predict(x_test)
    baseline_metrics = calculate_metrics(y_test, baseline_predictions)

    logging.info(
        "HOLDOUT_METRICS | rows=%d model_mae=%.6f model_rmse=%.6f model_r2=%.6f "
        "baseline_mae=%.6f baseline_rmse=%.6f baseline_r2=%.6f",
        len(x_test),
        model_metrics["mae"], model_metrics["rmse"], model_metrics["r2"],
        baseline_metrics["mae"], baseline_metrics["rmse"], baseline_metrics["r2"],
    )

    output_dir = ROOT / "training" / "output"
    model_dir = ROOT / "public" / "models"
    backend_model_dir = ROOT / "backend" / "models"
    output_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    backend_model_dir.mkdir(parents=True, exist_ok=True)

    prediction_report = pd.DataFrame({
        "actual": y_test.to_numpy(),
        "predicted": test_predictions,
        "absolute_error": np.abs(y_test.to_numpy() - test_predictions),
    })
    prediction_report.to_csv(
        output_dir / "evaluation_predictions.csv",
        index=False,
        encoding="utf-8-sig",
    )

    evaluation_report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_file": dataset_path.name,
        "worksheet": SHEET,
        "evaluation_method": "random_train_test_split",
        "test_size": TEST_SIZE,
        "random_state": RANDOM_STATE,
        "usable_rows": int(len(data)),
        "evaluation_train_rows": int(len(x_train)),
        "evaluation_test_rows": int(len(x_test)),
        "model": {"algorithm": "RandomForestRegressor", "metrics": model_metrics},
        "baseline": {"algorithm": "DummyRegressor(strategy=mean)", "metrics": baseline_metrics},
        "target_range": {
            "minimum": float(y.min()),
            "maximum": float(y.max()),
            "mean": float(y.mean()),
        },
        "feature_importances_from_evaluation_model": {
            name: float(value)
            for name, value in zip(FEATURES, evaluation_model.feature_importances_)
        },
        "warning": (
            "The workbook documentation describes the dataset as synthetic/random. "
            "These holdout metrics are software/training diagnostics, not evidence of "
            "real-world locomotive capability prediction."
        ),
    }
    (output_dir / "evaluation_report.json").write_text(
        json.dumps(evaluation_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Final deployment model: after evaluation is recorded, refit on every valid row.
    final_model = make_model()
    logging.info("FINAL_FIT_STARTED | rows=%d", len(x))
    final_model.fit(x, y)

    onnx_model = convert_sklearn(
        final_model,
        initial_types=[("features", FloatTensorType([None, 4]))],
        target_opset=17,
    )
    model_path = model_dir / "locomotive_model.onnx"
    model_path.write_bytes(onnx_model.SerializeToString())

    metadata = {
        "model_name": "locomotive-capability-regressor",
        "model_version": "0.3.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "algorithm": "RandomForestRegressor",
        "model_parameters": {
            "n_estimators": 80,
            "max_depth": 14,
            "min_samples_leaf": 8,
            "max_leaf_nodes": 128,
            "max_features": 1.0,
        },
        "features": FEATURES,
        "target": TARGET,
        "input_name": "features",
        "final_fit_rows": int(len(x)),
        "training_rows": int(len(x)),
        "test_rows": int(len(x_test)),
        "evaluation_train_rows": int(len(x_train)),
        "evaluation_test_rows": int(len(x_test)),
        "evaluation_method": "random_train_test_split",
        "random_state": RANDOM_STATE,
        "metrics": model_metrics,
        "baseline_metrics": baseline_metrics,
        "feature_importances": {
            name: float(value)
            for name, value in zip(FEATURES, final_model.feature_importances_)
        },
        "dataset_file": dataset_path.name,
        "dataset_is_synthetic": True,
        "warning": (
            "Workbook documentation describes this dataset as synthetic/random. "
            "Metrics are diagnostic only and do not establish operational validity."
        ),
    }
    metadata_path = model_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Create the exact ZIP format consumed by the local application.
    bundle_path = backend_model_dir / "model_bundle.zip"
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as bundle:
        bundle.write(model_path, arcname="locomotive_model.onnx")
        bundle.write(metadata_path, arcname="metadata.json")

    logging.info(
        "MODEL_EXPORTED | path=%s bytes=%d final_fit_rows=%d bundle=%s bundle_bytes=%d",
        model_path, model_path.stat().st_size, len(x), bundle_path, bundle_path.stat().st_size,
    )
    update_training_readme(evaluation_report, metadata, model_path, bundle_path)
    logging.info("README_UPDATED | path=%s", ROOT / "training" / "README.md")
    logging.info("REPORT_EXPORTED | path=%s", output_dir / "evaluation_report.json")
    logging.info("TRAIN_COMPLETE | status=success")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate and train the locomotive capability regression model."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "training" / "data" / "LocomotivDataSet.xlsx",
    )
    args = parser.parse_args()

    try:
        train(args.dataset.resolve())
        return 0
    except Exception:
        logging.exception("TRAIN_FAILED")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
