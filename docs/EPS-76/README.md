# EPS-76

## هدف

بررسی انتخاب مرسوله برای `bag.close` با فیلتر مقصد، chute، cursor، count و
درخواست‌های هم‌زمان.

## وضعیت پوشش

- Positive: `Implemented`
- Negative: `Implemented`؛ اجرای واقعی در Packing متمرکز است.
- Stress: `Planned`؛ هم‌زمانی انتخاب و بستن کیسه ارزش تست مستقل دارد.
- Protocol: `SignalR`
- Dependency: `Partial / External Dependency` — Packing parcel fixture

## Success

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_task_success.py -m eps76_success -q -s
```

## Negative

```powershell
$env:RUN_E2E="1"
$env:RUN_PACKING_NEGATIVE="1"
$env:PACKING_EPS76_CASE="TC-10"
.venv\Scripts\python.exe -m pytest tests/negative/test_packing_negative.py -m packing_negative -q -s
```

Caseهای Negative قابل اجرا:

`TC-08`، `TC-09`، `TC-10`، `TC-11`، `TC-12-chuteIds`،
`TC-12-parcelTypes`، `TC-12-serviceTypes`، `TC-13`، `TC-14`،
`TC-15`، `TC-15-empty`، `TC-16`، `TC-17`، `TC-18`

در سناریوهای هم‌زمان، مقصدها و barcodeهای تست باید از اجرای قبلی جدا باشند.
