# 🎯 Python Chapter 4: Functional Tricks, Comprehensions and Idioms (Functional & Idioms)

Python is known for clean, readable and short code, called **Pythonic Code**. In this chapter we meet the practical, frequently used Python tricks in this project.

---

## 1. Lambda functions (`lambda`) and First-Class Functions

In Python, functions can be passed to other functions like a variable.

### Example in `flows/device_lifecycle/device_auth_flow.py`:
```python
admin_token = run_step(
    report,
    "1. [BASE] Admin Login - POST /api/admin/login",
    lambda: admin.login(run_settings.admin_username, run_settings.admin_password),
    detail=lambda _: exchange_detail(rest_client.last_exchange),
)
```
### Why was `lambda` used?
If we wrote `admin.login(...)` directly, the function would run immediately on that line! By putting `lambda:` in front, we **wrapped the function** so that `run_step` runs it at the right time and measures its run time.

---

## 2. A deep look at Comprehensions in Python

In Python, building a list, dictionary or set with a traditional `for` loop is long. Instead we use a Comprehension:

### A) List Comprehension (building a list in one line)
```python
# from utils/step_report.py
# build a list of StepRecord objects, one for each step name:
self.records.extend(StepRecord(name=name) for name in step_names)

# extract the latency of all stress samples:
latencies = [sample.latency_seconds for sample in self.samples]
```

### B) Dict Comprehension (building a dictionary in one line)
```python
# from services/device_service.py
# remove keys whose value is None:
optional_values = {"barcode": barcode, "chuteId": chute_id}
cleaned_dict = {key: value for key, value in optional_values.items() if value is not None}
```
This line of code neatly filters out all `None` values so the request body stays clean.

### C) Set Comprehension (building a set of unique values)
```python
# from tests/success/test_base_success.py
# convert dictionary keys to a set for easy comparison:
assert set(result.scenario_responses["Destination Update"]) == {"TC-01", "TC-02", "TC-03", "TC-04"}
```

---

## 3. Unpacking operators (`*` and `**`)

### A) The single star `*` (Positional Unpacking)
1. **In a function signature (accepting any number of arguments):**
```python
# in ExecutionReport
def register(self, *step_names: str) -> None:
    # step_names becomes a tuple of all the inputs
```
2. **When calling a function (spreading the members of a list):**
```python
report.register(
    "1. Step One",
    "2. Step Two",
    *success_step_names(6),  # the list of later steps is unpacked and passed one by one!
)
```

### B) The double star `**` (Keyword Unpacking)
To merge dictionaries or pass a dictionary as named parameters of a function:
```python
# merge two dictionaries:
exchange = {**nested_exchange, **detail}

# pass values as keyword arguments:
error_detail = {"error": str(exc), **exchange_detail(ws.last_exchange)}
```

---

## 4. Advanced F-String tricks (Formatting)

String formatting in Python 3.6 and later is done with `f"..."`:

```python
# 1. a two-digit number padded with zeros on the left (:02d or :03d)
index = 5
print(f"{index:02d}")  # output: "05"
print(f"{index:03d}")  # output: "005"

# 2. a float with 3 digits after the decimal point (:.3f)
latency = 0.045678
print(f"{latency:.3f}s")  # output: "0.046s"

# 3. show the value using the object's repr with the !r sign
value = "hello"
print(f"actual={value!r}")  # output: actual='hello' (with quotes)
```
