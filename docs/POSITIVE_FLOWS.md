# Positive Flows

در این پروژه فقط دو Flow مثبت وجود دارد:

1. مسیر موفق پایهٔ کل فلو
2. Flow مستقل موفق WebSocket/SignalR

هیچ تست مثبت task-oriented جداگانه‌ای برای EPS-40، EPS-49، EPS-53، EPS-55،
EPS-64 یا EPS-71 وجود ندارد. دو Case مثبت EPS-71 به‌عنوان ادامهٔ هر دو Flow
موفق اجرا می‌شوند؛ سناریوهای task-oriented منفی در بخش Negative هستند و Stress
نیز دستهٔ مستقل خودش است.

## مسیر موفق پایه

مسیر:

1. Login ادمین
2. ثبت IP دستگاه
3. اتصال WebSocket و SignalR handshake
4. Auth دستگاه
5. `RegisterInbound`
6. ثبت مرسوله برای EPS-71، Case با شوتر
7. `destination.assign` برای EPS-71، Case با شوتر
8. ثبت مرسوله برای EPS-71، Case بدون شوتر
9. `destination.assign` برای EPS-71، Case بدون شوتر

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
موفق WebSocket را اجرا می‌کند و سپس دو Case مثبت EPS-71 را اجرا می‌کند:

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

مراحل EPS-71 با برچسب `[EPS-71]` مشخص می‌شوند و payload کامل ثبت مرسوله و
تخصیص مقصد را گزارش می‌کنند.

این Flowها خطی هستند؛ شکست هر مرحله باعث می‌شود مراحل بعدی با وضعیت
`NOT_EXECUTED` ثبت شوند.
