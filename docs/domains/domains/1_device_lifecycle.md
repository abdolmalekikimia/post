# دامنه ۱: راه‌اندازی، احراز هویت و همگام‌سازی دستگاه (Device Lifecycle & Auth)

این بخش مسئول ثبت، اعتبارسنجی شبکه، لاگین ادمین، همگام‌سازی تنظیمات، پیکربندی اولیه و احراز هویت دستگاه‌های سورتینگ روی بسترهای WebSocket/SignalR و REST است.

---

## 📊 ماتریس قابلیت‌های آزمون استوری‌ها (Story Capabilities Matrix)

| استوری | عنوان | تست مثبت (Success) | تست منفی (Negative) | تست استرس (Stress) | تست واحد آفلاین (Unit) |
|---|---|:---:|:---:|:---:|:---:|
| **EPS-40** | همگام‌سازی تنظیمات دستگاه و رد دستگاه غیرفعال | ✅ دارد | ✅ دارد | ➖ فاقد استرس (تنظیمات استاتیک) | ✅ دارد |
| **EPS-46** | اعتبارسنجی سیاست‌های اعزام خودکار (`AutoDispatchPolicy`) | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **EPS-49** | چرخهٔ کامل حیات دستگاه، ثبت IP و هندشیک WS | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **CPS-74** | مدیریت وضعیت و چرخه حیات دستگاه‌های تفکیک در Core | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **CPS-77** | مدیریت پیکربندی و نسخه اسنپ‌شات‌های راه‌اندازی (Bootstrap) | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **CPS-49** | غیرفعال‌سازی نود Edge و قطع دسترسی با JWT معتبر و Audit Log | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **CPS-9** | زیرساخت BuildingBlocks، سلامت سرویس و قفل قرارداد | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |
| **CPS-70** | کنترل دسترسی مدیریتی بر پایه نقش و ادعا (RBAC & Center Scoping) | ✅ دارد | ✅ دارد | ➖ فاقد استرس | ✅ دارد |

---

## ۱. اجرای تست‌های مثبت (Success Runs)

### ۱.۰ اجرای کل سناریوهای مثبت دامنه (Unified Success Suite)
```powershell
$env:RUN_E2E="1"
$env:RUN_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m success -q -s
```

مسیرهای سالم شامل ثبت دستگاه، اتصال سوکت، دریافت تنظیمات اولیه و همگام‌سازی سالم:

### ۱.۱ تست همگام‌سازی تنظیمات (EPS-40)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS40_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m eps40_success -q -s
```

### ۱.۲ تست سیاست‌های اعزام خودکار (EPS-46)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS46_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m eps46_success -q -s
```

### ۱.۳ تست چرخه عمر و لاگین دستگاه (EPS-49)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS49_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m eps49_success -q -s
```

### ۱.۴ تست مدیریت دستگاه Core (CPS-74)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS74_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m cps74_success -q -s
```

### ۱.۵ تست تنظیمات اولیه و اسنپ‌شات (CPS-77)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS77_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m cps77_success -q -s
```

### ۱.۶ تست غیرفعال‌سازی Edge و قطع دسترسی با Audit Log (CPS-49)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS49_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m cps49_success -q -s
```

### ۱.۷ تست قفل قرارداد و سلامت سرویس (CPS-9)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS9_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m cps9_success -q -s
```

### ۱.۸ تست کنترل دسترسی و فیلتر مراکز (CPS-70)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS70_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m cps70_success -q -s
```

---

## ۲. اجرای تست‌های منفی (Negative Runs)

### ۲.۰ اجرای کل سناریوهای منفی و امنیتی دامنه (Unified Negative Suite)
```powershell
$env:RUN_E2E="1"
$env:RUN_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m negative -q -s
```

سناریوهای خطای اعتبارسنجی توکن، آدرس IP نامعتبر، دستگاه‌های غیرفعال یا حذف‌شده:

### ۲.۱ تست‌های منفی تنظیمات و وضعیت غیرفعال (EPS-40)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS40_NEGATIVE="1"
$env:EPS40_CASE="all"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m eps40_negative -q -s
```

### ۲.۲ تست‌های منفی سیاست‌های اعزام (EPS-46)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS46_NEGATIVE="1"
$env:EPS46_CASE="all"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m eps46_negative -q -s
```

### ۲.۳ تست‌های منفی لاگین و اتصال سوکت (EPS-49)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS49_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m eps49_negative -q -s
```

### ۲.۴ تست‌های منفی مدیریت دستگاه Core (CPS-74)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS74_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m cps74_negative -q -s
```

### ۲.۵ تست‌های منفی تنظیمات Bootstrap (CPS-77)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS77_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m cps77_negative -q -s
```

### ۲.۶ تست‌های منفی و امنیتی کنترل دسترسی (CPS-70)
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS70_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/1_device_lifecycle -m cps70_negative -q -s
```

---

## ۳. آزمون‌های بار و استرس (Stress Runs)

> **توجه معماری:** استوری‌های دامنه ۱ مربوط به چرخه احراز هویت اولیه، ثبت IP و دریافت کانفیگ استاتیک هستند و ذاتاً شامل پردازش‌های پرتکرار یا استرس بلادرنگ نیستند؛ ازاین‌رو این دامنه فاقد سناریوی استرس مستقل است.

---

## ۴. اجرای آزمون‌های واحد آفلاین (Offline Unit Tests)

برای بررسی منطق بدون نیاز به برقراری ارتباط شبکه با Core یا Mock Backend:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps74_core.py tests/unit/test_cps77_core.py tests/unit/test_cps9_core.py tests/unit/test_cps49_core.py tests/unit/test_cps70_core.py tests/unit/test_signalr_client.py -v
```

---

## ۵. نمونه قرارداد و هدرهای الزامی (Contract Reference)

### مسیرهای اصلی:
- `POST /api/edge/devices` (CPS-74)
- `GET /api/edge/bootstrap/config` (CPS-77)
- `GET /health` و `GET /swagger/v1/swagger.json` (CPS-9)

### هدرهای استاندارد:
```http
Content-Type: application/json
Authorization: Bearer <VALID_JWT_TOKEN>
X-Correlation-ID: <UUID>
Idempotency-Key: <UNIQUE_KEY>
```

---

## ۶. راهنمای عیب‌یابی (Troubleshooting)

| خطا | علت احتمالی | راه‌حل |
|---|---|---|
| `401 Unauthorized` | توکن دستگاه منقضی شده یا ارائه نشده | بررسی توکن در `config/test.env` یا لاگین مجدد با ادمین |
| `WebSocket Connection Refused` | سرویس SignalR یا Mock در حال اجرا نیست | بررسی بالا بودن سرویس روی پورت مورد نظر (۵۰۲۵ یا پورت دستگاه) |
| `Device not active` | شناسه دستگاه در حالت Deactivated تعریف شده | بررسی وضعیت فیکسچر دستگاه در سرور تست |
