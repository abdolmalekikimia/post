# Positive Flows

تست‌های مثبت مستقل EPS-53، EPS-55 و EPS-64 حذف شده‌اند. سناریوهای آن‌ها اکنون
در هر دو Flow مثبت زیر اجرا می‌شوند:

- `tests/device_lifecycle/test_auth_success.py` — مسیر موفق پایه
- `tests/device_lifecycle/test_websocket_flow.py` — Flow مستقل WebSocket/SignalR

هر دو Flow مراحل مشترک Login، ثبت IP، Handshake و Auth را اجرا می‌کنند و سپس
ثبت واردهٔ پایه و caseهای EPS-53، EPS-55 و EPS-64 را روی همان اتصال اجرا
می‌کنند. شکست هر مرحله باعث `NOT_CHECKED` شدن مراحل بعدی می‌شود.

گزارش مرحله‌ها با برچسب دامنه تولید می‌شود:

```text
[EPS-49] Inbound Registration - RegisterInbound
[EPS-53] RegisterInbound - success_no_discrepancy
[EPS-55] RegisterInbound - postal_success
[EPS-64] RegisterInbound staging - image_staging_success
```

چهار مرحلهٔ آماده‌سازی با برچسب `[BASE]` گزارش می‌شوند.

در هر مرحله فقط payload ارسالی، response دریافتی و نتیجهٔ انتظار نمایش داده
می‌شود. پاسخ‌های status `2`، `3` یا `4` در caseهایی که همین status را انتظار
دارند، به‌عنوان PASS محسوب می‌شوند؛ چون این caseها رفتار مورد انتظار سرویس را
بررسی می‌کنند.

تعریف caseهای قابل استفادهٔ EPS-53 و EPS-55 برای Negative و Stress باقی
مانده است و حذف نشده است.
