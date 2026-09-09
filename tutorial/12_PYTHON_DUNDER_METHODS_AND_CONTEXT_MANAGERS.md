# 🪄 فصل ۵ پایتون: متدهای داندر و مدیریت زمینه (Dunder Methods & Context Managers)

متدهایی که نام آن‌ها با دو زیرخط (`__`) شروع و پایان می‌یابد، در پایتون **Dunder Methods** (مخفف Double Underscore) یا **Magic Methods** نامیده می‌شوند. این متدها نحوه رفتار اشیاء را در موقعیت‌های خاص زبان تعریف می‌کنند.

---

## ۱. متدهای داندر `__enter__` و `__exit__` (Context Manager)

آیا تا به حال دیده‌اید که برای کار با فایل‌ها از دستور `with` استفاده می‌شود؟
```python
with open("file.txt", "w") as f:
    f.write("hello")
```
پایتون پشت صحنه متد `__enter__` را در ابتدای بلوک و متد `__exit__` را در انتهای بلوک (حتی اگر ارور بدهد) صدا می‌زند.

### پیاده‌سازی Context Manager در `clients/rest_client.py`:
```python
class RestClient:
    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "RestClient":
        # وقتی وارد بلوک with می‌شویم اجرا می‌شود:
        return self

    def __exit__(self, *_: object) -> None:
        # وقتی از بلوک with خارج می‌شویم (یا کرش می‌کنیم) اجرا می‌شود:
        self.close()
```

### پیاده‌سازی در `clients/signalr_client.py`:
```python
class DeviceWebSocketClient:
    def __enter__(self) -> "DeviceWebSocketClient":
        self.connect()  # برقراری خودکار اتصال هنگام ورود
        return self

    def __exit__(self, *_: object) -> None:
        self.close()    # بستن قطعی سوکت هنگام خروج
```

### مزیت اصلی:
هرگز اتصال شبکه یا پورت در حافظه باز نمی‌ماند و تست‌های بعدی با کمبود سوکت یا اشغال پورت مواجه نخواهند شد!

---

## ۲. متدهای داندر `__repr__` و `__str__`

وقتی یک شیء را `print()` می‌کنید یا در محیط تعاملی می‌نویسید:
- پایتون دنبال `__str__` می‌گردد (نمایش خوانا برای کاربر).
- اگر نباشد، دنبال `__repr__` می‌گردد (نمایش دقیق شیء برای برنامه‌نویس و دیباگ).

```python
class StepRecord:
    def __str__(self) -> str:
        return f"Step({self.name}, status={self.status})"
```
> در کلاس‌هایی که دکوراتور `@dataclass` دارند، پایتون به طور خودکار یک `__repr__` کامل و باکیفیت شامل تمام فیلدها می‌سازد.

---

## ۳. نحوه کار دستور `try ... finally` در برابر Context Manager

در مواردی که نمی‌خواهیم یا نمی‌توانیم از `with` استفاده کنیم، بلوک `try ... finally` دقیقاً همان وظیفه پاکسازی منابع را انجام می‌دهد:

```python
# از flows/device_lifecycle/device_auth_flow.py
ws = DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds)
try:
    # ۱. اتصال به سوکت
    # ۲. احراز هویت
    # ۳. ثبت بارکد
    # ۴. اجرای سناریوهای وابسته
finally:
    # این بخش در هر شرایطی (حتی شکست تست یا پرتاب ارور) اجرا می‌شود
    ws.close()
```
