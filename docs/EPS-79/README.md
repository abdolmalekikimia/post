# EPS-79

## هدف

بررسی مسیر export قبل از بستن کیسه: ثبت مرسوله، تخصیص مقصد و `bag.close`.

## وضعیت پوشش

- Positive: `Implemented`
- Negative: `Implemented`؛ اجرای واقعی در Packing متمرکز است.
- Stress: `Planned`؛ ترتیب export، retry و بستن هم‌زمان باید بررسی شود.
- Protocol: `SignalR`
- Dependency: `Blocked / External Dependency` — Postal export و parcel fixture

## Success

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_task_success.py -m eps79_success -q -s
```

## Negative

```powershell
$env:RUN_E2E="1"
$env:RUN_PACKING_NEGATIVE="1"
$env:PACKING_EPS79_CASE="TC-16"
.venv\Scripts\python.exe -m pytest tests/negative/test_packing_negative.py -m packing_negative -q -s
```

Caseهای Negative قابل اجرا:

`TC-03`، `TC-04`، `TC-05`، `TC-06`، `TC-07`، `TC-08`،
`TC-11`، `TC-12`، `TC-13`، `TC-14`، `TC-15`، `TC-16`،
`TC-17`، `TC-18`، `TC-19`

سناریوهای Postal و retry به تغییر profile Mock بین تلاش‌ها نیاز دارند؛ اجرای
همهٔ Caseها با یک profile واحد نتیجهٔ قابل اتکا نمی‌دهد.
