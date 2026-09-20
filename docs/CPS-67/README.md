# CPS-67: Bag/Dispatch Storage (تخزین Bag و Dispatch)

این مستند تشریح‌کننده پیاده‌سازی و زیرساخت تست تسک **CPS-67** از سیستم **Core Post Sorting** (تیم B / Epic مدیریت جمع‌آوری و بسته‌بندی) است.

> **معماری:** پیاده‌سازی بر پایه **Clean Architecture** و **Domain-Driven Design (DDD)** با الگوی **CQRS سبک** و **Event-Driven** (مشابه CPS-58، CPS-74، CPS-77، CPS-82).

---

## 🎯 هدف بیزینسی (Business Goal)

ذخیره‌سازی اطلاعات **Bag** و **Dispatch** ارسال‌شده از Edge در Core برای:

- امکان **رهگیری**، **جستجو** و **مدیریت** بسته‌ها و ارسال‌ها در کل چرخه عمر
- فراهم کردن پایه برای **ParcelDossier Linking** (مرحله بعد)
- پشتیبانی از **Idempotency** برای جلوگیری از ثبت تکراری
- عدم ذخیره داده‌های حساس در پاسخ‌ها

**فاز 1 (Current):** فقط ذخیره‌سازی (Storage Only) — بدون محاسبه، بدون بسته‌سازی خودکار، بدون آمارگیری.

---

## 🌐 مشخصات سرویس

| مورد | مقدار |
|:---|:---|
| **Endpoint (Bag)** | `POST /api/edge/bags` |
| **Endpoint (Dispatch)** | `POST /api/edge/dispatches` |
| **Endpoint (Get Bag)** | `GET /api/edge/bags/{bagBarcode}` |
| **Endpoint (Get Dispatch)** | `GET /api/edge/dispatches/{dispatchId}` |
| **سرویس** | `DataIngestion.Api` / `Collection.Api` |
| **Response (Write)** | `202 Accepted` (Async) |
| **Response (Read)** | `200 OK` |
| **Error Responses** | `400 Bad Request`, `401 Unauthorized`, `404 Not Found`, `409 Conflict`, `500 Internal Server Error` |

---

## 📋 سناریوهای BDD تست‌شده (Acceptance Criteria)

| شناسه | عنوان سناریو | شرط | خروجی مورد انتظار |
|:---|:---|:---|:---|
| **TC-01** | ثبت موفق Bag | BagBarcode معتبر، تمام فیلدها پر | `202 Accepted`، `bagBarcode` برگردانده شود |
| **TC-02** | ثبت موفق Dispatch | DispatchId معتبر، تمام فیلدها پر | `202 Accepted`، `dispatchId` برگردانده شود |
| **TC-03** | Idempotent Bag (BagBarcode تکراری) | همان `idempotencyKey` و `bagBarcode` | `202 Accepted`، نتیجه یکسان (بدون خطا) |
| **TC-04** | درخواست بدون احراز هویت | بدون JWT Token | `401 Unauthorized` |
| **TC-05** | خطای اعتبارسنجی فیلدها | فیلدهای الزامی خالی (bagBarcode, memberBarcodes, correlationId, idempotencyKey) | `400 Bad Request` |
| **TC-06** | عدم لو رفتن اطلاعات حساس | پاسخ حاوی توکن/رمز/کلید | **ممنوع** (Security Assertion) |

---

## 📝 قرارداد درخواست (Real Core Contract)

### BagCloseRequest — POST /api/edge/bags

```json
{
  "bagBarcode": "string (required, max 64 chars)",
  "memberBarcodes": ["string array (required, min 1)"],
  "originCenter": "string (required, exactly 5 digits)",
  "destCenter": "string (required, exactly 5 digits)",
  "sealNumber": "string (required, max 32 chars)",
  "transportType": "string (required) - road|air|rail",
  "closedAtUtc": "date-time (required) - ISO 8601",
  "correlationId": "string (UUID v4, required)",
  "idempotencyKey": "string (>= 16 chars, required)",
  "createdByDeviceId": "string (optional)"
}
```

**Response (202 Accepted):**
```json
{
  "bagBarcode": "670000000000010000000001"
}
```

---

### DispatchRequest — POST /api/edge/dispatches

```json
{
  "dispatchId": "string (UUID, required)",
  "bagBarcodes": ["string array (required, min 1)"],
  "originCenter": "string (required, exactly 5 digits)",
  "destCenter": "string (required, exactly 5 digits)",
  "transportType": "string (required) - road|air|rail",
  "scheduledAtUtc": "date-time (required) - ISO 8601",
  "correlationId": "string (UUID v4, required)",
  "idempotencyKey": "string (>= 16 chars, required)"
}
```

**Response (202 Accepted):**
```json
{
  "dispatchId": "11111111-1111-1111-1111-444444444444"
}
```

---

### GET /api/edge/bags/{bagBarcode}

**Response (200 OK):**
```json
{
  "bagBarcode": "670000000000010000000001",
  "memberBarcodes": ["580000000000000000000001", "580000000000000000000002"],
  "originCenter": "59544",
  "destCenter": "71956",
  "sealNumber": "SEA-12345",
  "transportType": "road",
  "closedAtUtc": "2025-01-15T10:30:00Z",
  "createdByDeviceId": "DEVICE-001",
  "correlationId": "corr-cps67-success-001",
  "idempotencyKey": "idem-cps67-success-001-unique-key-12345",
  "createdAtUtc": "2025-01-15T10:30:05Z"
}
```

---

### GET /api/edge/dispatches/{dispatchId}

**Response (200 OK):**
```json
{
  "dispatchId": "11111111-1111-1111-1111-444444444444",
  "bagBarcodes": ["670000000000010000000001"],
  "originCenter": "59544",
  "destCenter": "71956",
  "transportType": "road",
  "scheduledAtUtc": "2025-01-15T12:00:00Z",
  "correlationId": "corr-cps67-success-001",
  "idempotencyKey": "idem-cps67-success-001-unique-key-12345",
  "createdAtUtc": "2025-01-15T10:30:05Z"
}
```

---

## ⚠️ نکات مهم

1. **Idempotency:** کلید `idempotencyKey` در سطح Domain/Application بررسی می‌شود. درخواست تکراری با همان کلید **بدون خطا** و با همان نتیجه پاسخ داده می‌شود (202 Accepted).
2. **Append-Only:** Bag و Dispatch هرگز حذف یا بازنویسی نمی‌شوند (Immutable).
3. **Event-Driven:** پس از ثبت موفق، رویدادهای `BagRegistered` / `DispatchRegistered` به صورت Async (non-blocking) منتشر می‌شوند.
4. **No Sensitive Data:** پاسخ‌ها هیچ‌وقت شامل `Authorization`، `Token`، `Secret`، `Password` یا کلیدهای خصوصی نیستند.
5. **Validation در Value Objects:** تمام اعتبارسنجی‌های فرمت (BagBarcode, DispatchId, ExchangeCenterCode, SealNumber, IdempotencyKey, CorrelationId) در Constructorهای Value Object انجام می‌شود.
6. **UTC Only:** تمام زمان‌ها به صورت UTC ذخیره و بازگشت داده می‌شوند.

---

## 🏗️ معماری کد (Clean Architecture)

```
src/
├── domain/bag_dispatch/                # Domain Layer
│   ├── value_objects/                  # BagBarcode, DispatchId, ExchangeCenterCode, TransportType,
│   │                                   # SealNumber, IdempotencyKey, CorrelationId, ParcelBarcode
│   ├── entities/                       # Bag, Dispatch (Aggregate Roots with Factory Methods)
│   ├── events/                         # BagRegistered, BagRegistrationFailed,
│   │                                   # DispatchRegistered, DispatchRegistrationFailed
│   ├── repositories/                   # BagRepository, DispatchRepository (Interfaces + Specs)
│   └── exceptions/                     # Domain Exceptions
│
├── application/                         # Application Layer
│   ├── commands/
│   │   ├── register_bag/               # RegisterBagCommand, RegisterBagResult, Handler, Validator
│   │   └── register_dispatch/          # RegisterDispatchCommand, RegisterDispatchResult, Handler, Validator
│   ├── queries/
│   │   ├── get_bag/                    # GetBagByBarcodeQuery, BagDTO, GetBagHandler
│   │   └── get_dispatch/               # GetDispatchByIdQuery, DispatchDTO, GetDispatchHandler
│   └── ports/                          # EventPublisherPort, BagDispatchPort (reuse from CPS-58)
│
├── infrastructure/                      # Infrastructure Layer
│   ├── persistence/
│   │   └── in_memory_bag_dispatch_repository.py  # InMemoryBagRepository, InMemoryDispatchRepository
│   ├── messaging/
│   │   └── event_publisher.py          # NullEventPublisher, InMemoryEventPublisher,
│   │                                   # RabbitMQEventPublisher, KafkaEventPublisher
│   └── config/
│       └── bag_dispatch_config.py      # BagDispatchConfig (env-driven)
│
├── interfaces/                          # Interface Layer
│   ├── rest/
│   │   ├── bag_dispatch_controller.py  # REST Controller (6 endpoints)
│   │   └── bag_dispatch_app.py         # FastAPI App with Pydantic Models
│   └── dto/
│       └── bag_dispatch_dto.py         # Request/Response DTOs + Converters
│
├── flows/bag_dispatch/                  # Test Flows
│   └── cps67_bag_dispatch_flow.py      # CPS-67 Flow (6 scenarios with run_step)
│
├── assertions/                          # Test Assertions
│   └── bag_dispatch_assertions.py      # Assertion Helpers
│
└── tests/unit/                          # Unit Tests
    └── test_cps67_core.py              # 6 Unit Tests (TC-01 to TC-06 + helpers)
```

---

## 🔑 الگوهای استفاده‌شده

| الگو | توضیح |
|:---|:---|
| **Value Objects** | `BagBarcode`, `DispatchId`, `ExchangeCenterCode`, `TransportType`, `SealNumber`, `IdempotencyKey`, `CorrelationId`, `ParcelBarcode` — اعتبارسنجی در Constructor |
| **Aggregate Root** | `Bag`, `Dispatch` — Factory Method (`create`) + Business Rules + `to_dict()` |
| **Domain Events** | `BagRegistered`, `BagRegistrationFailed`, `DispatchRegistered`, `DispatchRegistrationFailed` — انتشار Async پس از ثبت |
| **Repository Pattern** | `BagRepository`, `DispatchRepository` Interface — تفکیک Domain از Persistence |
| **CQRS سبک** | Commands (Write) جدا از Queries (Read) — `RegisterBagCommand` vs `GetBagByBarcodeQuery` |
| **Specification Pattern** | `BagSpec`, `DispatchSpec` — Queryهای انعطاف‌پذیر با Pagination |
| **Port/Adapter** | `EventPublisherPort` (reuse CPS-58), `BagDispatchPort` — تفکیک وابستگی‌ها |
| **Idempotency** | `IdempotencyKey` در سطح Domain/Application — جلوگیری از ثبت تکراری |
| **Result Pattern** | Handlerها `Result DTO` برمی‌گردانند (نه Exception برای کنترل بهتر در Controller) |

---

## 🚀 دستورات اجرا (CPS-67)

### اجرای تست E2E مسیر مثبت (Success):
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS67_SUCCESS="1"
.venv\Scripts\python.exe -m pytest tests/4_bagging -m cps67_success -q -s
```

### اجرای تست E2E مسیر منفی (Negative):
```powershell
$env:RUN_E2E="1"
$env:RUN_CPS67_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/4_bagging -m cps67_negative -q -s
```

### تست‌های واحد (Unit Tests - کاملاً آفلاین):
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps67_core.py -q -s
```

### اجرای ترکیبی CPS-67 با سایر تسک‌ها:
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps67_core.py tests/unit/test_cps58_core.py tests/unit/test_cps74_core.py tests/unit/test_cps77_core.py tests/unit/test_cps82_core.py -q
```

### اجرای FastAPI App (Development):
```powershell
.venv\Scripts\python.exe -m uvicorn interfaces.rest.bag_dispatch_app:app --reload --port 8081
```

---

## 🔧 پیکربندی (Configuration)

### در `config/settings.py`:
```python
# CPS-67 Bag/Dispatch Storage settings
core_bag_dispatch_path: str = os.getenv(
    "CORE_BAG_DISPATCH_PATH", "/api/edge/bags"
)
core_collection_dispatch_path: str = os.getenv(
    "CORE_COLLECTION_DISPATCH_PATH", "/api/edge/dispatches"
)
cps67_bag_barcode: str = os.getenv("CPS67_BAG_BARCODE", "670000000000010000000001")
cps67_dispatch_id: str = os.getenv("CPS67_DISPATCH_ID", "11111111-1111-1111-1111-444444444444")
cps67_origin_center: str = os.getenv("CPS67_ORIGIN_CENTER", "59544")
cps67_dest_center: str = os.getenv("CPS67_DEST_CENTER", "71956")
cps67_seal_number: str = os.getenv("CPS67_SEAL_NUMBER", "SEA-12345")
cps67_transport_type: str = os.getenv("CPS67_TRANSPORT_TYPE", "road")
cps67_scheduled_at_utc: str = os.getenv("CPS67_SCHEDULED_AT_UTC", "")
cps67_correlation_id: str = os.getenv("CPS67_CORRELATION_ID", "")
cps67_idempotency_key: str = os.getenv("CPS67_IDEMPOTENCY_KEY", "")
cps67_created_by_device_id: str = os.getenv("CPS67_CREATED_BY_DEVICE_ID", "")
```

### در `config/test.env.example`:
```bash
# CPS-67 Bag/Dispatch Storage settings
CORE_BAG_DISPATCH_PATH=/api/edge/bags
CORE_COLLECTION_DISPATCH_PATH=/api/edge/dispatches
CPS67_BAG_BARCODE=670000000000010000000001
CPS67_DISPATCH_ID=11111111-1111-1111-1111-444444444444
CPS67_ORIGIN_CENTER=59544
CPS67_DEST_CENTER=71956
CPS67_SEAL_NUMBER=SEA-12345
CPS67_TRANSPORT_TYPE=road
CPS67_SCHEDULED_AT_UTC=
CPS67_CORRELATION_ID=
CPS67_IDEMPOTENCY_KEY=
CPS67_CREATED_BY_DEVICE_ID=
```

### در `infrastructure/config/bag_dispatch_config.py`:
```python
@dataclass(frozen=True)
class BagDispatchConfig:
    database_connection_string: str = os.getenv("BAG_DISPATCH_DB_CONNECTION", "")
    event_publisher_type: str = os.getenv("BAG_DISPATCH_EVENT_PUBLISHER", "null").lower()
    rabbitmq_connection_url: str = os.getenv("BAG_DISPATCH_RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    rabbitmq_exchange: str = os.getenv("BAG_DISPATCH_RABBITMQ_EXCHANGE", "core.bag.dispatch")
    rabbitmq_routing_key: str = os.getenv("BAG_DISPATCH_RABBITMQ_ROUTING_KEY", "bag.dispatch.registered")
    kafka_bootstrap_servers: str = os.getenv("BAG_DISPATCH_KAFKA_SERVERS", "localhost:9092")
    kafka_topic: str = os.getenv("BAG_DISPATCH_KAFKA_TOPIC", "core.bag.dispatch.registered")
    kafka_client_id: str = os.getenv("BAG_DISPATCH_KAFKA_CLIENT_ID", "bag-dispatch-service")
    enable_bag_authorization: bool = os.getenv("BAG_DISPATCH_AUTH_CHECK", "true").lower() in ("1", "true", "yes", "on")
    enable_dispatch_authorization: bool = os.getenv("BAG_DISPATCH_DISPATCH_AUTH_CHECK", "true").lower() in ("1", "true", "yes", "on")
```

---

## 💡 مثال استفاده در کد (Python Domain)

```python
from domain.bag_dispatch.value_objects import (
    BagBarcode, DispatchId, ExchangeCenterCode, TransportType,
    SealNumber, CorrelationId, IdempotencyKey,
)
from domain.bag_dispatch.entities import Bag, Dispatch
from domain.bag_dispatch.events import BagRegistered, DispatchRegistered

# 1. ایجاد Bag با Factory
bag = Bag.create(
    bag_barcode=BagBarcode("670000000000010000000001"),
    member_barcodes=["580000000000000000000001", "580000000000000000000002"],
    origin_center=ExchangeCenterCode("59544"),
    dest_center=ExchangeCenterCode("71956"),
    seal_number=SealNumber("SEA-12345"),
    transport_type=TransportType.ROAD,
    closed_at_utc=datetime.fromisoformat("2025-01-15T10:30:00+00:00"),
    correlation_id=CorrelationId("11111111-1111-1111-1111-111111111111"),
    idempotency_key=IdempotencyKey("idem-unique-key-1234567890123456"),
    created_by_device_id="DEVICE-001",
)

# 2. تبدیل به Dict برای ذخیره/Event
bag_dict = bag.to_dict()

# 3. ساخت Event برای انتشار
event = BagRegistered.from_bag(bag)
await event_publisher.publish(event)

# 4. ایجاد Dispatch
dispatch = Dispatch.create(
    dispatch_id=DispatchId("11111111-1111-1111-1111-444444444444"),
    bag_barcodes=["670000000000010000000001"],
    origin_center=ExchangeCenterCode("59544"),
    dest_center=ExchangeCenterCode("71956"),
    transport_type=TransportType.ROAD,
    scheduled_at_utc=datetime.fromisoformat("2025-01-15T12:00:00+00:00"),
    correlation_id=CorrelationId("11111111-1111-1111-1111-111111111111"),
    idempotency_key=IdempotencyKey("idem-unique-key-1234567890123456"),
)

# 5. Query مثال
from application.queries.get_bag import GetBagHandler, GetBagByBarcodeQuery
from infrastructure.persistence.in_memory_bag_dispatch_repository import InMemoryBagRepository

repo = InMemoryBagRepository()
query_handler = GetBagHandler(repo)
result = query_handler.handle_by_barcode(GetBagByBarcodeQuery("670000000000010000000001"))
# result: BagDTO with all fields
```

---

## 🔐 امنیت و لاگینگ

* **Idempotency Key:** ≥ 16 کاراکتر، فقط ASCII قابل چاپ — جلوگیری از Replay Attack
* **Correlation ID:** UUID v4 — برای Distributed Tracing و لاگ‌های ساختاری
* **No IP Storage:** آدرس IP Device در Entity یا پاسخ‌ها ذخیره نمی‌شود
* **Structured Log:** شامل `Correlation-ID`، `BagBarcode`/`DispatchId`، `EventType`
* **Sensitive Data Check:**	Assertion در تست‌ها برای عدم لو رفتن `token`، `authorization`، `secret`، `password`، `apikey`
* **Transport Type Enum:** مقادیر مجاز `road`، `air`، `rail` — جلوگیری از تزریق مقدار نامعتبر
* **Center Code Validation:** دقیقاً ۵ رقم — جلوگیری از کدهای مرکز نامعتبر

---

## 📊 خروجی تست واحد (نمونه)

```text
========== Execution report: CPS-67 Bag/Dispatch Storage Flow ==========
01. [PASS] TC-01: Successful Bag registration
    payloadSent: {"method": "POST", "url": "http://localhost:5080/api/edge/bags", "payload": {"bagBarcode": "670000000000010000000001", "memberBarcodes": ["580000000000000000000001", "580000000000000000000002"], "originCenter": "59544", "destCenter": "71956", "sealNumber": "SEA-12345", "transportType": "road", "closedAtUtc": "2025-01-15T10:30:00Z", "correlationId": "corr-cps67-success-001", "idempotencyKey": "idem-cps67-success-001-unique-key-12345"}, "headers": {"Content-Type": "application/json", "X-Correlation-ID": "...", "Authorization": "<redacted>"}}
    responseReceived: {"statusCode": 202, "body": {"bagBarcode": "670000000000010000000001"}}
    expected: PASS

02. [PASS] TC-02: Successful Dispatch registration
    payloadSent: {"method": "POST", "url": "http://localhost:5080/api/edge/dispatches", "payload": {"dispatchId": "22222222-2222-2222-2222-555555555555", "bagBarcodes": ["670000000000010000000010", "670000000000010000000011"], "originCenter": "59544", "destCenter": "71956", "transportType": "road", "scheduledAtUtc": "2025-01-15T12:30:00Z", "correlationId": "corr-cps67-dispatch-001", "idempotencyKey": "idem-cps67-dispatch-001-unique-key-12345"}, "headers": {...}}
    responseReceived: {"statusCode": 202, "body": {"dispatchId": "22222222-2222-2222-2222-555555555555"}}
    expected: PASS

03. [PASS] TC-03: Idempotent Bag (same BagBarcode)
    payloadSent: {"method": "POST", "url": ".../api/edge/bags", "payload": {... "idempotencyKey": "idem-cps67-idempotent-001-unique-key-12345" ...}}
    responseReceived: {"statusCode": 202, "body": {"bagBarcode": "670000000000010000000020"}}
    expected: PASS

04. [PASS] TC-04: Unauthorized request (no token)
    payloadSent: {"method": "POST", "url": ".../api/edge/bags", "payload": {...}, "headers": {"Content-Type": "application/json", "X-Correlation-ID": "..."}}  # No Authorization
    responseReceived: {"statusCode": 401, "body": {"title": "Unauthorized", "status": 401, "detail": "Missing or invalid JWT authorization token"}}
    expected: PASS

05. [PASS] TC-05: Validation error (missing required fields)
    payloadSent: {"method": "POST", "url": ".../api/edge/bags", "payload": {"bagBarcode": "", "memberBarcodes": [], "correlationId": "", "idempotencyKey": "", ...}}
    responseReceived: {"statusCode": 400, "body": {"title": "Bad Request", "status": 400, "detail": "Validation failed: bagBarcode, memberBarcodes, correlationId, idempotencyKey are required"}}
    expected: PASS

06. [PASS] TC-06: No sensitive data leakage in response
    payloadSent: {... "sealNumber": "SEA-12350" ...}
    responseReceived: {"statusCode": 202, "body": {"bagBarcode": "670000000000010000000060"}}
    expected: PASS

Result: PASS=6, FAIL=0, NOT_CHECKED=0
```

---

## 🔗 ارتباط با سایر تسک‌ها

| تسک | ارتباط |
|:---|:---|
| **CPS-58** (Image Metadata) | EventPublisherPort مشترک برای انتشار رویدادها |
| **CPS-74** (Sorting Device) | Device Registration برای Auth در مراحل بعد |
| **CPS-77** (Bootstrap Config) | ExchangeCenterCode از Config سnapshot خوانده می‌شود |
| **CPS-82** (Edge Health) | Health Check برای Edgeهایی که Bag/Dispatch می‌فرستند |
| **EPS-76/EPS-79/EPS-83** (Bagging) | Bag Close در Edge → CPS-67 در Core ثبت می‌شود |
| **EPS-113** (Monitoring) | رویدادهای `BagRegistered`/`DispatchRegistered` برای Event Monitoring |
| **ParcelDossier (Future)** | Consumer رویدادها به ParcelDossier لینک می‌کند |

---

## ✅ Checklist پیاده‌سازی

- [x] Domain: value_objects (BagBarcode, DispatchId, ExchangeCenterCode, TransportType, SealNumber, IdempotencyKey, CorrelationId, ParcelBarcode), entities (Bag, Dispatch), events (BagRegistered, BagRegistrationFailed, DispatchRegistered, DispatchRegistrationFailed), repositories (BagRepository, DispatchRepository + Specs), exceptions
- [x] Application: Commands (register_bag, register_dispatch) + Handlers + Validators, Queries (get_bag, get_dispatch) + Handlers + DTOs
- [x] Infrastructure: InMemoryBagRepository, InMemoryDispatchRepository, BagDispatchConfig, EventPublisher implementations
- [x] Interfaces: BagDispatchController (6 endpoints), BagDispatchApp (FastAPI + Pydantic), Request/Response DTOs
- [x] Flows: cps67_bag_dispatch_flow.py (6 scenarios with run_step)
- [x] Assertions: bag_dispatch_assertions.py
- [x] Unit Tests: test_cps67_core.py (6 flow tests + domain/VO tests)
- [x] Config: settings.py, test.env.example (cps67_* settings)
- [x] Markers: pytest.ini (cps67, cps67_success, cps67_negative)
- [x] Documentation: docs/CPS-67/README.md

---

## 📝 نکات مهم پیاده‌سازی

1. **Phase 1 Scope:** فقط Storage. هیچ منطق محاسبه، Auto-Close، یا Statistics وجود ندارد.
2. **Event Publishing:** Async fire-and-follow — Handler صبر نمی‌کند.
3. **Controller Pattern:** بازگشت `(status_code, result)` برای کنترل کامل HTTP Status.
4. **Pydantic Validation:** در FastAPI App برای اعتبارسنجی اولیه Request Body.
5. **Configuration-Driven:** تمام مقادیر پیش‌فرض از Environment Variables خوانده می‌شوند.
6. **Open/Closed Principle:** قابلیت افزودن TransportType جدید، Query Spec جدید بدون تغییر کد موجود.

---

**Version:** 1.0.0  
**Status:** ✅ Complete  
**Date:** 2025-01-15