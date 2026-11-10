# 🐍 Python Chapter 1: Basics, Data Types and Control Structures (Python Basics & Control Flow)

In this chapter you learn Python from the ground up, with real examples taken line by line from this project's code.

---

## 1. Basic data types in Python (Data Types)

In Python everything is an Object. The following data types are used repeatedly in this project:

### A) Strings (`str`) and common methods
In Python strings are immutable (Immutable).
```python
# example from clients/rest_client.py
self.base_url = base_url.rstrip("/")  # remove the extra slash from the end of the address

# example from utils/test_data.py
digits = "".join(character for character in configured_barcode if character.isdigit())
prefix = digits[:18].ljust(18, "0")   # pad zeros on the right up to a length of 18 digits
```

### B) Integers and floats (`int`, `float`)
```python
# safely convert a string from the environment to a number with a default value:
timeout_seconds: float = float(os.getenv("TIMEOUT_SECONDS", "10"))
inbound_timeout_ms: int = int(os.getenv("INBOUND_TIMEOUT_MS", "5000"))
```

### C) Collection data structures (`list`, `dict`, `set`, `tuple`)
| Structure | Trait | Example in the project |
|---|---|---|
| **List `[]`** | ordered, mutable, accepts duplicate members | `barcodes: list[str] = ["123", "456"]` |
| **Dict `{}`** | key-value pairs, extremely fast lookup $O(1)$ | `payload = {"deviceId": "demo", "timeoutMs": 5000}` |
| **Set `{}`** | unordered, unique values only, no duplicates | `{"1", "true", "yes", "on"}` (to check boolean values) |
| **Tuple `()`** | ordered, immutable (Immutable) | `excluded=(destination_code,)` |

---

## 2. Converting environment values to booleans (`bool`)

In `config/settings.py` this line of code is written:
```python
unique_run_data: bool = os.getenv("UNIQUE_RUN_DATA", "1").lower() in {"1", "true", "yes", "on"}
```
### Python analysis:
1. `os.getenv("UNIQUE_RUN_DATA", "1")`: reads the variable; if it is not set it returns the string `"1"`.
2. `.lower()`: converts the string to lower case so `"True"` and `"TRUE"` are the same.
3. `in {"1", "true", "yes", "on"}`: checks membership of the string in a `set`. Lookup in a `set` has $O(1)$ time complexity, the fastest possible.

---

## 3. Python's magic built-in functions (Built-in Functions)

### 1. The `enumerate(iterable, start=1)` function
When you want to loop over a list and also have the index number (row number):
```python
# from utils/step_report.py
for index, record in enumerate(self.records, start=1):
    print(f"{index:02d}. [{record.status}] {record.name}")
# output:
# 01. [PASS] Admin Login
# 02. [PASS] Connect WebSocket
```

### 2. The `any()` and `all()` functions
These functions work on a list of conditions:
- `any(...)`: returns True if **at least one** condition is True (like a logical OR).
- `all(...)`: returns True only when **all** conditions are True (like a logical AND).

```python
# from clients/signalr_client.py
# check whether at least one of the frames is an empty dictionary
if not any(frame == {} for frame in frames):
    raise RuntimeError(f"Unexpected SignalR handshake response: {frames}")
```

```python
# from utils/step_report.py
# check whether a sensitive word is in the field name
if any(secret in lowered_key for secret in ("password", "token", "authorization")):
    sanitized[key] = "<redacted>"
```

### 3. The `sum()` function with a Generator Expression
In Python, instead of writing a loop and a manual counter, you can use `sum` over a generator:
```python
# from utils/stress.py
# count the number of successful samples:
passed_count = sum(sample.passed for sample in self.samples)
```
> In Python, `True` equals the number `1` and `False` equals `0`, so `sum()` counts the True items!

---

## 4. Conditionals and compact forms

### One-line condition (Ternary Operator / Conditional Expression)
```python
# structure: <value if true> if <condition> else <value if false>
result = "PASS" if sample.passed else "FAIL"
```

### A `while` loop with a smart timeout (`Deadline`)
In `clients/signalr_client.py`, instead of a dangerous infinite loop, the Deadline pattern with `time.monotonic()` is used:
```python
deadline = time.monotonic() + self.timeout
while True:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Timed out waiting for response")
    
    # receive frames with the remaining time
    frames = self._receive_frames(timeout=remaining)
    ...
```
