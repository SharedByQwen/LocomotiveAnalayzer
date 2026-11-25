# Locomotive Analyzer

ابزار محلی تحلیل قابلیت سیر لکوموتیو با رابط React و API پایتون.

## اجرای برنامه در Windows

برای اجرای کل برنامه فقط فایل **START.bat** را اجرا کن.

Starter به‌ترتیب:
- وجود Python و Node.js را بررسی می‌کند و در صورت امکان با winget نصب می‌کند.
- محیط مجازی Python را ایجاد و وابستگی‌ها را نصب/به‌روزرسانی می‌کند.
- وابستگی‌های Frontend را نصب می‌کند.
- تست‌های Frontend و Build تایپ‌اسکریپت را اجرا می‌کند.
- Backend و Frontend را اجرا و آماده بودن API را بررسی می‌کند.
- مدل ONNX را در پس‌زمینه بارگذاری می‌کند؛ بنابراین حتی اگر مدل نصب نباشد یا بارگذاری آن طول بکشد، رابط کاربری بالا می‌آید.

آدرس برنامه: http://127.0.0.1:5173

پنجره Starter را تا پایان استفاده نبند. لاگ‌های Backend:
- `backend/backend.stdout.log`
- `backend/backend.stderr.log`

## مدل

فایل مدل در Git ذخیره نمی‌شود. برای اجرای پیش‌بینی، فایل ZIP شامل دو فایل زیر را از رابط برنامه نصب کن یا آن را در مسیر زیر قرار بده:

`backend/models/model_bundle.zip`

محتویات ZIP:
- `locomotive_model.onnx`
- `metadata.json`

اگر مدل موجود نباشد، برنامه در حالت بدون مدل اجرا می‌شود و پیش‌بینی تا زمان نصب مدل در دسترس نخواهد بود.

## معماری

- Frontend: React + TypeScript + Vite
- Backend: Python + FastAPI
- Inference: ONNX Runtime روی CPU
- بارگذاری مدل هنگام شروع Backend در Thread جداگانه انجام می‌شود.

## آموزش مدل

تمام ابزارهای آموزش در پوشه [`training/`](training/) قرار دارند:
- رابط گرافیکی آموزش روی Windows: [`training/TRAIN_LOCAL.bat`](training/TRAIN_LOCAL.bat)
- Notebook آموزش Google Colab: [`training/colab_train.ipynb`](training/colab_train.ipynb)
- راهنمای پارامترها و گزارش خودکار آخرین آموزش: [`training/README.md`](training/README.md)

هر دو روش از هسته مشترک `training/train_model.py` استفاده می‌کنند. پس از آموزش موفق، مدل ONNX، بسته ZIP آماده نصب، گزارش معیارها و بخش نتایج README به‌روزرسانی می‌شوند.

## محدودیت اعتبار

مستندات فایل Excel فعلی داده‌ها را مصنوعی/تصادفی معرفی می‌کند. بنابراین معیارهای MAE، RMSE و R² صرفاً معیارهای فنی همین داده هستند و اعتبار پیش‌بینی خرابی واقعی لکوموتیو را ثابت نمی‌کنند.

نسخه فعلی برای اجرای محلی/شبکه توسعه است و API احراز هویت ندارد؛ پیش از انتشار عمومی باید احراز هویت، TLS، کنترل دسترسی آپلود و Rate Limit اضافه شوند.
