# دامنه ۳: تصمیم‌گیری، تخصیص و تغییر مقصد و شوتر (Destination & Chute Assignment)

این بخش مسئول منطق تصمیم‌گیری مقصد تفکیک، تخصیص چتر خروجی (`Chute`)، جستجوی سریع مقصد و تغییر مقصد پیش از بستن کیسه است.

## استوری‌های پوشش داده شده
- **EPS-60:** جستجوی سریع مقصد در خط تفکیک و تایم‌اوت پستی
- **EPS-71:** تخصیص مقصد و چتر، اعتبارسنجی فرمت و خطاهای مقصد
- **EPS-73:** تغییر مقصد/چتر قبل از بستن کیسه، رد تغییر پس از بستن، و استرس هم‌زمانی

---

## ۱. اجرای تست‌های مثبت (Success)

تست‌های جستجوی مقصد، تخصیص با/بدون چتر و تغییر مقصد پیش از بستن:

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS60_SUCCESS="1"
$env:RUN_EPS71_SUCCESS="1"
$env:RUN_EPS73_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/3_destination -m success -q -s
```

---

## ۲. اجرای تست‌های منفی (Negative)

بررسی خطاهای مقصد نامعتبر، چتر نامعتبر، تغییر مقصد در کیسه بسته و فرمت‌های نامعتبر:

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS60_NEGATIVE="1"
$env:RUN_EPS71_NEGATIVE="1"
$env:RUN_EPS73_NEGATIVE="1"
$env:EPS60_CASE="all"
$env:EPS71_CASE="all"
$env:EPS73_CASE="all"
.venv\Scripts\python.exe -m pytest tests/3_destination -m negative -q -s
```

---

## ۳. آزمون‌های بار و استرس (Stress)

استرس مسابقه در بین `bag.close` و `destination.assign` در EPS-73:

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS73_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_eps73_stress.py -q -s
```