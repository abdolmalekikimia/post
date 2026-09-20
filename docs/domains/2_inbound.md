# دامنه ۲: ورود، اعتبارسنجی ابعاد/وزن، تصاویر، سوابق و Idempotency (Inbound & Verification)

این بخش مسئول ورود اولیه مرسوله به خط سورتینگ، اعتبارسنجی ابعاد و وزن فیزیکی، تشخیص مغایرت با سابقه ثبت‌شده، آپلود ناهمگام تصاویر، استعلام تاریخچه رویداد از Core، ثبت نتایج عملیات و تضمین Idempotency در پردازش درخواست‌ها است.

---

## 📊 ماتریس قابلیت‌های آزمون استوری‌ها (Story Capabilities Matrix)

| استوری | عنوان | تست مثبت (Success) | تست منفی (Negative) | تست استرس (Stress) | تست واحد آفلاین (Unit) |
|---|---|:---:|:---:|:---:|:---:|
| **EPS-53** | اعتبارسنجی ابعاد و وزن و مغایرت‌سنجی فیزیکی | ✅ دارد | ✅ دارد | ⏳ دارد (غیرفعال/Skip) | ✅ دارد |
| **EPS-55** | اورکستریشن ثبت ورودی، مغایرت بارکد و خطای پستی | ✅ دارد | ✅ دارد | ⏳ دارد (غیرفعال/Skip) | ✅ دارد |
| **EPS-64** | آپلود ناهمگام (Lazy Upload) تصاویر مرسوله | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **EPS-66** | بازخوانی مجدد بر اساس وضعیت قبلی مرسوله (Reread) | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **EPS-68** | بازنویسی وضعیت مرسوله از سوی Core | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **CPS-20** | استعلام بلادرنگ سابقه مرسوله از Core | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **CPS-65** | ارزیاب وضعیت بیزینسی مرسوله (`ParcelStatusEvaluator`) | ✅ دارد | ➖ فاقد منفی (منطق خالص) | ➖ فاقد استرس | ✅ دارد (کامل) |
| **CPS-80** | صدور Pre-signed URL آپلود مستقیم به Object Storage | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **CPS-86** | ثبت نتیجه عملیات پستی در Core | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **CPS-58** | ثبت متادیتای تصاویر مرسوله در Data Ingestion | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **CPS-61** | اتصال غیرهمزمان داده تکمیلی و متادیتای تصویر به پرونده مرسوله | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **CPS-63** | اعتبارسنجی ساختاری رویداد عملیاتی و سازگاری بارکدها (14/24/37) | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **CPS-33** | مدیریت تکرار و عدم ایجاد داده تکراری (Idempotency) | ✅ دارد | ✅ دارد | ⏳ سناریوی هم‌زمانی (TC-03) | ✅ دارد |

---

## ۱. اجرای تست‌های مثبت (Success Runs)

### ۱.۰ اجرای کل سناریوهای مثبت دامنه (Unified Success Suite)
```powershell
$env:RUN_E2E="1"
$env:RUN_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m success -q -s
```

مسیرهای سالم پردازش مرسولات استاندارد، ثبت موفق نتایج و استعلام‌های معتبر:

### ۱.۱ ابعاد و وزن فیزیکی (EPS-53)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS53_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m eps53_success -q -s
```

### ۱.۲ اورکستریشن ورودی (EPS-55)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS55_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m eps55_success -q -s
```

### ۱.۳ آپلود تصاویر (EPS-64)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS64_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m eps64_success -q -s
```

### ۱.۴ بازخوانی مجدد (EPS-66)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS66_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m eps66_success -q -s
```

### ۱.۵ استعلام بلادرنگ سابقه (CPS-20)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS20_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m cps20_success -q -s
```

### ۱.۶ آدرس موقت آپلود تصویر (CPS-80)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS80_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m cps80_success -q -s
```

### ۱.۷ ثبت نتیجه عملیات (CPS-86)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS86_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m cps86_success -q -s
```

### ۱.۸ ثبت متادیتای تصاویر (CPS-58)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS58_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m cps58_success -q -s
```

### ۱.۹ اتصال غیرهمزمان متادیتای تصویر به پرونده (CPS-61)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS61_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m cps61_success -q -s
```

### ۱.۱۰ اعتبارسنجی ساختاری رویداد و مجموعه بارکدها (CPS-63)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS63_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m cps63_success -q -s
```

### ۱.۱۱ آزمون عدم تکرار عملیات (CPS-33)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS33_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m cps33_success -q -s
```

---

## ۲. اجرای تست‌های منفی (Negative Runs)

### ۲.۰ اجرای کل سناریوهای منفی و خطای دامنه (Unified Negative Suite)
```powershell
$env:RUN_E2E="1"
$env:RUN_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m negative -q -s
```

سناریوهای مغایرت ابعاد، مرسولات برگشتی، انقضای توکن تصویر و خطاهای پستی:

### ۲.۱ مغایرت ابعاد و رد بسته (EPS-53)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS53_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m eps53_negative -q -s
```

### ۲.۲ عدم تطابق بارکد و خطای وب‌سرویس پستی (EPS-55)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS55_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m eps55_negative -q -s
```

### ۲.۳ خطای آپلود تصویر (EPS-64)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS64_NEGATIVE="1"
$env:EPS64_NEGATIVE_CASE="all"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m eps64_negative -q -s
```

### ۲.۴ خطای بازخوانی مجدد (EPS-66)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS66_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m eps66_negative -q -s
```

### ۲.۵ بازنویسی وضعیت و خطای Core (EPS-68)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS68_NEGATIVE="1"
$env:EPS68_CASE="all"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m eps68_negative -q -s
```

### ۲.۶ مرسوله برگشتی یا نامعتبر در استعلام (CPS-20)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS20_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m cps20_negative -q -s
```

### ۲.۷ انقضا و خطای امضای URL تصویر (CPS-80)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS80_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m cps80_negative -q -s
```

### ۲.۸ گزارش خطا و Retry ناموفق (CPS-86)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS86_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m cps86_negative -q -s
```

### ۲.۹ خطای متادیتای نامعتبر تصویر (CPS-58)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS58_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/2_inbound -m cps58_negative -q -s
```

---

## ۳. آزمون‌های بار و استرس (Stress Runs)

> **توجه:** آزمون‌های استرس به صورت پیش‌فرض غیرفعال هستند تا به شکست ناخواسته به دلیل عدم آمادگی کامل بک‌اند منجر نشوند. برای اجرای آنها متغیر `$env:RUN_STRESS="1"` الزامی است:

```powershell
$env:RUN_E2E="1"
$env:RUN_STRESS="1"
$env:RUN_EPS53_STRESS="1"
$env:RUN_EPS55_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_eps53_stress.py tests/stress/test_eps55_stress.py -q -s
```

---

## ۴. اجرای آزمون‌های واحد آفلاین (Offline Unit Tests)

بدون نیاز به شبکه و سرویس زنده:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps65_status_evaluator.py tests/unit/test_cps20_core.py tests/unit/test_cps80_core.py tests/unit/test_cps86_core.py tests/unit/test_cps58_core.py tests/unit/test_cps33_core.py -v
```

---

## ۵. نمونه قرارداد و هدرهای الزامی (Contract Reference)

### مسیرهای اصلی:
- `POST /api/edge/parcels/inbound-query` (CPS-20)
- `POST /api/edge/images/presigned-url` (CPS-80)
- `POST /api/edge/operational-results` (CPS-86)
- `POST /api/edge/images/metadata` (CPS-58)

### نمونه هدرها:
```http
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>
X-Correlation-ID: <UUID>
Idempotency-Key: <UNIQUE_UUID>
```

---

## ۶. راهنمای عیب‌یابی (Troubleshooting)

| خطا | علت احتمالی | راه‌حل |
|---|---|---|
| `401 Unauthorized` | توکن احراز هویت لبه ست نشده است | مقدار `CORE_AUTH_TOKEN` یا توکن دستگاه را تنظیم کنید |
| `discrepancyDetected = true` | اختلاف ابعاد با مقادیر از پیش ثبت‌شده | بررسی تلرانس مجاز در `config/test.env` |
| `Idempotency Divergence` | تغییر شناسه در ارسال مجدد | اطمینان از ارسال همان Payload با همان کلید در سناریوی Replay |
