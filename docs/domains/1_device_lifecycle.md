# دامنه ۱: راه‌اندازی، احراز هویت و همگام‌سازی دستگاه (Device Lifecycle & Auth)

این بخش مسئول ثبت، اعتبارسنجی شبکه، لاگین ادمین، همگام‌سازی تنظیمات و احراز هویت دستگاه‌های سورتینگ روی بستر WebSocket/SignalR است.

## استوری‌های پوشش داده شده
- **EPS-40:** همگام‌سازی تنظیمات دستگاه و رد دستگاه‌های غیرفعال
- **EPS-46:** اعتبارسنجی سیاست‌های اعزام خودکار (`AutoDispatchPolicy`) در زمان Sync
- **EPS-49:** چرخهٔ عمر کامل دستگاه، ثبت IP، هندشیک و خطاهای REST/WS

---

## ۱. اجرای تست‌های مثبت (Success)

تست‌های مسیر سالم شامل لاگین معتبر، ثبت IP، اتصال به سوکت و احراز هویت موفق:

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS40_SUCCESS="1"
$env:RUN_EPS46_SUCCESS="1"
$env:RUN_EPS49_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m success -q -s
```

---

## ۲. اجرای تست‌های منفی (Negative)

بررسی سناریوهای خطای اعتبارسنجی، توکن‌های نامعتبر، دستگاه ناشناخته و عدم تطابق وضعیت:

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS40_NEGATIVE="1"
$env:RUN_EPS46_NEGATIVE="1"
$env:RUN_EPS49_NEGATIVE="1"
$env:EPS40_CASE="all"
$env:EPS46_CASE="all"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m negative -q -s
```

---

## ۳. آزمون‌های بار و استرس (Stress)

این بخش نیازی به آزمون استرس مستقل ندارد (قراردادهای Lifecycle و Policy تمرکز بر صحت اعتبارسنجی دارند).
