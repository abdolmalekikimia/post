# EPS-181: تعریف سناریوهای منفی تست برای تولید متغیرهای محیطی Mock

> **تیم:** B  |  **اولویت:** Medium  |  **نوع:** Task  |  **اپیک:** (Edge) یکپارچه‌سازی واقعی پست، سخت‌سازی QA استقرار پایلوت

---

## 🎯 هدف و شرح تسک

تعریف سناریوهای منفی موردنیاز برای تولید متغیرهای محیطی در محیط Mock و آماده‌سازی داده‌های آزمون جهت اجرای آسان توسط تسترها و تیم QA. سناریوها باید شرایط **نامعتبر، ناقص یا خطادار** را پوشش داده تا رفتار سرویس Edge در این حالات بررسی شود.

### 📋 خروجی‌های مورد انتظار تحقق‌یافته:
1. ✅ **تعریف سناریوهای منفی تست:** ۱۱ سناریوی تفکیک‌شده در ۳ سرویس هدف (PostalApi, CoreApi, EdgeConfig).
2. ✅ **آماده‌سازی داده‌های تست و متغیرهای محیطی Mock:** قالب‌بندی استاندارد متغیرهای محیطی ASP.NET Core (`__`).
3. ✅ **مستندسازی نتیجه مورد انتظار هر سناریو:** وضعیت پاسخ Edge (`status=2`، `status=1`) و محتوای پیام خطا.
4. ✅ **فراهم‌شدن اطلاعات لازم برای اجرای تست توسط تیم QA:** راهنمای گام‌به‌گام استقرار و تست.

---

## 📊 ماتریس سناریوهای منفی Mock و داده‌های تست

| شناسه | نام سناریو | سرویس هدف | بارکد / داده تست | متغیر محیطی Mock | وضعیت مورد انتظار | پیام خطای مورد انتظار |
|-------|-----------|-----------|------------------|-------------------|-------------------|------------------------|
| **NEG-POSTAL-01** | `postal_timeout` | PostalApi | `200000000000000000000003` | `Integrations__PostalApi__Mock__ScenarioOverrides__<BC>=Timeout`<br>`Integrations__PostalApi__RegistrationPolling__TimeoutMs=2000` | `status=2` | شامل `timeout` |
| **NEG-POSTAL-02** | `postal_rejected` | PostalApi | `200000000000000000000002` | `Integrations__PostalApi__Mock__ScenarioOverrides__<BC>=Rejected` | `status=2` | شامل `rejected` |
| **NEG-POSTAL-03** | `postal_unavailable` | PostalApi | `200000000000000000000004` | `Integrations__PostalApi__Mock__ScenarioOverrides__<BC>=Unavailable` | `status=2` | شامل `unavailable` |
| **NEG-POSTAL-04** | `postal_pending` | PostalApi | `200000000000000000000005` | `Integrations__PostalApi__Mock__ScenarioOverrides__<BC>=Pending`<br>`Integrations__PostalApi__Mock__RegistrationResolutionDelay=00:00:10` | `status=2` | شامل `pending` |
| **NEG-CORE-01** | `core_history_rejected` | CoreApi | `100000000000000000000004`<br>Origin: `59544` | `Integrations__CoreApi__Mock__HistoryRecords__<BC>__Status=Rejected`<br>`Integrations__CoreApi__Mock__RefusalDestinationOverrides__59544=11369` | `status=2` | شامل `rejected` (هدایت به ۱۱۳۶۹) |
| **NEG-CORE-02** | `core_history_timeout` | CoreApi | `100000000000000000000007` | `Integrations__CoreApi__Mock__ScenarioOverrides__<BC>=Timeout` | `status=2` | شامل `timeout` (فعال‌سازی Fallback محلی) |
| **NEG-CORE-03** | `core_history_unavailable` | CoreApi | `100000000000000000000008` | `Integrations__CoreApi__Mock__ScenarioOverrides__<BC>=Unavailable` | `status=2` | شامل `unavailable` |
| **NEG-CORE-04** | `core_history_discrepancy` | CoreApi | `100000000000000000000002`<br>Measured: 1500g, Hist: 500g | `Integrations__CoreApi__Mock__HistoryRecords__<BC>__Status=Success`<br>`Integrations__CoreApi__Mock__HistoryRecords__<BC>__DiscrepancyDetected=true` | `status=1` | گزارش اختلاف وزن (`weight mismatch`) |
| **NEG-CONFIG-01** | `autodispatch_invalid_deadline` | EdgeConfig | مرکز: `59544` | `Integrations__CoreApi__Mock__ConfigSnapshots__59544__AutoDispatchPolicy__AllowedDeadline=-01:00:00` | `status=2` | رد همگام‌سازی به علت deadline منفی |
| **NEG-AUTH-01** | `device_inactive` | EdgeConfig | Device: `EPS40-INACTIVE-001` | `Integrations__CoreApi__Mock__ConfigSnapshots__59544__Devices__1__ActivationStatus=Inactive` | اتصال رد می‌شود | خطای `401/403 Inactive Device` |
| **NEG-BAG-01** | `parcel_bag_error` | PostalApi | `790000000000000000000001` | `Integrations__PostalApi__Mock__ParcelErrorOverrides__<BC>=true` | `status=2` | خطای `parcel error` هنگام بستن کیسه |

---

## 🛠️ ساختار فایل‌های پروژه

```
post/
├── assertions/
│   └── eps181_mock_env_assertions.py       # اعتبارسنجی فرمت کلیدها و کامل‌بودن پروفایل‌ها
├── utils/
│   └── mock_env_generator.py               # مولد خودکار متغیرهای محیطی و فایل .env
├── flows/
│   └── mock_env/
│       ├── __init__.py
│       └── eps181_mock_env_flow.py         # جریان BDD برای اعتبارسنجی سناریوها
├── tests/
│   ├── unit/
│   │   └── test_eps181_core.py             # ۲۶ تست یونیت بدون نیاز به سرویس زنده
│   └── mock_env/
│       ├── __init__.py
│       └── test_eps181_negative_mock_env.py# تست‌های تولید داده و خروجی تستر QA
└── docs/
    └── EPS-181/
        └── README.md                       # همین مستند
```

---

## 🚀 راهنمای اجرای آزمون برای تیم QA

### ۱. اجرای تست‌های یونیت و صحت‌سنجی مولد متغیرها
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_eps181_core.py tests/mock_env/test_eps181_negative_mock_env.py -q -s
```

### ۲. تولید فایل کامل متغیرهای محیطی برای استقرار روی سرور Mock
تیم QA می‌تواند با اجرای اسکریپت تک‌خطی زیر، فایل استاندارد `.env` تمام سناریوها را استخراج نماید:
```powershell
.venv\Scripts\python.exe -c "from utils.mock_env_generator import MockEnvGenerator; print(MockEnvGenerator().render_env_file())" | Set-Content -Encoding utf8 negative_mock_profiles.env
```

### ۳. اعمال متغیرها و ری‌استارت سرویس Mock
1. متغیرهای سناریوی مورد نظر را در فایل محیطی سرویس Mock (یا کانتینر داکر) کپی کنید.
2. سرویس Mock را ری‌استارت کنید تا مقادیر جدید کش شوند.
3. با بارکد معرفی‌شده در جدول فوق، درخواست ثبت ورودی یا بستن کیسه را ارسال کنید.
4. بررسی کنید که پاسخ دریافتی مطابق ستون **«وضعیت مورد انتظار»** باشد.
