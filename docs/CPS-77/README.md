# CPS-77: Bootstrap Configuration Management

این مستند تشریح‌کننده پیاده‌سازی تست تسک **CPS-77** از سیستم **Core Post Sorting** است.

> **معماری:** Clean Architecture + DDD با CQRS سبک و Event-Driven (مشابه CPS-58/67/74).

---

## 🎯 هدف بیزینسی

مدیریت اسنپ‌شات‌های پیکربندی **Immutable** برای مراکز تبادل. دستگاه‌های Edge در startup/sync آخرین اسنپ‌شات منتشرشده را دریافت می‌کنند:

- Immutable Snapshots — پس از ایجاد هرگز تغییر نمی‌کند؛ تغییر = اسنپ‌شات جدید
- نسخه‌بندی صعودی (Monotonic) به‌ازای هر ExchangeCenterCode
- فقط **یک** اسنپ‌شات Published در هر لحظه برای هر مرکز
- Edge فقط Published را می‌بیند (Draftها مخفی)
- `parcelHistoryCheckEnabled` تعیین می‌کند Edge به CPS-20 صدا بزند یا نه

---

## 🌐 قرارداد سرویس (Real Core Contract)

| متد | مسیر | توضیح |
|:---|:---|:---|
| GET | `/api/edge/bootstrap?exchangeCenterCode={code}` | آخرین اسنپ‌شات Published مرکز |
| GET | `/api/edge/bootstrap?exchangeCenterCode={code}&version={v}` | نسخه خاص (فقط اگر Published) |
| GET | `/api/admin/configurations` | لیست اسنپ‌شات‌ها (Admin) |
| POST | `/api/admin/configurations` | ساخت اسنپ‌شات Draft (Admin) |
| POST | `/api/admin/configurations/{id}/publish` | انتشار Draft (Admin) |

### BootstrapResponse (Edge):

```json
{
  "configVersion": 5,
  "exchangeCenterCode": "59544",
  "generatedAtUtc": "2025-01-15T10:30:00Z",
  "publishedAtUtc": "2025-01-15T10:30:00Z",
  "devices": [
    {"deviceId": "guid", "logicalCode": "SORT-001", "deviceType": "Sorter", "status": "Active", "exchangeCenterCode": "59544"}
  ],
  "operationalSettings": {
    "parcelHistoryCheckEnabled": true,
    "repeatReadingThresholdHours": 6,
    "returnToOriginThresholdHours": 72,
    "duplicateReadThresholdHours": 6,
    "returnedThresholdHours": 72
  },
  "routingCodes": {
    "originCodes": ["59544"],
    "destinationCodes": ["11369", "71956"],
    "chuteMapping": {"CH-01": "11369", "CH-02": "71956"}
  },
  "metadata": {"createdBy": "admin-user", "description": "Initial config"}
}
```

---

## 📋 سناریوهای BDD (۹ سناریو)

| شناسه | سناریو | خروجی مورد انتظار |
|:---|:---|:---|
| TC-01 | Bootstrap موفق | `200` آخرین Published |
| TC-02 | نسخه‌بندی Immutable | نسخه جدید = قدیمی + ۱ |
| TC-03 | همگرایی Edge | دریافت نسخه جدید و جایگزینی |
| TC-04 | مرکز نامعتبر | `404` |
| TC-05 | تغییر وضعیت دستگاه در اسنپ‌شات جدید | `200` با وضعیت جدید |
| TC-06 | درخواست غیرمجاز | `401` |
| TC-07 | فقط Published برگردد | Draftها مخفی |
| TC-08 | `parcelHistoryCheckEnabled=false` | Edge از CPS-20 رد می‌شود |
| TC-09 | `parcelHistoryCheckEnabled=true` | Edge به CPS-20 صدا می‌زند |

---

## 🏗️ معماری کد

```
domain/bootstrap_config/
├── value_objects/   # SnapshotId, ConfigVersion, ExchangeCenterCode, PublicationStatus,
│                    # DeviceSnapshot, OperationalSettings, RoutingCodes, SnapshotMetadata, CorrelationId
├── entities/        # ConfigurationSnapshot (Aggregate Root - Immutable)
├── events/          # ConfigurationSnapshotCreated/Published/Archived
├── repositories/    # ConfigurationSnapshotRepository
└── exceptions/      # Domain exceptions
application/
├── commands/create_snapshot/   # Command + Handler + Validator
├── commands/publish_snapshot/  # Command + Handler
├── queries/get_bootstrap/      # Query + DTO + Handler
└── queries/get_snapshots/      # Query + DTO + Handler
infrastructure/persistence/  # InMemoryConfigurationSnapshotRepository
interfaces/
├── rest/  # bootstrap_controller.py, admin_config_controller.py
└── dto/   # bootstrap_dto.py
flows/bootstrap/      # cps77_bootstrap_flow.py
assertions/           # bootstrap_assertions.py
tests/unit/           # test_cps77_core.py
```

---

## 🔑 قوانین دامنه

1. **هویت ترکیبی:** `(ExchangeCenterCode, ConfigVersion)` + `SnapshotId` یکتا
2. **چرخه عمر:** Draft → Published → Archived
3. انتشار نسخه جدید، نسخه Published قبلی را Archive می‌کند
4. نسخه خاص از Edge فقط در صورت Published برگردد

---

## 🚀 اجرا

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps77_core.py -q -s
```

---

## 🔧 پیکربندی

```python
# config/settings.py
core_bootstrap_path: str = os.getenv("CORE_BOOTSTRAP_PATH", "/api/edge/bootstrap")
core_admin_configurations_path: str = os.getenv("CORE_ADMIN_CONFIGURATIONS_PATH", "/api/admin/configurations")
cps77_exchange_center_code: str = os.getenv("CPS77_EXCHANGE_CENTER_CODE", "59544")
cps77_auto_sync_enabled: bool = ...
```

```bash
# config/test.env.example
CORE_BOOTSTRAP_PATH=/api/edge/bootstrap
CORE_ADMIN_CONFIGURATIONS_PATH=/api/admin/configurations
CPS77_EXCHANGE_CENTER_CODE=59544
CPS77_AUTO_SYNC_ENABLED=true
```

---

**Version:** 1.0.0
**Status:** ✅ Complete
**Date:** 2025-01-15
