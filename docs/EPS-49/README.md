# EPS-49

## هدف

بررسی خطاهای چرخهٔ عمر دستگاه و قرارداد خطاهای REST و WebSocket.

## معماری و دامنه

- **دامنه:** بخش ۱ — راه‌اندازی، احراز هویت و همگام‌سازی خط (`tests/1_device_lifecycle/`)
- **ماژول تست:** `tests/1_device_lifecycle/test_device_lifecycle_and_auth.py`

## وضعیت پوشش

- Positive: `Implemented`
- Negative: `Implemented`
- Stress: `نیاز ندارد`؛ تمرکز EPS-49 روی قرارداد Lifecycle و Auth است.
- Protocol: `Mixed` (Admin API + WebSocket/SignalR)
- Dependency: `Ready` — Admin API و fixture معتبر دستگاه

## نحوهٔ اجرا

### تست‌های Success
مسیر سالم EPS-49 شامل Login معتبر ادمین، ثبت IP معتبر دستگاه، اتصال و handshake موفق WebSocket و Auth معتبر دستگاه است.

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m eps49_success -q -s
```

### تست‌های Negative
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS49_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m eps49_negative -q -s
```

### اجرای کلی هر دو مسیر EPS-49
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS49_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m "eps49_success or eps49_negative" -q -s
```

Caseهای قابل اجرا:
`invalid_username`، `invalid_password`، `empty_credentials`، `invalid_ip_format`، `unknown_device`، `missing_admin_token`، `invalid_device_id`، `invalid_device_token`، `empty_device_token`، `invalid_handshake_protocol`، `register_before_auth`، `malformed_register_payload`، `auth_after_connection_close`

جزئیات: [EPS49.md](../EPS49.md)