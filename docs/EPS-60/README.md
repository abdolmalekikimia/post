# EPS-60

## هدف

بررسی Pending، timeout، unavailable، rejected و lookup مقصد برای barcodeهای
۱۴، ۲۴ و ۳۷ رقمی.

## وضعیت پوشش

- Positive: `Implemented`
- Negative: `Implemented`
- Stress: `Planned`؛ تکرار Pending، timeout و retry ارزش بررسی دارد.
- Protocol: `SignalR`
- Dependency: `Blocked / External Dependency` — Global Postal Mock scenario

## Success

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_task_success.py -m eps60_success -q -s
```

Success مربوط به `TC-08` است و به Postal Mock با سناریوی `Success` و مقصد معتبر
نیاز دارد.

## Negative

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS60_NEGATIVE="1"
$env:EPS60_CASE="TC-01"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps60_negative.py -q -s
```

هر اجرا فقط یک Case را می‌پذیرد، چون `PostalApi:Mock:Scenario` سراسری است.

جزئیات: [EPS60.md](../EPS60.md)
