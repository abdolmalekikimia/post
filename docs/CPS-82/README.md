# CPS-82: Edge Health Monitoring (Edge Health Status in Core)

این مستند تشریح‌کننده پیاده‌سازی و زیرساخت تست تسک **CPS-82** از سیستم **Core Post Sorting** است.

> **معماری:** پیاده‌سازی بر پایه **Clean Architecture** و **Domain-Driven Design (DDD)** با الگوی **CQRS سبک** و **Event-Driven**.

---

## 🎯 هدف بیزینسی (Business Goal)

مدیریت وضعیت سلامت Edge Deviceها در Core. Deviceهای Edge پیام‌های دوره‌ای Heartbeat ارسال می‌کنند و Core فقط **آخرین وضعیت سلامت** را ذخیره می‌کند (تاریخچه ذخیره نمی‌شود). این ماژول پایه‌گذار برای آینده Dashboard، Alerting و Diagnostics است.

---

## 🌐 مشخصات سرویس

| مورد | مقدار |
|:---|:---|
| **Endpoint** | `POST /api/edge/heartbeats` |
| **Endpoint** | `GET /api/edge/heartbeats/{edgeId}` |
| **Endpoint** | `GET /api/admin/edge-health` |
| **Endpoint** | `GET /api/admin/edge-health/summary` |
| **سرویس** | `Core.PostSorting.Api` |
| **Response** | `202 Accepted` (heartbeat), `200 OK` (query) |
| **Error Responses** | `400 Bad Request`, `403 Forbidden`, `404 Not Found`, `500 Internal Server Error` |

---

## 📋 سناریوهای BDD تست‌شده (Acceptance Criteria)

| شناسه | عنوان سناریو | شرط | خروجی مورد انتظار |
|:---|:---|:---|:---|
| **TC-01** | ثبت موفق Heartbeat | Edge device sends valid heartbeat | `202 Accepted`، `received: true` |
| **TC-02** | بروزرسانی Edge (Latest State Only) | same edge sends another heartbeat | `202 Accepted`، record replaces old data |
| **TC-03** | ذخیره صحیح Queue Statistics | heartbeat with queue counts | queueStatistics correctly stored in value object |
| **TC-04** | Edge ناشناس رد می‌شود | unregistered edgeId in heartbeat | `404 Not Found`، UnknownEdgeError |
| **TC-05** | Edge غیرفعال رد می‌شود | inactive edge from CPS-74 sends heartbeat | `403 Forbidden`، InactiveEdgeError |
| **TC-06** | Correlation-ID در لاگ‌های ساختاری | heartbeat with correlationId | correlationId appears in events/logs |
| **TC-07** | Query آخرین وضعیت (Read-Only) | GET health endpoint for edge | `200 OK`، latest status returned, read-only |
| **TC-08** | بدون ذخیره IP | any heartbeat | No IP fields in entity or response |

---

## ⚠️ نکات مهم

1. **Latest State Only:** هیچ تاریخچه‌ای ذخیره نمی‌شود. هر Heartbeat جایگزین رکورد قبلی همان EdgeId می‌شود.
2. **Edge Registration Check:** اگر EdgeId ثبت‌نام نشده باشد، Heartbeat رد می‌شود (Unsupported Edge).
3. **Inactive Edge Rejection:** اگر Device از CPS-74 غیرفعال (Inactive) باشد، Heartbeat رد می‌شود (403).
4. **ConnectionStatus Self-Reported:** وضعیت اتصال توسط Edge گزارش می‌شود: `Connected`, `Degraded`, `Disconnected`.
5. **No IP Storage:** هیچ‌وقت آدرس IP Device ذخیره نمی‌شود (امنیت).
6. **All Times UTC:** تمام زمان‌ها به صورت UTC ذخیره و بازگشت داده می‌شوند.
7. **QueueStatistics Value Object:** `localQueueCount`, `pendingCount`, `failedCount`, `dlqCount` به صورت Value Object.
8. **Offline Detection:** آستانه‌های زمانی قابل پیکربندی: `HeartbeatTimeout`, `OfflineThreshold`, `WarningThreshold`.

---

## 📝 قرارداد درخواست (Real Core Contract)

### HeartbeatRequest (POST /api/edge/heartbeats):
```json
{
  "edgeId": "EDGE-TEST-001",
  "exchangeCenterCode": "59544",
  "softwareVersion": "2.5.1",
  "configurationVersion": 5,
  "connectionStatus": "Connected|Degraded|Disconnected",
  "localQueueCount": 12,
  "pendingCount": 3,
  "failedCount": 1,
  "dlqCount": 0,
  "lastSuccessfulSync": "2025-01-15T10:29:00Z",
  "correlationId": "uuid"
}
```

### HeartbeatResponse (202 Accepted):
```json
{
  "received": true,
  "serverTime": "2025-01-15T10:30:00Z"
}
```

### EdgeHealthStatusDTO (Query response):
```json
{
  "edgeId": "EDGE-TEST-001",
  "exchangeCenterCode": "59544",
  "softwareVersion": "2.5.1",
  "configurationVersion": 5,
  "connectionStatus": "Connected",
  "lastHeartbeatAt": "2025-01-15T10:30:00Z",
  "lastSuccessfulSync": "2025-01-15T10:29:00Z",
  "lastUpdatedUtc": "2025-01-15T10:30:00Z",
  "queueStatistics": {"localQueueCount": 12, "pendingCount": 3, "failedCount": 1, "dlqCount": 0}
}
```

### HealthSummaryDTO (Admin summary):
```json
{
  "totalEdges": 15,
  "activeEdges": 12,
  "offlineEdges": 3,
  "degradedEdges": 1,
  "averageHeartbeatIntervalSeconds": 30,
  "lastUpdatedUtc": "2025-01-15T10:30:00Z"
}
```

---

## 🏗️ معماری کد (Clean Architecture)

```
domain/edge_health/                  # Domain Layer
├── value_objects/                   # EdgeId, ExchangeCenterCode, SoftwareVersion, ConfigurationVersion, ConnectionStatus, QueueStatistics, HeartbeatInterval, CorrelationId
├── entities/                        # EdgeHealthStatus (Aggregate Root with business rules)
├── events/                          # HeartbeatReceived, EdgeWentOffline, EdgeBackOnline
├── repositories/                    # EdgeHealthRepository (Interface)
├── exceptions/                      # UnknownEdgeError, InactiveEdgeError, EdgeHealthNotFoundError, etc.
└── __init__.py                      # Package exports

application/                         # Application Layer
├── commands/
│   └── receive_heartbeat/           # Command, Handler, Validator
│       ├── __init__.py              # ReceiveHeartbeatCommand, ReceiveHeartbeatResult
│       ├── handler.py               # ReceiveHeartbeatHandler
│       └── validator.py             # ReceiveHeartbeatValidator
├── queries/
│   ├── get_edge_health/             # GetEdgeHealthQuery, EdgeHealthDTO, GetEdgeHealthHandler
│   │   └── __init__.py
│   └── get_health_summary/          # GetHealthSummaryQuery, HealthSummaryDTO, GetHealthSummaryHandler
│       └── __init__.py
└── ports/                           # EventPublisherPort (CPS-58)

infrastructure/                      # Infrastructure Layer
├── persistence/
│   └── in_memory_edge_health_repository.py  # InMemory Implementation
└── ...

interfaces/                          # Interface Layer
├── rest/
│   ├── heartbeat_controller.py      # Edge-facing REST: POST /api/edge/heartbeats, GET /api/edge/heartbeats/{edgeId}
│   └── admin_health_controller.py   # Admin-facing REST: GET /api/admin/edge-health, GET /api/admin/edge-health/summary
└── dto/
    └── edge_health_dto.py           # Request/Response DTOs

flows/health/                        # Test Flows
└── cps82_health_flow.py             # CPS-82 Test Flow with SimulatedHttpClient

assertions/                          # Test Assertions
└── edge_health_assertions.py        # CPS-82 Assertion Helpers

tests/unit/                          # Unit Tests
└── test_cps82_core.py               # 8 Unit Tests (TC-01 to TC-08)
```

---

## 🔑 الگوهای استفاده‌شده

| الگو | توضیح |
|:---|:---|
| **Aggregate Root** | `EdgeHealthStatus` - Latest state only, update_from_heartbeat replaces existing record |
| **Value Objects** | `EdgeId`, `ExchangeCenterCode`, `SoftwareVersion`, `ConfigurationVersion`, `QueueStatistics`, `CorrelationId` |
| **Domain Events** | `HeartbeatReceived`, `EdgeWentOffline`, `EdgeBackOnline` |
| **Repository Pattern** | `EdgeHealthRepository` - Interface, InMemory test implementation |
| **CQRS سبک** | `ReceiveHeartbeatCommand` (Write) separate from `GetEdgeHealthQuery` (Read) |
| **Latest State Only** | No history. Each heartbeat replaces the previous record for that EdgeId |
| **No IP Storage** | IP address is never stored in health data or entity attributes |
| **Offline Detection** | Configurable thresholds: HeartbeatTimeout, OfflineThreshold, WarningThreshold |

---

## 🚀 دستورات اجرا (CPS-82)

### تست‌های واحد (Unit Tests - کاملاً آفلاین):
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps82_core.py -q -s
```

### اجرای ترکیبی CPS-82 با سایر تسک‌ها:
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps82_core.py tests/unit/test_cps74_core.py -q
```

---

## 🔧 پیکربندی (Configuration)

### در `config/settings.py`:
```python
# CPS-82: Edge Health Monitoring settings
core_heartbeats_path: str = os.getenv(
    "CORE_HEARTBEATS_PATH", "/api/edge/heartbeats"
)
core_admin_health_path: str = os.getenv(
    "CORE_ADMIN_HEALTH_PATH", "/api/admin/edge-health"
)
cps82_edge_id: str = os.getenv(
    "CPS82_EDGE_ID", "EDGE-TEST-001"
)
cps82_exchange_center_code: str = os.getenv(
    "CPS82_EXCHANGE_CENTER_CODE", "59544"
)
cps82_offline_threshold_seconds: int = int(
    os.getenv("CPS82_OFFLINE_THRESHOLD_SECONDS", "120")
)
cps82_heartbeat_timeout_seconds: int = int(
    os.getenv("CPS82_HEARTBEAT_TIMEOUT_SECONDS", "60")
)
```

### در `.env`:
```bash
CORE_HEARTBEATS_PATH=/api/edge/heartbeats
CORE_ADMIN_HEALTH_PATH=/api/admin/edge-health
CPS82_EDGE_ID=EDGE-TEST-001
CPS82_EXCHANGE_CENTER_CODE=59544
CPS82_OFFLINE_THRESHOLD_SECONDS=120
CPS82_HEARTBEAT_TIMEOUT_SECONDS=60
```

---

## 💡 مثال استفاده در کد (Python Domain)

```python
from domain.edge_health.value_objects import (
    EdgeId, ExchangeCenterCode, SoftwareVersion, ConfigurationVersion,
    ConnectionStatus, QueueStatistics, CorrelationId,
)
from domain.edge_health.entities import EdgeHealthStatus

# 1. ایجاد Health Status از Heartbeat اولیه
health = EdgeHealthStatus.register_from_heartbeat(
    edge_id=EdgeId("EDGE-TEST-001"),
    exchange_center_code=ExchangeCenterCode("59544"),
    software_version=SoftwareVersion("2.5.1"),
    configuration_version=ConfigurationVersion(5),
    connection_status=ConnectionStatus.CONNECTED,
    last_successful_sync=datetime.now(timezone.utc),
    last_heartbeat_at=datetime.now(timezone.utc),
    queue_statistics=QueueStatistics(
        local_queue_count=12,
        pending_count=3,
        failed_count=1,
        dlq_count=0,
    ),
)

# 2. بروزرسانی با Heartbeat جدید (Latest State Only)
health.update_from_heartbeat(
    software_version=SoftwareVersion("2.5.2"),
    configuration_version=ConfigurationVersion(6),
    connection_status=ConnectionStatus.CONNECTED,
    last_heartbeat_at=datetime.now(timezone.utc),
    last_successful_sync=datetime.now(timezone.utc),
    queue_statistics=QueueStatistics(
        local_queue_count=5,
        pending_count=1,
        failed_count=0,
        dlq_count=0,
    ),
)

# 3. بررسی وضعیت Offline
assert not health.is_stale(timeout_seconds=60)

# 4. تبدیل به DTO
dto = health.to_dto()
print(dto.to_response_dict())
```

---

## 📊 خروجی تست واحد (نمونه - مختصر)

```text
========== Execution report: CPS-82 Edge Health Monitoring Flow ==========
01. [PASS] TC-01: Successful heartbeat registration
02. [PASS] TC-02: Update existing Edge health (latest state only)
03. [PASS] TC-03: Queue statistics stored correctly
04. [PASS] TC-04: Unknown Edge rejected
05. [PASS] TC-05: Inactive Edge rejected
06. [PASS] TC-06: Correlation-ID in structured logs
07. [PASS] TC-07: Health query returns latest status
08. [PASS] TC-08: No IP address stored in health data

Result: PASS=8, FAIL=0, NOT_CHECKED=0
```

---

## 🔗 ارتباط با سایر تسک‌ها

| تسک | ارتباط |
|:---|:---|
| **CPS-74** (Sorting Device Management) | Edge Registration و Active/Inactive status از CPS-74 استفاده می‌شود (Unknown/Inactive Edge Rejection) |
| **Dashboard (Future)** | اطلاعات سلامت Edgeها برای نمایش در Dashboard استفاده می‌شود |
| **Alerting (Future)** | تشخیص Offline و ارسال هشدار بر اساس Offline Threshold |
| **Diagnostics (Future)** | تحلیل QueueStatistics و ConnectionStatus برای Diagnostics |

---

## ✅ Checklist پیاده‌سازی

- [x] Domain: value_objects (EdgeId, ExchangeCenterCode, SoftwareVersion, ConfigurationVersion, ConnectionStatus, QueueStatistics, HeartbeatInterval, CorrelationId), entity (EdgeHealthStatus), events (HeartbeatReceived, EdgeWentOffline, EdgeBackOnline), repository interface (EdgeHealthRepository), exceptions
- [x] Application: Commands (receive_heartbeat), Queries (get_edge_health, get_health_summary), Handlers, Validators, DTOs
- [x] Infrastructure: InMemoryEdgeHealthRepository
- [x] Interfaces: HeartbeatController, AdminHealthController, Request/Response DTOs
- [x] Flows: cps82_health_flow.py (8 scenarios)
- [x] Assertions: edge_health_assertions.py
- [x] Unit Tests: test_cps82_core.py (8 domain/VO tests)
- [x] Config: settings.py, test.env.example (core_heartbeats_path, cps82_*)
- [x] Markers: pytest.ini (cps82_success, cps82_negative)
- [x] Documentation: docs/CPS-82/README.md
- [x] Commit: "feat(cps-82): implement CPS-82 Edge Health Monitoring with Clean Architecture, Heartbeat Processing, Unit Tests"

---

**Version:** 1.0.0  
**Status:** ✅ Complete  
**Date:** 2025-01-15