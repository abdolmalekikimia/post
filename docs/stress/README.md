# Stress Tests

تست‌های Stress برای volume، endurance و race condition طراحی شده‌اند و از
Success و Negative مستقل هستند.

## وضعیت فعلی

Stress فعلاً طبق سیاست پروژه غیرفعال است. فایل‌های Stress با `skip` علامت‌گذاری
شده‌اند و pytest نیز مسیر `tests/stress` و تست کمکی
`tests/unit/test_stress.py` را در اجرای معمول مستثنی می‌کند.

تا زمان آماده‌شدن fixtureهای واقعی، هیچ دستور Stress نباید اجرا شود.

## سناریوهای آماده

```text
tests/stress/test_history_backend_stress.py
tests/stress/test_delivery_merge_stress.py
tests/stress/test_destination_update_stress.py
```

کاتالوگ Stress:

- History Backend: `invalid_barcode`، `negative_weight`، `invalid_dimensions`،
  `upstream_rejected`، `upstream_timeout`، `upstream_unavailable`
- Delivery Merge: `barcode_mismatch`، `delivery_rejected`، `delivery_timeout`،
  `delivery_unavailable`، `destination_error`، `returning`
- Destination Update: `TC-06` — race هم‌زمان `container.close` و `route.assign`

Caseهای History Backend و Delivery Merge که به fixture نیاز دارند، فقط پس از فعال‌شدن flag
متناظر وارد مجموعهٔ فعال می‌شوند.

سناریوی Destination Update در هر iteration، `container.close` و `route.assign` را با دو
اتصال مستقل هم‌زمان اجرا می‌کند. برای جلوگیری از تداخل iterationها،
`STRESS_WORKERS=1` در نظر گرفته شده است.

## تنظیمات

```dotenv
STRESS_ITERATIONS=50
STRESS_WORKERS=1
STRESS_DELAY_SECONDS=5
STRESS_FAIL_FAST=true
```

سناریوهای وابسته به fixture با این flagها کنترل می‌شوند:

```dotenv
HISTORY_BACKEND_STRESS_FIXTURES_READY=1
DELIVERY_MERGE_STRESS_FIXTURES_READY=1
```

برای فعال‌سازی دوبارهٔ Stress، ابتدا باید policy غیرفعال‌سازی در تست‌ها و
`pytest.ini` بازبینی شود و fixtureهای Backend آماده باشند.
