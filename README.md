# EPS-49 Python happy-path test

این پروژه فقط مسیر موفق EPS-49 را تست می‌کند:

1. ورود ادمین
2. ثبت IP دستگاه
3. اتصال WebSocket
4. ارسال Auth
5. ارسال RegisterInbound

## راه‌اندازی

```powershell
python -m pip install -r requirements.txt
```

مقادیر واقعی `ADMIN_PASSWORD` و `DEVICE_TOKEN` را در `config/test.env` وارد کنید.
همچنین دستگاه باید در دیتابیس seed شده، فعال باشد و IP آن با `DEVICE_IP` یکسان باشد.

## اجرای تست

```powershell
$env:RUN_E2E="1"
python -m pytest -q
```

یا مستقیماً:

```powershell
python -m flows.device_auth_flow
```
