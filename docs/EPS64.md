# EPS-64 — Lazy Async Supplementary Upload

## جایگاه EPS-64 در معماری تست

Success مثبت EPS-64 در Flow مستقل task-oriented اجرا می‌شود:

```text
tests/success/test_task_success.py
```

این مسیر یک تصویر JPEG معتبر، `imageId` و `supplementaryData` کامل ارسال می‌کند
و انتظار `status=0` دارد.

سناریوهای task-oriented مربوط به EPS-64 فقط به‌صورت Negative اجرا می‌شوند:

```text
tests/negative/test_eps64_negative.py
flows/inbound/eps64_negative_flow.py
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
$env:RUN_EPS64_NEGATIVE="1"
$env:EPS64_NEGATIVE_CASE="all"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps64_negative.py -q -s
```

برای اجرای یک Case مشخص، مقدار `EPS64_NEGATIVE_CASE` را برابر نام Case قرار
بده. Caseهای `image_rejected`، `image_timeout` و `image_unavailable` به Mock
متناظر Backend نیاز دارند.

## نکتهٔ Worker

پاسخ `status=0` در `RegisterInbound` فقط Stage شدن آیتم را تأیید می‌کند.
تأیید نهایی ارسال غیرهمزمان، retry، unavailable، dead-letter و cleanup باید
از طریق لاگ سرویس یا SQLite انجام شود؛ چون endpoint تشخیصی مستقیمی در اختیار
این پروژه نیست.

مقدارهای قابل تنظیم:

```dotenv
EPS64_IMAGE_BARCODE=300000000000000000000001
EPS64_SUPPLEMENTARY_BARCODE=300000000000000000000002
EPS64_IMAGE_ID=img-001
EPS64_IMAGE_DESCRIPTION=front
```
