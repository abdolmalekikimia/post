# 🧱 فصل ۲ پایتون: شی‌گرایی پیشرفته و Dataclasses (OOP & Modern Classes)

شی‌گرایی (Object-Oriented Programming) در پایتون بسیار منعطف و قدرتمند است. در این فصل، ساختار کلاس‌ها، ارث‌بری، دکوراتورهای متد و نحوه استفاده حرفه‌ای از `dataclasses` را با هم یاد می‌گیریم.

---

## ۱. ساختار یک کلاس استاندارد در پایتون

```python
class RestClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        if timeout <= 0:
            raise ValueError("HTTP timeout must be greater than zero")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.last_exchange: dict[str, Any] = {}
```
### نکات مهم:
- `__init__`: تابع سازنده (Constructor) شیء است که هنگام ساختن نمونه جدید صدا زده می‌شود.
- `self`: اشاره به نمونه جاری شیء در حافظه دارد (معادل `this` در جاوا، C# یا جاوااسکریپت).
- `self.base_url`: یک ویژگی نمونه (Instance Attribute) می‌سازد.

---

## ۲. تفاوت متدهای معمولی، `@staticmethod` و `@classmethod`

در پایتون ۳ مدل متد در کلاس داریم:

```python
class DeviceWebSocketClient:
    RECORD_SEPARATOR = "\x1e"  # متغیر کلاسی (Class Attribute)

    # ۱. متد معمولی (نیاز به نمونه شیء و دسترسی به self دارد)
    def connect(self) -> dict[str, Any]:
        self._socket = create_connection(self.ws_url)

    # ۲. متد کلاسی (دسترسی به خود کلاس با cls دارد نه نمونه)
    @classmethod
    def _decode_frames(cls, raw_response: str) -> list[dict[str, Any]]:
        # دسترسی به متغیر کلاسی با cls.RECORD_SEPARATOR
        for chunk in raw_response.split(cls.RECORD_SEPARATOR):
            ...

    # ۳. متد استاتیک (تابع مستقلی که نه به self و نه به cls دسترسی ندارد)
    @staticmethod
    def _authorization_headers(token: str | None) -> dict[str, str]:
        if token is None:
            return {}
        return {"Authorization": f"Bearer {token}"}
```

---

## ۳. دکوراتور `@property` (ویژگی‌های محاسباتی)

وقتی می‌خواهید یک متد رفتاری مثل یک متغیر داشته باشد (بدون نیاز به پرانتز `()` هنگام صدا زدن)، از `@property` استفاده می‌کنید:

```python
# از utils/stress.py
@dataclass
class StressSummary:
    samples: list[StressSample] = field(default_factory=list)

    @property
    def total_requests(self) -> int:
        return len(self.samples)

    @property
    def passed_expected_responses(self) -> int:
        return sum(sample.passed for sample in self.samples)
```

### نحوه استفاده:
```python
summary = StressSummary(...)
# به جای summary.total_requests() می‌نویسیم:
print(summary.total_requests)
```
این کار خوانایی کد را به شدت افزایش می‌دهد.

---

## ۴. جادوی `dataclasses` در پایتون مدرن

قبل از پایتون ۳.۷ برای ساختن کلاسی که فقط داده نگه می‌دارد، باید کد زیادی می‌نوشتیم (`__init__`, `__repr__`, `__eq__`). با ماژول `dataclasses` پایتون همه این‌ها را خودکار می‌سازد!

### الف) ساخت کلاس داده ساده (`@dataclass`)
```python
# از utils/step_report.py
@dataclass
class StepRecord:
    name: str
    status: StepStatus = StepStatus.PENDING
    duration_seconds: float = 0.0
    message: str = ""
    error: str = ""
```
پایتون به طور خودکار توابع زیر را برای شما می‌سازد:
- `__init__(self, name, status=..., duration_seconds=..., message=..., error=...)`
- `__repr__(self)`: برای چاپ تمیز شیء در ترمینال یا لاگ
- `__eq__(self, other)`: برای مقایسه دو شیء بر اساس مقادیر فیلدهایشان

### ب) ساخت اشیاء تخریب‌ناپذیر با `@dataclass(frozen=True)`
اگر می‌خواهید فیلدهای کلاس بعد از مقداردهی اولیه به هیچ وجه قابل تغییر نباشند (Immutable)، از `frozen=True` استفاده کنید:
```python
@dataclass(frozen=True)
class Settings:
    base_url: str = "https://api.example.invalid"
    device_id: str = "demo-device"

s = Settings()
# اگر این کار را بکنید پایتون FrozenInstanceError پرتاب می‌کند:
# s.base_url = "https://hack.com"  <-- خطا!
```

### ج) مقدار پیش‌فرض متغیر با `field(default_factory=...)`
در پایتون قرار دادن لیست یا دیکشنری خالی به عنوان مقدار پیش‌فرض در آرگومان تابع یا فیلد کلاس اشتباه است (چون بین تمام نمونه‌ها به اشتراک گذاشته می‌شود). راه درست استفاده از `default_factory` است:
```python
@dataclass
class ExecutionReport:
    flow_name: str
    # هر نمونه جدید یک لیست تازه می‌گیرد:
    records: list[StepRecord] = field(default_factory=list)
```

### د) متد ویژه `__post_init__`
این متد بلافاصله بعد از `__init__` خودکار dataclass اجرا می‌شود و بهترین جا برای اعتبارسنجی مقادیر ورودی یا محاسبات اولیه است:
```python
@dataclass(frozen=True)
class Settings:
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("TIMEOUT_SECONDS must be greater than zero")
        
        # برای تغییر دادن فیلد در یک frozen dataclass باید از object.__setattr__ استفاده شود:
        # object.__setattr__(self, "some_field", some_value)
```

---

## ۵. ارث‌بری (Inheritance) و کلاس‌های خطای اختصاصی

در پایتون می‌توانید از کلاس‌های موجود ارث‌بری کنید تا رفتار آن‌ها را شخصی‌سازی کنید.

```python
# از utils/step_report.py
class FlowExecutionError(AssertionError):
    """یک استثنای سفارشی که از AssertionError ارث‌بری کرده است"""
    def __init__(
        self,
        flow_name: str,
        failed_step: str,
        cause: Exception,
        report: ExecutionReport,
    ) -> None:
        self.flow_name = flow_name
        self.failed_step = failed_step
        self.cause = cause
        self.report = report
        # فراخوانی سازنده کلاس والد (super)
        super().__init__(
            f"{flow_name} stopped at '{failed_step}': "
            f"{type(cause).__name__}: {cause}"
        )
```
### مزیت این کار:
چون این کلاس فرزند `AssertionError` است، Pytest آن را به عنوان شکست تست شناسایی می‌کند، ولی در عین حال شیء `report` و گام متوقف شده را در خود دارد!
