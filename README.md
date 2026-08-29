# Sorting Device & Postal Integration Tests

نام منطقی پروژه:

`sorting-device-postal-integration-tests`

این مخزن، تست‌های Python برای سامانه مدیریت دستگاه‌های سورتینگ و تعامل آن با
سامانه‌های پستی است.

## مدل اجرای تست‌ها

تست‌ها دقیقاً در سه دسته نگهداری می‌شوند:

1. **Success**: فقط مسیر موفق پایهٔ کل فلو و Flow مستقل موفق WebSocket/SignalR.
2. **Negative**: سناریوهای منفی مستقل و task-oriented برای هر EPS.
3. **Stress**: تست‌های volume/endurance مستقل از Success و Negative.

سناریوهای مثبتِ مستقل EPS-40، EPS-49، EPS-53، EPS-55 و EPS-64 در دستهٔ Success
وجود ندارند. هر تست Negative فقط رفتار منفی همان تسک را بررسی می‌کند.

## ساختار پروژه

```text
post/
├── config/                 # تنظیمات اجرا و environment تست
├── clients/                # REST و WebSocket/SignalR clients
├── services/               # سرویس‌های ادمین و دستگاه
├── flows/
│   ├── device_lifecycle/   # مسیر موفق پایه، WebSocket و EPS-49 Negative
│   ├── config_sync/        # EPS-40 Negative
│   ├── inbound/            # EPS-53/EPS-55/EPS-64 و Stress
│   ├── destination/        # آماده توسعه
│   ├── bag/                # آماده توسعه
│   ├── dispatch/           # آماده توسعه
│   └── reporting/          # آماده توسعه
├── assertions/             # بررسی قرارداد پاسخ‌ها
├── tests/
│   ├── success/            # فقط دو Flow مثبت
│   ├── negative/           # Negativeهای task-oriented
│   ├── stress/             # Stress/Endurance
│   └── unit/               # تست‌های واحد
├── utils/                  # logging و گزارش مرحله‌ای
├── docs/                   # مستندات هر دسته و هر EPS
├── requirements.txt
└── pytest.ini
```

## راه‌اندازی

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

فایل `config/test.env` را از روی `config/test.env.example` بساز و مقدارهای
محیط تست را وارد کن. این فایل شامل credentialهای محلی است و در Git commit
نمی‌شود.

پیش‌نیاز اجرای E2E:

- دستگاه در سرویس تعریف و فعال باشد.
- Sync سرویس با Core انجام شده باشد.
- IP کلاینت تست با IP ثبت‌شده برای دستگاه یکسان باشد.
- Mockهای Core و Postal برای سناریوی مربوطه آماده باشند.

## 1) Success

### مسیر موفق پایه

این Flow کل مسیر خطی را اجرا می‌کند: Login، ثبت IP، اتصال و Handshake،
احراز هویت دستگاه و `RegisterInbound`.

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_base_success.py -q -s
```

### Flow مستقل موفق WebSocket/SignalR

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_websocket_success.py -q -s
```

در گزارش این دو Flow، مراحل مشترک با `[BASE]` مشخص می‌شوند. این دو Flow تنها
مسیرهای مثبت قابل اجرای پروژه هستند.

## 2) Negative

پاسخ منفی مورد انتظار، مانند `status=2` یا `status=4`، باعث PASS شدن می‌شود.
پاسخ غیرمنتظره یا خطای Transport باعث FAIL می‌شود. در هر Flow اگر Login،
ثبت IP، Handshake یا Auth لازم شکست بخورد، مراحل بعدی اجرا نمی‌شوند.

### EPS-40

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS40_NEGATIVE="1"
$env:EPS40_CASE="TC-02"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps40_negative.py -q -s
```

Caseهای قابل اجرای خودکار: `TC-02`، `TC-03`، `TC-04`، `TC-06` و `TC-07`.
برای Caseهای وابسته به Mock، پس از تغییر Snapshot سرویس را Restart کن.

### EPS-46

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS46_NEGATIVE="1"
$env:EPS46_CASE="TC-03"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps46_negative.py -q -s
```

Caseهای `TC-03` و `TC-04` رد شدن کل Sync در پیکربندی نامعتبر را بررسی می‌کنند.
`TC-05` یک Case اکتشافی برای پذیرش deadline منفی در حالت Disabled است. برای
هر Case باید `AutoDispatchPolicy` و `ConfigVersion` در Mock تغییر کند و سرویس
Restart شود. جزئیات در [docs/EPS46.md](docs/EPS46.md) آمده است.

### EPS-49

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS49_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps49_negative.py -q -s
```

### EPS-53

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS53_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps53_negative.py -q -s
```

### EPS-55

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS55_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps55_negative.py -q -s
```

### EPS-64

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS64_NEGATIVE="1"
$env:EPS64_NEGATIVE_CASE="all"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps64_negative.py -q -s
```

### EPS-49 Negative و سایر مستندات

- [Positive flows](docs/POSITIVE_FLOWS.md)
- [Negative و Stress](docs/NEGATIVE_AND_STRESS.md)
- [EPS-40](docs/EPS40.md)
- [EPS-49 Negative](docs/EPS49_NEGATIVE.md)
- [EPS-64](docs/EPS64.md)
- [Project structure](docs/PROJECT_STRUCTURE.md)

## 3) Stress

Stress مستقل از Success و Negative اجرا می‌شود و برای volume/endurance است.

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS53_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_eps53_stress.py -q -s

$env:RUN_EPS55_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_eps55_stress.py -q -s
```

تنظیمات Stress در `config/test.env`:

```dotenv
STRESS_ITERATIONS=50
STRESS_WORKERS=1
STRESS_DELAY_SECONDS=5
STRESS_FAIL_FAST=true
```

برای هر مرحله payload ارسالی، response دریافتی، انتظار و نتیجه ثبت می‌شود.
مراحل بعدی پس از شکست مرحلهٔ قبلی اجرا نمی‌شوند و با `NOT_EXECUTED` گزارش
می‌شوند.
