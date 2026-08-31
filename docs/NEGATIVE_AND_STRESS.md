# Negative و Stress

معماری تست‌ها سه بخش دارد:

1. **Success**: مسیر موفق پایه و Flow مستقل WebSocket/SignalR.
2. **Negative**: سناریوهای منفی مستقل بر اساس هر تسک.
3. **Stress**: تست‌های volume/endurance مستقل.

## Negative

هر Negative Flow فقط رفتار منفی تسک خودش را بررسی می‌کند و سناریوی مثبت
تسک‌محور ندارد. پاسخ منفی مورد انتظار، مانند `status=2`، `status=3`،
`status=4` یا HTTP خطادار مورد انتظار، PASS محسوب می‌شود. پاسخ غیرمنتظره یا
خطای Transport FAIL است.

فایل‌ها:

```text
tests/negative/test_eps40_negative.py
tests/negative/test_eps49_negative.py
tests/negative/test_eps53_negative.py
tests/negative/test_eps55_negative.py
tests/negative/test_eps64_negative.py
tests/negative/test_eps71_negative.py
tests/negative/test_eps73_negative.py
tests/negative/test_eps76_negative.py
```

اگر پیش‌شرط‌های لازم مانند Login، ثبت IP، Handshake یا Auth شکست بخورد،
مراحل وابسته اجرا نمی‌شوند و `NOT_EXECUTED` گزارش می‌شوند.

## Stress

Stress از Negative جداست و برای volume/endurance اجرا می‌شود. تنظیمات قابل
تغییر در `config/test.env`:

```dotenv
STRESS_ITERATIONS=50
STRESS_WORKERS=1
STRESS_DELAY_SECONDS=5
STRESS_FAIL_FAST=true
```

برای هر iteration، payload، response، correlationId، expected/actual و latency
ثبت می‌شود. گزارش نهایی شامل تعداد کل، موفق، پاسخ غیرمنتظره، خطاهای Transport،
reset، timeout و latencyهای min/avg/max و p50/p95/p99 است.

فایل‌های Stress:

```text
tests/stress/test_eps53_stress.py
tests/stress/test_eps55_stress.py
tests/stress/test_eps73_stress.py
```

اجرا:

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS53_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_eps53_stress.py -q -s

$env:RUN_EPS55_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_eps55_stress.py -q -s

$env:RUN_EPS73_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_eps73_stress.py -q -s
```

هر Stress Flow بر اساس EPS خودش اجرا می‌شود. Stress مربوط به EPS-73، یعنی
TC-06، در هر iteration یک مرسولهٔ یکتا می‌سازد و `bag.close` و
`destination.assign` را با دو اتصال مستقل هم‌زمان اجرا می‌کند. فقط دو نتیجه
اتمی قابل قبول است: بستن کیسه زودتر و رد شدن تخصیص، یا موفق شدن تخصیص و
انتخاب‌نشدن مرسوله توسط `bag.close`. قرارگرفتن مرسوله در هر دو نتیجه FAIL است.
برای جلوگیری از تداخل مرسوله‌های iterationهای مختلف، EPS-73 فقط با
`STRESS_WORKERS=1` اجرا می‌شود؛ هم‌زمانی واقعی داخل هر iteration با دو اتصال
مستقل انجام می‌شود.
