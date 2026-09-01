# Policy Sync — RoutingPolicy Negative Tests

Policy Sync دریافت و نگهداری تنظیمات `RoutingPolicy` را هنگام Config Sync
بررسی می‌کند. این Story منطق واقعی بستن خودکار دپش را اجرا نمی‌کند.

## محدودیت Black-box

این مقدار فعلاً مصرف‌کنندهٔ قابل مشاهده‌ای در WebSocket یا API دیگری ندارد.
بنابراین تست فقط می‌تواند از طریق `Auth` به‌صورت غیرمستقیم بررسی کند که بستهٔ
Config Sync پذیرفته یا رد شده است. برای بررسی مقدار دقیق ذخیره‌شده، Dev باید
Database یا لاگ سرویس را بررسی کند.

قبل از هر Case:

1. در Snapshot مسیر `Integrations:UpstreamApi:Mock:ConfigSnapshots:<SiteCode>`
   مقدار `RoutingPolicy` را تغییر بده.
2. `ConfigVersion` را افزایش بده.
3. سرویس را Restart کن تا Sync هنگام Startup اجرا شود.
4. دستگاه و IP موردنیاز Case را طبق محیط تست آماده کن.

نمونهٔ معتبر:

```json
"RoutingPolicy": {
  "IsEnabled": true,
  "AllowedDeadline": "02:00:00"
}
```

## جایگاه در پروژه

Policy Sync در دستهٔ Negative قرار دارد:

```text
flows/config_sync/policy_sync_negative_flow.py
tests/negative/test_policy_sync_negative.py
```

TC-01 و TC-02 مستندات عمومی منبع، رفتار مثبت task-oriented هستند و عمداً به Success
اضافه نشده‌اند؛ Success فقط مسیر موفق پایه و Flow مستقل WebSocket/SignalR است.

## Caseهای پیاده‌سازی‌شده

| Case | Mock موردنیاز | انتظار |
|---|---|---|
| TC-03 | `IsEnabled=true`, deadline=`00:00:00`، `ConfigVersion` جدید | `status=2`؛ کل Sync رد شود |
| TC-04 | `IsEnabled=true`, deadline منفی، `ConfigVersion` جدید | `status=2`؛ کل Sync رد شود |
| TC-05 | `IsEnabled=false`, deadline منفی، `ConfigVersion` جدید | `status=0`؛ یافتهٔ اکتشافی کیفیت داده |

در TC-03 و TC-04، دستگاه جدید باید فقط در Snapshot نامعتبر تعریف شده باشد تا
رد شدن کل Sync از طریق Auth قابل مشاهده باشد. ثبت IP در Flow عمداً انجام
نمی‌شود و باید به‌عنوان پیش‌شرط محیط تست آماده باشد. در TC-05 دستگاه Active
موجود است و Flow IP آن را ثبت می‌کند.

## اجرا

```powershell
$env:RUN_E2E="1"
$env:RUN_POLICY_SYNC_NEGATIVE="1"
$env:POLICY_SYNC_CASE="TC-03"
.venv\Scripts\python.exe -m pytest tests/negative/test_policy_sync_negative.py -q -s
```

برای اجرای TC-04 یا TC-05 مقدار `POLICY_SYNC_CASE` را تغییر بده.

پاسخ مورد انتظار PASS محسوب می‌شود؛ پاسخ غیرمنتظره یا خطای Transport باعث
FAIL می‌شود. گزارش هر مرحله شامل `payloadSent`، `responseReceived`، انتظار و
نتیجه است.
