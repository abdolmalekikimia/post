# 🪄 Python Chapter 5: Dunder Methods and Context Management (Dunder Methods & Context Managers)

Methods whose names start and end with two underscores (`__`) are called **Dunder Methods** (short for Double Underscore) or **Magic Methods** in Python. They define how objects behave in special situations of the language.

---

## 1. The dunder methods `__enter__` and `__exit__` (Context Manager)

Have you ever seen the `with` statement used to work with files?
```python
with open("file.txt", "w") as f:
    f.write("hello")
```
Behind the scenes Python calls `__enter__` at the start of the block and `__exit__` at the end of the block (even if an error occurs).

### The Context Manager implementation in `clients/rest_client.py`:
```python
class RestClient:
    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "RestClient":
        # runs when we enter the with block:
        return self

    def __exit__(self, *_: object) -> None:
        # runs when we leave the with block (or crash):
        self.close()
```

### The implementation in `clients/signalr_client.py`:
```python
class DeviceWebSocketClient:
    def __enter__(self) -> "DeviceWebSocketClient":
        self.connect()  # connect automatically on entry
        return self

    def __exit__(self, *_: object) -> None:
        self.close()    # close the socket for certain on exit
```

### Main benefit:
A network connection or port is never left open in memory, and later tests never run out of sockets or hit a busy port!

---

## 2. The dunder methods `__repr__` and `__str__`

When you `print()` an object or type it in an interactive shell:
- Python looks for `__str__` (a readable display for the user).
- If it is missing, it looks for `__repr__` (an exact display of the object for the programmer and for debugging).

```python
class StepRecord:
    def __str__(self) -> str:
        return f"Step({self.name}, status={self.status})"
```
> In classes with the `@dataclass` decorator, Python automatically builds a complete, high-quality `__repr__` that includes all the fields.

---

## 3. How `try ... finally` works compared to a Context Manager

Where we do not want to, or cannot, use `with`, a `try ... finally` block does exactly the same resource-cleanup job:

```python
# from flows/device_lifecycle/device_auth_flow.py
ws = DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds)
try:
    # 1. connect to the socket
    # 2. authenticate
    # 3. register the barcode
    # 4. run the dependent scenarios
finally:
    # this part runs in every case (even if the test fails or an error is raised)
    ws.close()
```
