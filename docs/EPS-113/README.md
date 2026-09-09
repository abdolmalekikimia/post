# EPS-113

## هدف

ثبت و ارسال رویدادهای ارتباطی به سرویس ثبت وقایع مرکزی جهت پایش وضعیت و تسهیل عیب‌یابی سامانه لبه، شامل رویدادهای:
1. برقراری اتصال (`ConnectionEstablished`)
2. قطع اتصال (`Disconnection`)
3. تلاش ناموفق (`FailedConnectionAttempt`)
4. وضعیت غیرعادی (`AbnormalCondition`)
5. چاپ مجدد برچسب (`LabelReprint`)

## معماری و دامنه

- **دامنه:** بخش ۵ — پایش وضعیت و ثبت وقایع مرکزی (`tests/5_monitoring/`)
- **ماژول تست:** `tests/5_monitoring/test_telemetry_and_events.py`

## وضعیت پوشش

- Positive: `Implemented` (TC-01, TC-05, TC-06)
- Negative: `Implemented` (TC-02, TC-03, TC-04, TC-07)
- Stress: `نیاز ندارد`
- Protocol: `SignalR`
- Dependency: `Partial / External Dependency` — Central Event Service و شواهد رویدادهای سرور مرکزی

## Caseهای تست

| Case | عنوان | دسته‌بندی | نوع رویداد مرکزی |
|---|---|---|---|
| `TC-01` | ثبت برقراری اتصال | Success | `ConnectionEstablished` |
| `TC-02` | ثبت قطع اتصال | Negative | `Disconnection` |
| `TC-03` | ثبت تلاش ناموفق احراز هویت | Negative | `FailedConnectionAttempt` |
| `TC-04` | ثبت وضعیت غیرعادی و پیام ناهنجار | Negative | `AbnormalCondition` |
| `TC-05` | ثبت چاپ مجدد برچسب | Success | `LabelReprint` |
| `TC-06` | بافر آفلاین و عدم انسداد در قطعی سرور مرکزی | Success | `ConnectionEstablished` |
| `TC-07` | مدیریت نوسان مکرر اتصال (Flapping) و یکتایی رویدادها | Negative | `Disconnection` |

## نحوهٔ اجرا

### تست‌های Success
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS113_SUCCESS="1"
$env:EPS113_CASE="all"
.venv\Scripts\python.exe -m pytest tests/5_monitoring -m eps113_success -q -s
```

### تست‌های Negative
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS113_NEGATIVE="1"
$env:EPS113_CASE="all"
.venv\Scripts\python.exe -m pytest tests/5_monitoring -m eps113_negative -q -s
```

### اجرای کل تست‌های EPS-113
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS113_SUCCESS="1"
$env:RUN_EPS113_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/5_monitoring -m "eps113_success or eps113_negative" -q -s
```
