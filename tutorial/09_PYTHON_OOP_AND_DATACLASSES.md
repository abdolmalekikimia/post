# 🧱 Python Chapter 2: Advanced OOP and Dataclasses (OOP & Modern Classes)

Object-Oriented Programming is very flexible and powerful in Python. In this chapter we learn class structure, inheritance, method decorators and the professional use of `dataclasses`.

---

## 1. Structure of a standard class in Python

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
### Important notes:
- `__init__`: the object's constructor (Constructor), called when a new instance is created.
- `self`: refers to the current instance of the object in memory (equivalent to `this` in Java, C# or JavaScript).
- `self.base_url`: creates an Instance Attribute.

---

## 2. Regular methods vs `@staticmethod` vs `@classmethod`

In Python there are 3 kinds of methods in a class:

```python
class DeviceWebSocketClient:
    RECORD_SEPARATOR = "\x1e"  # Class Attribute

    # 1. regular method (needs an instance and has access to self)
    def connect(self) -> dict[str, Any]:
        self._socket = create_connection(self.ws_url)

    # 2. class method (has access to the class itself through cls, not to the instance)
    @classmethod
    def _decode_frames(cls, raw_response: str) -> list[dict[str, Any]]:
        # access the class attribute with cls.RECORD_SEPARATOR
        for chunk in raw_response.split(cls.RECORD_SEPARATOR):
            ...

    # 3. static method (an independent function with access to neither self nor cls)
    @staticmethod
    def _authorization_headers(token: str | None) -> dict[str, str]:
        if token is None:
            return {}
        return {"Authorization": f"Bearer {token}"}
```

---

## 3. The `@property` decorator (computed attributes)

When you want a method to behave like a variable (no parentheses `()` when calling it), use `@property`:

```python
# from utils/stress.py
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

### How to use it:
```python
summary = StressSummary(...)
# instead of summary.total_requests() we write:
print(summary.total_requests)
```
This greatly improves code readability.

---

## 4. The magic of `dataclasses` in modern Python

Before Python 3.7, building a class that only holds data took a lot of code (`__init__`, `__repr__`, `__eq__`). With the `dataclasses` module, Python generates all of these automatically!

### A) A simple data class (`@dataclass`)
```python
# from utils/step_report.py
@dataclass
class StepRecord:
    name: str
    status: StepStatus = StepStatus.PENDING
    duration_seconds: float = 0.0
    message: str = ""
    error: str = ""
```
Python automatically builds these functions for you:
- `__init__(self, name, status=..., duration_seconds=..., message=..., error=...)`
- `__repr__(self)`: for clean printing of the object in a terminal or log
- `__eq__(self, other)`: to compare two objects by the values of their fields

### B) Immutable objects with `@dataclass(frozen=True)`
If you want the class fields to be impossible to change after initialization (Immutable), use `frozen=True`:
```python
@dataclass(frozen=True)
class Settings:
    base_url: str = "https://api.example.invalid"
    device_id: str = "demo-device"

s = Settings()
# if you do this, Python raises FrozenInstanceError:
# s.base_url = "https://hack.com"  <-- error!
```

### C) A default value with `field(default_factory=...)`
In Python, putting an empty list or dictionary as the default value of a function argument or class field is wrong (because it is shared between all instances). The right way is `default_factory`:
```python
@dataclass
class ExecutionReport:
    flow_name: str
    # every new instance gets a fresh list:
    records: list[StepRecord] = field(default_factory=list)
```

### D) The special `__post_init__` method
This method runs right after the dataclass's automatic `__init__` and is the best place to validate input values or do initial calculations:
```python
@dataclass(frozen=True)
class Settings:
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("TIMEOUT_SECONDS must be greater than zero")
        
        # to change a field in a frozen dataclass you must use object.__setattr__:
        # object.__setattr__(self, "some_field", some_value)
```

---

## 5. Inheritance and custom error classes

In Python you can inherit from existing classes to customize their behavior.

```python
# from utils/step_report.py
class FlowExecutionError(AssertionError):
    """A custom exception that inherits from AssertionError"""
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
        # call the parent class constructor (super)
        super().__init__(
            f"{flow_name} stopped at '{failed_step}': "
            f"{type(cause).__name__}: {cause}"
        )
```
### Benefit:
Because this class is a child of `AssertionError`, Pytest recognizes it as a test failure, yet it also carries the `report` object and the step that stopped!
