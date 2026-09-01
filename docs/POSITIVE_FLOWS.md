# Positive Flows

در این پروژه فقط دو Flow مثبت وجود دارد:

1. مسیر موفق پایهٔ کل فلو
2. Flow مستقل موفق WebSocket/SignalR

هیچ تست مثبت task-oriented جداگانه‌ای برای Configuration Sync، Device Lifecycle، History Backend، Delivery Merge،
Lazy Upload یا Destination Assignment وجود ندارد. دو Case مثبت Destination Assignment به‌عنوان ادامهٔ هر دو Flow
موفق اجرا می‌شوند؛ سناریوهای task-oriented منفی در بخش Negative هستند و Stress
نیز دستهٔ مستقل خودش است.

## مسیر موفق پایه

مسیر:

1. Login ادمین
2. ثبت IP دستگاه
3. اتصال WebSocket و SignalR handshake
4. Auth دستگاه
5. `RegisterItem`
6. ثبت مرسوله برای Destination Assignment، Case با شوتر
7. `route.assign` برای Destination Assignment، Case با شوتر
8. ثبت مرسوله برای Destination Assignment، Case بدون شوتر
9. `route.assign` برای Destination Assignment، Case بدون شوتر

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
موفق WebSocket را اجرا می‌کند و سپس دو Case مثبت Destination Assignment را اجرا می‌کند:

- `TC-01`: تخصیص مقصد با `chuteId`
- `TC-02`: تخصیص مقصد بدون `chuteId`

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

مراحل Destination Assignment با برچسب `[Destination Assignment]` مشخص می‌شوند و payload کامل ثبت مرسوله و
تخصیص مقصد را گزارش می‌کنند.

این Flowها خطی هستند؛ شکست هر مرحله باعث می‌شود مراحل بعدی با وضعیت
`NOT_EXECUTED` ثبت شوند.
