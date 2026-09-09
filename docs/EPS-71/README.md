# EPS-71

## هدف

بررسی تخصیص مقصد با و بدون `chuteId`.

## وضعیت پوشش

- Positive: `Implemented`
- Negative: `Implemented`
- Stress: `Planned`؛ فشار و تکرار تخصیص مقصد می‌تواند رفتار state را آشکار کند.
- Protocol: `SignalR`
- Dependency: `Partial / External Dependency` — Destination و Bag fixture

## Success

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_task_success.py -m eps71_success -q -s
```

## Negative

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS71_NEGATIVE="1"
$env:EPS71_CASE="TC-07"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps71_negative.py -q -s
```

Caseهای قابل اجرا:

`TC-03-missing`، `TC-03-empty`، `TC-04-missing`، `TC-04-empty`،
`TC-05-short`، `TC-05-long`، `TC-06`، `TC-07`، `TC-08`، `TC-09`، `TC-13`

کدهای مقصد باید از فهرست معتبر Backend Mock انتخاب شوند.

جزئیات: [EPS71.md](../EPS71.md)
