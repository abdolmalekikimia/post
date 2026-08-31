# EPS-71 — Destination Assignment Tests

EPS-71 اعتبارسنجی و نگهداری مقصد عملیاتی مرسوله را از طریق
`destination.assign` بررسی می‌کند. دو Case مثبت آن داخل هر دو مسیر موفق پروژه
اجرا می‌شوند و Caseهای task-oriented منفی در تست Negative باقی می‌مانند.

## جریان

1. Login ادمین
2. ثبت IP دستگاه
3. WebSocket/SignalR handshake
4. Auth دستگاه
5. مسیر Success: ثبت مرسوله با `RegisterInbound`
6. مسیر Success: ارسال `destination.assign` با شوتر
7. مسیر Success: ثبت مرسولهٔ دوم
8. مسیر Success: ارسال `destination.assign` بدون شوتر
9. مسیر Negative: آماده‌سازی و ارسال ورودی منفی
10. بررسی پاسخ منفی مورد انتظار

قرارداد وضعیت `destination.assign`:

- `status=1`: تخصیص موفق
- `status=2`: خطا

target واقعی Hub در کلاینت پروژه `AssignDestination` است. مقدار
`messageType` همچنان `destination.assign` باقی می‌ماند؛ target باید دقیقاً با
نام متد Hub یکی باشد. `DestinationAssign` نام payload/response است و متد Hub
نیست.

## Caseهای مثبت در Success

- `TC-01`: ثبت یک بارکد معتبر و تخصیص مقصد با `destinationCenterCode` و
  `chuteId`
- `TC-02`: ثبت یک بارکد معتبر و تخصیص مقصد فقط با
  `destinationCenterCode`، بدون `chuteId`

این Caseها در فایل زیر به‌صورت Flow مستقل جداگانه اجرا نمی‌شوند و از هر دو
مسیر موفق فراخوانی می‌شوند:

```text
flows/destination/eps71_success_flow.py
```

در گزارش مراحل آن‌ها با برچسب `[EPS-71]` نمایش داده می‌شود.

## Caseهای Negative

- `TC-03-missing` و `TC-03-empty`: بارکد غایب یا خالی
- `TC-04-missing` و `TC-04-empty`: مقصد غایب یا خالی
- `TC-05-short` و `TC-05-long`: مقصد چهار یا شش رقمی
- `TC-06`: مقصد شامل حرف
- `TC-07`: بارکد با طول/ساختار نامعتبر
- `TC-08`: بارکد معتبر بدون سابقهٔ `inbound.register`
- `TC-09`: تخصیص مقصد بعد از بسته‌شدن کیسه
- `TC-13`: تخصیص بعد از مرز بستن کیسه

TC-01 و TC-02 در Success اجرا می‌شوند و در این Negative Flow تکرار نمی‌شوند.
TC-14/TC-15 اکتشافی یا مثبت‌اند؛ بنابراین در این Negative Flow اجرا نمی‌شوند.
منطق انتخاب مرسوله و فیلترهای `bag.close` در EPS-76 قرار دارد.

## اجرا

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS71_NEGATIVE="1"
$env:EPS71_CASE="TC-07"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps71_negative.py -q -s
```

برای اجرای همهٔ Caseها:

```powershell
$env:EPS71_CASE="all"
```

برای TC-09 و TC-13، Flow ابتدا همان بارکد را ثبت و تخصیص می‌دهد، سپس با
`bag.close` آن را می‌بندد و در پایان تخصیص مجدد را با انتظار خطا بررسی می‌کند.
بنابراین target و قرارداد `BagClose` نیز باید در Backend موجود باشد.

در گزارش هر مرحله `payloadSent`، `responseReceived`، `expected` و خطای دقیق
در صورت شکست نمایش داده می‌شود. پاسخ خطای مورد انتظار PASS است؛ پاسخ موفق
غیرمنتظره یا خطای Transport FAIL است.
