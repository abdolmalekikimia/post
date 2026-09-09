# CPS-65: نگهداری تاریخچه رویداد و تشخیص وضعیت مرسوله (Parcel Status Evaluation)

این مستند تشریح‌کننده پیاده‌سازی و زیرساخت تست تسک **CPS-65** از سیستم **Core Post Sorting** (تیم B / Epic دریافت و ثبت داده‌های عملیاتی مرسوله) است.

> **معماری:** پیاده‌سازی بر پایه **Clean Architecture** و **Domain-Driven Design (DDD)**. منطق تشخیص وضعیت در `ParcelStatusEvaluator` (Domain Service) قرار دارد و تماماً مستقل از لایه‌های API و Infrastructure است.

---

## 🎯 هدف بیزینسی (Business Goal)

سیستم Edge هنگام ثبت هر خوانش مرسوله، انتظار دارد Core تمام سوابق خوانش را به‌صورت **Append-Only** نگهداری کرده و بر اساس **قوانین زمانی قابل‌پیکربندی**، وضعیت جاری مرسوله را تشخیص دهد:

| وضعیت | کد عددی RegisterInbound | CoreToEdgeStatus | شرط زمانی (پیش‌فرض) |
|:---|:---:|:---|:---|
| **خوانش مجدد** (Duplicate Read) | 1 | `success` | `< 6 ساعت` |
| **مرسوله بازگشتی** (Returning) | 3 | `returning` | `6 - 72 ساعت` |
| **مرجوع به مبدأ** (Return to Origin) | 4 | `rejected` | `> 72 ساعت` |
| **مرسوله جدید** (Not Found) | 0 | `success` | سابقه‌ای ندارد |

مقادیر آستانه (6 و 72 ساعت) **باید در Configuration مرکزی** نگهداری شوند و بدون تغییر کد/Deploy قابل ویرایش باشند.

---

## 🌐 مشخصات سرویس

| مورد | مقدار |
|:---|:---|
| **Domain Service** | `domain.parcel_status_evaluator.ParcelStatusEvaluator` |
| **تنظیمات (Settings)** | `cps65_duplicate_read_threshold_hours`, `cps65_returned_threshold_hours`, `cps65_return_to_origin_threshold_hours` |
| **Environment Variables** | `CPS65_DUPLICATE_READ_THRESHOLD_HOURS`, `CPS65_RETURNED_THRESHOLD_HOURS`, `CPS65_RETURN_TO_ORIGIN_THRESHOLD_HOURS` |

---

## 📋 سناریوهای BDD تست‌شده (Acceptance Criteria)

| شناسه | عنوان سناریو | شرط | خروجی مورد انتظار |
|:---|:---|:---|:---|
| **TC-01** | تشخیص خوانش مجدد | سپری‌شده `< 6h` | `ParcelHistoryStatus.DUPLICATE_READ` |
| **TC-02** | تشخیص مرسوله بازگشتی | `6h ≤ سپری‌شده ≤ 72h` | `ParcelHistoryStatus.RETURNING` (Status 3) |
| **TC-03** | تشخیص مرجوع به مبدأ | سپری‌شده `> 72h` | `ParcelHistoryStatus.RETURN_TO_ORIGIN` (Status 4) |
| **TC-04** | مرسوله جدید (بدون سابقه) | لیست سابقه خالی | `ParcelHistoryStatus.NOT_FOUND` (Status 0) |
| **TC-05** | مرزبندی دقیقاً ۶ ساعت | `= 6h` | `RETURNING` (شامل مرز بالا) |
| **TC-06** | مرزبندی دقیقاً ۷۲ ساعت | `= 72h` | `RETURNING` (شامل مرز بالا) |
| **TC-07** | بیش از ۷۲ ساعت | `72.01h` | `RETURN_TO_ORIGIN` |
| **TC-08** | استفاده از جدیدترین خوانش | چند سابقه وجود دارد | ارزیابی بر اساس آخرین رکورد |
| **TC-09** | آستانه‌های قابل پیکربندی | تغییر در Settings | سیستم از مقادیر جدید استفاده می‌کند |
| **TC-10** | اعتبارسنجی Configuration | مقادیر نامعتبر | `ValueError` در زمان ساخت Evaluator |

---

## 🏗️ معماری کد (Code Structure)

```
domain/
└── parcel_status_evaluator.py          # Domain Service اصلی

tests/unit/
└── test_cps65_status_evaluator.py      # 14 تست واحد کامل

config/
├── settings.py                          # تعریف Settings (cps65_*_threshold_hours)
└── test.env.example                     # متغیرهای محیطی نمونه
```

### کلاس‌های اصلی:

| کلاس | وظیفه |
|:---|:---|
| `ParcelHistoryStatus` (Enum) | `NOT_FOUND`, `DUPLICATE_READ`, `RETURNING`, `RETURN_TO_ORIGIN` |
| `ParcelReading` (Dataclass) | نمایش یک رکورد خوانش (reading_id, barcode, scanned_at_utc, ...) |
| `StatusEvaluationResult` (Dataclass) | نتیجه ارزیابی: status, elapsed_hours, threshold_applied, rule_description |
| `ParcelStatusEvaluator` | موتور ارزیابی با injection تنظیمات از `Settings` |

---

## 🚀 دستورات اجرا

### تست‌های واحد (Unit Tests - کاملاً آفلاین):
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps65_status_evaluator.py -q -s
```

### تست همه ماژول‌های Core:
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps65_status_evaluator.py tests/unit/test_cps20_core.py tests/unit/test_cps80_core.py -q
```

---

## 🔧 پیکربندی (Configuration)

### در `config/settings.py`:
```python
cps65_duplicate_read_threshold_hours: int = int(
    os.getenv("CPS65_DUPLICATE_READ_THRESHOLD_HOURS", "6")
)
cps65_returned_threshold_hours: int = int(
    os.getenv("CPS65_RETURNED_THRESHOLD_HOURS", "72")
)
cps65_return_to_origin_threshold_hours: int = int(
    os.getenv("CPS65_RETURN_TO_ORIGIN_THRESHOLD_HOURS", "72")
)
```

### در `.env` یا Environment Variables:
```bash
CPS65_DUPLICATE_READ_THRESHOLD_HOURS=6
CPS65_RETURNED_THRESHOLD_HOURS=72
CPS65_RETURN_TO_ORIGIN_THRESHOLD_HOURS=72
```

---

## 💡 مثال استفاده در کد

```python
from domain.parcel_status_evaluator import (
    ParcelStatusEvaluator,
    ParcelReading,
    ParcelHistoryStatus,
    create_evaluator,
)
from datetime import datetime, timezone, timedelta

# ۱. ساخت Evaluator (از Settings پیش‌فرض یا سفارشی)
evaluator = create_evaluator()  # یا ParcelStatusEvaluator(custom_settings)

# ۲. آماده‌سازی سوابق قبلی (مرتب: جدیدترین اول)
previous_readings = [
    ParcelReading(
        reading_id="reading-123",
        barcode="590001234567890123456789",
        scanned_at_utc=datetime.now(timezone.utc) - timedelta(hours=24),
        edge_id="EDGE-001",
        exchange_center_code="59544",
        device_id="DEVICE-001",
    )
]

# ۳. ارزیابی وضعیت برای خوانش جدید
now = datetime.now(timezone.utc)
result = evaluator.evaluate(
    barcode="590001234567890123456789",
    current_scan_time=now,
    previous_readings=previous_readings,
)

# ۴. نتیجه
print(f"Status: {result.status}")           # ParcelHistoryStatus.RETURNING
print(f"Elapsed: {result.elapsed_hours:.2f}h")  # 24.00h
print(f"Rule: {result.rule_description}")    # "Elapsed 24.00h in range [6h, 72h] -> Returning (Status 3)"
print(f"Status Code: {evaluator.get_status_code(result.status)}")  # 3
print(f"CoreToEdgeStatus: {evaluator.get_core_to_edge_status(result.status)}")  # "returning"
```

---

## 📊 خروجی تست واحد (نمونه)

```text
tests/unit/test_cps65_status_evaluator.py ....... 14 passed

Test Coverage:
✓ No previous readings -> NOT_FOUND
✓ < 6h -> DUPLICATE_READ
✓ 6h boundary -> RETURNING
✓ 24h -> RETURNING
✓ 72h boundary -> RETURNING
✓ 72.01h -> RETURN_TO_ORIGIN
✓ 100h -> RETURN_TO_ORIGIN
✓ Multiple readings -> uses most recent
✓ Custom thresholds from Settings
✓ Invalid threshold validation (ValueError)
✓ Status code mapping (0, 1, 3, 4)
✓ CoreToEdgeStatus mapping (success, returning, rejected)
```

---

## 🔗 ارتباط با سایر تسک‌ها

| تسک | ارتباط |
|:---|:---|
| **CPS-20** (Inbound Query) | از `ParcelStatusEvaluator` برای محاسبه `status`، `recordedOriginCode`، `recordedDestinationCode` و `discrepancyDetected` استفاده می‌کند |
| **EPS-68** (بازنویسی وضعیت توسط Core) | مصرف‌کننده منطق تشخیص وضعیت |
| **EPS-66** (بازخوانی مجدد - Reread) | پایه تصمیم‌گیری برای Duplicate Read |

---

## 🔐 امنیت و لاگینگ

* **بدون Hard-code**: تمام آستانه‌ها از Configuration بارگذاری می‌شوند
* **Structured Log**: شامل `Correlation-ID`، `ParcelBarcode`، `PreviousStatus`، `CalculatedStatus`، `Rule`، `ElapsedHours`
* **Metrics**: شمارش Duplicate/Returning/ReturnToOrigin، میانگین زمان محاسبه، خطاهای Rule Evaluation
* **Stateless**: `ParcelStatusEvaluator` قابل مقیاس‌سازی و جایگزینی در آینده

---

## 📝 نکات مهم پیاده‌سازی

1. **Append-Only History**: سوابق هرگز حذف یا بازنویسی نمی‌شوند
2. **Strategy Pattern Ready**: `ParcelStatusEvaluator` قابل توسعه برای Rule Engine پیشرفته
3. **Configuration Validation**: اعتبارسنجی ترتیبی آستانه‌ها در Constructor (`duplicate < returned ≤ return_to_origin`)
4. **Timezone Aware**: تمام محاسبه‌ها بر اساس `UTC` انجام می‌شوند
5. **Unit Testable**: ۱۰۰٪ قابل تست واحد بدون وابستگی به دیتابیس یا API