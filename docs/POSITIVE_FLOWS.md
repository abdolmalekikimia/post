# Positive Flows

در این پروژه فقط دو Flow مثبت وجود دارد:

1. مسیر موفق پایهٔ کل فلو
2. Flow مستقل موفق WebSocket/SignalR

هیچ تست مثبت task-oriented جداگانه‌ای برای EPS-40، EPS-49، EPS-53، EPS-55 یا
EPS-64 در این دسته وجود ندارد. سناریوهای task-oriented فقط در بخش Negative
پیاده‌سازی می‌شوند؛ Stress نیز دستهٔ مستقل خودش است.

## مسیر موفق پایه

مسیر:

1. Login ادمین
2. ثبت IP دستگاه
3. اتصال WebSocket و SignalR handshake
4. Auth دستگاه
5. `RegisterInbound`

فایل اجرا:

```text
tests/success/test_base_success.py
```

اجرا:

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_base_success.py -q -s
```

## Flow مستقل WebSocket/SignalR

این Flow برای اعتبارسنجی مستقل transport و پیام‌های دستگاه است و همان مسیر
موفق WebSocket را اجرا می‌کند:

```text
tests/success/test_websocket_success.py
```

اجرا:

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_websocket_success.py -q -s
```

## گزارش

هر مرحله با برچسب `[BASE]` و شمارهٔ خودش گزارش می‌شود و شامل این سه بخش اصلی
است:

- `payloadSent`: payload واقعی ارسال‌شده
- `responseReceived`: پاسخ واقعی Backend
- `expected` یا `error`: نتیجهٔ assertion و خطای دقیق در صورت شکست

این Flowها خطی هستند؛ شکست هر مرحله باعث می‌شود مراحل بعدی با وضعیت
`NOT_EXECUTED` ثبت شوند.
