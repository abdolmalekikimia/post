# 📚 فصل ۶ پایتون: ماژول‌های کتابخانه استاندارد و مدیریت خطاها (Standard Library & Exception Handling)

پایتون شعاری دارد: **"Batteries Included"** (یعنی همراه با باتری/امکانات کامل عرضه می‌شود). در این فصل بررسی می‌کنیم که کدام ماژول‌های داخلی پایتون در این پروژه استفاده شده‌اند و چرا.

---

## ۱. مدیریت پیشرفته خطاها و Exception Chaining (`raise ... from exc`)

یکی از امکانات فوق‌العاده پایتون ۳، امکان **زنجیره‌سازی خطاها** با عبارت `from` است.

### مثال در `utils/step_report.py`:
```python
try:
    result = action()
except Exception as exc:
    # ثبت شکست در گزارش و علامت‌گذاری گام‌های بعدی
    report.failed(...)
    report.mark_remaining_not_executed()
    report.print()
    
    # پرتاب خطای اختصاصی با حفظ منشأ اصلی خطا (exc):
    raise FlowExecutionError(
        report.flow_name,
        step_name,
        exc,
        report,
    ) from exc
```

### چرا `from exc` مهم است؟
وقتی تست با خطای `FlowExecutionError` کرش می‌کند، پایتون در گزارش خطا (Traceback) می‌نویسد:
`The above exception was the direct cause of the following exception...`
و دقیقاً نشان می‌دهد که مثلاً خطای اصلی یک `ConnectionResetError` در خط ۷۴ فلان فایل بوده است.

---

## ۲. بررسی ماژول‌های استاندارد پرکاربرد در این پروژه

### ۱. ماژول `pathlib` (مدیریت مدرن مسیر فایل‌ها)
به جای استفاده از روش‌های قدیمی `os.path.join`:
```python
# از config/settings.py
from pathlib import Path

# گرفتن مسیر دقیق دایرکتوری ریشه پروژه:
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# اتصال مسیرها با عملگر اسلش (/):
env_file = PROJECT_ROOT / "config" / "test.env"
```

### ۲. ماژول `time.monotonic()` در برابر `time.time()`
برای اندازه‌گیری مدت‌زمان اجرای یک عملیات (Benchmarking):
```python
started_at = time.monotonic()
# انجام عملیات...
duration = time.monotonic() - started_at
```
### چرا `monotonic` به جای `time.time`؟
ساعت سیستم (`time.time()`) ممکن است توسط کاربر یا همگام‌سازی ساعت اینترنتی (NTP) به عقب یا جلو کشیده شود؛ اما `monotonic` ساعتی است که در CPU سخت‌افزار همیشه فقط رو به جلو می‌رود و هرگز منفی نمی‌شود.

### ۳. ماژول `datetime` با منطقه زمانی (`timezone.utc`)
در پایتون مدرن، همیشه باید زمان‌ها را با منطقه زمانی (Timezone-aware) ذخیره کرد:
```python
from datetime import datetime, timezone

# ساخت زمان دقیق به وقت گرینویچ با فرمت ISO:
timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
# خروجی استاندارد: "2025-02-18T14:30:00Z"
```

### ۴. ماژول `enum` و ارث‌بری چندگانه با `str`
```python
from enum import Enum

class StepStatus(str, Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    NOT_EXECUTED = "NOT_EXECUTED"
```
### چرا هم از `str` و هم از `Enum` ارث‌بری شده؟
این تکنیک (StrEnum) باعث می‌شود مقادیر Enum هم مثل یک رشته مستقیم رفتار کنند (قابل چاپ در JSON، ذخیره در دیتابیس بدون تبدیل دستی `status.value`) و هم تایپ‌سیف (Type-safe) باشند.

### ۵. ماژول `json.JSONDecoder().raw_decode`
در `clients/signalr_client.py` برای پارس کردن چندین تکه JSON چسبیده به هم:
```python
decoder = json.JSONDecoder()
frame, consumed = decoder.raw_decode(chunk)
# consumed نشان می‌دهد چند کاراکتر مصرف شده و بقیه رشته را برای آبجکت بعدی نگه می‌دارد!
chunk = chunk[consumed:].lstrip()
```

### ۶. ماژول `statistics` (محاسبات آماری در تست‌های استرس)
در `utils/stress.py` برای محاسبه میانگین زمان پاسخ:
```python
import statistics

avg_latency = statistics.fmean(values) if values else 0.0
```
> تابع `fmean` در مقایسه با `mean` بسیار سریع‌تر است چون محاسبات را مستقیماً در قالب ممیز شناور (C-level Float) انجام می‌دهد.
