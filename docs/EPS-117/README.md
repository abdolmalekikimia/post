# EPS-117: تأمین داده خام رویدادهای عملیاتی برای گزارش‌گیری مرکزی

> **تیم:** P  |  **اولویت:** Medium  |  **نوع:** Task  |  **اپیک:** Edge Reporting & Telemetry

---

## 🎯 هدف تسک

تهیه و ارسال رویدادهای خام (Raw Operational Events) از Edge سرور به سمت سرور گزارش‌گیری مرکزی، جهت تغذیه داشبوردهای مدیریتی، گزارش‌های تحلیلی و سیستم‌های مانیتورینگ لحظه‌ای.

---

## 📋 سناریوهای آزمون (۱۰ سناریوی BDD)

| شناسه | عنوان | نوع رویداد | داده‌های غنی‌شده در Payload |
|-------|-------|-----------|---------------------------|
| **TC-01** | ثبت ورود مرسوله | `InboundRegistered` | `barcode`, `weightGrams`, `dimensionsMm` (طول/عرض/ارتفاع)، `postalOriginCode` |
| **TC-02** | ثبت خروج مرسوله | `OutboundRegistered` | `barcode`, `assignedChute` (شوتر تخصیصی)، `destinationCode` (مرکز مقصد)، `sortStatus` |
| **TC-03** | تخصیص مقصد و شوتر | `DestinationAssigned` | `barcode`, `chuteNumber` (شماره شوتر)، `destinationCode`، `reason` (دلیل تخصیص) |
| **TC-04** | نهایی‌سازی و بستن کیسه | `BagClosed` | `bagBarcode`، `parcelCount` (تعداد مرسولات)، `totalWeightGrams`، `destinationCode`، `sealNumber` (شماره مهر و موم) |
| **TC-05** | بستن محموله و دیسپچ | `DispatchClosed` | `dispatchBarcode`، `bagsCount` (تعداد کیسه‌ها)، `totalWeightGrams`، `transportType` (نوع وسیله نقلیه) |
| **TC-06** | خطای عملیاتی | `OperationalError` | `errorCode` (کد خطا)، `severity` (شدت)، `componentId` (شناسه کامپوننت)، `message` (پیام توصیفی) |
| **TC-07** | هشدار عملیاتی | `OperationalWarning` | `warningCode` (کد هشدار)، `severity`، `componentId`، `message` |
| **TC-08** | عدم ثبت تکراری رویدادها | `InboundRegistered` | ارسال مجدد رویداد با `eventId` یکسان — بررسی عدم شمارش مضاعف |
| **TC-09** | بافر آفلاین و ترتیب زمانی | `OutboundRegistered` | ارسال ۵ رویداد با `occurredAtUtc` متوالی — بررسی حفظ ترتیب زمانی پس از بازپخش |
| **TC-10** | تأخیر دریافت تله‌متری (SLA) | `InboundRegistered` | اندازه‌گیری فاصله زمانی `occurredAtUtc` تا ACK دریافتی — باید کمتر از **۵۰۰ میلی‌ثانیه** باشد |

---

## 📌 ساختار پوشش جامع (Acceptance Criteria)

### ۱. پوشش رویدادهای اصلی چرخه حیات مرسوله
- ✅ ورود، خروج، تخصیص مقصد، بستن کیسه، بستن دیسپچ
- ✅ خطاهای سخت‌افزاری/نرم‌افزاری و هشدارهای عملیاتی

### ۲. غنی‌سازی Payload با فیلدهای تجاری واقعی
- ✅ ابعاد و وزن مرسولات، شماره شوتر و مقصد، تعداد و وزن کیسه‌ها
- ✅ شماره مهر و موم، نوع وسیله نقلیه، کدهای خطا و هشدار

### ۳. جلوگیری از شمارش مضاعف (Idempotency)
- ✅ ارسال مجدد رویداد با شناسه یکسان باعث ثبت مضاعف نمی‌شود
- ✅ سرور پاسخ `200` یا `DuplicateIgnored` برمی‌گرداند

### ۴. پشتیبانی از بافر آفلاین
- ✅ رویدادهای ذخیره‌شده در حالت آفلاین پس از وصل مجدد ارتباط با حفظ ترتیب زمانی ارسال می‌شوند
- ✅ اعتبارسنجی صعودی بودن `occurredAtUtc` در باچ دریافتی

### ۵. تأخیر دریافت تله‌متری (Ingestion Latency SLA)
- ✅ فاصله زمانی بین تولید رویداد (`occurredAtUtc`) تا دریافت تاییدیه (ACK) باید **کمتر از ۵۰۰ میلی‌ثانیه** باشد

---

## 🗂️ ساختار فایل‌های پیاده‌سازی

```
post/
├── assertions/
│   └── eps117_assertions.py                 # ۶ تابع اعتبارسنجی (-envelope, type, payload, idempotency, batch, latency)
├── flows/
│   └── reporting/
│       └── eps117_operational_events_flow.py  # ۱۰ سناریوی BDD با جزئیات غنی‌شده
├── tests/
│   ├── unit/
│   │   └── test_eps117_core.py               # ۲۳ تست یونیت (بدون نیاز به سرویس)
│   └── 5_monitoring/
│       └── test_eps117_operational_events.py  # تست E2E لایو با ۱۰ سناریو
└── docs/
    └── EPS-117/
        └── README.md                         # همین فایل راهنما
```

---

## 🚀 راهنمای اجرای تست

### ۱. اجرای تست‌های یونیت (مستقل، بدون سرور)
```powershell
python -m pytest tests/unit/test_eps117_core.py -v
```

### ۲. اجرای تست E2E لایو (با سرور Edge فعال)
```powershell
$env:RUN_E2E="1"
python -m pytest tests/5_monitoring/test_eps117_operational_events.py -v -s
```

---

## 📊 خلاصه خروجی مورد انتظار تست E2E

```
Result: PASS=12, FAIL=0, NOT_CHECKED=0

  01. PASS  [PRECONDITION] Admin Login
  02. PASS  [PRECONDITION] Register Device IP
  03. PASS  TC-01: InboundRegistered  (weightGrams: 1500, dims: 400×300×250)
  04. PASS  TC-02: OutboundRegistered (chute: CH-07, destination: 59544)
  05. PASS  TC-03: DestinationAssigned (chuteNumber: 7, reason: PostalCodeMatch)
  06. PASS  TC-04: BagClosed (parcelCount: 12, seal: SEAL-90421)
  07. PASS  TC-05: DispatchClosed (bagsCount: 3, transport: Van)
  08. PASS  TC-06: OperationalError (ERR-4010, OCR-CAM-02, High)
  09. PASS  TC-07: OperationalWarning (WRN-1030, BELT-DRIVE-01, Medium)
  10. PASS  TC-08: Idempotency (duplicate eventId accepted cleanly)
  11. PASS  TC-09: Offline Buffering (5 events, chronological order preserved)
  12. PASS  TC-10: Ingestion Latency (latency < 500 ms SLA)
```
