# EPS-60 — Pending response و رفتار بارکد

این تست بر اساس سندی است که محتوای آن با EPS-61 / G6-08 و G6-09
مطابقت دارد. هدف آن بررسی این است که در صورت Timeout یا بی‌پاسخ‌ماندن
Postal، Edge پاسخ `Pending` بدهد و دستگاه سورت متوقف نشود.

## جایگاه در معماری

EPS-60 یک تست task-oriented است و در دستهٔ Negative اجرا می‌شود. مسیرهای
Success پروژه تغییر نکرده‌اند. Flow در فایل
`flows/inbound/eps60_pending_flow.py` و تست اجرایی در
`tests/negative/test_eps60_negative.py` قرار دارد.

## تعداد و نحوهٔ اجرا

کاتالوگ EPS-60 شامل **۱۰ سناریو** از `TC-01` تا `TC-10` است. به‌دلیل اینکه
`Integrations:PostalApi:Mock:Scenario` یک سوییچ سراسری است، در هر اجرای
E2E فقط یک Case انتخاب می‌شود؛ در نتیجه باید قبل از هر اجرا Mock متناسب با
Case تنظیم شود.

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS60_NEGATIVE="1"
$env:EPS60_CASE="TC-01"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps60_negative.py -q -s
```

مقدار `EPS60_CASE` می‌تواند یکی از `TC-01` تا `TC-10` باشد. مقدار `all`
عمداً پذیرفته نمی‌شود، چون یک Mock سراسری نمی‌تواند هم‌زمان رفتارهای
`Pending`، `Success` و `Rejected` را برای این Caseها فراهم کند.

## پیش‌نیاز Mock

مقدار زیر باید در محیط تست توسط Dev/DevOps تنظیم شود:

```text
Integrations:PostalApi:Mock:Scenario
```

| Case | Mock موردنیاز | انتظار اصلی |
|---|---|---|
| TC-01 | `Pending` | بارکد ۲۴ رقمی، `status=1` |
| TC-02 | `Pending` | بودجهٔ Timeout دستگاه کمتر از Timeout سرور |
| TC-03 | `Pending` | تکرار همان درخواست پس از Pending |
| TC-04 | `Timeout` یا `Unavailable` | بارکد ۱۴ رقمی، Pending با مقصد خالی |
| TC-05 | `Pending` | رفتار fallback فعلی برای بارکد ۲۴ رقمی |
| TC-06 | `Pending` | بارکد ۳۷ رقمی مانند ۲۴ رقم اول آن |
| TC-07 | `Timeout` یا `Unavailable` | تکرار هدفمند رفتار TC-04 |
| TC-08 | `Success` | بارکد ۱۴ رقمی، `status=0` و مقصد معتبر |
| TC-09 | `Rejected` | بارکد ۱۴ رقمی، `status=2` و خطای غیرخالی |
| TC-10 | هر مقدار | طول بارکد نامعتبر، رد فوری با `status=2` |

پس از اتمام تست‌های Timeout یا تغییر Mock، مقدار محیط را به `Success`
برگردانید تا روی تست‌های دیگر اثر نگذارد.

## انتظار پاسخ

برای Caseهای Pending، تست این موارد را بررسی می‌کند:

- `status` برابر `1`
- `originCode` برابر کد مرکز محلی، پیش‌فرض `59544`
- `destinationCode` خالی یا `null`
- `errorMessage` خالی یا `null`
- پاسخ در محدودهٔ Timeout تنظیم‌شده برگردد و اتصال Hang نشود

برای بارکد ۳۷ رقمی، فقط ۲۴ رقم اول مبنای رفتار است. بارکدهایی با طول غیر
از ۱۴، ۲۴ و ۳۷ رقم وارد منطق Pending نمی‌شوند و مستقیماً رد می‌شوند.

در گزارش Flow برای هر مرحله این سه بخش ثبت می‌شود:

```text
payloadSent
responseReceived
expected
```

در صورت شکست Login، ثبت IP، Handshake، Auth یا هر Case، مراحل بعدی اجرا
نمی‌شوند و با `NOT_CHECKED` گزارش می‌شوند.
