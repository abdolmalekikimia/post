# Device Lifecycle Negative Scenarios

این تست‌ها مستقل از مسیر موفق پایه اجرا می‌شوند و مسیر موفق پایه را تغییر نمی‌دهند.

پیش‌شرط معتبر Login فقط برای اجرای تست‌های وابسته به توکن ادمین استفاده می‌شود. پاسخ منفی موردانتظار، مانند HTTP `400/401/403/404/422` یا پاسخ دستگاه با `status=2`، باعث PASS شدن همان سناریو می‌شود. پاسخ موفقِ ناخواسته یا خطای غیرمنتظره باعث توقف Flow و `NOT_CHECKED` شدن مراحل بعدی می‌شود.

سناریوهای فعال:

- Login با username نامعتبر
- Login با password نامعتبر
- Login با credential خالی
- ثبت IP با فرمت نامعتبر
- ثبت IP برای دستگاه ناشناخته (رفتار فعلی: `200/upsert`؛ نیازمند تأیید پس از اتصال Gateway به Upstream)
- ثبت IP بدون توکن ادمین
- Auth با `deviceId` نامعتبر
- Auth با `deviceToken` نامعتبر
- Auth با token خالی
- Handshake با protocol نامعتبر
- RegisterItem قبل از Auth
- RegisterItem با payload ناقص
- Auth پس از بسته‌شدن اتصال

## سؤال باز QA — Update Device IP برای دستگاه ناشناخته

در محیط فعلی که Gateway هنوز به Upstream متصل نیست، Backend برای درخواست زیر پاسخ
موفق برگردانده است:

```text
PUT /api/devices/unknown-demo-device/ip
HTTP 200
{
  "deviceId": "unknown-demo-device",
  "ipAddress": "0.0.0.0"
}
```

تفسیر فعلی این است که endpoint برای ثبت یا جایگزینی
`DeviceNetworkBinding` به‌صورت upsert عمل می‌کند و وجود قبلی Device را
بررسی نمی‌کند. این رفتار هنوز قرارداد نهایی محسوب نمی‌شود، چون Gateway به Upstream
متصل نیست.

بعد از برقرار شدن اتصال واقعی Gateway به Upstream، این سناریو باید دوباره با یک
`deviceId` که در Upstream وجود ندارد اجرا شود و یکی از این دو رفتار به‌صورت رسمی
تأیید شود:

1. `200` و ثبت binding برای دستگاه ناشناخته مجاز است؛
2. فقط دستگاه موجود مجاز است و باید پاسخ خطای قراردادی مانند `404` برگردد.

در صورت انتخاب حالت دوم، سناریوی `unknown_device` در
`flows/device_lifecycle/device_lifecycle_negative_flow.py` باید دوباره به انتظار `4xx`
برگردد. در صورت انتخاب حالت اول، رفتار فعلی `200/upsert` صحیح است و باید در
قرارداد API مستند شود. این مورد از نظر QA یک سؤال قراردادی و همچنین بررسی
یکپارچگی داده/امنیت است، نه صرفاً یک خطای تست.

اجرای تست:

```powershell
$env:RUN_E2E="1"
$env:RUN_DEVICE_LIFECYCLE_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/negative/test_device_lifecycle_negative.py -q -s
```
