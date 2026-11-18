# Model training

The script reads the workbook sheet named گزارش روزانه.

Only four columns are model inputs, in this exact order:
1. وضعیت سیر قبل (۱=سالم، ۰=خراب)
2. روز از آخرین خرابی در سیر
3. زمان تعمیرات امروز (ساعت)
4. هزینه تعمیر (یورو)

Target: قابلیت سیر امروز.

Date columns and locomotive number are deliberately excluded from model features. The script uses a deterministic random 80/20 train/test split and reports MAE, RMSE and R². ONNX model and metadata are written to public/models.

The supplied workbook guide describes its data as synthetic/random. Do not interpret test metrics as evidence of operational predictive accuracy.