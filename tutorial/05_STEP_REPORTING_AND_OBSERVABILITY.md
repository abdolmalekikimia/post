# 📊 سیستم گزارش‌دهی مرحله‌ای و شفافیت اجرای تست (Step Reporting & Observability)

یکی از وجوه تمایز این پروژه نسبت به پروژه‌های تست معمولی، وجود یک سیستم گزارش‌دهی داخلی، بدون وابستگی خارجی و بسیار قدرتمند در `utils/step_report.py` است.

---

## ۱. چرا به سیستم گزارش‌دهی مرحله‌ای (Step Reporter) نیاز داریم؟

در تست‌های پیچیده ادغامی (Integration Tests) که شامل ۱۰ تا ۲۰ مرحله پیاپی هستند:
- اگر تست در مرحله هفتم شکست بخورد، فهمیدن اینکه دقیقاً چه پارامترهایی ارسال شده، چه پاسخی آمده و ۶ مرحله قبل چقدر طول کشیده‌اند در حالت عادی بسیار دشوار است.
- سیستم `ExecutionReport` خروجی را دقیقاً مانند یک کنسول استاندارد مانیتورینگ نمایش می‌دهد.

### نمونه خروجی گزارش در کنسول:
```text
Execution report: Project base success flow
01. [PASS] 1. [BASE] Admin Login - POST /api/admin/login
    payloadSent: {"username": "admin", "password": "<redacted>"}
    responseReceived: {"token": "<redacted>", "expiresIn": 3600}
    expected: PASS
02. [PASS] 2. [BASE] Update Device IP - PUT /api/devices/{deviceId}/ip
    payloadSent: {"deviceId": "demo-device", "ip": "127.0.0.1"}
    responseReceived: {"status": "SUCCESS"}
    expected: PASS
03. [PASS] 3. [BASE] SignalR Connect/Handshake - WebSocket /hubs/device
    payloadSent: {"protocol": "json", "version": 1}
    responseReceived: {}
    expected: PASS
04. [FAIL] 4. [BASE] Device Authentication - Auth
    payloadSent: {"deviceId": "demo-device", "deviceToken": "<redacted>"}
    error: RuntimeError: Remote host closed the WebSocket
    expected: FAIL
05. [NOT_CHECKED] 5. [BASE] Inbound Registration - RegisterItem
    expected: NOT_CHECKED

Result: PASS=3, FAIL=1, NOT_CHECKED=1
```

---

## ۲. مکانیسم‌های مهم در `utils/step_report.py`

### الف) ثبت زمان و وضعیت مراحل با `Enum` و `Dataclass`
```python
class StepStatus(str, Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    NOT_EXECUTED = "NOT_EXECUTED"

@dataclass
class StepRecord:
    name: str
    status: StepStatus = StepStatus.PENDING
    duration_seconds: float = 0.0
    message: str = ""
    payload_sent: object = None
    response_received: object = None
    expectation: str = "NOT_CHECKED"
    error: str = ""
```

### ب) ماسک‌کردن خودکار اطلاعات حساس (Secret Redaction)
یکی از الزامات امنیتی در گزارش‌دهی تست، جلوگیری از چاپ شدن توکن‌ها و رمزهای عبور است. تابع `format_detail` در `step_report.py` به صورت بازگشتی دیکشنری‌ها را بررسی کرده و کلیدهایی مثل `password`، `token`، `authorization` و `secret` را با `<redacted>` جایگزین می‌کند:
```python
if any(s in lowered_key for s in ("password", "token", "authorization", "secret")):
    sanitized[key] = "<redacted>"
```
> اگر متغیر محیطی `REPORT_SHOW_SECRETS=1` تنظیم شود، برای مقاصد دیباگ محلی، مقادیر واقعی نمایش داده خواهند شد.

### ج) تابع اجرای مرحله (`run_step`)
تابع `run_step` به عنوان یک Wrapper هوشمند عمل می‌کند:
1. زمان شروع را با `time.monotonic()` ثبت می‌کند.
2. تابع اکشن اصلی را اجرا می‌کند.
3. در صورت موفقیت، مدت زمان و داده‌های دریافتی را در وضعیت `PASSED` ذخیره می‌کند.
4. در صورت بروز هرگونه Exception:
   - وضعیت گام به `FAILED` تغییر می‌کند.
   - متد `mark_remaining_not_executed()` فراخوانی می‌شود تا تمام گام‌های بعدی در وضعیت `NOT_EXECUTED` قرار گیرند.
   - گزارش فوراً در خروجی چاپ می‌شود (`report.print()`).
   - یک خطای اختصاصی `FlowExecutionError` بالا داده می‌شود تا Pytest تست را متوقف کند.
