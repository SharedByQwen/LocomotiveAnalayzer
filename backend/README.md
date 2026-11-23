# Backend API

این سرویس مدل ONNX را در Backend بارگذاری می‌کند و پیش‌بینی را از طریق HTTP API انجام می‌دهد. برای راه‌اندازی عادی، از فایل واحد `scripts/start_windows.bat` در ریشه پروژه استفاده کن.

فایل ZIP خروجی Google Colab بدون Extract در مسیر زیر ذخیره می‌شود:

`backend/models/model_bundle.zip`

ZIP باید شامل `locomotive_model.onnx` و `metadata.json` باشد. Backend فایل ZIP را هنگام شروع می‌خواند، مدل را اعتبارسنجی و در حافظه بارگذاری می‌کند. ZIP برای اجرای بعدی روی دیسک باقی می‌ماند.

API:
- `GET /api/health`
- `GET /api/model/status`
- `POST /api/model/upload`
- `POST /api/predict`

برای استقرار اینترنتی، احراز هویت، TLS، محدودیت آپلود و Rate Limit لازم است. نسخه فعلی روی loopback اجرا می‌شود و برای انتشار عمومی ایمن‌سازی نشده است.
