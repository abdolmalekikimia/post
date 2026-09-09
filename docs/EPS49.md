# EPS-49 Negative Scenarios

راهنمای تست‌های Negative مربوط به چرخهٔ عمر دستگاه و قراردادهای REST و
WebSocket در EPS-49.

این تست‌ها مستقل از مسیر موفق پایه اجرا می‌شوند و مسیر موفق پایه را تغییر نمی‌دهند.

پیش‌شرط معتبر Login فقط برای اجرای تست‌های وابسته به توکن ادمین استفاده می‌شود. پاسخ منفی موردانتظار، مانند HTTP `400/401/403/404/422` یا پاسخ دستگاه با `status=2`، باعث PASS شدن همان سناریو می‌شود. پاسخ موفقِ ناخواسته یا خطای غیرمنتظره فقط همان سناریو را `FAIL` می‌کند؛ سناریوهای بعدی همچنان اجرا می‌شوند تا گزارش کامل‌تری از کل Suite به‌دست بیاید.

سناریوهای فعال:

- Login با username نامعتبر
- Login با password نامعتبر
- Login با credential خالی
- ثبت IP با فرمت نامعتبر
- ثبت IP برای دستگاه ناشناخته (رفتار فعلی: `200/upsert`؛ نیازمند تأیید پس از اتصال Edge به Core)
- ثبت IP بدون توکن ادمین
- Auth با `deviceId` نامعتبر
- Auth با `deviceToken` نامعتبر
- Auth با token خالی
- Handshake با protocol نامعتبر
- RegisterInbound قبل از Auth
- RegisterInbound با payload ناقص
- Auth پس از بسته‌شدن اتصال

## سؤال باز QA — Update Device IP برای دستگاه ناشناخته

در محیط فعلی که Edge هنوز به Core متصل نیست، Backend برای درخواست زیر پاسخ
موفق برگردانده است:

```text
PUT /admin/devices/UNKNOWN-DEVICE-001/ip
HTTP 200
{
  "deviceId": "UNKNOWN-DEVICE-001",
  "ipAddress": "192.168.10.191"
}
```

تفسیر فعلی این است که endpoint برای ثبت یا جایگزینی
`DeviceNetworkBinding` به‌صورت upsert عمل می‌کند و وجود قبلی Device را
بررسی نمی‌کند. این رفتار هنوز قرارداد نهایی محسوب نمی‌شود، چون Edge به Core
متصل نیست.

بعد از برقرار شدن اتصال واقعی Edge به Core، این سناریو باید دوباره با یک
`deviceId` که در Core وجود ندارد اجرا شود و یکی از این دو رفتار به‌صورت رسمی
تأیید شود:

1. `200` و ثبت binding برای دستگاه ناشناخته مجاز است؛
2. فقط دستگاه موجود مجاز است و باید پاسخ خطای قراردادی مانند `404` برگردد.

در صورت انتخاب حالت دوم، سناریوی `unknown_device` در
`flows/device_lifecycle/eps49_negative_flow.py` باید دوباره به انتظار `4xx`
برگردد. در صورت انتخاب حالت اول، رفتار فعلی `200/upsert` صحیح است و باید در
قرارداد API مستند شود. این مورد از نظر QA یک سؤال قراردادی و همچنین بررسی
یکپارچگی داده/امنیت است، نه صرفاً یک خطای تست.

اجرای تست:

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS49_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps49_negative.py -q -s
```

## اجرای تست کلی پروژه

در اجرای کلی پروژه، تست منفی EPS-49 با برچسب `EPS-49/negative` اجرا می‌شود. تست مثبت
EPS-49 نیز به‌صورت جداگانه با برچسب `EPS-49/success` اجرا می‌شود.

```powershell
& .venv\Scripts\python.exe scripts/run_all_tests.py
```
