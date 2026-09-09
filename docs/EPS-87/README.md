# EPS-87

## هدف

بررسی قرارداد کامل پاسخ `bag.close` شامل `n/p/m/q`، `errors` و bag identity.

## وضعیت پوشش

- Positive: `Implemented`
- Negative: `Implemented`؛ اجرای واقعی در Packing متمرکز است.
- Stress: `نیاز ندارد`؛ تمرکز اصلی روی قرارداد دقیق پاسخ است.
- Protocol: `SignalR`
- Dependency: `Partial / External Dependency` — ParcelErrorOverrides در Postal Mock

## Success

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_task_success.py -m eps87_success -q -s
```

## Contract / Negative

```powershell
$env:RUN_E2E="1"
$env:RUN_PACKING_NEGATIVE="1"
$env:PACKING_EPS87_CASE="TC-06"
.venv\Scripts\python.exe -m pytest tests/negative/test_packing_negative.py -m packing_negative -q -s
```

Caseهای قابل اجرا:

`TC-01`، `TC-02`، `TC-03`، `TC-04`، `TC-05`، `TC-06`،
`TC-07`، `TC-08`، `TC-09`، `TC-10`

برای Caseهای failure باید `ParcelErrorOverrides` در Postal Mock تنظیم شود.
