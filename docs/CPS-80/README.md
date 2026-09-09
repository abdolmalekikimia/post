# CPS-80: مدیریت Object Storage و صدور Pre-signed URL

این مستند تشریح‌کننده پیاده‌سازی و زیرساخت تست تسک **CPS-80** از سیستم **Core Post Sorting** (تیم B / Epic مدیریت تصاویر مرسولات Object Storage) است.

> **هدف معماری:** سیستم Edge قبل از ارسال تصویر مرسوله، یک Pre-signed URL معتبر و محدود به زمان از Core دریافت می‌کند تا تصویر را مستقیماً در Object Storage (سازگار با S3 مانند MinIO) بارگذاری کند؛ بدون اینکه فایل از داخل سرویس‌های Core عبور کند یا در دیتابیس رابطه‌ای ذخیره شود.

---

## 🌐 مشخصات سرویس و اتصالات

- **Base URL:** `http://192.168.20.196:5080/`
- **Storage URL:** `http://192.168.20.196:9000/` (یا endpoint های ابری S3)
- **Core Endpoint:** `POST /api/edge/parcels/images/presigned-url`
- **Headers:**
  - `Content-Type: application/json`
  - `Authorization: Bearer <JWT_Token>`
  - `X-Correlation-ID: {guid}`

### ساختار بدنه درخواست (Request Payload):
```json
{
  "barcode": "590001234567890123456789",
  "contentType": "image/jpeg",
  "fileSizeBytes": 102400,
  "imageType": "ParcelTopView"
}
```

### ساختار بدنه پاسخ (Response Payload):
```json
{
  "status": 0,
  "payload": {
    "objectKey": "parcels/2025/03/10/590001234567890123456789_top.jpg",
    "uploadUrl": "http://192.168.20.196:9000/parcel-images/parcels/2025/03/10/590001234567890123456789_top.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&...",
    "httpMethod": "PUT",
    "expiresInSeconds": 300,
    "expiresAt": "2025-03-10T12:05:00Z",
    "requiredHeaders": {
      "Content-Type": "image/jpeg"
    }
  },
  "errorMessage": null
}
```

---

## 📋 سناریوهای BDD تست‌شده (Acceptance Criteria)

| شناسه | عنوان سناریو | دسته | رفتار و خروجی مورد انتظار |
|---|---|---|---|
| **TC-01** | صدور موفق Pre-signed URL | Success | تولید URL معتبر با زمان انقضا و بازگشت با وضعیت 200 OK |
| **TC-02** | آپلود مستقیم تصویر | Success | ارسال باینری تصویر با HTTP PUT مستقیم به Storage بدون عبور از Core |
| **TC-03** | انقضای زمان اعتبار URL | Negative | رد درخواست آپلود توسط Storage در صورت انقضای امضا (403 Forbidden) |
| **TC-04** | درخواست غیرمجاز (Unauthorized) | Negative | رد درخواست در صورت عدم ارائه توکن معتبر JWT (401 / 403) |
| **TC-05** | عدم افشای اطلاعات زیرساخت | Security | عدم وجود Credential، SecretKey یا اطلاعات حساس داخلی در پاسخ Core |
| **TC-06** | قابلیت تعویض Provider | Contract | حفظ قرارداد مستقل S3-compatible بدون وابستگی Domain به MinIO خاص |

---

## 🚀 دستورات اجرا

### ۱. اجرای سناریوهای مثبت (Success - شامل TC-01, TC-02, TC-05, TC-06):
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS80_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound/test_cps80_presigned_url.py -m cps80_success -q -s
```

### ۲. اجرای سناریوهای منفی و اعتبارسنجی انقضا/دسترسی (Negative - شامل TC-03, TC-04):
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS80_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound/test_cps80_presigned_url.py -m cps80_negative -q -s
```

### ۳. اجرای کلیه تست‌های آفلاین/شبیه‌سازی شده CPS-80 (Unit):
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps80_core.py -q -s
```
