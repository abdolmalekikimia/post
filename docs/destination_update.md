# Destination Update — Operational destination update

Destination Update رفتار `route.assign` را قبل و بعد از بسته‌شدن کیسه بررسی می‌کند.
موارد مثبت آن داخل هر دو مسیر Success پروژه اجرا می‌شوند و سناریوی منفی
task-oriented در مسیر Negative قرار دارد.

در SignalR، پیام با `messageType: "route.assign"` ارسال می‌شود اما
target متد Hub باید `AssignRoute` باشد.

## قرارداد وضعیت

- `RegisterItem`: موفقیت با `status=0`
- `route.assign`: موفقیت با `status=1`
- `container.close`: موفقیت با `status=0`
- `counts.n`: تعداد مرسوله‌های انتخاب‌شده توسط `container.close`

## سناریوهای مثبت در Success

### TC-01 — تغییر مقصد و شوتر قبل از بستن کیسه

مرسوله ابتدا به مقصد `11111` و شوتر `CH-A` تخصیص می‌یابد، سپس به مقصد
`22222` و شوتر `CH-B` تغییر می‌کند. با `container.close` مقصد قدیمی باید
`counts.n=0` و مقصد جدید با فیلتر `CH-B` باید حداقل یک مرسوله نشان دهد.

### TC-02 — تغییر مقصد بدون `chuteId`

مرسوله ابتدا با شوتر `CH-A` ثبت می‌شود و سپس مقصد به `22222` تغییر می‌کند،
بدون اینکه `chuteId` در payload جدید وجود داشته باشد. فیلتر شوتر قدیمی باید
`counts.n=0` و جست‌وجوی مقصد جدید بدون فیلتر شوتر باید حداقل یک مرسوله نشان دهد.

### TC-03 — تخصیص کاملاً تکراری

همان مقصد و همان شوتر دوباره ارسال می‌شود. پاسخ باید `status=1` باشد و
`container.close` با همان مقصد و شوتر باید مرسوله را پیدا کند.

### TC-04 — مقصد یکسان با شوتر متفاوت

همان مقصد با شوتر `CH-Z` ارسال می‌شود. پاسخ باید `status=1` باشد، اما شوتر
ذخیره‌شده نباید از `CH-A` تغییر کند. فیلتر `CH-Z` باید خالی و فیلتر `CH-A`
باید شامل مرسوله باشد.

این چهار Case در فایل زیر قرار دارند و به‌صورت تست مثبت جداگانه اجرا نمی‌شوند:

```text
flows/destination/destination_update_success_flow.py
```

هر مرحله در گزارش شامل payload ارسالی، response دریافتی و نتیجهٔ assertion
است.

## سناریوی منفی

### TC-05 — تغییر مقصد بعد از بستن کیسه

مرسوله به مقصد `11111` و شوتر `CH-A` تخصیص داده می‌شود، سپس `container.close` برای
همان مقصد اجرا می‌شود. بعد از آن تغییر مقصد به `33333` با شوتر `CH-B` ارسال
می‌شود.

رفتار مورد انتظار نسخهٔ فعلی:

```text
status=2
errorMessage شامل closed/bagged یا معادل فارسی «بسته/کیسه»
```

این تست باید رد امن را تأیید کند؛ یعنی سرویس crash نکند و دادهٔ محلی خراب
نشود. مسیر واقعی تشخیص مرسولهٔ برگشتی طبق مستندات عمومی هنوز در این تسک پیاده‌سازی نشده
و به‌عنوان Requirement Gap مستند می‌شود.

اجرا:

```powershell
$env:RUN_E2E="1"
$env:RUN_DESTINATION_UPDATE_NEGATIVE="1"
$env:DESTINATION_UPDATE_CASE="TC-05"
.venv\Scripts\python.exe -m pytest tests/negative/test_destination_update_negative.py -q -s
```

در صورت شکست Login، ثبت IP، Handshake، Auth یا setup، مراحل بعدی
`NOT_EXECUTED` می‌شوند. دریافت پاسخ منفی مورد انتظار باعث PASS شدن تست است؛
پاسخ غیرمنتظره یا خطای Transport باعث FAIL می‌شود.

## TC-06 — هم‌زمانی

TC-06 شامل اجرای هم‌زمان `container.close` و `route.assign` با دو اتصال
WebSocket است. این Case تست race/concurrency است و نباید داخل Success یا
Negative معمولی اجرا شود؛ جای مناسب آن `tests/stress/` است.
