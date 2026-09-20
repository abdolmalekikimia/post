# دامنه ۵: پایش وضعیت، رویدادها و سلامت سامانه (Monitoring, Events & Health)

این بخش مسئول ثبت، ارسال و بافرینگ رویدادهای ارتباطی سامانه لبه به سرویس مرکزی، پایش سلامت دوره‌ای دستگاه‌های لبه (Heartbeat / Health Monitoring) و تشخیص ناهنجاری‌ها و نوسانات است.

---

## 📊 ماتریس قابلیت‌های آزمون استوری‌ها (Story Capabilities Matrix)

| استوری | عنوان | تست مثبت (Success) | تست منفی (Negative) | تست استرس (Stress) | تست واحد آفلاین (Unit) |
|---|---|:---:|:---:|:---:|:---:|
| **EPS-113** | ثبت رویدادهای مرکزی، بافر آفلاین و پایش Flapping | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **CPS-82** | پایش سلامت سیستم‌های لبه و دریافت ضربان قلب (Edge Health) | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |

---

## ۱. اجرای تست‌های مثبت (Success Runs)

### ۱.۰ اجرای کل سناریوهای مثبت دامنه (Unified Success Suite)
```powershell
$env:RUN_E2E="1"
$env:RUN_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/5_monitoring -m success -q -s
```

مسیرهای سالم ثبت رویداد، ارسال ضربان قلب (Heartbeat) و تخلیه بافر آفلاین:

### ۱.۱ ثبت رویدادهای سیستم و عملکرد بافر (EPS-113)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS113_SUCCESS="1"
$env:EPS113_CASE="all"
.venv\Scripts\python.exe -m pytest tests/5_monitoring -m eps113_success -q -s
```

### ۱.۲ پایش سلامت و گزارش وضعیت پایدار لبه (CPS-82)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS82_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/5_monitoring -m cps82_success -q -s
```

---

## ۲. اجرای تست‌های منفی (Negative Runs)

### ۲.۰ اجرای کل سناریوهای منفی و خطای دامنه (Unified Negative Suite)
```powershell
$env:RUN_E2E="1"
$env:RUN_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/5_monitoring -m negative -q -s
```

سناریوهای قطع ناگهانی ارتباط، شکست لاگین، پیام‌های خارج از پروتکل و خطای گزارش سلامت:

### ۲.۱ قطع ارتباط، خطاهای اتصال و Flapping شبکه (EPS-113)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS113_NEGATIVE="1"
$env:EPS113_CASE="all"
.venv\Scripts\python.exe -m pytest tests/5_monitoring -m eps113_negative -q -s
```

### ۲.۲ گزارش سلامت نامعتبر یا تاخیر ضربان قلب (CPS-82)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS82_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/5_monitoring -m cps82_negative -q -s
```

---

## ۳. آزمون‌های بار و استرس (Stress Runs)

> **توجه معماری:** استوری‌های این دامنه مربوط به گزارش وضعیت و ثبت رویدادهای خط هستند و نیازی به تست استرس مستقل ندارند.

---

## ۴. اجرای آزمون‌های واحد آفلاین (Offline Unit Tests)

اجرای سریع پردازش رویدادها و ارزیابی ضربان قلب به صورت آفلاین:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_eps113_flow.py tests/unit/test_cps82_core.py -v
```

---

## ۵. نمونه قرارداد و هدرهای الزامی (Contract Reference)

### مسیر اصلی پایش سلامت:
- `POST /api/edge/health/heartbeat` (CPS-82)

### نمونه Body ضربان قلب:
```json
{
  "edgeId": "EDGE-TEST-001",
  "status": "Healthy",
  "cpuUsagePercent": 14.5,
  "memoryUsagePercent": 42.0,
  "diskUsagePercent": 61.2,
  "timestampUtc": "2025-01-15T12:00:00Z"
}
```

---

## ۶. راهنمای عیب‌یابی (Troubleshooting)

| خطا | علت احتمالی | راه‌حل |
|---|---|---|
| `OfflineBufferOverflow` | قطعی طولانی‌مدت اتصال و پر شدن بافر لوکال | بازیابی اتصال شبکه و بررسی تخلیه خودکار رویدادها |
| `HeartbeatTimeout` | عدم ارسال ضربان در بازه آستانه مجاز | بررسی فاصله زمانی تایمر پایش سلامت در لبه |
| `InvalidEventPayload` | فیلدهای ضروری رویداد پر نشده است | بررسی ساختار پیام رویداد ارسالی |
