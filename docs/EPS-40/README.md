# EPS-40

## هدف

بررسی همگام‌سازی تنظیمات دستگاه و احراز هویت دستگاه پس از Config Sync.

## معماری و دامنه

- **دامنه:** بخش ۱ — راه‌اندازی، احراز هویت و همگام‌سازی خط (`tests/1_device_lifecycle/`)
- **ماژول تست:** `tests/1_device_lifecycle/test_device_lifecycle_and_auth.py`

## وضعیت پوشش

- Positive: `Implemented`
- Negative: `Implemented`
- Stress: `نیاز ندارد`؛ تمرکز EPS-40 روی صحت Config Sync و Auth است.
- Protocol: `Mixed` (Admin API + SignalR)
- Dependency: `Blocked / External Dependency` — Core ConfigSnapshot و Restart سرویس

## نحوهٔ اجرا

### تست‌های Success
```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m eps40_success -q -s
```

### تست‌های Negative
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS40_NEGATIVE="1"
$env:EPS40_CASE="all"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m eps40_negative -q -s
```

این تست‌ها شامل Login، ثبت IP، اتصال SignalR و Auth موفق دستگاه Active، و همچنین سناریوهای منفی `TC-02`، `TC-03`، `TC-04`، `TC-06` و `TC-07` می‌باشند.

برای TC-04 و TC-06 باید Snapshot Core با وضعیت دستگاه Inactive و نسخهٔ مناسب تنظیم و سرویس Restart شود. TC-07 به حذف binding قبلی IP نیاز دارد.

جزئیات: [EPS40.md](../EPS40.md)