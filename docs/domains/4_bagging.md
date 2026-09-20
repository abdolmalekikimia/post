# دامنه ۴: کیسه‌بندی، بستن کیسه، صدور بارنامه و ذخیره دپش (Bagging, Labeling & Dispatch)

این بخش مسئول انتخاب مرسولات، ثبت صادره در سامانه پستی، صدور شناسه کیسه، تولید برچسب بارنامه (`BagLabel`)، مدیریت قطعی ارتباط پستی، و ذخیره‌سازی داده‌های Bag و Dispatch در سامانه مرکزی (Core) است.

---

## 📊 ماتریس قابلیت‌های آزمون استوری‌ها (Story Capabilities Matrix)

| استوری | عنوان | تست مثبت (Success) | تست منفی (Negative) | تست استرس (Stress) | تست واحد آفلاین (Unit) |
|---|---|:---:|:---:|:---:|:---:|
| **EPS-76** | انتخاب مرسولات با فیلتر شوتر، شمارنده و هم‌زمانی | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **EPS-79** | ترتیب ثبت صادره در سامانه پستی قبل از بستن فیزیکی | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **EPS-83** | تولید برچسب Base64، قطع پست و آزادسازی فوری مقصد | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **EPS-87** | قرارداد پاسخ کامل `bag.close`، شمارنده‌ها و کد خطاها | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **EPS-89** | ممیزی فیزیکی مرسولات و هویت کیسه | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **CPS-67** | ذخیره‌سازی و ارتباط اطلاعات کیسه و دپش (Bag / Dispatch Storage) | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |

---

## ۱. اجرای تست‌های مثبت (Success Runs)

### ۱.۰ اجرای کل سناریوهای مثبت دامنه (Unified Success Suite)
```powershell
$env:RUN_E2E="1"
$env:RUN_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/4_bagging -m success -q -s
```

بستن موفق کیسه، صدور شناسه، صدور بارنامه Base64 و ثبت ساختار Bag/Dispatch:

### ۱.۱ بستن موفق و انتخاب مرسولات (EPS-76)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS76_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/4_bagging -m eps76_success -q -s
```

### ۱.۲ ترتیب صادره پستی (EPS-79)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS79_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/4_bagging -m eps79_success -q -s
```

### ۱.۳ تولید برچسب و بارنامه Base64 (EPS-83)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS83_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/4_bagging -m eps83_success -q -s
```

### ۱.۴ ممیزی کیسه (EPS-89)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS89_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/4_bagging -m eps89_success -q -s
```

### ۱.۵ ذخیره و پیوند کیسه و دپش در Core (CPS-67)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS67_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/4_bagging -m cps67_success -q -s
```

---

## ۲. اجرای تست‌های منفی (Negative Runs)

### ۲.۰ اجرای کل سناریوهای منفی و خطای دامنه (Unified Negative Suite)
```powershell
$env:RUN_E2E="1"
$env:RUN_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/4_bagging -m negative -q -s
```

بررسی قطعی سامانه پستی، خطای عدم تطابق بارکد، کیسه خالی و بستن مجدد کیسه بسته:

### ۲.۱ خطای انتخاب و نبود مرسوله واجد شرایط (EPS-76)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS76_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/4_bagging -m eps76_negative -q -s
```

### ۲.۲ خطای قطعی ارتباط پستی و آزادسازی قفل (EPS-83)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS83_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/4_bagging -m eps83_negative -q -s
```

### ۲.۳ خطای ممیزی و بارکد نامعتبر (EPS-89)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS89_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/4_bagging -m eps89_negative -q -s
```

### ۲.۴ خطای ثبت داده ناقص کیسه و دپش (CPS-67)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS67_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/4_bagging -m cps67_negative -q -s
```

---

## ۳. آزمون‌های بار و استرس (Stress Runs)

> **توجه:** مدیریت صف و وضعیت قفل شوترها در صورت اعمال بار هم‌زمان توسط آزمون‌های داخلی ماژول پکینگ کنترل می‌شود و فاقد رانر استرس مستقل بیرونی است.

---

## ۴. اجرای آزمون‌های واحد آفلاین (Offline Unit Tests)

اجرای سریع کل قواعد بیزینسی کیسه‌بندی و ذخیره‌سازی:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_eps83_flow.py tests/unit/test_cps67_core.py -v
```

---

## ۵. نمونه قرارداد و هدرهای الزامی (Contract Reference)

### مسیرهای اصلی:
- `POST /api/edge/bags` (CPS-67 Bag Registration)
- `POST /api/edge/dispatches` (CPS-67 Dispatch Registration)

### نمونه Body ثبت کیسه (`BagCloseRequest`):
```json
{
  "bagBarcode": "BAG-IR-59544-001",
  "memberBarcodes": ["PK998877665544"],
  "originCenter": "59544",
  "destCenter": "11369",
  "sealNumber": "SEAL-998811",
  "transportType": "Ground",
  "closedAt": "2025-01-15T12:00:00Z"
}
```

---

## ۶. راهنمای عیب‌یابی (Troubleshooting)

| خطا | علت احتمالی | راه‌حل |
|---|---|---|
| `PostalServiceTimeout` | عدم پاسخ‌دهی شبیه‌ساز یا سرور پستی | بررسی وضعیت سرویس پست یا فعال‌سازی Fallback خودکار |
| `BagAlreadyClosed` | کیسه با این بارکد قبلاً بسته شده است | اطمینان از تولید بارکد یکتای کیسه در هر تست |
| `SealNumberMismatch` | شماره پلمپ تکراری یا نامعتبر | استفاده از پلمپ معتبر طبق الگوی استاندارد پستی |
