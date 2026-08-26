# EPS-64 — Lazy Async Supplementary Upload

## Scope

این بخش فقط شروع ارسال غیرهمزمان را از مسیر `RegisterInbound` بررسی می‌کند.
پاسخ موفق WebSocket باید `status=0` باشد. بعد از این پاسخ، سرویس Edge آیتم
تصویر یا `supplementaryData` را در صف محلی قرار می‌دهد و `LazyUploadWorker`
آن را به‌صورت background به Core/Object Storage ارسال می‌کند.

طبق نیازمندی EPS-64، endpoint مستقیمی برای مشاهده صف یا اجرای دستی Worker وجود
ندارد. بنابراین حذف رکورد پس از موفقیت Worker باید از طریق لاگ سرویس یا
بازرسی SQLite بررسی شود و assertion تست WebSocket عمداً فقط پاسخ بلادرنگ را
بررسی می‌کند.

## محل اجرای مسیر موفق

سناریوهای مثبت EPS-64 دیگر تست مستقل ندارند و در هر دو Flow مثبت اجرا می‌شوند:

1. مسیر موفق پایه: `tests/device_lifecycle/test_auth_success.py`
2. Flow مستقل: `tests/device_lifecycle/test_websocket_flow.py`

در صورت شکست هر مرحله، مراحل بعدی اجرا نمی‌شوند و برای هر مرحله payload
ارسالی و response دریافتی در گزارش چاپ می‌شود.

## اجرا همراه با مسیرهای مثبت

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/device_lifecycle/test_auth_success.py -q -s
.venv\Scripts\python.exe -m pytest tests/device_lifecycle/test_websocket_flow.py -q -s
```

مقدارهای قابل تنظیم در `config/test.env`:

```dotenv
EPS64_IMAGE_BARCODE=300000000000000000000001
EPS64_SUPPLEMENTARY_BARCODE=300000000000000000000002
EPS64_IMAGE_ID=img-001
EPS64_IMAGE_DESCRIPTION=front
```

قبل از اجرا، Mockهای Core، Object Storage و Worker را طبق نیازمندی تنظیم و
سرویس را restart کنید. برای مسیر موفق، overrideها باید روی حالت پیش‌فرض
`Success` باشند.

## افزودن سناریوهای منفی آینده

هر سناریو با `Eps64Case` تعریف می‌شود و orchestration تغییر نمی‌کند:

```python
Eps64Case(
    name="image_rejected",
    barcode="300000000000000000000010",
    images=(image_payload,),
    expected_status=2,
    expected_error_contains="rejected",
)
```

سناریوهای retry، timeout، unavailable و dead-letter نیازمند بررسی وضعیت صف
و زمان‌بندی Worker هستند و باید با لاگ یا SQLite تکمیل شوند، نه با پاسخ مستقیم
WebSocket.
