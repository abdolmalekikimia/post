# EPS-64

## هدف

بررسی ثبت تصویر و دادهٔ تکمیلی در مسیر lazy asynchronous upload.

## وضعیت پوشش

- Positive: `Implemented`
- Negative: `Implemented`
- Stress: `Planned`؛ پایداری Worker و صف Upload باید در حجم بالا بررسی شود.
- Protocol: `SignalR`
- Dependency: `Partial / External Dependency` — log یا SQLite برای شواهد Worker

## Success

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_task_success.py -m eps64_success -q -s
```

این تست یک تصویر JPEG معتبر، `imageId` و `supplementaryData` کامل ارسال می‌کند.

## Negative

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS64_NEGATIVE="1"
$env:EPS64_NEGATIVE_CASE="all"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps64_negative.py -q -s
```

نتیجهٔ نهایی Worker باید از طریق log یا SQLite سرویس بررسی شود.

جزئیات: [EPS64.md](../EPS64.md)
