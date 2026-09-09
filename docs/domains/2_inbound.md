# دامنه ۲: ورود، اعتبارسنجی ابعاد/وزن، تصاویر و استعلام سابقه (Inbound & Verification)

این بخش مسئول ثبت ورود اولیهٔ مرسوله (`RegisterInbound`)، اعتبارسنجی ابعاد و وزن فیزیکی، تشخیص مغایرت با سامانه مرکزی، آپلود ناهمگام تصاویر، بازخوانی مجدد بارکدها و استعلام بلادرنگ سابقه مرسوله از Core است.

## استوری‌های پوشش داده شده
- **EPS-53:** اعتبارسنجی ابعاد و وزن، مغایرت‌سنجی و fallback به Core
- **EPS-55:** اورکستریشن ثبت ورودی، عدم تطابق بارکدها و خطاهای وب‌سرویس پستی
- **EPS-64:** مدیریت آپلود ناهمگام (Lazy Upload) تصاویر مرسوله
- **EPS-66:** رفتار بازخوانی مجدد بر اساس وضعیت قبلی مرسوله (Reread)
- **EPS-68:** بازنویسی وضعیت مرسوله از سوی Core (کدهای ۳ و ۴)
- **CPS-20:** سرویس استعلام بلادرنگ سابقه مرسوله از Core (`/api/edge/parcels/inbound-query`)
- **CPS-80:** مدیریت Object Storage و صدور Pre-signed URL برای آپلود مستقیم تصویر (`/api/edge/images/presigned-url`)
- **CPS-65:** نگهداری تاریخچه رویداد و تشخیص وضعیت مرسوله (Duplicate/Returning/Return-to-Origin) — Domain Service `ParcelStatusEvaluator`
- **CPS-86:** ذخیره نتیجه عملیات پستی (Operational Result Storage) — `POST /api/edge/operational-results`

---

## ۱. اجرای تست‌های مثبت (Success)

تست‌های ثبت موفق، ثبت با مغایرت مجاز، اورکستریشن سالم، ارسال تصویر و استعلام‌های موفق Core:

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS53_SUCCESS="1"
$env:RUN_EPS55_SUCCESS="1"
$env:RUN_EPS64_SUCCESS="1"
$env:RUN_EPS66_SUCCESS="1"
$env:RUN_CPS20_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m success -q -s
```

---

## ۲. اجرای تست‌های منفی (Negative)

بررسی سناریوهای مرسولات برگشتی، خطاهای فرمت بارکد، رد شدن توسط سامانه پستی، خطای تصویر، مرسولات بازگشتی و مرجوع به مبدأ:

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS53_NEGATIVE="1"
$env:RUN_EPS55_NEGATIVE="1"
$env:RUN_EPS64_NEGATIVE="1"
$env:RUN_EPS66_NEGATIVE="1"
$env:RUN_EPS68_NEGATIVE="1"
$env:RUN_CPS20_NEGATIVE="1"
$env:EPS64_NEGATIVE_CASE="all"
$env:EPS68_CASE="all"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m negative -q -s
```

---

## ۳. آزمون‌های بار و استرس (Stress)

تست بار و ارسال متوالی بسته‌ها برای اعتبارسنجی عملکرد موتور Inbound:

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS53_STRESS="1"
$env:RUN_EPS55_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_eps53_stress.py tests/stress/test_eps55_stress.py -q -s
```

---

## ۴. اجرای تست‌های CPS-80 (Object Storage & Pre-signed URL)

### ۴.۱ سناریوهای موفق (Success - TC-01, TC-02, TC-05, TC-06):
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS80_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m cps80_success -q -s
```

### ۴.۲ سناریوهای منفی و انقضا (Negative - TC-03, TC-04):
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS80_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m cps80_negative -q -s
```

### ۴.۳ تست‌های واحد (Unit - شبیه‌سازی آفلاین):
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps80_core.py -q -s
```

---

## ۵. اجرای تست‌های CPS-65 (Parcel Status Evaluation)

### ۵.۱ تست‌های واحد Domain Service (آفلاین - کامل):
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps65_status_evaluator.py -q -s
```

### ۵.۲ تست‌های ترکیبی CPS-65 + CPS-20 + CPS-80:
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps65_status_evaluator.py tests/unit/test_cps20_core.py tests/unit/test_cps80_core.py -q
```

### ۵.۳ پیکربندی آستانه‌ها (Environment Variables):
```powershell
$env:CPS65_DUPLICATE_READ_THRESHOLD_HOURS="6"
$env:CPS65_RETURNED_THRESHOLD_HOURS="72"
$env:CPS65_RETURN_TO_ORIGIN_THRESHOLD_HOURS="72"
```

---

## ۶. اجرای تست‌های CPS-86 (Operational Result Storage)

### ۶.۱ تست‌های واحد (Unit - شبیه‌سازی آفلاین):
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps86_core.py -q -s
```

### ۶.۲ تست‌های ترکیبی CPS-20 + CPS-65 + CPS-80 + CPS-86:
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps20_core.py tests/unit/test_cps65_status_evaluator.py tests/unit/test_cps80_core.py tests/unit/test_cps86_core.py -q
```

### ۶.۳ پیکربندی (Environment Variables):
```powershell
$env:CORE_OPERATIONAL_RESULTS_PATH="/api/edge/operational-results"
$env:CPS86_CORRELATION_ID="corr-test-001"
$env:CPS86_PARCEL_BARCODE="860000000000000000000001"
$env:CPS86_CALL_RESULT="RegisterInbound_Success"
$env:CPS86_ERROR_CODE="POSTAL_API_TIMEOUT"
$env:CPS86_ERROR_MESSAGE="Postal API did not respond within timeout"
$env:CPS86_ATTEMPTS="3"
$env:CPS86_FINAL_STATUS="Success"
```
