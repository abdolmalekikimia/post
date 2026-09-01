# Lazy Upload — Lazy Async Supplementary Upload

## جایگاه Lazy Upload در معماری تست

Lazy Upload تست مثبت مستقل ندارد. مسیرهای Success پروژه فقط در این دو فایل هستند:

```text
tests/success/test_base_success.py
tests/success/test_websocket_success.py
```

سناریوهای task-oriented مربوط به Lazy Upload فقط به‌صورت Negative اجرا می‌شوند:

```text
tests/negative/test_lazy_upload_negative.py
flows/inbound/lazy_upload_negative_flow.py
```

## Negativeهای قابل اجرا

- `invalid_barcode`
- `image_missing_image_id`
- `image_missing_content`
- `image_invalid_mime_type`
- `supplementary_data_incomplete`
- `image_rejected`
- `image_timeout`
- `image_unavailable`

پاسخ منفی مورد انتظار PASS است؛ پاسخ غیرمنتظره یا خطای Transport FAIL است.
اگر پیش‌شرط‌های Flow شکست بخورند، مراحل بعدی اجرا نمی‌شوند.

## اجرا

```powershell
$env:RUN_E2E="1"
$env:RUN_LAZY_UPLOAD_NEGATIVE="1"
$env:LAZY_UPLOAD_NEGATIVE_CASE="all"
.venv\Scripts\python.exe -m pytest tests/negative/test_lazy_upload_negative.py -q -s
```

برای اجرای یک Case مشخص، مقدار `LAZY_UPLOAD_NEGATIVE_CASE` را برابر نام Case قرار
بده. Caseهای `image_rejected`، `image_timeout` و `image_unavailable` به Mock
متناظر Backend نیاز دارند.

## نکتهٔ Worker

پاسخ `status=0` در `RegisterItem` فقط Stage شدن آیتم را تأیید می‌کند.
تأیید نهایی ارسال غیرهمزمان، retry، unavailable، dead-letter و cleanup باید
از طریق لاگ سرویس یا SQLite انجام شود؛ چون endpoint تشخیصی مستقیمی در اختیار
این پروژه نیست.

مقدارهای قابل تنظیم:

```dotenv
LAZY_UPLOAD_IMAGE_BARCODE=300000000000000000000001
LAZY_UPLOAD_SUPPLEMENTARY_BARCODE=300000000000000000000002
LAZY_UPLOAD_IMAGE_ID=img-001
LAZY_UPLOAD_IMAGE_DESCRIPTION=front
```
