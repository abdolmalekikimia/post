# 🏷️ Python Chapter 3: Typing and Modern Python Syntax (Type Hints & Modern Python)

Python is a dynamic language, but from version 3.5 on a powerful **Type Hinting** system was added. This project uses the latest Python standards (Python 3.10+ / 3.11+).

---

## 1. Why is Type Hinting vital in serious projects?

1. **Auto-Complete and IDE intelligence:** editors such as PyCharm or VS Code suggest exactly the methods and fields of each object.
2. **Fewer runtime bugs:** tools such as `mypy` find type mismatches before the code runs.
3. **Self-documenting code:** anyone reading the code knows what input to give and what output to expect.

---

## 2. The kinds of Type Hints used in the project

### A) Union types with the pipe operator `|` (Python 3.10 and later)
Instead of writing `Union[str, None]` or `Optional[str]`, modern Python uses the `|` sign:
```python
# a variable that is either a string or None:
token: str | None = None

# a variable that is either a string or a function:
Detail = object | Callable[[T], object]
```

### B) Generic list and dictionary types (Generic Types)
From Python 3.9 on there is no need to import `from typing import List, Dict`; you can use lower-case `list` and `dict` directly:
```python
barcodes: list[str]
last_exchange: dict[str, Any]
scenario_responses: dict[str, dict[str, dict[str, Any]]]
```

### C) The `Any` and `object` types
- `Any`: turns off type checking for a variable (when the data has no fixed structure, like JSON returned from the web).
- `object`: refers to any object in Python.

### D) Using `Callable` for function inputs
When a function receives another function as input (a Callback):
```python
from typing import Callable, TypeVar

T = TypeVar("T")

# a function that takes no input () and returns an output of type T:
def run_step(
    report: ExecutionReport,
    step_name: str,
    action: Callable[[], T],  # the input is a function!
) -> T:
    result = action()
    return result
```

### E) Generic types with `TypeVar`
In the code above, `T = TypeVar("T")` means the output of `run_step` has exactly the type that `action` returns (if action returns a dictionary, the output of run_step is also a dictionary).

---

## 3. The magic statement `from __future__ import annotations`

At the top of `utils/step_report.py`, `utils/stress.py` and `utils/test_data.py` this line exists:
```python
from __future__ import annotations
```

### What does this line do?
1. **Solves the Postponed Evaluation problem:** if inside a class method you want the return type to be the class itself:
   ```python
   class DeviceWebSocketClient:
       def __enter__(self) -> DeviceWebSocketClient:  # normally Python raises an error because the class is not fully defined yet!
           return self
   ```
   With `from __future__ import annotations`, Python stores all types as strings and raises no `NameError`.
2. **Better startup performance:** because Python does not evaluate the types immediately when the file loads.

---

## 4. The immutable dictionary object (`MappingProxyType`)

In `clients/signalr_client.py` it is written:
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

### Why was a regular dictionary not used?
In Python a regular dictionary `{}` is always Mutable. So if someone writes in a test:
`TARGET_BY_MESSAGE_TYPE["auth"] = "FakeAuth"`, the whole project breaks!
With `MappingProxyType`, this dictionary becomes Read-Only and any attempt to modify it stops at once with a `TypeError`.
