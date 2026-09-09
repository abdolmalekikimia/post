# CPS-20: سرویس بررسی و استعلام سابقه مرسوله (بلادرنگ)

این مستند تشریح‌کننده پیاده‌سازی و زیرساخت تست تسک **CPS-20** از سیستم **Core Post Sorting** (تیم B / Epic دریافت و ثبت داده‌های عملیاتی مرسوله) است.

> **نکته مهم معماری:** در حال حاضر زیرساخت تست مستقل برای Core آماده شده است، بدون اینکه Core و Edge هنوز به یکدیگر متصل شده باشند. این تست‌ها می‌توانند به صورت ایزوله روی Core API مستقیم (`http://192.168.20.196:5080/`) یا در حالت قرارداد تست شوند.

---

## 🌐 مشخصات سرویس و اتصالات

- **Base URL:** `http://192.168.20.196:5080/`
- **Swagger:** `http://192.168.20.196:5080/swagger/index.html?urls.primaryName=parcel-lifecycle`
- **Endpoint:** `POST /api/edge/parcels/inbound-query`
- **Generic Headers:**
  - `Content-Type: application/json`
  - `X-Correlation-ID: {guid}`
  - `Idempotency-Key: {guid}`

### تغییر نام فیلدها طبق نظر کارفرما:
- فیلدها از `originCode` / `destinationCode` به **`recordedOriginCode`** و **`recordedDestinationCode`** تغییر یافته‌اند.

---

## 📋 سناریوهای BDD تست‌شده (Acceptance Criteria)

| شناسه | عنوان سناریو | دسته | رفتار فیلدهای خروجی |
|---|---|---|---|
| **TC-01** | استعلام موفق سابقه مرسوله قبل از پایان Timeout | Success | بازگشت پاسخ بلادرنگ سابقه مرسوله |
| **TC-02** | مرسوله بازگشتی (Returning) | Negative | `recordedOriginCode` و `recordedDestinationCode` مطابق مبدأ و مقصد اصلی و بدون نگاشت ویژه |
| **TC-03** | مرسوله مرجوع به مبدأ (Return to Origin) | Negative | `recordedOriginCode` = مبدأ اصلی، و `recordedDestinationCode` = کد مقصد متناظر با شهر مبدأ |
| **TC-04** | نبود سابقه در Core (مرسوله جدید) | Success | بازگشت پاسخ استاندارد برای مرسوله جدید بدون بروز خطای سیستمی |
| **TC-05** | رهگیری و Traceability | Success | حفظ و ردیابی کامل `Correlation-ID` در طول درخواست و لاگ‌ها |

---

## 🚀 دستورات اجرا

### ۱. اجرای سناریوهای مثبت (Success - شامل TC-01, TC-04, TC-05):
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS20_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m cps20_success -q -s
```

### ۲. اجرای سناریوهای بازگشتی و مرجوعی (Negative - شامل TC-02, TC-03):
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS20_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m cps20_negative -q -s
```

### ۳. آزمون واحد قرارداد و اعتبارسنجی (بدون نیاز به شبکه):
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps20_core.py -q
```
