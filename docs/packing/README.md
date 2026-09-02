# Packing — قرارداد بستن کیسه

این بخش قرارداد مشترک `container.close` را برای Container Selection، Export Before Container، Container Response و Physical Container Audit
به‌صورت مستقل بررسی می‌کند.

## Success

فایل تست:

```text
tests/success/test_packing_success.py
```

اجرا:

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_packing_success.py -m packing_success -q -s
```

هر تست مسیر زیر را اجرا می‌کند:

```text
RegisterItem → route.assign → container.close
```

پاسخ موفق باید `status=0`، `resultType=Completed` و شمارنده‌های
`n=1, p=0, m=0, q=0` داشته باشد. در Container Response وجود معتبر `bagBarcode` و
`bagLabel` نیز بررسی می‌شود.

## Negative

فایل تست:

```text
tests/negative/test_packing_negative.py
```

اجرا:

```powershell
$env:RUN_E2E="1"
$env:RUN_PACKING_NEGATIVE="1"
$env:PACKING_CONTAINER_SELECTION_CASE="TC-10"
$env:PACKING_EXPORT_BEFORE_CONTAINER_CASE="TC-16"
$env:PACKING_CONTAINER_RESPONSE_CASE="TC-06"
$env:PACKING_PHYSICAL_CONTAINER_AUDIT_CASE="TC-04"
.venv\Scripts\python.exe -m pytest tests/negative/test_packing_negative.py -m packing_negative -q -s
```

Caseهای پیش‌فرض، قرارداد خطای `container.close` را جداگانه برای هر EPS بررسی می‌کنند:

- Container Selection: `count` نامعتبر
- Export Before Container: `messageType` نامعتبر
- Container Response: نبود مرسولهٔ واجد شرایط
- Physical Container Audit: مرسولهٔ انتخاب‌نشده

برای انتخاب Case دیگر فقط مقدار `PACKING_EPS*_CASE` را تغییر بده. Caseهای
وابسته به Delivery Network Mock یا state قبلی باید با profile مناسب و جداگانه اجرا شوند.

## نکتهٔ قرارداد

در Success انتظار می‌رود خطای parcel وجود نداشته باشد و identity کیسه در
پاسخ برگردد. در Negative، status/resultType/counts/errors بر اساس Case همان
EPS از Flow اصلی آن بررسی می‌شود.
