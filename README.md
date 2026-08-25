# Sorting Device & Postal Integration Tests

نام منطقی پروژه:

`sorting-device-postal-integration-tests`

این پروژه، تست‌های Python برای سامانه مدیریت دستگاه‌های سورتینگ و تعامل آن با سامانه‌های پستی است. ساختار پروژه بر اساس سند «فرآیندهای عملیاتی و تعاملات سامانه مدیریت دستگاه‌های سورتینگ با سامانه‌های پستی» طراحی شده است.

در وضعیت فعلی، بخش‌های زیر توسعه داده شده‌اند:

- اتصال WebSocket/SignalR دستگاه
- ورود ادمین و ثبت IP دستگاه
- احراز هویت دستگاه
- ثبت وارده
- اعتبارسنجی بارکدهای ۱۴، ۲۴ و ۳۷ رقمی
- سناریوهای EPS-53 مربوط به تاریخچه Core
- سناریوهای EPS-55 مربوط به Postal، Destination و Merge
- Flow مستقل تست WebSocket/SignalR دستگاه
- اجرای وابسته؛ در صورت دریافت نتیجه غیرمنتظره، سناریوی بعدی اجرا نمی‌شود
- گزارش مرحله‌ای شامل وضعیت موفق، ناموفق و اجرا‌نشده
- ثبت payload ارسالی و response دریافتی برای هر مرحله

## ساختار پروژه

```text
post/
├── config/                 # تنظیمات اجرا و environment تست
├── clients/                # کلاینت‌های REST و WebSocket/SignalR
├── services/               # سرویس‌های ادمین و دستگاه
├── flows/
│   ├── device_lifecycle/   # ثبت، تنظیم، اتصال و احراز هویت دستگاه
│   ├── inbound/            # ثبت وارده و تاریخچه مرسوله
│   ├── destination/        # مقصد عملیاتی و شوتر - فاز بعدی
│   ├── bag/                # بستن کیسه و لیبل - فاز بعدی
│   ├── dispatch/           # بستن دپش - فاز بعدی
│   └── reporting/          # گزارش‌های عملیاتی و مدیریتی - فاز بعدی
├── assertions/             # بررسی پاسخ‌ها و قراردادها
├── tests/
│   ├── device_lifecycle/   # تست چرخه عمر دستگاه
│   ├── inbound/            # تست ثبت وارده و Core history
│   ├── destination/        # آماده توسعه
│   ├── bag/                # آماده توسعه
│   ├── dispatch/           # آماده توسعه
│   ├── reporting/          # آماده توسعه
│   └── unit/               # تست‌های واحد
└── utils/                  # ابزارهای عمومی و logging
```

جزئیات وضعیت توسعه و نگاشت ساختار به فصل‌های سند در [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) ثبت شده است.

## راه‌اندازی

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

فایل `config/test.env` را از روی `config/test.env.example` بساز و مقدارهای محیط تست را وارد کن. این فایل در Git commit نمی‌شود.

دستگاه باید در سرویس تعریف و فعال باشد، همگام‌سازی سیستم لبه انجام شده باشد و IP کلاینت تست با IP ثبت‌شده دستگاه یکسان باشد.

## اجرای تست‌ها

تست‌های واحد:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit -q
```

مسیر موفق پایه:

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/device_lifecycle -q -s
```

سناریوهای EPS-53:

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS53="1"
.venv\Scripts\python.exe -m pytest tests/inbound/test_core_history.py -q -s
```

سناریوهای EPS-55:

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS55="1"
.venv\Scripts\python.exe -m pytest tests/inbound/test_eps55.py -q -s
```

Flow مستقل WebSocket/SignalR:

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/device_lifecycle/test_websocket_flow.py -q -s
```

قبل از اجرای تست‌های E2E، Mockهای Postal/Core را مطابق نیازمندی تست تنظیم و سرویس را restart کن.

بعد از اجرای هر Flow، گزارش مرحله‌ای چاپ می‌شود. اگر یک مرحله شکست بخورد، همان مرحله با وضعیت `FAILED`
ثبت می‌شود و تمام مراحل بعدی با وضعیت `NOT_EXECUTED` گزارش می‌شوند.
برای هر مرحله، بخش `payloadSent` درخواست واقعی و بخش `responseReceived` پاسخ واقعی را نشان می‌دهد.
در صورت خطا، نوع خطا، متن خطا، payload ارسالی و پاسخ دریافتی همان مرحله ثبت می‌شود.

## وضعیت فازهای بعدی

فرآیندهای ثبت مقصد عملیاتی، ثبت صادره، بستن کیسه، چاپ مجدد لیبل، بستن دپش، همگام‌سازی آفلاین و گزارش‌گیری در ساختار پروژه رزرو شده‌اند و بعد از دریافت قرارداد رسمی APIها و قواعد کسب‌وکار شرکت پست توسعه داده خواهند شد.
