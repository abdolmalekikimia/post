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

## اجرای مسیر موفق در Postman

فایل‌های Postman در پوشهٔ `postman` قرار دارند:

- `EPS-49-happy-path.postman_collection.json`
- `EPS-49-local.postman_environment.example.json`

برای اجرای محلی، environment نمونه را در Postman import کن و مقدارهای `adminPassword` و `deviceToken` را در Postman وارد کن. سپس این درخواست‌ها را به‌ترتیب اجرا کن:

1. `1.1 Login`
2. `1.2 Update Device IP`
3. در `2.1 Auth - success` روی `Connect` بزن و پیام Auth را ارسال کن.
4. پاسخ Auth باید `status=0` و `sessionId` داشته باشد.
5. بدون بستن همان اتصال، payload درخواست `2.2 RegisterInbound - success` را در همان تب WebSocket ارسال کن.
6. پاسخ RegisterInbound باید `status=0` باشد.

فایل `EPS-49-local.postman_environment.json` برای اجرای محلی ساخته می‌شود و در Git نادیده گرفته شده است؛ credentialها داخل فایل commit نمی‌شوند.

در تست Python بین هر عملیات API/WebSocket پنج ثانیه فاصله وجود دارد. این مقدار از متغیر `API_DELAY_SECONDS` در `config/test.env` خوانده می‌شود و در صورت نیاز قابل تغییر است.

## EPS-55 Python orchestration

سناریوهای EPS-55 در `flows/eps55_flow.py` پیاده‌سازی شده‌اند و شامل اعتبارسنجی چندبارکدی،
ثبت پست، Polling/Pending، جستجوی مقصد ۱۴رقمی و merge با نتیجهٔ Core هستند.
هر سناریو بلافاصله بعد از پاسخ validate می‌شود؛ اگر نتیجهٔ مورد انتظار نگیرد، سناریوی بعدی اجرا نمی‌شود.

قبل از اجرای E2E، Mockهای Postal/Core را طبق `EPS-55-test-requirements.md` در `appsettings.json`
تنظیم و سرویس را restart کن. سپس:

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS55="1"
.venv\Scripts\python.exe -m pytest tests/inbound_orchestration -q -s
```

برای اجرای تست‌های پایهٔ EPS-49 و EPS-53 نیز همین اصل برقرار است: Login، Update IP،
SignalR handshake و Auth باید موفق شوند تا مرحلهٔ بعدی اجرا شود.
