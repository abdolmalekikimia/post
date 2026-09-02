# Success Tests

این سند راهنمای تمام مسیرهای موفق پروژه است. تست‌های این بخش به سرویس Gateway و
در صورت نیاز به Upstream/Delivery Network Mock آماده نیاز دارند.

## تست‌های موجود

- Smoke مسیر پایه: Login، ثبت IP، Handshake، Auth و `RegisterItem`
- Smoke مستقل WebSocket/SignalR
- Success مستقل Configuration Sync، History Backend، Destination Lookup، Lazy Upload، Destination Assignment و Destination Update
- قرارداد موفق بستن کیسه در Packing برای Container Selection، Export Before Container، Container Response و Physical Container Audit

هر مرحله payload ارسال‌شده، پاسخ Backend، نتیجهٔ assertion و مراحل اجرا‌نشده
پس از شکست مرحلهٔ قبلی را گزارش می‌کند.

## کاتالوگ Caseهای Success

- Configuration Sync: `healthy_device_auth`
- History Backend: `success_no_discrepancy`، `success_with_discrepancy`
- Destination Lookup: `TC-08`
- Lazy Upload: `valid_image_registration`
- Destination Assignment: `TC-01_with_chute`، `TC-02_without_chute`
- Destination Update: `TC-01`، `TC-02`، `TC-03`، `TC-04`
- Packing Container Selection/79/87/89: یک Success contract مستقل برای هر EPS

Smoke مسیر پایه و WebSocket/SignalR نیز Caseهای مثبت Destination Update از `TC-01` تا
`TC-04` را پوشش می‌دهند.

## اجرای همهٔ Success

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success -q -s
```

## Smoke مسیر پایه

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_base_success.py -q -s
```

## Smoke مستقل WebSocket/SignalR

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_websocket_success.py -q -s
```

## اجرای Success یک EPS

Successهای task-oriented در فایل زیر قرار دارند:

```text
tests/success/test_task_success.py
```

نمونهٔ اجرای Destination Assignment:

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_task_success.py -m destination_assignment_success -q -s
```

## Success قرارداد Packing

مسیر مثبت `RegisterItem → route.assign → container.close` برای
Container Selection/79/87/89 در suite مستقل Packing نگهداری می‌شود:

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_packing_success.py -m packing_success -q -s
```

جزئیات setup و کیس‌های Packing در
[docs/packing/README.md](../packing/README.md) قرار دارد.
