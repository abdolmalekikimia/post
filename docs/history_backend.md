# History Backend — Upstream History Negative Scenarios

سناریوهای History Backend پاسخ `RegisterItem` را بر اساس سابقهٔ مرسوله در Upstream
بررسی می‌کنند.

## وضعیت fixtureهای Upstream

سناریوهای زیر فقط زمانی قابل اجرای واقعی هستند که دادهٔ مرجع لازم برای
barcodeهایشان در Mock Upstream تعریف شده باشد:

برای دو سناریوی Rejected، `HistoryFixture` باید با وضعیت `Rejected` ثبت شود:

- `upstream_rejected_with_destination`
- `upstream_rejected_without_destination`

- `upstream_timeout`
- `upstream_unavailable`

برای دو سناریوی discrepancy، همان HistoryFixture باید مقادیر مرجع فیزیکی
محموله را داشته باشد تا اختلاف با payload دستگاه قابل محاسبه باشد:

- `weight_discrepancy`
- `dimensions_discrepancy`

در محیط Gateway-only، barcode بدون HistoryFixture طبق رفتار پیش‌فرض Mock موفق
تلقی می‌شود و پاسخ `status=0` می‌گیرد. تست نباید این پاسخ را به‌عنوان
Rejected یا discrepancy قبول کند و نباید انتظار `status=4` یا یک شیء
`discrepancy` را بدون fixture اعمال کند.

## اجرای تست

برای اجرای سناریوهای عمومی:

```powershell
$env:RUN_E2E="1"
$env:RUN_HISTORY_BACKEND_NEGATIVE="1"
$env:HISTORY_BACKEND_READY="0"
.venv\Scripts\python.exe -m pytest tests/negative/test_history_backend_negative.py -q -s
```

پس از افزودن HistoryFixtureهای لازم در Mock، اعمال mapping مقصد مرجوعی
`10001 -> 22222` و ثبت مقادیر مرجع فیزیکی برای barcode discrepancy:

```powershell
$env:RUN_E2E="1"
$env:RUN_HISTORY_BACKEND_NEGATIVE="1"
$env:HISTORY_BACKEND_READY="1"
.venv\Scripts\python.exe -m pytest tests/negative/test_history_backend_negative.py -q -s
```

تا قبل از فعال‌کردن این flag، سناریوهای وابسته به fixture از اجرای E2E کنار
گذاشته می‌شوند تا پاسخ پیش‌فرض Mock باعث Failure کاذب نشود.

سناریوهای `upstream_timeout` و `upstream_unavailable` باید با trigger واقعی یا signal
قابل مشاهده از Upstream اجرا شوند. صرفاً دریافت `status=0` فقط fallback نهایی را
تأیید می‌کند و علت timeout یا unavailable را اثبات نمی‌کند.
