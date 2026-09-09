# EPS-89

## هدف

بررسی مسیر بستن فیزیکی کیسه، خطای parcel و audit شناسهٔ bag.

## وضعیت پوشش

- Positive: `Implemented`
- Negative: `Implemented`؛ اجرای واقعی در Packing متمرکز است.
- Stress: `نیاز ندارد`؛ audit و قرارداد هویت bag ریسک اصلی این EPS هستند.
- Protocol: `SignalR`
- Dependency: `Partial / External Dependency` — audit log/queue/database evidence

## Success

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_task_success.py -m eps89_success -q -s
```

## Negative / Audit

```powershell
$env:RUN_E2E="1"
$env:RUN_PACKING_NEGATIVE="1"
$env:PACKING_EPS89_CASE="TC-04"
.venv\Scripts\python.exe -m pytest tests/negative/test_packing_negative.py -m packing_negative -q -s
```

Caseهای قابل اجرا:

`TC-01`، `TC-02`، `TC-03`، `TC-04`، `TC-05`، `TC-06`

قرارداد پاسخ `bag.close` خودکار بررسی می‌شود؛ audit نهایی باید در log، queue یا
database سرویس Backend بررسی شود.
