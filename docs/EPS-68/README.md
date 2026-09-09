# EPS-68

## هدف

بررسی override وضعیت Core در پاسخ `RegisterInbound`.

## وضعیت پوشش

- Positive: `Missing`
- Negative: `Implemented`
- Stress: `نیاز ندارد`؛ این EPS یک قرارداد پاسخ و Mapping وضعیت است.
- Protocol: `SignalR`
- Dependency: `Blocked / External Dependency` — Core HistoryRecord fixtures

## اجرا

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS68_NEGATIVE="1"
$env:EPS68_CASE="all"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps68_negative.py -q -s
```

`TC-01` وضعیت Returning را به `status=3` و `TC-02` وضعیت Rejected را به
`status=4` تبدیل می‌کند. `TC-03` و `TC-04` نبودن override اشتباه را بررسی
می‌کنند.

بارکدهای fixture باید با HistoryRecord متناظر در Core Mock تنظیم شوند.
