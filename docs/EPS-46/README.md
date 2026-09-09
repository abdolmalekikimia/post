# EPS-46

## هدف

بررسی اعتبارسنجی `AutoDispatchPolicy` هنگام Config Sync.

## معماری و دامنه

- **دامنه:** بخش ۱ — راه‌اندازی، احراز هویت و همگام‌سازی خط (`tests/1_device_lifecycle/`)
- **ماژول تست:** `tests/1_device_lifecycle/test_device_lifecycle_and_auth.py`

## وضعیت پوشش

- Positive: `Implemented`
- Negative: `Implemented`
- Stress: `نیاز ندارد`
- Protocol: `Mixed` (Admin API + Config Sync/SignalR)
- Dependency: `Blocked / External Dependency` — ConfigVersion، Policy snapshot و Restart سرویس

## نحوهٔ اجرا

### تست‌های Success (شامل TC-01 مسیر مثبت)
```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m eps46_success -q -s
```

### تست‌های Negative (TC-03, TC-04, TC-05)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS46_NEGATIVE="1"
$env:EPS46_CASE="all"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m eps46_negative -q -s
```

برای هر Case باید `ConfigVersion` افزایش یابد، Snapshot تغییر کند و سرویس Restart شود.

جزئیات: [EPS46.md](../EPS46.md)