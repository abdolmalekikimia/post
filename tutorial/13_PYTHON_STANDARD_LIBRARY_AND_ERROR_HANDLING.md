# 📚 Python Chapter 6: Standard Library Modules and Error Handling (Standard Library & Exception Handling)

Python has a motto: **"Batteries Included"** (it ships with a full set of features). In this chapter we look at which built-in Python modules this project uses, and why.

---

## 1. Advanced error handling and Exception Chaining (`raise ... from exc`)

One of the great features of Python 3 is **chaining errors** with the `from` keyword.

### Example in `utils/step_report.py`:
```python
try:
    result = action()
except Exception as exc:
    # record the failure in the report and mark the later steps
    report.failed(...)
    report.mark_remaining_not_executed()
    report.print()
    
    # raise the custom error while keeping the original cause (exc):
    raise FlowExecutionError(
        report.flow_name,
        step_name,
        exc,
        report,
    ) from exc
```

### Why is `from exc` important?
When a test crashes with a `FlowExecutionError`, Python writes in the error report (Traceback):
`The above exception was the direct cause of the following exception...`
and shows exactly that, for example, the original error was a `ConnectionResetError` on line 74 of some file.

---

## 2. The commonly used standard modules in this project

### 1. The `pathlib` module (modern file-path handling)
Instead of the old `os.path.join` approach:
```python
# from config/settings.py
from pathlib import Path

# get the exact path of the project root directory:
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# join paths with the slash operator (/):
env_file = PROJECT_ROOT / "config" / "test.env"
```

### 2. `time.monotonic()` vs `time.time()`
To measure how long an operation takes (Benchmarking):
```python
started_at = time.monotonic()
# do the operation...
duration = time.monotonic() - started_at
```
### Why `monotonic` instead of `time.time`?
The system clock (`time.time()`) can be moved backward or forward by the user or by internet time sync (NTP); `monotonic` is a clock in the CPU hardware that only ever moves forward and never goes negative.

### 3. The `datetime` module with a timezone (`timezone.utc`)
In modern Python, times should always be stored with a timezone (Timezone-aware):
```python
from datetime import datetime, timezone

# build the exact time in UTC with ISO format:
timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
# standard output: "2025-02-18T14:30:00Z"
```

### 4. The `enum` module and multiple inheritance with `str`
```python
from enum import Enum

class StepStatus(str, Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    NOT_EXECUTED = "NOT_EXECUTED"
```
### Why inherit from both `str` and `Enum`?
This technique (StrEnum) makes Enum values behave like a plain string (printable in JSON, storable in a database without a manual `status.value` conversion) and also type-safe (Type-safe).

### 5. The `json.JSONDecoder().raw_decode` module
In `clients/signalr_client.py`, to parse several JSON pieces stuck together:
```python
decoder = json.JSONDecoder()
frame, consumed = decoder.raw_decode(chunk)
# consumed shows how many characters were used up and keeps the rest of the string for the next object!
chunk = chunk[consumed:].lstrip()
```

### 6. The `statistics` module (statistics in stress tests)
In `utils/stress.py`, to compute the average response time:
```python
import statistics

avg_latency = statistics.fmean(values) if values else 0.0
```
> `fmean` is much faster than `mean` because it computes directly in floating point (C-level Float).
