# 🏷️ فصل ۳ پایتون: سیستم تایپینگ و سینتکس پایتون مدرن (Type Hints & Modern Python)

پایتون زبانی داینامیک است، اما از نسخه ۳.۵ به بعد سیستم قدرتمند **Type Hinting** به آن اضافه شد. در این پروژه از جدیدترین استانداردهای پایتون (Python 3.10+ / 3.11+) استفاده شده است.

---

## ۱. چرا Type Hinting در پروژه‌های جدی حیاتی است؟

1. **Auto-Complete و هوشمندی IDE:** ویرایشگرهایی مثل PyCharm یا VS Code دقیقاً متدها و فیلدهای هر شیء را به شما پیشنهاد می‌دهند.
2. **کاهش خطاهای زمان اجرا (Runtime Bugs):** ابزارهایی مثل `mypy` قبل از اجرای کد، مغایرت تایپ‌ها را پیدا می‌کنند.
3. **مستندسازی زنده (Self-Documenting Code):** هر کس کد را بخواند می‌داند چه ورودی باید بدهد و چه خروجی دریافت خواهد کرد.

---

## ۲. بررسی انواع Type Hint های استفاده شده در پروژه

### الف) تایپ‌های ترکیبی با عملگر پایپ `|` (Union در پایتون ۳.۱۰ به بعد)
به جای نوشتن `Union[str, None]` یا `Optional[str]`، در پایتون مدرن از علامت `|` استفاده می‌شود:
```python
# متغیری که یا رشته است یا None:
token: str | None = None

# متغیری که یا رشته است یا تابع:
Detail = object | Callable[[T], object]
```

### ب) تایپ‌های جنریک لیست و دیکشنری (Generic Types)
از پایتون ۳.۹ به بعد نیازی به ایمپورت `from typing import List, Dict` نیست و می‌توان مستقیماً از حروف کوچک `list` و `dict` استفاده کرد:
```python
barcodes: list[str]
last_exchange: dict[str, Any]
scenario_responses: dict[str, dict[str, dict[str, Any]]]
```

### ج) نوع `Any` و `object`
- `Any`: خاموش کردن بررسی تایپ برای یک متغیر (وقتی داده ساختار مشخصی ندارد مثل JSON بازگشتی از وب).
- `object`: اشاره به هر شیء در پایتون.

### د) استفاده از `Callable` برای توابع ورودی
وقتی یک تابع، تابعی دیگر را به عنوان ورودی دریافت می‌کند (Callback):
```python
from typing import Callable, TypeVar

T = TypeVar("T")

# تابعی که هیچ ورودی نمی‌گیرد () و خروجی از نوع T برمی‌گرداند:
def run_step(
    report: ExecutionReport,
    step_name: str,
    action: Callable[[], T],  # ورودی یک تابع است!
) -> T:
    result = action()
    return result
```

### ه) تایپ‌های جنریک با `TypeVar`
در کد بالا `T = TypeVar("T")` یعنی خروجی تابع `run_step` دقیقاً همان نوعی خواهد بود که خروجی `action` است (اگر action یک دیکشنری برگرداند، خروجی run_step هم دیکشنری خواهد بود).

---

## ۳. دستور جادویی `from __future__ import annotations`

در ابتدای فایل‌های `utils/step_report.py`, `utils/stress.py` و `utils/test_data.py` این خط وجود دارد:
```python
from __future__ import annotations
```

### این خط چه کار می‌کند؟
1. **حل مشکل Postponed Evaluation:** اگر داخل متد یک کلاس بخواهید تایپ بازگشتی را خود همان کلاس بگذارید:
   ```python
   class DeviceWebSocketClient:
       def __enter__(self) -> DeviceWebSocketClient:  # در حالت عادی پایتون خطا می‌دهد چون هنوز کلاس کامل تعریف نشده!
           return self
   ```
   با اضافه کردن `from __future__ import annotations`، پایتون تمام تایپ‌ها را به صورت رشته ذخیره می‌کند و خطای `NameError` نمی‌دهد.
2. **بهبود سرعت اجرای برنامه (Performance):** چون پایتون زمان لود شدن فایل، تایپ‌ها را بلافاصله ارزیابی نمی‌کند.

---

## ۴. شیء دیکشنری غیرقابل تغییر (`MappingProxyType`)

در فایل `clients/signalr_client.py` نوشته شده:
```python
from types import MappingProxyType

TARGET_BY_MESSAGE_TYPE = MappingProxyType(
    {
        "auth": "Auth",
        "item.register": "RegisterItem",
        "route.assign": "AssignRoute",
        "container.close": "CloseContainer",
    }
)
```

### چرا از دیکشنری معمولی استفاده نشده؟
در پایتون دیکشنری معمولی `{}` همیشه قابل تغییر (Mutable) است. یعنی اگر کسی در تستی بنویسد:
`TARGET_BY_MESSAGE_TYPE["auth"] = "FakeAuth"`، کل پروژه خراب می‌شود!
اما با `MappingProxyType`، این دیکشنری فقط خواندنی (Read-Only) می‌شود و هر تلاشی برای دستکاری آن بلافاصله با `TypeError` متوقف خواهد شد.
