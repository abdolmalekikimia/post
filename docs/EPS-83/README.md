# EPS-83

## هدف

بررسی تولید و ارسال برچسب کیسه (`bagLabel`) در قالب Placeholder (JSON با کدگذاری Base64)، رفتار قطع و در دسترس نبودن سامانهٔ پستی و آزادسازی فوری مقصد برای تلاش مجدد.

## معماری و دامنه

- **دامنه:** بخش ۴ — کیسه‌بندی و صدور بارنامه (`tests/4_bagging/`)
- **ماژول تست:** `tests/4_bagging/test_bagging_and_labeling.py`

## وضعیت پوشش

- Positive: `Implemented` (S1, S2, S5, S6, S7, S8)
- Negative: `Implemented` (S3, S3b, S4)
- Stress: `نیاز ندارد`
- Protocol: `SignalR`
- Dependency: `Partial / External Dependency` — Bag و Destination fixtures؛ تنظیم Mock پستی

## Caseهای تست

| Case | عنوان | دسته‌بندی | نتیجهٔ مورد انتظار |
|---|---|---|---|
| `S1` | ایجاد کیسه | Success | `status: 0`, `resultType: Completed`, `bagBarcode` |
| `S2` | تولید برچسب معتبر | Success | `bagLabel` معتبر Base64 شامل JSON با اعضای موفق |
| `S3` | نبود مرسوله واجد شرایط | Negative | `resultType: NoEligibleParcels`, بدون `bagBarcode`/`bagLabel` |
| `S3b` | همهٔ مرسولات ناموفق | Negative | `resultType: AllParcelsFailed`, بدون `bagBarcode`/`bagLabel` |
| `S4` | قطع سامانه پستی | Negative | خطای فوری `status: 2, resultType: Error` + آزادسازی مقصد |
| `S5` | خطای جزئی | Success | `Completed` با مرسولهٔ موفق در برچسب و عدم درج خطادار |
| `S6` | تلاش مجدد بعد از موفقیت | Success | بسته شدن کیسه جدید با بارکد جدید |
| `S7` | تأیید آزادسازی فوری قفل مقصد | Success | بسته شدن موفق کیسه پس از خطای قبلی |
| `S8` | برچسب کیسه با مرسولات جدید و معوق | Success | برچسب شامل تمام اعضای موفق مرسولات |

## نحوهٔ اجرا

### اجرای تست‌های Success
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS83_SUCCESS="1"
$env:EPS83_CASE="all"
.venv\Scripts\python.exe -m pytest tests/4_bagging -m eps83_success -q -s
```

### اجرای تست‌های Negative
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS83_NEGATIVE="1"
$env:EPS83_CASE="all"
.venv\Scripts\python.exe -m pytest tests/4_bagging -m eps83_negative -q -s
```

### اجرای کل تست‌های EPS-83
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS83_SUCCESS="1"
$env:RUN_EPS83_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/4_bagging -m "eps83_success or eps83_negative" -q -s
```
