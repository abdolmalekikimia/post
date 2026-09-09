# 🎓 راهنمای جامع یادگیری پایتون و معماری پروژه تست اتوماسیون

این مستندات آموزشی برای این آماده شده است تا هر زمان فرصت کردید، بتوانید پایتون را به صورت **پروژه‌محور و از پایه تا پیشرفته** از روی همین پروژه یاد بگیرید و همزمان با ساختار معماری و الگوهای طراحی حرفه‌ای آشنا شوید.

---

## 🧭 دو مسیر یادگیری (Learning Tracks)

برای مطالعه، دو بخش تفکیک‌شده در اختیارتان است:
1. **مسیر ۱: یادگیری زبان پایتون (Python Mastery)** — اگر می‌خواهید سینتکس، شی‌گرایی، ترفندها و امکانات پیشرفته پایتون را یاد بگیرید.
2. **مسیر ۲: معماری و متدولوژی تست (Architecture & QA)** — اگر می‌خواهید ساختار لایه‌ها، پروتکل‌های شبکه و پیاده‌سازی تست‌ها را بررسی کنید.

---

## 🐍 مسیر ۱: یادگیری زبان پایتون (پروژه‌محور و عمیق)

| فصل | فایل | موضوعات آموزش داده شده در پایتون |
|---|---|---|
| **فصل ۱** | [`08_PYTHON_BASICS_AND_CONTROL_FLOW.md`](08_PYTHON_BASICS_AND_CONTROL_FLOW.md) | **مبانی و ساختارهای کنترلی:** متغیرها، رشته‌ها و برش آن‌ها، تبدیل‌های ایمن به `bool` و `int`، توابع داخلی `enumerate`، `any`، `all`، `sum`، عملگرهای سه‌تایی و حلقه‌ها |
| **فصل ۲** | [`09_PYTHON_OOP_AND_DATACLASSES.md`](09_PYTHON_OOP_AND_DATACLASSES.md) | **شی‌گرایی و کلاس‌ها:** سازنده `__init__`، تفاوت `@staticmethod` و `@classmethod`، دکوراتور `@property`، کلاس‌های داده (`@dataclass`)، اشیاء تخریب‌ناپذیر با `frozen=True`، `field(default_factory=...)` و متد جادویی `__post_init__` |
| **فصل ۳** | [`10_PYTHON_TYPE_HINTING_AND_MODERN_SYNTAX.md`](10_PYTHON_TYPE_HINTING_AND_MODERN_SYNTAX.md) | **سیستم تایپینگ در پایتون مدرن:** استفاده از پایپ `|` برای Union، ماژول `typing` (`Callable`, `TypeVar`, `Any`)، دیکشنری غیرقابل تغییر `MappingProxyType` و دستور `from __future__ import annotations` |
| **فصل ۴** | [`11_PYTHON_FUNCTIONAL_TRICKS_AND_IDIOMS.md`](11_PYTHON_FUNCTIONAL_TRICKS_AND_IDIOMS.md) | **ترفندهای تابعی و کدهای پایتونیک:** توابع لامبدا (`lambda`)، ساختارهای تک‌خطی (List, Dict, Set Comprehensions)، باز کردن بسته‌ها با `*args` و `**kwargs` و قالب‌بندی F-Strings |
| **فصل ۵** | [`12_PYTHON_DUNDER_METHODS_AND_CONTEXT_MANAGERS.md`](12_PYTHON_DUNDER_METHODS_AND_CONTEXT_MANAGERS.md) | **متدهای داندر و مدیریت منابع:** نحوه کار دستور `with` با متدهای `__enter__` و `__exit__`، تفاوت `__str__` و `__repr__` و مدیریت تمیز سوکت‌ها |
| **فصل ۶** | [`13_PYTHON_STANDARD_LIBRARY_AND_ERROR_HANDLING.md`](13_PYTHON_STANDARD_LIBRARY_AND_ERROR_HANDLING.md) | **کتابخانه استاندارد و مدیریت خطاها:** زنجیره‌سازی خطاها با `raise ... from exc`، ماژول‌های `pathlib`، `datetime` و تایم‌زون UTC، `time.monotonic`، `enum.Enum`، پارس تکه‌ای JSON با `raw_decode` و ماژول `statistics` |

---

## 🏛️ مسیر ۲: معماری و تکنیک‌های تست اتوماسیون (SDET Framework)

| شماره | فایل | موضوعات معماری و تست |
|---|---|---|
| **فصل ۷** | [`01_ARCHITECTURE_AND_DESIGN_PATTERNS.md`](01_ARCHITECTURE_AND_DESIGN_PATTERNS.md) | **معماری ۶ لایه‌ای و الگوهای طراحی:** معماری `Test → Flow → Service → Client → Assertion → Reporting` و الگوهای Facade, Adapter, Step Runner |
| **فصل ۸** | [`02_CLIENTS_AND_PROTOCOLS.md`](02_CLIENTS_AND_PROTOCOLS.md) | **کلاینت‌ها و پروتکل‌های شبکه:** کار با Session در HTTP و پیاده‌سازی عمیق پروتکل **SignalR Hub** بر بستر WebSocket (بایت `0x1E`، Handshake، InvocationId، تفکیک فریم‌ها و پینگ‌ها) |
| **فصل ۹** | [`03_FLOWS_AND_ORCHESTRATION.md`](03_FLOWS_AND_ORCHESTRATION.md) | **مدیریت سناریوهای E2E (Flows):** هماهنگی چند سرویس متوالی در یک سناریو، جریان‌های مثبت (Happy Path) و جریان‌های منفی (Negative Cases) |
| **فصل ۱۰** | [`04_ASSERTIONS_AND_CONTRACT_TESTING.md`](04_ASSERTIONS_AND_CONTRACT_TESTING.md) | **تست قرارداد و اعتبارسنجی‌ها:** اعتبارسنجی ساختار داده‌ها، استخراج فیلدها و تفکیک خطای سیستمی از خطای بیزنسی |
| **فصل ۱۱** | [`05_STEP_REPORTING_AND_OBSERVABILITY.md`](05_STEP_REPORTING_AND_OBSERVABILITY.md) | **سیستم گزارش‌دهی مرحله‌ای (Step Reporter):** نحوه ساخت گزارش‌های خوانا، ماسک کردن خودکار پسوردها و توکن‌ها (Redaction) و ایزولاسیون مراحل با `run_step` |
| **فصل ۱۲** | [`06_CONFIG_AND_TEST_DATA_MANAGEMENT.md`](06_CONFIG_AND_TEST_DATA_MANAGEMENT.md) | **تنظیمات و داده‌های تست:** استفاده از متغیرهای محیطی و توابع تولید بارکد و داده‌های تصادفی یکتا برای جلوگیری از تداخل |
| **فصل ۱۳** | [`07_PYTEST_STRATEGY_AND_CI_CD.md`](07_PYTEST_STRATEGY_AND_CI_CD.md) | **استراتژی Pytest و تست‌های Stress:** فیلتر تست‌ها با مارکرها، سناریوهای شرایط رقابتی (Race Condition) و همزمانی، و استراتژی اجرای امن در CI/CD |

---

> 💡 **چگونه مطالعه کنیم؟**
> می‌توانید ابتدا از **مسیر ۱ (فصل‌های ۱ تا ۶)** شروع کنید تا به تمام سینتکس‌ها و امکانات پایتون مسلط شوید، سپس به سراغ **مسیر ۲ (فصل‌های ۷ تا ۱۳)** بروید تا ببینید این قابلیت‌ها چطور در کنار هم یک سیستم اتوماسیون تست پیشرفته را تشکیل داده‌اند.
