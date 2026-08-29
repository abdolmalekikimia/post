# EPS-49 Negative Scenarios

این تست‌ها مستقل از مسیر موفق پایه اجرا می‌شوند و مسیر موفق پایه را تغییر نمی‌دهند.

پیش‌شرط معتبر Login فقط برای اجرای تست‌های وابسته به توکن ادمین استفاده می‌شود. پاسخ منفی موردانتظار، مانند HTTP `400/401/403/404/422` یا پاسخ دستگاه با `status=2`، باعث PASS شدن همان سناریو می‌شود. پاسخ موفقِ ناخواسته یا خطای غیرمنتظره باعث توقف Flow و `NOT_CHECKED` شدن مراحل بعدی می‌شود.

سناریوهای فعال:

- Login با username نامعتبر
- Login با password نامعتبر
- Login با credential خالی
- ثبت IP با فرمت نامعتبر
- ثبت IP برای دستگاه ناشناخته
- ثبت IP بدون توکن ادمین
- Auth با `deviceId` نامعتبر
- Auth با `deviceToken` نامعتبر
- Auth با token خالی
- Handshake با protocol نامعتبر
- RegisterInbound قبل از Auth
- RegisterInbound با payload ناقص
- Auth پس از بسته‌شدن اتصال

اجرای تست:

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS49_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps49_negative.py -q -s
```
