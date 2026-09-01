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
tests/negative/test_configuration_sync_negative.py
tests/negative/test_device_lifecycle_negative.py
tests/negative/test_history_backend_negative.py
tests/negative/test_delivery_merge_negative.py
tests/negative/test_lazy_upload_negative.py
tests/negative/test_destination_assignment_negative.py
tests/negative/test_destination_update_negative.py
tests/negative/test_bag_selection_negative.py
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

سناریوهای Stress وابسته به fixtureهای ثابت با flagهای
`HISTORY_BACKEND_STRESS_FIXTURES_READY` و `DELIVERY_MERGE_STRESS_FIXTURES_READY` کنترل می‌شوند.
تا وقتی barcodeهای trigger در بک‌اند آماده نباشند، این سناریوها اجرا نمی‌شوند
تا پاسخ عادی به‌عنوان نتیجهٔ سناریوی خطا ثبت نشود.

فایل‌های Stress:

```text
tests/stress/test_history_backend_stress.py
tests/stress/test_delivery_merge_stress.py
tests/stress/test_destination_update_stress.py
```

اجرا:

```powershell
$env:RUN_E2E="1"
$env:RUN_HISTORY_BACKEND_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_history_backend_stress.py -q -s

$env:RUN_DELIVERY_MERGE_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_delivery_merge_stress.py -q -s

$env:RUN_DESTINATION_UPDATE_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_destination_update_stress.py -q -s
```

هر Stress Flow بر اساس سناریوی مربوطه اجرا می‌شود. Stress مربوط به Destination Update، یعنی
TC-06، در هر iteration یک مرسولهٔ یکتا می‌سازد و `container.close` و
`route.assign` را با دو اتصال مستقل هم‌زمان اجرا می‌کند. فقط دو نتیجه
اتمی قابل قبول است: بستن کیسه زودتر و رد شدن تخصیص، یا موفق شدن تخصیص و
انتخاب‌نشدن مرسوله توسط `container.close`. قرارگرفتن مرسوله در هر دو نتیجه FAIL است.
برای جلوگیری از تداخل مرسوله‌های iterationهای مختلف، Destination Update فقط با
`STRESS_WORKERS=1` اجرا می‌شود؛ هم‌زمانی واقعی داخل هر iteration با دو اتصال
مستقل انجام می‌شود.
