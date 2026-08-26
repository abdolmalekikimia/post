# EPS-53/EPS-55 Negative و Stress

سناریوهای مثبت EPS-53 و EPS-55 داخل مسیر موفق پایه و Flow مستقل
WebSocket/SignalR اجرا می‌شوند. تست‌های Negative این سند مستقل هستند.

## Negative

هر Flow مراحل پایهٔ Login، ثبت IP، Handshake و Auth را اجرا می‌کند. اگر یکی از
این مراحل شکست بخورد، مراحل بعدی اجرا نمی‌شوند. در سناریوها، status منفی
مورد انتظار مثل `2`، `3` یا `4` باعث Pass شدن تست می‌شود؛ فقط پاسخ متفاوت یا
خطای ارتباطی Fail است.

## Stress

Stress دارای warm-up و سپس iterationهای قابل تنظیم است. هر worker اتصال و Auth
مستقل دارد. ترکیب بار با وزن‌های تعریف‌شده در caseها حفظ می‌شود:

- EPS-53: بارکد نامعتبر ۳۰٪، وزن/ابعاد ۲۰٪، Core Reject ۲۰٪،
  Timeout ۱۵٪ و Unavailable ۱۵٪
- EPS-55: mismatch ۲۰٪، Postal Reject ۲۰٪، Timeout ۱۵٪، Unavailable ۱۵٪،
  Destination ۱۵٪ و Merge/Returning ۱۵٪

برای هر درخواست correlationId، payload، response، status مورد انتظار و واقعی و
latency ثبت می‌شود. `STRESS_FAIL_FAST=true` با اولین پاسخ غیرمنتظره یا خطای
Transport متوقف می‌کند؛ با `false` همهٔ iterationها برای جمع‌آوری گزارش ادامه
می‌یابند. فاصلهٔ پیش‌فرض بین درخواست‌ها ۵ ثانیه است.

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS53_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/inbound/test_eps53_negative.py -q -s

$env:RUN_EPS55_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/inbound/test_eps55_negative.py -q -s

$env:RUN_EPS53_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_eps53_stress.py -q -s

$env:RUN_EPS55_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_eps55_stress.py -q -s
```
