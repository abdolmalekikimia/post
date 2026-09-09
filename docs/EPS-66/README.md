# EPS-66 — خوانش مجدد State-driven

پیاده‌سازی فعلی EPS-66 مبتنی بر زمان نیست. مقادیر `ShortTerm=6h` و
`LongTerm=72h` فقط از Core سینک و Validate می‌شوند و در تصمیم `RegisterInbound`
در Edge استفاده نمی‌شوند.

## وضعیت پوشش

- Protocol: `SignalR`
- Positive: `Implemented`
- Negative: `Implemented`
- Stress: `Planned`؛ تست هم‌زمانی rescan و `bag.close` نیازمند اجرای جداگانه است.
- Dependency: `Partial / External Dependency`

## حالت اجرای Backend

منطق Flow در هر دو حالت یکسان است و فقط Fixture Provider تغییر می‌کند:

```powershell
# حالت Mock؛ پیش‌فرض
$env:EPS66_BACKEND_MODE = "mock"

# حالت Core واقعی؛ بدون اعمال Overrideهای Mock
$env:EPS66_BACKEND_MODE = "core"
$env:EPS66_CORE_READY = "1"
```

در حالت Mock باید HistoryRecordهای EPS-66 در Backend Mock فعال باشند. وضعیت
`EdgeParcel` و `BagCloseAttempt` بخشی از Core Mock نیست و باید با Flow عمومی یا
Seed دیتابیس Edge آماده شود.

## Caseها

- `TC-01`: rescan با مقصد ثابت و کیسه باز؛ Postal نباید دوباره ثبت کند.
- `TC-02`: تغییر مقصد مرسوله باز با `AssignDestination`؛ مقصد قبلی در state حفظ
  می‌شود.
- `TC-03`: rescan پس از `ExportRegistered` یا `Bagged`؛ مسیر
  `RegisterFreshAfterPriorOutbound` اجرا می‌شود.
- `TC-04`: خوانش جدیدتر، مقدار Canonical را جلو می‌برد.
- `TC-05`: خوانش قدیمی‌تر نباید Canonical را عقب ببرد.
- `TC-06`: retry همان Attempt با همان Timestamp باید از Ledger replay شود.

## اجرا

```powershell
$env:RUN_E2E = "1"
$env:RUN_EPS66_SUCCESS = "1"
.\.venv\Scripts\python.exe -m pytest tests/success/test_eps66_success.py -m eps66_success -vv

$env:RUN_EPS66_NEGATIVE = "1"
.\.venv\Scripts\python.exe -m pytest tests/negative/test_eps66_negative.py -m eps66_negative -vv
```

برای Core واقعی، قبل از اجرا HistoryRecord، وضعیت مرسوله و دسترسی مشاهدهٔ
Idempotency/ReadingId باید توسط محیط آماده شده باشد.
