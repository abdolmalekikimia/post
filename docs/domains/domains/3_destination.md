# دامنه ۳: تصمیم‌گیری، تخصیص و تغییر مقصد/شوتر (Destination & Chute Assignment)

این بخش مسئول دریافت اطلاعات پستی، استعلام مقصد نهایی مرسوله، تخصیص به شوتر یا خروجی مناسب، مدیریت وضعیت تعلیق (Pending) و تغییر بلادرنگ مقصد مرسوله در حین حرکت روی نوار نقاله است.

---

## 📊 ماتریس قابلیت‌های آزمون استوری‌ها (Story Capabilities Matrix)

| استوری | عنوان | تست مثبت (Success) | تست منفی (Negative) | تست استرس (Stress) | تست واحد آفلاین (Unit) |
|---|---|:---:|:---:|:---:|:---:|
| **EPS-60** | تخصیص خروجی و مدیریت پاسخ‌های در حال انتظار (Pending) | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **EPS-71** | تخصیص مقصد و شوتر بر اساس کد پستی و سیاست‌های خط | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **EPS-73** | به‌روزرسانی و تغییر مقصد در حین حرکت (Destination Update) | ✅ دارد | ✅ دارد | ⏳ دارد (غیرفعال/Skip) | ✅ دارد |

---

## ۱. اجرای تست‌های مثبت (Success Runs)

### ۱.۰ اجرای کل سناریوهای مثبت دامنه (Unified Success Suite)
```powershell
$env:RUN_E2E="1"
$env:RUN_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/3_destination -m success -q -s
```

مسیرهای سالم تخصیص مقصد و مسیریابی به شوتر:

### ۱.۱ استعلام و تخصیص اولیه مقصد (EPS-60)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS60_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/3_destination -m eps60_success -q -s
```

### ۱.۲ تخصیص قطعی شوتر (EPS-71)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS71_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/3_destination -m eps71_success -q -s
```

### ۱.۳ تغییر موفق مقصد مرسوله (EPS-73)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS73_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/3_destination -m eps73_success -q -s
```

---

## ۲. اجرای تست‌های منفی (Negative Runs)

### ۲.۰ اجرای کل سناریوهای منفی و خطای دامنه (Unified Negative Suite)
```powershell
$env:RUN_E2E="1"
$env:RUN_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/3_destination -m negative -q -s
```

سناریوهای خطای مسیریابی، کد پستی نامعتبر، شوت پر یا تغییر دیرهنگام مقصد:

### ۲.۱ خطای بارکد یا انقضای زمان پاسخ در تعلیق (EPS-60)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS60_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/3_destination -m eps60_negative -q -s
```

### ۲.۲ عدم امکان تخصیص به شوتر یا مقصد مسدود (EPS-71)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS71_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/3_destination -m eps71_negative -q -s
```

### ۲.۳ رد تغییر مقصد به دلیل رد شدن مرسوله از نقطه انحراف (EPS-73)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS73_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/3_destination -m eps73_negative -q -s
```

---

## ۳. آزمون‌های بار و استرس (Stress Runs)

تست مسابقه هم‌زمانی و ارسال پی‌درپی تغییر مقصد مرسوله (Race Condition Stress Test):

> **توجه:** به صورت پیش‌فرض غیرفعال است و نیاز به متغیر `$env:RUN_STRESS="1"` دارد:

```powershell
$env:RUN_E2E="1"
$env:RUN_STRESS="1"
$env:RUN_EPS73_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_eps73_stress.py -q -s
```

---

## ۴. اجرای آزمون‌های واحد آفلاین (Offline Unit Tests)

اجرای سریع بدون وابستگی به شبکه و دستگاه:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_eps71_success_flow.py tests/unit/test_eps73_flow.py -v
```

---

## ۵. راهنمای عیب‌یابی (Troubleshooting)

| خطا | علت احتمالی | راه‌حل |
|---|---|---|
| `DestinationNotFound` | کد پستی مقصد در جدول نگاشت هاب موجود نیست | افزودن کد پستی به جدول پیکربندی سنترال هاب |
| `ChuteFullException` | ظرفیت شوتر پر شده است | شبیه‌سازی خالی شدن شوتر یا بستن کیسه فعلی |
| `UpdateTooLate` | بسته از حسگر تصمیم‌گیری رد شده است | بررسی تایمینگ شبیه‌ساز حرکت تسمه نقاله |
