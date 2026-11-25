# Backend API

این سرویس مدل ONNX را در Backend بارگذاری می‌کند و پیش‌بینی را از طریق HTTP API انجام می‌دهد.

فایل مدل:
`backend/models/model_bundle.zip`

ZIP باید شامل `locomotive_model.onnx` و `metadata.json` باشد. فایل‌ها می‌توانند داخل زیرپوشه ZIP هم باشند.

Backend هنگام Startup مدل را در Thread پس‌زمینه بارگذاری می‌کند؛ بنابراین Health API و رابط کاربری تا پایان بارگذاری معطل نمی‌مانند. وضعیت‌های مدل از طریق `GET /api/model/status` قابل مشاهده‌اند: `loading`، `ready`، `missing` و `error`.

برای اجرای کل برنامه در Windows فقط از فایل ریشه پروژه استفاده کن:

`START.bat`

API:
- `GET /api/health`
- `GET /api/model/status`
- `POST /api/model/upload`
- `POST /api/predict`

برای انتشار عمومی، احراز هویت، TLS، محدودیت آپلود و Rate Limit لازم است.
