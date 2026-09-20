# CPS-49: غیرفعال‌سازی Edge و ثبت Audit Log امنیتی

مستندات و سناریوهای آزمون قابلیت غیرفعال‌سازی نودهای Edge توسط مدیر سامانه و قطع دسترسی بلادرنگ (حتی با داشتن توکن JWT معتبر) و ثبت وقایع در Audit Log تغییرناپذیر (Immutable).

---

## 🎯 اهداف بیزینسی (Business Objectives)

1. **غیرفعال‌سازی امنیتی:** امکان خروج نودهای معیوب، مسروقه یا خارج از سرویس از مدار توسط مدیر سامانه.
2. **قطع دسترسی فوری (Defense-in-Depth):** به‌محض غیرفعال‌سازی یک Edge، فراخوانی کلیه APIهای Core توسط آن نود حتی با JWT معتبر، بلافاصله باید با کد وضعیت `401 Unauthorized` یا `403 Forbidden` مسدود شود.
3. **ثبت Audit Log مستقل و امن:** ثبت کامل متادیتا (User، Edge، Action، Timestamp، CorrelationId و IP) و عدم ذخیره هیچ‌گونه دیتای محرمانه (رمز، سکرت یا توکن خام).
4. **قابلیت جستجو:** امکان استعلام و فیلتر سوابق مدیریتی بر اساس شناسه Edge و CorrelationId.

---

## 🧪 سناریوهای آزمون BDD (Acceptance Criteria)

| شناسه | سناریو | پیش‌شرط | ورودی | رفتار مورد انتظار |
|---|---|---|---|---|
| **TC-01** | غیرفعال‌سازی موفق Edge | نود Edge فعال در سیستم | PUT `/api/admin/devices/{edgeId}/status` با توکن ادمین | تغییر وضعیت Edge به Disabled و بازگرداندن 200/204 |
| **TC-02** | مسدودسازی فوری با JWT معتبر | Edge قبلاً غیرفعال شده | فراخوانی API با هدر Bearer توکن معتبر Edge | مسدودسازی قطعی با HTTP 401 یا 403 و ثبت تلاش ناموفق |
| **TC-03** | جامعیت لاگ ممیزی (Audit Log) | عملیات غیرفعال‌سازی انجام شده | استعلام رکوردهای Audit لاگ | وجود فیلدهای اجباری: UserId, EdgeId, Operation, Time, IP, CorrId |
| **TC-04** | امنیت و عدم افشای اطلاعات حساس | ثبت لاگ ممیزی | ارزیابی محتوای رکورد لاگ | عدم وجود کلمات کلیدی توکن، پسورد یا سکرت در متن لاگ |
| **TC-05** | فیلتر و رهگیری سوابق | رکوردهای متعددی در دیتابیس | GET `/api/admin/audit-logs?edgeId=...` | بازگرداندن سوابق ممیزی متناظر با Edge انتخاب‌شده |

---

## 📁 ساختار فایل‌های آزمون

```
post/
├── assertions/
│   └── cps49_audit_assertions.py          # توابع بررسی موفقیت قطع دسترسی، خطای ۴۰۳/۴۰۱ و جامعیت Audit
├── flows/
│   └── device_management/
│       ├── cps49_edge_deactivation_flow.py # فلو چندمرحله‌ای تست غیرفعال‌سازی، پروب امنیتی و استعلام لاگ
│       └── __init__.py
├── tests/
│   ├── unit/
│   │   └── test_cps49_core.py             # آزمون‌های واحد آفلاین با Mock Client
│   └── 1_device_lifecycle/
│       └── test_cps49_edge_audit.py       # آزمون‌های یکپارچه‌سازی و E2E
└── docs/
    └── CPS-49/
        └── README.md                      # این مستند
```

---

## 🚀 نحوه اجرای تست‌ها

### ۱. اجرای تست‌های آفلاین واحد:
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps49_core.py -v
```

### ۲. اجرای تست‌های E2E:
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS49_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m cps49_success -q -s
```
