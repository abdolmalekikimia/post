# CPS-33: Cross-Cutting Idempotency Management Tests

مستندات و سناریوهای آزمون قابلیت **Idempotency (جلوگیری از ثبت و پردازش تکراری عملیات)** در تعامل میان Edge و Core.

---

## 🎯 هدف بیزینسی (Business Objective)

در سامانه‌های توزیع‌شده تفکیک و هاب پستی، به دلیل نوسانات شبکه، قطعی ارتباط، Timeoutها، یا تلاش‌های مجدد سخت‌افزارهای سورتینگ (Retry)، ممکن است یک درخواست نوشتن (مانند ثبت نتیجه عملیات، ثبت تصویر یا بارنامه) بیش از یک‌بار ارسال شود.

سامانه Core باید تضمین کند:
1. عملیات فقط **یک‌بار** اثر داده شده و هیچ رکورد تکراری ایجاد نشود.
2. در درخواست‌های مجدد با همان `Idempotency-Key`، پاسخ اولیه بدون اجرای مجدد به متقاضی بازگردانده شود (Replay).
3. در ارسال هم‌زمان چندین درخواست با کلید یکسان، Race Condition رخ نداده و همه پاسخ یکسان بگیرند.

---

## 🧪 سناریوهای آزمون BDD (Acceptance Criteria)

| شناسه | سناریو | پیش‌شرط | ورودی | رفتار مورد انتظار |
|---|---|---|---|---|
| **TC-01** | **پردازش اولین درخواست** | کلید جدید و معتبر | POST با `Idempotency-Key: <unique_uuid>` | انجام عملیات، ثبت در منبع داده، بازگرداندن پاسخ موفق (200/202) |
| **TC-02** | **ارسال مجدد (Immediate Replay / Retry)** | درخواست قبلاً ثبت شده | ارسال مجدد همان Payload با همان `Idempotency-Key` | عدم ایجاد رکورد جدید، بازگرداندن دقیقاً همان نتیجه و کد وضعیت قبلی |
| **TC-03** | **ارسال هم‌زمان (Concurrent Requests)** | ارسال هم‌زمان چند Thread | ۴ درخواست موازی با همان `Idempotency-Key` | جلوگیری از Duplicate، پاسخ یکسان و پایدار به تمام درخواست‌ها بدون خطای 500 |
| **TC-05** | **کلید جدید (Distinct Key)** | کلید متفاوت با دیتای جدید | POST با `Idempotency-Key` متفاوت | انجام عملیات جدید مستقل |

---

## 📁 ساختار فایل‌های تست

```
post/
├── assertions/
│   ├── idempotency_assertions.py         # متدهای اعتبارسنجی Idempotency
│   └── cps33_idempotency_assertions.py   # اکسپورت استاندارد
├── flows/
│   └── idempotency/
│       ├── cps33_idempotency_flow.py     # پیاده‌سازی Flow تست‌ها با Multi-threading
│       └── __init__.py
├── tests/
│   ├── unit/
│   │   └── test_cps33_core.py            # تست یونیت مستقل با Mock Client
│   └── 2_inbound/
│       └── test_cps33_idempotency.py     # تست‌های E2E / Integration
└── docs/
    └── CPS-33/
        └── README.md                     # این مستند
```

---

## 🚀 نحوه اجرای تست‌ها

### ۱. اجرای تست‌های یونیت (سریع و بدون نیاز به سرویس بیرونی):
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps33_core.py -v
```

### ۲. اجرای تست‌های E2E (در برابر سرویس Core یا Mock Backend):
```powershell
$env:RUN_E2E="1"; $env:RUN_CPS33_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound/test_cps33_idempotency.py -v
```

### ۳. اجرای از طریق Test Runner یکپارچه:
```powershell
.venv\Scripts\python.exe scripts/run_core_tests.py
```
