# 🐍 فصل ۱ پایتون: مبانی، انواع داده و ساختارهای کنترلی (Python Basics & Control Flow)

در این فصل، پایتون را از پایه با مثال‌های واقعی برگرفته از خط به خط کدهای همین پروژه یاد می‌گیرید.

---

## ۱. انواع داده‌های پایه در پایتون (Data Types)

در پایتون، همه‌چیز یک شیء (Object) است. در این پروژه انواع داده‌های زیر مکرراً استفاده شده‌اند:

### الف) رشته‌ها (`str`) و متدهای پرکاربرد
در پایتون رشته‌ها غیرقابل تغییر (Immutable) هستند.
```python
# مثال از clients/rest_client.py
self.base_url = base_url.rstrip("/")  # حذف اسلش اضافه از انتهای آدرس

# مثال از utils/test_data.py
digits = "".join(character for character in configured_barcode if character.isdigit())
prefix = digits[:18].ljust(18, "0")   # اضافه کردن صفر به سمت راست تا طول ۱۸ رقم شود
```

### ب) اعداد صحیح و اعشاری (`int`, `float`)
```python
# تبدیل ایمن رشته دریافتی از محیط به عدد با مقدار پیش‌فرض:
timeout_seconds: float = float(os.getenv("TIMEOUT_SECONDS", "10"))
inbound_timeout_ms: int = int(os.getenv("INBOUND_TIMEOUT_MS", "5000"))
```

### ج) ساختارهای داده مجموعه‌ای (`list`, `dict`, `set`, `tuple`)
| ساختار | ویژگی | مثال در پروژه |
|---|---|---|
| **List `[]`** | مرتب، قابل تغییر، پذیرنده عضو تکراری | `barcodes: list[str] = ["123", "456"]` |
| **Dict `{}`** | جفت کلید-مقدار، جستجوی فوق‌العاده سریع $O(1)$ | `payload = {"deviceId": "demo", "timeoutMs": 5000}` |
| **Set `{}`** | بدون ترتیب، فقط مقادیر یکتا، بدون تکرار | `{"1", "true", "yes", "on"}` (برای بررسی مقادیر بولی) |
| **Tuple `()`** | مرتب، غیرقابل تغییر (Immutable) | `excluded=(destination_code,)` |

---

## ۲. تکنیک تبدیل مقادیر محیطی به بولی (`bool`)

در فایل `config/settings.py` این خط کد نوشته شده است:
```python
unique_run_data: bool = os.getenv("UNIQUE_RUN_DATA", "1").lower() in {"1", "true", "yes", "on"}
```
### تحلیل پایتونی:
1. `os.getenv("UNIQUE_RUN_DATA", "1")`: متغیر را می‌خواند؛ اگر ست نشده بود رشته `"1"` را برمی‌گرداند.
2. `.lower()`: رشته را به حروف کوچک تبدیل می‌کند تا `"True"` و `"TRUE"` هر دو یکسان شوند.
3. `in {"1", "true", "yes", "on"}`: عضویت رشته را در یک `set` چک می‌کند. جستجو در `set` با پیچیدگی زمانی $O(1)$ انجام می‌شود که سریع‌ترین حالت ممکن است.

---

## ۳. توابع داخلی جادویی پایتون (Built-in Functions)

### ۱. تابع `enumerate(iterable, start=1)`
زمانی که می‌خواهید روی یک لیست حلقه بزنید و همزمان شماره اندیس (شماره ردیف) را داشته باشید:
```python
# از utils/step_report.py
for index, record in enumerate(self.records, start=1):
    print(f"{index:02d}. [{record.status}] {record.name}")
# خروجی:
# 01. [PASS] Admin Login
# 02. [PASS] Connect WebSocket
```

### ۲. توابع `any()` و `all()`
این توابع روی یک لیست شرط‌ها عمل می‌کنند:
- `any(...)`: اگر **حداقل یکی** از شرط‌ها True باشد، True می‌دهد (مانند OR منطقی).
- `all(...)`: فقط زمانی True می‌دهد که **همه** شرط‌ها True باشند (مانند AND منطقی).

```python
# از clients/signalr_client.py
# بررسی اینکه آیا حداقل یکی از فریم‌ها یک دیکشنری خالی است؟
if not any(frame == {} for frame in frames):
    raise RuntimeError(f"Unexpected SignalR handshake response: {frames}")
```

```python
# از utils/step_report.py
# بررسی اینکه آیا کلمه حساس در نام فیلد هست یا نه
if any(secret in lowered_key for secret in ("password", "token", "authorization")):
    sanitized[key] = "<redacted>"
```

### ۳. تابع `sum()` با Generator Expression
در پایتون می‌توان به جای نوشتن حلقه و شمارنده دستی، از `sum` روی یک مولد استفاده کرد:
```python
# از utils/stress.py
# شمارش تعداد نمونه‌های موفق:
passed_count = sum(sample.passed for sample in self.samples)
```
> در پایتون، مقدار `True` معادل عددی `1` و `False` معادل `0` است؛ بنابراین `sum()` تعداد موارد True را می‌شمارد!

---

## ۴. ساختارهای شرطی و فشرده‌سازی

### شرط تک‌خطی (Ternary Operator / Conditional Expression)
```python
# ساختار: <مقدار در صورت درستی> if <شرط> else <مقدار در صورت نادرستی>
result = "PASS" if sample.passed else "FAIL"
```

### حلقه `while` با تایم‌اوت هوشمند (`Deadline`)
در `clients/signalr_client.py` به جای حلقه بی‌نهایت و خطرناک، از الگوی Deadline با `time.monotonic()` استفاده شده است:
```python
deadline = time.monotonic() + self.timeout
while True:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Timed out waiting for response")
    
    # دریافت فریم‌ها با زمان باقیمانده
    frames = self._receive_frames(timeout=remaining)
    ...
```
