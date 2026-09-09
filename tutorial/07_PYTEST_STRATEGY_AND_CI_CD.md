# 🚀 استراتژی اجرای Pytest، تست‌های Stress و CI/CD

در این بخش بررسی می‌کنیم که تست‌ها با چه متدولوژی در Pytest دسته‌بندی و اجرا می‌شوند و چگونه تست‌های حجم بالا، همزمانی و Race Condition مدیریت شده‌اند.

---

## ۱. دسته‌بندی تست‌ها با مارکرهای Pytest (`pytest.ini`)

در فایل `pytest.ini` مارکرهای متعددی برای تفکیک دقیق انواع تست‌ها تعریف شده است:
- `unit`: تست‌های واحد که کامپوننت‌ها، اعتبارسنجی‌ها، کلاینت‌ها و متدهای کمکی را به صورت کاملاً مجزا و سریع بررسی می‌کنند (بدون نیاز به شبکه).
- `success`: تست‌های سناریوی موفق (Happy Path).
- `negative`: سناریوهای منفی و اعتبارسنجی خطاها.
- `stress`: تست‌های حجم بالا، پایداری، همزمانی و Race Condition.
- `e2e`: تست‌های سرتاسری که نیاز به سرور در حال اجرا دارند.

### مزیت مارکرها:
امکان اجرای هدفمند با سوییچ `-m`:
```powershell
# فقط تست‌های یونیت
pytest tests/unit -q

# فقط تست‌های موفقیت
pytest -m "success" -q

# همه تست‌های سرتاسری به جز استرس
pytest -m "e2e and not stress" -q
```

---

## ۲. طراحی تست‌های تنش و همزمانی (Stress & Race Conditions)

در پوشه `tests/stress/` سناریوهای حساسی مانند شرایط رقابتی (Race Condition) تست می‌شوند.

### مثال: سناریوی Race Condition در تغییر مقصد (`tests/stress/test_destination_update_stress.py`)
- **مسئله در دنیای واقعی:** اگر اپراتور دکمه بستن کیسه (`container.close`) را بزند و دقیقاً در همان میلی‌ثانیه دستگاه بسته‌ای را به همان کیسه تخصیص دهد (`route.assign`)، سیستم چه رفتاری نشان می‌دهد؟
- **نحوه پیاده‌سازی تست:**
  با استفاده از `ThreadPoolExecutor` یا اجرای موازی در `utils/stress.py`، دو درخواست همزمان از دو کانکشن مستقل ارسال می‌شوند و سپس بررسی می‌شود که سیستم هرگز وضعیت نامعتبر (Inconsistent State) ثبت نکند؛ یعنی یا درخواست دوم را با خطای مناسب رد کند یا شمارنده کیسه دقیق بماند.

---

## ۳. اجرای ایمن در CI/CD با `RUN_E2E` Guard

از آنجا که این مخزن به صورت Public در گیت‌هاب قرار دارد و به سرور پروداکشن واقعی متصل نیست:
- در ابتدای تمام تست‌های ادغامی یک محافظ (Guard) قرار دارد:
  ```python
  if os.getenv("RUN_E2E", "0") != "1":
      pytest.skip("Set RUN_E2E=1 to run against the local demo service")
  ```
- پایپ‌لاین گیت‌هاب اکشنز (`.github/workflows/qa.yml`) بدون نیاز به ماک سرور، تست‌های واحد، امنیت سورس‌کد و اعتبارسنجی سینتکس را با موفقیت اجرا می‌کند.
- هر زمان برنامه‌نویس یا تستر بخواهد در محیط محلی با ماک‌سرور تست کند، متغیر محیطی را ست می‌کند:
  ```powershell
  $env:RUN_E2E="1"
  pytest tests/success -q -s
  ```

---

## ۴. جمع‌بندی دستورات پرکاربرد اجرایی

| دستور | کاربرد |
|---|---|
| `.venv\Scripts\python.exe -m pytest tests/unit -q` | اجرای تمام یونیت‌تست‌ها به صورت آفلاین |
| `.venv\Scripts\python.exe -m pytest -q` | اجرای سوئیت امن پیش‌فرض |
| `$env:RUN_E2E="1"; .venv\Scripts\python.exe -m pytest tests/success -q -s` | اجرای سناریوهای موفق سرتاسری |
| `$env:RUN_E2E="1"; .venv\Scripts\python.exe -m pytest tests/negative -q -s` | اجرای سناریوهای منفی |
| `$env:RUN_E2E="1"; .venv\Scripts\python.exe -m pytest tests/stress -q -s -o addopts=""` | اجرای تست‌های استرس و همزمانی |
| `.venv\Scripts\python.exe -m scripts.run_scenarios --list` | فهرست کردن ماتریس تمام سناریوهای پوشش داده شده |
