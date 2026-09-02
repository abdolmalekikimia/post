# Configuration Sync — Configuration Synchronization Negative Tests

Configuration Sync مربوط به همگام‌سازی فهرست دستگاه‌ها و پیکربندی از Upstream است. در
معماری فعلی، تست مستقل مثبت Configuration Sync وجود ندارد؛ فقط سناریوهای منفی این تسک
در دستهٔ Negative اجرا می‌شوند.

## پیش‌نیاز

1. Snapshot را در مسیر
   `Integrations:UpstreamApi:Mock:DemoSnapshots:<SiteCode>` تنظیم کن.
2. مقدار `SiteCode` و کلید Snapshot با مرکز تست، مثلاً `10001`،
   یکسان باشند.
3. برای دستگاه‌ها `DeviceId`، `DeviceToken` و `ActivationStatus` را تنظیم کن.
4. بعد از تغییر Mock، سرویس را Restart کن؛ Sync اولیه هنگام Startup انجام
   می‌شود.
5. برای TC-07، IP دستگاه نباید از قبل مجاز باشد و Flow عمداً endpoint ثبت IP
   را اجرا نمی‌کند.

## Caseهای Negative خودکار

| Case | هدف | انتظار |
|---|---|---|
| TC-02 | دستگاه خارج از فهرست Sync | `status=2` و `invalid device credentials` |
| TC-03 | Token اشتباه دستگاه معتبر | `status=2` و `invalid device credentials` |
| TC-04 | دستگاه Inactive بعد از Sync | `status=2` و `device not active` |
| TC-06 | دستگاه Inactive با Token معتبر | `status=2` و `device not active` |
| TC-07 | دستگاه Active بدون IP مجاز | `status=2` و `source ip mismatch` |

TC-01 و TC-05 سناریوی مثبت/رفتار سالم Sync هستند و در Negative اجرا نمی‌شوند.
تأیید مسیر مثبت کلی فقط از طریق دو Flow موجود در `tests/success` انجام می‌شود.

## اجرا

```powershell
$env:RUN_E2E="1"
$env:RUN_CONFIGURATION_SYNC_NEGATIVE="1"
$env:CONFIGURATION_SYNC_CASE="TC-02"
.venv\Scripts\python.exe -m pytest tests/negative/test_configuration_sync_negative.py -q -s
```

برای Case دیگر مقدار `CONFIGURATION_SYNC_CASE` را تغییر بده. هر Case مستقل اجرا می‌شود،
چون وضعیت Snapshot و Restart موردنیاز Caseها با هم متفاوت است.

گزارش شامل payload واقعی، response واقعی، انتظار Case و نتیجهٔ PASS/FAIL است.
