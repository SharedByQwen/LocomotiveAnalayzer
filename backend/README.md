# Backend API

این سرویس مدل ONNX را در Backend بارگذاری می‌کند و پیش‌بینی را از طریق HTTP API انجام می‌دهد.

فایل مدل را دستی در مسیر زیر قرار بده:

`backend/models/model_bundle.zip`

ZIP باید شامل `locomotive_model.onnx` و `metadata.json` باشد. فایل‌ها می‌توانند داخل زیرپوشه ZIP هم باشند؛ نیازی به Extract نیست.

برای اجرای کل برنامه فقط از اسکریپت واحد زیر استفاده کن:

`scripts/start_windows.bat`

Backend هنگام شروع ZIP را اعتبارسنجی و مدل را در حافظه بارگذاری می‌کند. ZIP برای اجراهای بعدی روی دیسک باقی می‌ماند.

API:
- `GET /api/health`
- `GET /api/model/status`
- `POST /api/model/upload`
- `POST /api/predict`

برای انتشار عمومی، احراز هویت، TLS، محدودیت آپلود و Rate Limit لازم است.
