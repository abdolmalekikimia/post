# CPS-9: BuildingBlocks & Edge-Core Contract Lock Tests

مستندات و آزمون‌های یکپارچه‌سازی مربوط به پایش سلامت سرویس‌ها (`/health`)، انتشار مستندات OpenAPI (`/swagger`) و قفل قراردادهای ارتباطی Edge و Core (`/api/edge/*`).

---

## 🎯 اهداف بیزینسی (Business Objectives)

1. **دسترسی‌پذیری و پایش سلامت:** اطمینان از پاسخ‌دهی مسیرهای پایش سلامت سرویس‌ها.
2. **ثبات و قفل قراردادها (Contract Lock):** اعتبارسنجی ساختار پاسخ اندپوینت‌های مسیر `/api/edge/*` و جلوگیری از ایجاد تغییرات ناسازگار (Breaking Changes).
3. **نگاشت صحیح کدهای وضعیت (Q11 Compliance):** تطابق دقیق وضعیت‌های بیزینسی با استانداردهای HTTP Status Code.

---

## 🧪 سناریوهای آزمون BDD (Acceptance Criteria)

| شناسه | سناریو | متد / مسیر | رفتار مورد انتظار |
|---|---|---|---|
| **TC-01** | بررسی سلامت سرویس | `GET /health` | دریافت وضعیت HTTP 200 و وضعیت Healthy |
| **TC-02** | بررسی مستندات API | `GET /swagger/v1/swagger.json` | دریافت وضعیت HTTP 200 و مشخصات OpenAPI |
| **TC-03** | تطابق قرارداد استعلام ورودی | `POST /api/edge/parcels/inbound-query` | دریافت فیلدهای الزامی بدون تغییر ساختار |
| **TC-04** | نگاشت استاندارد خطاها و وضعیت | `POST /api/edge/operational-results` | تطابق کدهای وضعیت پاسخ طبق قرارداد |

---

## 📁 ساختار فایل‌های تست

```
post/
├── assertions/
│   └── cps9_contract_assertions.py       # اعتبارسنجی ساختار قرارداد و سلامت
├── flows/
│   └── contract/
│       ├── cps9_contract_flow.py         # اجرای گام‌به‌گام سناریوهای سلامت و قرارداد
│       └── __init__.py
├── tests/
│   ├── unit/
│   │   └── test_cps9_core.py             # تست یونیت مستقل با Mock Client
│   └── 1_device_lifecycle/
│       └── test_cps9_contracts.py        # تست‌های یکپارچه‌سازی و E2E
└── docs/
    └── CPS-9/
        └── README.md                     # این مستند
```

---

## 🚀 نحوه اجرای تست‌ها

### ۱. اجرای تست‌های یونیت:
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps9_core.py -v
```

### ۲. اجرای تست‌های E2E:
```powershell
$env:RUN_E2E="1"; $env:RUN_CPS9_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle/test_cps9_contracts.py -v
```
