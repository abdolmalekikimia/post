# 🌐 کلاینت‌ها و پروتکل‌های ارتباطی (Clients & Protocols)

در این بخش پیاده‌سازی دو کلاینت اصلی پروژه یعنی **REST HTTP** و **SignalR / WebSocket** را با تمام جزئیات فنی بررسی می‌کنیم.

---

## ۱. کلاینت REST (`clients/rest_client.py`)

کلاینت REST برای فراخوانی APIهای سنتی HTTP (مثل لاگین ادمین، ثبت IP و غیره) استفاده می‌شود.

### نکات کلیدی در پیاده‌سازی `RestClient`:
1. **استفاده از `requests.Session()`:** به جای استفاده از `requests.post()` تکی، از شیء Session استفاده شده تا کانکشن‌های TCP مجدداً استفاده شوند (Connection Pooling) و سرعت تست‌ها بالاتر برود.
2. **ثبت وضعیت تبادل (`last_exchange`):** قبل از ارسال درخواست و پس از دریافت پاسخ، دقیقاً متد، آدرس URL، بدنه درخواست (Payload)، وضعیت کد HTTP و بدنه پاسخ در یک دیکشنری ذخیره می‌شود تا در صورت خطا، گزارش‌دهنده به آن دسترسی داشته باشد.
3. **مدیریت ایمن توکن احراز هویت:** تابع `_authorization_headers` اگر توکن مقدار داشته باشد هدر `Authorization: Bearer <token>` را تزریق می‌کند و اگر `None` باشد هدر خالی برمی‌گرداند.

---

## ۲. پیاده‌سازی پروتکل SignalR Hub بر بستر WebSocket (`clients/signalr_client.py`)

این بخش یکی از پیشرفته‌ترین و جذاب‌ترین قسمت‌های این فریم‌ورک تست است. SignalR یک پروتکل استاندارد مایکروسافت برای ارتباطات بلادرنگ است که روی WebSocket سوار می‌شود.

### الف) کاراکتر جداکننده فریم‌ها (Record Separator `0x1E`)
در پروتکل JSON Hub در SignalR، هر پیام باید با کاراکتر اسکی `0x1E` (بایت 30 در جدول ASCII یا همان Record Separator) پایان یابد.
```python
RECORD_SEPARATOR = "\x1e"
```
هنگام ارسال، این بایت به انتهای رشته JSON اضافه می‌شود:
```python
self._socket.send(raw_message + self.RECORD_SEPARATOR)
```
و هنگام دریافت، فریم‌ها با همین کاراکتر از هم تفکیک (`split`) می‌شوند.

### ب) فرآیند Handshake (دست‌تکانی اولیه)
وقتی سوکت باز می‌شود، کلاینت بلافاصله باید پیام درخواست پروتکل را بفرستد:
```json
{"protocol": "json", "version": 1}
```
سرور در پاسخ، یک آبجکت JSON خالی (`{}`) برمی‌گرداند. اگر خطایی در هندشیک باشد، سرور فیلد `{"error": "..."}` برمی‌گرداند.

کد مربوطه در `_receive_handshake`:
```python
def _receive_handshake(self) -> list[dict[str, Any]]:
    frames = self._receive_frames()
    for frame in frames:
        if frame.get("error"):
            raise RuntimeError(f"SignalR handshake failed: {frame['error']}")
    if not any(frame == {} for frame in frames):
        raise RuntimeError(f"Unexpected SignalR handshake response: {frames}")
    return frames
```

### ج) انواع فریم‌ها در پروتکل SignalR (Frame Types)
| کد فریم (Type) | نام | کاربرد | رفتار کلاینت |
|---|---|---|---|
| `1` | Invocation | ارسال درخواست متد از کلاینت به سرور | کلاینت با `invocationId` یکتا ارسال می‌کند |
| `3` | Completion | پاسخ سرور به یک فراخوانی قبلی | تطبیق با `invocationId` و بازگرداندن نتیجه (`result`) |
| `6` | Ping / Keep-Alive | پیام زنده‌بودن ارتباط از سرور | نادیده گرفته می‌شود تا جریان منتظر پاسخ مسدود نشود (`continue`) |
| `7` | Close | پیام بستن کانکشن توسط سرور | پرتاب خطای صریح برای آگاهی تست |

### د) چرخه حیات متد `invoke`:
```python
def invoke(self, target: str, arguments: list[Any], invocation_id: str | None = None):
    # ۱. تولید شناسه یکتا برای این درخواست
    invocation_id = invocation_id or str(uuid4())
    
    # ۲. ساخت فریم با Type=1
    request = {
        "type": 1,
        "invocationId": invocation_id,
        "target": target,
        "arguments": arguments,
    }
    self._send_frame(request)
    
    # ۳. حلقه انتظار دریافت پاسخ با محاسبه زمان باقیمانده (Timeout Deadline)
    # ۴. نادیده گرفتن فریم‌های Ping (Type 6)
    # ۵. تطبیق invocationId فریم دریافتی با شناسه ارسالی
    # ۶. بررسی فیلد correlationId در دیتای بیزنسی
    # ۷. بازگرداندن دیکشنری result
```

این پیاده‌سازی باعث می‌شود که حتی در صورت دریافت بسته‌های ناهماهنگ یا پینگ‌های مکرر سرور، تست‌ها بدون هیچ‌گونه Flakiness (ناپایداری) و با حداکثر دقت کار کنند.
