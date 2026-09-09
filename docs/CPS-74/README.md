# CPS-74: Sorting Device Management (Device Lifecycle)

این مستند تشریح‌کننده پیاده‌سازی و زیرساخت تست تسک **CPS-74** از سیستم **Core Post Sorting** است.

> **معماری:** پیاده‌سازی بر پایه **Clean Architecture** و **Domain-Driven Design (DDD)** با الگوی **CQRS سبک** و **Event-Driven**.

---

## 🎯 هدف بیزینسی (Business Goal)

حذف ناپایدار (Soft Delete) و لایف‌سیکل کامل Deviceهای سورتینگ در Core با قوانین کسب‌وکار محکم:

- Admin يمكن مدیریت کامل Deviceها (ثبت، ویرایش فعال/غیرفعال)
- LogicalCode unique در کل سیستم - برای رهگیری و کاربردهای عملیاتی
- DeviceId/DeviceToken به صورت امن تولید شده - unguessable
- exchangeCenterCode داده‌های Hardware - immutable بعد از ایجاد
- چرخه عمر Soft (Active/Inactive) - چیزی حذف نمی‌شود
- هیچ‌وقت IP احراز هویت Device ذخیره نمی‌شود
- Device تعاملی (auth) فقط با Device فعال قابل استفاده است

---

## 🌐 مشخصات سرویس

| مورد | مقدار |
|:---|:---|
| **Endpoint** | `POST /api/edge/devices` |
| **Endpoint** | `GET /api/edge/devices/{deviceId}` |
| **Endpoint** | `GET /api/edge/devices/logical/{logicalCode}` |
| **Endpoint** | `PUT /api/edge/devices/{deviceId}` |
| **Endpoint** | `POST /api/edge/devices/{deviceId}/deactivate` |
| **Endpoint** | `POST /api/edge/devices/{deviceId}/activate` |
| **سرویس** | `DeviceManagement.Api` |
| **Response** | `201 Created` (registration), `200 OK` (others) |
| **Error Responses** | `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `409 Conflict`, `500 Internal Server Error` |

---

## 📋 سناریوهای BDD تست‌شده (Acceptance Criteria)

| شناسه | عنوان سناریو | شرط | خروجی مورد انتظار |
|:---|:---|:---|:---|
| **TC-01** | ثبت موفق Device | registering device with valid data | `201 Created`، `deviceId`, `deviceToken` تولید شود |
| **TC-02** |LogicalCode تکراری | تلاش برای ثبت LogicalCode دو بار | `409 Conflict`، DuplicateLogicalCodeError |
| **TC-03** | بروزرسانی صرفاً توصیفی | update name/owner/description only | `200 OK`، deviceId/deviceToken/logicalCode/centerCode unchanged |
| **TC-04** | تلاش برای تغییر centerCode | update attempting to change exchangeCenterCode | `400 Bad Request`، ExchangeCenterCodeNotImmutableError |
| **TC-05** | غیرفعال‌سازی Device | deactivate active device | `200 OK`، status تبدیل به Inactive |
| **TC-06** | احراز هویت Device غیرفعال | Device با توکن نادرست یا در وضعیت Inactive | `401/403 Unauthorized`، InvalidDeviceToken |
| **TC-07** | بدون ذخیره IP | Device ثبت شده | هیچ‌وقت field IP در داده‌ها نیست |

---

## ⚠️ نکات مهم

1. **Soft Lifecycle:** Device هرگز حذف نمی‌شود. فقط وضعیت به Inactive تغییر می‌کند.
2. **LogicalCode Unique:** LogicalCode طول عمر چرخه مدیران Deviceهای سورتینگ.
3. **Tokens Secure:** DeviceToken با `secrets.token_hex(32)` (64 hex chars) تولید می‌شود و به صورت Hash ذخیره می‌شود. Plain همیشه در پاسخ از Core برگردانده می‌شود.
4. **Immutable CenterCode:** exchangeCenterCode با داده‌های Hardware اصلی (SKU) متصل است؛ نمی‌توان تغییر داد.
5. **No IP Storage:** هیچ‌وقتی آدرس IP برای احراز هویت Device ذخیره نمی‌شود (پیام امنیتی).
6. **Event-Driven:** DeviceRegistered، DeviceUpdated، DeviceDeactivated، DeviceActivated در Thread غیرهمگام منتشر می‌شوند.

---

## 📝 قرارداد درخواست (Real Core Contract)

### RegisterDeviceRequest (POST /api/edge/devices):
```json
{
  "name": "string (required, max 100)",
  "deviceType": "string (required) - Sorter|Scanner|Camera|Printer|Conveyor",
  "logicalCode": "string (required, unique across system)",
  "owner": "string (required)",
  "exchangeCenterCode": "string (required, 5 digits, IMMUTABLE after creation)",
  "description": "string (optional, max 500)",
  "correlationId": "string (UUID, required)"
}
```

### RegisterDeviceResponse (201 Created):
```json
{
  "deviceId": "guid (generated)",
  "deviceToken": "string (generated secure token)",
  "logicalCode": "string",
  "status": "Active",
  "createdAtUtc": "date-time"
}
```

### UpdateDeviceRequest (PUT /api/edge/devices/{deviceId}):
```json
{
  "name": "string (optional)",
  "owner": "string (optional)",
  "description": "string (optional)",
  "correlationId": "string (required)"
}
```
**NOTE:** exchangeCenterCode CANNOT be changed - returns 400 if attempted.

### Response (All successful requests):
```json
{
  "deviceId": "guid",
  "logicalCode": "string",
  "name": "string",
  "owner": "string",
  "description": "string|null",
  "deviceType": "string",
  "exchangeCenterCode": "string",
  "status": "Active|Inactive",
  "createdAtUtc": "date-time",
  "updatedAtUtc": "date-time|null"
}
```

### Deactivate/Activate Response (200 OK):
```json
{
  "deviceId": "guid",
  "status": "Inactive|Active",
  "updatedAtUtc": "date-time"
}
```

---

## 🏗️ معماری کد (Clean Architecture)

```
src/
├── domain/sorting_device/          # Domain Layer
│   ├── value_objects/             # DeviceId, DeviceToken, LogicalCode, DeviceType, DeviceStatus, ExchangeCenterCode, CorrelationId
│   ├── entities/                  # SortingDevice (Aggregate Root with business rules)
│   ├── events/                    # DeviceRegistered, DeviceUpdated, DeviceDeactivated, DeviceActivated
│   ├── repositories/              # SortingDeviceRepository (Interface)
│   └── exceptions/                # Domain exceptions
│
├── application/                    # Application Layer
│   ├── commands/                  # register_device, update_device, deactivate_device, activate_device
│   │   ├── __init__.py            # Command & Result DTOs
│   │   ├── handler.py             # Command Handlers
│   │   └── validator.py           # Validators (optional, could use Domain validation)
│   ├── queries/                   # get_device (by id/logical code)
│   │   ├── __init__.py            # Query & Handler
│   │   └── handler.py
│   └── ports/                     # EventPublisherPort (reuse from CPS-58)
│
├── infrastructure/                 # Infrastructure Layer
│   └── persistence/               # InMemorySortingDeviceRepository
│
├── interfaces/                     # Interface Layer
│   ├── rest/                      # DeviceController + app.py
│   └── dto/                       # Request/Response DTOs
│
├── flows/device/                   # Test Flows
│   └── cps74_device_flow.py
│
├── assertions/                     # Test Assertions
│   └── device_assertions.py
│
└── tests/unit/                     # Unit Tests
    └── test_cps74_core.py
```

---

## 🔑 الگوهای استفاده‌شده

| الگو | توضیح |
|:---|:---|
| **Aggregate Root** | `SortingDevice` - مدیریت لایف‌سیکل با قوانین محکم |
| **Value Objects** | تمام اعداد معنایی - اعتبارسنجی در Constructor |
| **Domain Events** | `DeviceRegistered`, `DeviceUpdated`, `DeviceDeactivated`, `DeviceActivated` |
| **Repository Pattern** | `SortingDeviceRepository` - تفکیک Domain از Persistence |
| **CQRS سبک** | Commands (Write) Power separate from Queries (Read) |
| **Immutability** | deviceId/deviceToken/logicalCode never change |  
| **Event-Driven** | انتشار Event پس از تغییرات در Thread غیرهمگام |
| **Enum-based Types** | `DeviceType`, `DeviceStatus` - datatype-immutability |
| **Secure Token Storage** | DeviceToken as SHA-256 hash; plain returned first time |

---

## 🚀 دستورات اجرا (CPS-74)

### تست‌های واحد (Unit Tests - کاملاً آفلاین):
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps74_core.py -q -s
```

### اجرای ترکیبی CPS-74 با سایر تسک‌ها:
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps74_core.py tests/unit/test_cps58_core.py tests/unit/test_cps58_core.py -q
```

---

## 🔧 پیکربندی (Configuration)

### در `config/settings.py`:
```python
# CPS-74: Sorting Device Management settings
core_device_path: str = os.getenv(
    "CORE_DEVICE_PATH", "/api/edge/devices"
)
cps74_device_name: str = os.getenv(
    "CPS74_DEVICE_NAME", "Main Conveyor Sorter"
)
cps74_exchange_center_code: str = os.getenv(
    "CPS74_EXCHANGE_CENTER_CODE", "11369"
)
```

### در `.env`:
```bash
CORE_DEVICE_PATH=/api/edge/devices
CPS74_DEVICE_NAME=Main Conveyor Sorter
CPS74_EXCHANGE_CENTER_CODE=11369
```

---

## 💡 مثال استفاده در کد (Python Domain)

```python
from domain.sorting_device.value_objects import (
    DeviceType, LogicalCode, ExchangeCenterCode, CorrelationId
)
from domain.sorting_device.entities import SortingDevice

# 1. ایجاد Device با Factory
device = SortingDevice.create(
    name="Primary Conveyor Sorter",
    device_type=DeviceType.SORTER,
    logical_code=LogicalCode("MLST-001"),
    owner="Central Operations",
    exchange_center_code=ExchangeCenterCode("11369"),
    description="Luxury sorting conveyor",
)

# 2. ساختار immutable fields را داشته است (generated by create)
print(device.device_id)          # DeviceId(generated)
print(device.device_token_plain) # Secure token string
print(str(device.logical_code))  # "MLST-001"
print(device.status)             # DeviceStatus.ACTIVE

# 3. اعتبارسنجی توکن
if device.verify_token(provided_token):
    print("Authentication successful")

# 4. تغییر وضعیت
device.deactivate()
assert device.status == DeviceStatus.INACTIVE
device.activate()
assert device.status == DeviceStatus.ACTIVE

# 5. update توصیفی
new_cid = CorrelationId.generate()
device.update_descriptive_fields(
    name="Updated Conveyor Sorter",
    owner="Operations Team",
    description="Updated description",
    correlation_id=new_cid,
)

# Verify immutables unchanged
assert device.device_id == initial_device_id
assert device.device_token_hash == initial_hash
assert device.logical_code == initial_code
assert device.exchange_center_code == initial_center_code

# Verify updated fields
assert device.name == "Updated Conveyor Sorter"
assert device.owner == "Operations Team"
assert device.correlation_id == new_cid
```

---

## 🔐 امنیت و لاگینگ

* **LogicalCode Unique:** جلوگیری از تداخل Deviceهای سورتینگ
* **Secure Tokens:** SHA-256 hash + random generation (64 hex chars)
* **No IP Storage:** discoverability محدود نگه داشته شود (در Forensics)
* **CorrelationId Audit Trail:** audit event-based برای monitoring
* **Soft Lifecycle:** Data never deleted for compliance

---

## 📊 خروجی تست واحد (نمونه - مختصر)

```text
========== Execution report: CPS-74 Sorting Device Management Flow ==========
01. [PASS] TC-01: Successful device registration
02. [PASS] TC-02: Duplicate logical code rejected
03. [PASS] TC-03: Update descriptive fields
04. [PASS] TC-04: ExchangeCenterCode change rejected
05. [PASS] TC-05: Deactivate device
06. [PASS] TC-06: Inactive device auth rejected
07. [PASS] TC-07: No IP stored in device data

Result: PASS=7, FAIL=0, NOT_CHECKED=0
```

---

## 🔗 ارتباط با سایر تسک‌ها

| تسک | ارتباط |
|:---|:---|
| **EPS-49** (Device Auth) | Deviceهای فعال برای EPS-49 auth باید ID/Token معتبر داشته باشند |
| **EPS-86** (Operational Results) | Device Registered/Updated/Deactivated events به Operational Results منتشر می‌شوند |
| **Postman EPS-74** | {(mediaType).null} Action: Add EPS-74 collection for endpoint testing |

---

## ✅ Checklist پایتک

- [x] Domain: value_objects, entity (SortableDevice), events, repository interface, exceptions
- [x] Application: Commands (register/update/deactivate/activate), Queries, Handlers, DTOs
- [x] Infrastructure: InMemory Repository (with duplicate LogicalCode check)
- [x] Interfaces: DeviceController, Request/Response DTOs
- [x] Flows: cps74_device_flow.py (7 scenarios)
- [x] Assertions: device_assertions.py
- [x] Unit Tests: test_cps74_core.py (7 flow tests + 10 domain/vo tests)
- [x] Config: settings.py, test.env.example (core_device_path, cps74_*)
- [x] Markers: pytest.ini (cps74_success, cps74_negative)
- [x] Documentation: docs/CPS-74/README.md
- [x] Commit: "feat(cps-74): implement CPS-74 Sorting Device Management with Clean Architecture, Device Lifecycle, Unit Tests"

---

**Version:** 1.0.0  
**Status:** ✅ Complete  
**Date:** 2025-01-15