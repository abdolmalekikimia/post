# CPS-70: کنترل دسترسی مدیریتی بر پایه نقش و ادعا (RBAC & Center Scoping)

مستندات و سناریوهای آزمون سیستم کنترل دسترسی مبتنی بر نقش (Role-Based Access Control) و اعمال خودکار محدوده مراکز مبادله (Claim-Based Data Scoping) در سامانه Core.

---

## 🎯 اهداف بیزینسی و امنیتی (Business & Security Objectives)

1. **دسترسی کامل مدیر کل (`SystemAdmin`):** دسترسی نامحدود و بدون فیلتر مرکز مبادله به تمام اطلاعات، تنظیمات و رویدادهای سراسر شبکه پستی.
2. **محدودسازی خودکار مدیر مرکز (`CenterManager`):** اعمال خودکار محدودیت دسترسی در تمام Queryها بر اساس مراکز مجاز موجود در Claim توکن JWT (`allowedCenters`).
3. **جلوگیری از دسترسی متقاطع به سایر مراکز (Cross-Center Protection):** تلاش برای دسترسی به مرکز غیرمجاز باید با خطای `403 Forbidden` مسدود شده و هیچ‌گونه اطلاعاتی از مرکز نامجاز افشا نشود.
4. **امنیت در برابر توکن‌های جعلی یا دستکاری‌شده (Tampered Tokens):** رد فوری هرگونه JWT بدون امضای معتبر با کد `401 Unauthorized` قبل از ورود به لایه بیزینس.
5. **رهگیری امنیتی و Correlation-ID:** حفظ شناسه پیگیری در لاگ‌های امنیتی شامل UserId، Role، AllowedCenters و Endpoint.

---

## 🧪 سناریوهای آزمون BDD (Acceptance Criteria)

| شناسه | عنوان سناریو | نقش و شرایط ورودی | رفتار مورد انتظار |
|---|---|---|---|
| **TC-01** | دسترسی نامحدود SystemAdmin | نقش SystemAdmin به مرکز ۷۱۹۵۶ | دسترسی مجاز (`200 OK`) بدون اعمال فیلتر مرکز |
| **TC-02** | فیلتر داده مجاز برای CenterManager | نقش CenterManager و مرکز مجاز ۵۹۵۴۴ | دسترسی مجاز (`200 OK`) با فیلتر داده فقط برای مرکز ۵۹۵۴۴ |
| **TC-03** | رد دسترسی به مرکز غیرمجاز | مدیر مرکز ۵۹۵۴۴ در تلاش برای دسترسی به ۷۱۹۵۶ | رد درخواست با خطای `403 Forbidden` بدون افشای داده |
| **TC-04** | رد توکن فاقد Claim مراکز مجاز | نقش CenterManager بدون فیلد allowedCenters | رد با خطای `403 Forbidden` یا `400 Bad Request` |
| **TC-05** | رد توکن با امضای دستکاری‌شده | JWT با امضای نامعتبر / Tampered | رد فوری با خطای `401 Unauthorized` توسط Middleware |
| **TC-06** | رد درخواست فاقد توکن احراز هویت | درخواست بدون هدر Authorization | رد با خطای `401 Unauthorized` |

---

## 📁 ساختار فایل‌های آزمون

```
post/
├── assertions/
│   └── cps70_rbac_assertions.py          # توابع بررسی دسترسی SystemAdmin، فیلتر داده، 403 و 401
├── flows/
│   └── auth/
│       ├── cps70_rbac_auth_flow.py       # فلو آزمون ۶ سناریوی RBAC و تولید توکن آزمایشی
│       └── __init__.py
├── tests/
│   ├── unit/
│   │   └── test_cps70_core.py            # آزمون‌های واحد آفلاین اعتبارسنجی Claimها و امضای JWT
│   └── 1_device_lifecycle/
│       └── test_cps70_rbac.py            # آزمون‌های یکپارچه‌سازی و E2E دامنه ۱
└── docs/
    └── CPS-70/
        └── README.md                     # این مستند
```

---

## 🚀 دستورات اجرا

### ۱. اجرای تست E2E مسیر مثبت (Success):
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS70_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m cps70_success -q -s
```

### ۲. اجرای تست E2E مسیر منفی و امنیتی (Negative):
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS70_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m cps70_negative -q -s
```

### ۳. اجرای تست‌های آفلاین واحد (Unit Tests):
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps70_core.py -q -s
```
