# CPS-164: تست پچ روی استیج (Core Stage Patch Verification)

این مستند تشریح‌کننده زیرساخت تست و صحت‌سنجی پچ اعمال‌شده روی سرور استیج (**192.168.20.160**) برای تسک **CPS-164** از سیستم **Core Post Sorting** است.

---

### 📌 هدف و سناریوهای تست (8 BDD Acceptance Scenarios)

زیرساخت تست CPS-164 موارد زیر را پس از اعمال آپدیت/پچ روی سرور استیج ارزیابی می‌کند:

1. **TC-01 (Admin Auth)**: ورودی موفق با نام‌کاربری ادمین پچ (`national.manager`) و دریافت توکن معتبر JWT از Identity Service.
2. **TC-02 (Edge Bootstrap Auth)**: ورودی موفق با کاربر بوت‌استرپ (`edge-bootstrap`).
3. **TC-03 (Inbound Query API)**: استعلام مرسوله با بارکد ۲۴ رقمی پویا (`/api/edge/parcels/inbound-query`).
4. **TC-04 (Presigned URL)**: دریافت آدرس آپلود زمان‌دار از MinIO/S3 (`/api/edge/images/presigned-url`).
5. **TC-05 (Bag Registration)**: ثبت اطلاعات کیسه پستی به همراه کلید تکرارپذیری منحصر‌به‌فرد (`/api/edge/bags`).
6. **TC-06 (Operational Results)**: ثبت نتایج عملیاتی پست (`/api/edge/operational-results`).
7. **TC-07 (Edge Heartbeat)**: ثبت سیگنال پایش سلامت و وضعیت صف‌های لبه (`/api/edge/heartbeat`).
8. **TC-08 (Device Management)**: ثبت دستگاه تفکیک پستی جدید (`/api/admin/devices`).

---

### 🚀 نحوه اجرا

#### ۱. اجرای تست‌های واحد (Mock Offline Test):
جهت اطمینان از صحت کدها بدون اتصال به شبکه:
```bash
.venv\Scripts\python.exe -m pytest tests/unit/test_cps164_core.py -v
```

#### ۲. اجرای تست زنده روی سرور استیج (Live Stage Server):
هر زمان که سرویس‌های استیج بالا آمدند و آماده تست بودند:
```bash
$env:RUN_STAGE="1"
.venv\Scripts\python.exe -m pytest tests/stage/test_cps164_stage_patch.py -v -s
```

یا با تنظیم آدرس اختصاصی:
```bash
$env:STAGE_SERVER_URL="http://192.168.20.160"
.venv\Scripts\python.exe -m pytest tests/stage/test_cps164_stage_patch.py -v -s
```

---

### 🛡️ ضمانت تکرارپذیری (Repeatability & Isolation)
- **تولید بارکد پویا**: در هر نوبت اجرا، بارکدهای ۲۴ و ۳۷ رقمی بر اساس اسلات اختصاصی تولید می‌شوند.
- **شناسه Correlation-ID و Idempotency-Key یکتا**: تمامی درخواست‌ها با GUID یکتا ارسال می‌شوند تا تداخلی با داده‌های قبلی دیتابیس استیج ایجاد نشود.
- **بی‌خطر بودن اجرا**: اجرای تست‌ها داده‌های موجود روی استیج را خراب نکرده و با متغیر `RUN_STAGE=1` کنترل می‌شود.
