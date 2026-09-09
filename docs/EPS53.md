# EPS-53 — Core History Negative Scenarios

سناریوهای EPS-53 پاسخ `RegisterInbound` را بر اساس سابقهٔ مرسوله در Core
بررسی می‌کنند.

## وضعیت fixtureهای Core

سناریوهای زیر فقط زمانی قابل اجرای واقعی هستند که دادهٔ مرجع لازم برای
barcodeهایشان در Mock Core تعریف شده باشد:

برای دو سناریوی Rejected، `HistoryRecord` باید با وضعیت `Rejected` ثبت شود:

- `core_rejected_with_destination`
- `core_rejected_without_destination`

- `core_timeout`
- `core_unavailable`

برای دو سناریوی discrepancy، همان HistoryRecord باید مقادیر مرجع فیزیکی
محموله را داشته باشد تا اختلاف با payload دستگاه قابل محاسبه باشد:

- `weight_discrepancy`
- `dimensions_discrepancy`

در محیط Edge-only، barcode بدون HistoryRecord طبق رفتار پیش‌فرض Mock موفق
تلقی می‌شود و پاسخ `status=0` می‌گیرد. تست نباید این پاسخ را به‌عنوان
Rejected یا discrepancy قبول کند و نباید انتظار `status=4` یا یک شیء
`discrepancy` را بدون fixture اعمال کند.

## اجرای تست

برای اجرای سناریوهای عمومی:

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS53_NEGATIVE="1"
$env:EPS53_CORE_HISTORY_READY="0"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps53_negative.py -q -s
```

پس از افزودن HistoryRecordهای لازم در Mock، اعمال mapping مقصد مرجوعی
`59544 -> 11369` و ثبت مقادیر مرجع فیزیکی برای barcode discrepancy:

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS53_NEGATIVE="1"
$env:EPS53_CORE_HISTORY_READY="1"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps53_negative.py -q -s
```

تا قبل از فعال‌کردن این flag، سناریوهای وابسته به fixture از اجرای E2E کنار
گذاشته می‌شوند تا پاسخ پیش‌فرض Mock باعث Failure کاذب نشود.

سناریوهای `core_timeout` و `core_unavailable` باید با trigger واقعی یا signal
قابل مشاهده از Core اجرا شوند. صرفاً دریافت `status=0` فقط fallback نهایی را
تأیید می‌کند و علت timeout یا unavailable را اثبات نمی‌کند.
