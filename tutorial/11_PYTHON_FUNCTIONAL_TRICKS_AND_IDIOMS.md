# 🎯 فصل ۴ پایتون: ترفندهای تابعی، Comprehensions و اصطلاحات پایتونی (Functional & Idioms)

پایتون به نوشتن کدهای تمیز، خوانا و کوتاه معروف است که به آن اصطلاحاً **Pythonic Code** می‌گویند. در این فصل با ترفندهای کاربردی و پرکاربرد پایتون در این پروژه آشنا می‌شویم.

---

## ۱. توابع لامبدا (`lambda`) و توابع درجه اول (First-Class Functions)

در پایتون، توابع می‌توانند مانند یک متغیر به توابع دیگر پاس داده شوند.

### مثال در `flows/device_lifecycle/device_auth_flow.py`:
```python
admin_token = run_step(
    report,
    "1. [BASE] Admin Login - POST /api/admin/login",
    lambda: admin.login(run_settings.admin_username, run_settings.admin_password),
    detail=lambda _: exchange_detail(rest_client.last_exchange),
)
```
### چرا از `lambda` استفاده شد؟
اگر مستقیماً می‌نوشتیم `admin.login(...)`، این تابع فوراً در همان خط اجرا می‌شد! اما با قرار دادن `lambda:`، ما **تابع را بسته‌بندی کردیم** تا `run_step` در زمان مناسب خودش آن را اجرا کند و زمان اجرایش را اندازه بگیرد.

---

## ۲. درک عمیق Comprehensions در پایتون

در پایتون، ساختن لیست، دیکشنری یا ست با حلقه `for` سنتی طولانی است. به جای آن از Comprehension استفاده می‌کنیم:

### الف) List Comprehension (ساخت لیست تک‌خطی)
```python
# از utils/step_report.py
# ساخت لیستی از آبجکت‌های StepRecord به ازای هر نام گام:
self.records.extend(StepRecord(name=name) for name in step_names)

# استخراج زمان تأخیر تمام نمونه‌های استرس:
latencies = [sample.latency_seconds for sample in self.samples]
```

### ب) Dict Comprehension (ساخت دیکشنری تک‌خطی)
```python
# از services/device_service.py
# حذف کلیدهایی که مقدارشان None است:
optional_values = {"barcode": barcode, "chuteId": chute_id}
cleaned_dict = {key: value for key, value in optional_values.items() if value is not None}
```
این خط کد به زیبایی تمام مقادیر `None` را فیلتر می‌کند تا بدنه درخواست تمیز بماند.

### ج) Set Comprehension (ساخت مجموعه یکتا)
```python
# از tests/success/test_base_success.py
# تبدیل کلیدهای دیکشنری به یک ست برای مقایسه آسان:
assert set(result.scenario_responses["Destination Update"]) == {"TC-01", "TC-02", "TC-03", "TC-04"}
```

---

## ۳. عملگرهای باز کردن بسته (Unpacking: `*` و `**`)

### الف) علامت ستاره تکی `*` (Positional Unpacking)
۱. **در ورودی تابع (پذیرفتن تعداد نامحدود آرگومان):**
```python
# در ExecutionReport
def register(self, *step_names: str) -> None:
    # step_names تبدیل به یک تاپل از تمام ورودی‌ها می‌شود
```
۲. **در هنگام صدا زدن تابع (پخش کردن اعضای یک لیست):**
```python
report.register(
    "1. Step One",
    "2. Step Two",
    *success_step_names(6),  # لیست گام‌های بعدی باز شده و تک‌تک پاس داده می‌شوند!
)
```

### ب) علامت دو ستاره `**` (Keyword Unpacking)
برای ادغام دیکشنری‌ها یا ارسال دیکشنری به عنوان پارامترهای نام‌دار تابع:
```python
# ادغام دو دیکشنری:
exchange = {**nested_exchange, **detail}

# ارسال مقادیر به صورت keyword argument:
error_detail = {"error": str(exc), **exchange_detail(ws.last_exchange)}
```

---

## ۴. ترفندهای پیشرفته F-Strings (Formatting)

فرمت‌دهی رشته‌ها در پایتون ۳.۶ به بعد با `f"..."` انجام می‌شود:

```python
# ۱. عدد دورقمی با پر کردن صفر در سمت چپ (:02d یا :03d)
index = 5
print(f"{index:02d}")  # خروجی: "05"
print(f"{index:03d}")  # خروجی: "005"

# ۲. اعشار با دقت ۳ رقم بعد از ممیز (:.3f)
latency = 0.045678
print(f"{latency:.3f}s")  # خروجی: "0.046s"

# ۳. نمایش مقدار با استفاده از repr شیء با علامت !r
value = "hello"
print(f"actual={value!r}")  # خروجی: actual='hello' (همراه با کوتیشن)
```
