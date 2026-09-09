# CPS-58: ثبت Metadata تصویر و ارتباط با مرسوله (Image Metadata Registration)

این مستند تشریح‌کننده پیاده‌سازی و زیرساخت تست تسک **CPS-58** از سیستم **Core Post Sorting** (تیم B / Epic مدیریت تصاویر مرسولات) است.

> **معماری:** پیاده‌سازی بر پایه **Clean Architecture** و **Domain-Driven Design (DDD)** با الگوی **CQRS سبک** و **Event-Driven**.

---

## 🎯 هدف بیزینسی (Business Goal)

پس از بارگذاری موفق تصویر در Object Storage (via CPS-80)، **اطلاعات توصیفی (Metadata)** آن را در Core ثبت کن تا:
- امکان **رهگیری**، **بازیابی** و **مدیریت** تصاویر در کل چرخه عمر مرسوله فراهم شود
- فایل اصلی **هرگز در SQL Server ذخیره نشود** (فقط ObjectKey)
- ارتباط با **ParcelDossier** و **ReadingRecord** (اختیاری) برقرار شود

---

## 🌐 مشخصات سرویس

| مورد | مقدار |
|:---|:---|
| **Endpoint** | `POST /api/edge/images/metadata` |
| **سرویس** | `DataIngestion.Api` |
| **Response** | `202 Accepted` (Async) |
| **Error Responses** | `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `409 Conflict`, `413 Payload Too Large`, `415 Unsupported Media Type`, `503 Service Unavailable` |

---

## 📋 سناریوهای BDD تست‌شده (Acceptance Criteria)

| شناسه | عنوان سناریو | شرط | خروجی مورد انتظار |
|:---|:---|:---|:---|
| **TC-01** | ثبت موفق Metadata | تصویر آپلود شده | `202 Accepted`، `attachmentId` تولید شود |
| **TC-02** | Idempotency (جلوگیری از تکرار) | `idempotencyKey` تکراری | `202 Accepted`، `attachmentId` یکسان |
| **TC-03** | رد ObjectKey نامعتبر (Path Traversal) | `../` در ObjectKey | `400 Bad Request` |
| **TC-04** | رد بدون احراز هویت | بدون JWT | `401 Unauthorized` |
| **TC-05** | خطای اعتبارسنجی فیلدها | فیلدهای الزامی خالی | `400 Bad Request` |
| **TC-06** | عدم لو رفتن اطلاعات حساس | پاسخ حاوی توکن/رمز | **ممنوع** (Security Check) |

---

## 📝 قرارداد درخواست (Real Core Contract)

**Endpoint:** `POST /api/edge/images/metadata`

**Request (ImageMetadataRequest):**
```json
{
  "parcelBarcode": "string (24 digits, required)",
  "edgeId": "string (required)",
  "objectKey": "string (required) - path in Object Storage",
  "contentType": "string (required) - MIME type",
  "attachmentType": "string (required) - ParcelTopView|ParcelSideView|LabelImage|DamageImage|SealImage|Other",
  "occurredAtUtc": "date-time (required) - ISO 8601",
  "correlationId": "string (UUID, required)",
  "idempotencyKey": "string (>= 16 chars, required)",
  "readingRecordId": "string (UUID, optional)"
}
```

**Response:** `202 Accepted` with optional `attachmentId`

---

## 🏗️ معماری کد (Clean Architecture)

```
src/
├── domain/                          # Domain Layer
│   └── image_metadata/
│       ├── value_objects/            # ObjectKey, IdempotencyKey, AttachmentType, ...
│       ├── entities/                 # SupplementaryAttachment
│       ├── events/                   # ImageMetadataRegistered, ImageMetadataRegistrationFailed
│       ├── repositories/             # ImageMetadataRepository (Interface)
│       └── exceptions/               # Domain Exceptions
│
├── application/                     # Application Layer
│   ├── commands/
│   │   └── register_image_metadata/  # Command, Handler, Validator
│   ├── queries/
│   │   └── get_image_metadata/       # Query, Handler, DTOs
│   └── ports/                       # EventPublisherPort, ParcelDossierPort
│
├── infrastructure/                  # Infrastructure Layer
│   ├── persistence/                 # InMemoryRepository, SqlRepository
│   ├── messaging/                   # EventPublisher (RabbitMQ, Kafka, InMemory)
│   ├── config/                      # ImageMetadataConfig
│   └── parcel_port.py              # HttpParcelDossierPort, InMemoryParcelDossierPort
│
├── interfaces/                      # Interface Layer
│   ├── rest/
│   │   ├── controller.py           # ImageMetadataController
│   │   └── app.py                  # FastAPI App
│   └── dto/                         # Request/Response DTOs
│
├── flows/images/                    # Test Flows
│   └── cps58_image_metadata_flow.py
│
├── assertions/                      # Test Assertions
│   └── image_metadata_assertions.py
│
└── tests/unit/                      # Unit Tests
    └── test_cps58_core.py
```

---

## 🔑 الگوهای استفاده‌شده

| الگو | توضیح |
|:---|:---|
| **Value Objects** | `ObjectKey`, `IdempotencyKey`, `ParcelBarcode`, ... — اعتبارسنجی در Constructor |
| **Entity** | `SupplementaryAttachment` — Aggregate Root با Factory Method |
| **Domain Events** | `ImageMetadataRegistered` — انتشار Async پس از ثبت |
| **Repository Pattern** | `ImageMetadataRepository` Interface — تفکیک Domain از Persistence |
| **CQRS سبک** | Commands (Write) جدا از Queries (Read) |
| **Specification Pattern** | `ImageMetadataSpec` — Queryهای انعطاف‌پذیر |
| **Port/Adapter** | `EventPublisherPort`, `ParcelDossierPort` — تفکیک وابستگی‌ها |
| **Idempotency** | `IdempotencyKey` در سطح Domain/Application — جلوگیری از ثبت تکراری |

---

## 🚀 دستورات اجرا

### تست‌های واحد (Unit Tests - کاملاً آفلاین):
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps58_core.py -q -s
```

### اجرای FastAPI App (Development):
```powershell
.venv\Scripts\python.exe -m uvicorn interfaces.rest.app:app --reload --port 8080
```

### تست‌های ترکیبی CPS-58 با سایر تسک‌ها:
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps58_core.py tests/unit/test_cps80_core.py tests/unit/test_cps86_core.py -q
```

---

## 🔧 پیکربندی (Configuration)

### در `config/settings.py`:
```python
# CPS-58: Image Metadata Registration settings
core_image_metadata_path: str = os.getenv(
    "CORE_IMAGE_METADATA_PATH", "/api/edge/images/metadata"
)
cps58_parcel_barcode: str = os.getenv("CPS58_PARCEL_BARCODE", "580000000000000000000001")
cps58_edge_id: str = os.getenv("CPS58_EDGE_ID", "EDGE-TEST-001")
cps58_object_key: str = os.getenv("CPS58_OBJECT_KEY", "parcels/2025/03/10/580000000000000000000001_top.jpg")
cps58_bucket_name: str = os.getenv("CPS58_BUCKET_NAME", "parcel-images")
cps58_content_type: str = os.getenv("CPS58_CONTENT_TYPE", "image/jpeg")
cps58_attachment_type: str = os.getenv("CPS58_ATTACHMENT_TYPE", "ParcelTopView")
```

### در `.env`:
```bash
CORE_IMAGE_METADATA_PATH=/api/edge/images/metadata
CPS58_PARCEL_BARCODE=580000000000000000000001
CPS58_EDGE_ID=EDGE-TEST-001
CPS58_DEVICE_ID=DEVICE-TEST-001
CPS58_CENTER_ID=59544
CPS58_OBJECT_KEY=parcels/2025/03/10/580000000000000000000001_top.jpg
CPS58_BUCKET_NAME=parcel-images
CPS58_CONTENT_TYPE=image/jpeg
CPS58_FILE_SIZE_BYTES=102400
CPS58_ATTACHMENT_TYPE=ParcelTopView
```

---

## 💡 مثال استفاده در کد

```python
from interfaces.dto import RegisterImageMetadataRequestDTO
from interfaces.rest.controller import ImageMetadataController
from application.commands.register_image_metadata import RegisterImageMetadataHandler
from application.queries.get_image_metadata import GetImageMetadataHandler
from infrastructure.persistence.in_memory_repository import InMemoryImageMetadataRepository
from infrastructure.messaging.event_publisher import InMemoryEventPublisher
from infrastructure.parcel_port import InMemoryParcelDossierPort

# 1. Dependency Injection
repo = InMemoryImageMetadataRepository()
event_publisher = InMemoryEventPublisher()
parcel_port = InMemoryParcelDossierPort()

cmd_handler = RegisterImageMetadataHandler(
    repository=repo,
    event_publisher=event_publisher,
    parcel_port=parcel_port,
)
query_handler = GetImageMetadataHandler(repository=repo)
controller = ImageMetadataController(cmd_handler, query_handler)

# 2. Register Metadata
request = RegisterImageMetadataRequestDTO(
    parcel_barcode="580000000000000000000001",
    edge_id="EDGE-TEST-001",
    device_id="DEVICE-TEST-001",
    center_id="59544",
    object_key="parcels/2025/03/10/580000000000000000000001_top.jpg",
    bucket_name="parcel-images",
    content_type="image/jpeg",
    file_size_bytes=102400,
    attachment_type="ParcelTopView",
    correlation_id="11111111-1111-1111-1111-111111111111",
    idempotency_key="idem-12345678901234567890",
    occurred_at_utc="2025-01-15T10:30:00Z",
)

status_code, response = await controller.register_metadata(request)
# status_code: 202
# response: RegisterImageMetadataResponseDTO(success=True, attachment_id="...")

# 3. Query Metadata
from interfaces.dto import GetImageMetadataByIdQuery
result = query_handler.handle_by_id(GetImageMetadataByIdQuery(attachment_id))
# result: ImageMetadataDTO with all metadata
```

---

## 📊 خروجی تست واحد (نمونه)

```text
Execution report: CPS-58 Image Metadata Registration Flow
01. [PASS] TC-01: Successful metadata registration after upload
    payloadSent: {"method": "POST", "url": "http://192.168.20.196:5080/api/edge/images/metadata", "payload": {"parcelBarcode": "580000000000000000000001", "edgeId": "EDGE-TEST-001", "objectKey": "parcels/2025/03/10/580000000000000000000001_top.jpg", "contentType": "image/jpeg", "attachmentType": "ParcelTopView", ...}, "headers": {"Content-Type": "application/json", "X-Correlation-ID": "...", "Authorization": "<redacted>"}}
    responseReceived: {"statusCode": 202, "body": {"attachmentId": "11111111-1111-1111-1111-111111111111"}}
    expected: PASS

02. [PASS] TC-02: Idempotent retry with same idempotency key
    payloadSent: {... "idempotencyKey": "idem-cps58-idempotent-001-unique-key-12345" ...}
    responseReceived: {"statusCode": 202, "body": {"attachmentId": "11111111-1111-1111-1111-111111111111"}}
    expected: PASS

03. [PASS] TC-03: Invalid ObjectKey rejected (path traversal attempt)
    payloadSent: {... "objectKey": "../etc/passwd" ...}
    responseReceived: {"statusCode": 400, "body": {"title": "Bad Request", "detail": "Invalid ObjectKey"}}
    expected: PASS

04. [PASS] TC-04: Unauthorized request rejected (no token)
    payloadSent: {... headers without Authorization ...}
    responseReceived: {"statusCode": 401, "body": {"title": "Unauthorized", "status": 401}}
    expected: PASS

05. [PASS] TC-05: Validation error for missing required fields
    payloadSent: {... "parcelBarcode": "", "correlationId": "", "idempotencyKey": "" ...}
    responseReceived: {"statusCode": 400, "body": {"title": "Bad Request", "detail": "Validation failed"}}
    expected: PASS

06. [PASS] TC-06: No sensitive data leaked in response
    payloadSent: {... "attachmentType": "DamageImage" ...}
    responseReceived: {"statusCode": 202, "body": {"attachmentId": "..."}}
    expected: PASS

Result: PASS=6, FAIL=0, NOT_CHECKED=0
```

---

## 🔗 ارتباط با سایر تسک‌ها

| تسک | ارتباط |
|:---|:---|
| **CPS-80** (Pre-signed URL) | CPS-80 Pre-signed URL صادر می‌کند → Edge عکس آپلود می‌کند → **CPS-58 Metadata ثبت می‌کند** |
| **EPS-64** (Lazy Upload) | تصاویر بصورت ناهمگام آپلود و Metadata ثبت می‌شود |
| **CPS-20** (Inbound Query) | Metadata تصاویر مرتبط با مرسوله قابل بازیابی است |
| **EPS-113** (Monitoring) | رویدادهای ImageMetadataRegistered برای Event Monitoring |

---

## 🔐 امنیت و لاگینگ

* **مسیر فایل**: هرگز مستقیماً در اختیار کاربر قرار نگیرد (فقط ObjectKey)
* **ObjectKey Validation**: جلوگیری از Path Traversal (`../`)
* **Idempotency**: جلوگیری از ثبت تکراری در سطح Domain
* **No File in DB**: فایل تصویر هرگز در SQL Server ذخیره نشود
* **Structured Log**: شامل `Correlation-ID`، `AttachmentId`، `ParcelBarcode`
* **Sensitive Data**: بررسی عدم لو رفتن Token/Secret در پاسخ

---

## 📝 نکات مهم پیاده‌سازی

1. **Append-Only**: Metadata هرگز حذف یا بازنویسی نمی‌شود (Immutable)
2. **Event-Driven**: انتشار `ImageMetadataRegistered` بصورت Async (non-blocking)
3. **Idempotency**: با `IdempotencyKey` در سطح Domain
4. **Provider-Agnostic**: وابستگی به MinIO/S3 در Domain وجود ندارد
5. **Clean Architecture**: جداسازی کامل Domain/Application/Infrastructure/Interface
6. **Open/Closed**: قابلیت افزودن `AttachmentType` جدید بدون تغییر کد موجود
7. **Configuration-Driven**: تمام مقادیر از Config خوانده می‌شوند