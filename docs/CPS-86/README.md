# CPS-86: ذخیره نتیجه عملیات پستی (Operational Result Storage)

این مستند تشریح‌کننده پیاده‌سازی و زیرساخت تست تسک **CPS-86** از سیستم **Core Post Sorting** (تیم B / Epic پایش، سلامت و مشاهده‌پذیری) است.

> **معماری:** پیاده‌سازی بر پایه **Clean Architecture** و **Domain-Driven Design (DDD)**. سرویس `OperationalResult.Api` یک سرویس جداگانه (Sidecar) است که بر مسیر حیاتی (Critical Path) تأثیر نمی‌گذارد.

---

## 🎯 هدف بیزینسی (Business Goal)

سیستم Core باید **نتیجه تمامی عملیات** انجام‌شده توسط Edge بر روی سامانه‌های پستی (Stored Procedure، Web API، سرویس‌های خارجی) را به‌صورت **استاندارد، مستقل و Append-Only** ذخیره کند تا:

- امکان **رهگیری** (Traceability) عملیات فراهم شود
- **ممیزی** (Audit) و عیب‌یابی خطاها امکان‌پذیر باشد
- **گزارش‌گیری** و **تحلیل عملکرد** operações پشتیبانی شود
- Core **مستقیمًا** با سامانه‌های پستی ارتباط **نداشته باشد** (جداسازی کامل)

---

## 🌐 مشخصات سرویس

| مورد | مقدار |
|:---|:---|
| **Endpoint** | `POST /api/edge/operational-results` |
| **سرویس** | `OperationalResult.Api` |
| **قرارداد درخواست** | `OperationalResultRequest` |
| **معماری** | Clean Architecture + DDD |
| **ذخیره‌سازی** | Append-Only (حذف فیزیکی ممنوع) |

---

## 📋 سناریوهای BDD تست‌شده (Acceptance Criteria)

| شناسه | عنوان سناریو | شرط | خروجی مورد انتظار |
|:---|:---|:---|:---|
| **TC-01** | ثبت موفق نتیجه عملیات | عملیات موفق | ذخیره با `Status=Success`، Correlation-ID، تایم‌استمپ‌ها |
| **TC-02** | ثبت عملیات ناموفق | عملیات با خطا | ذخیره با `Status=Failure`، `ErrorCode`، `ErrorMessage` |
| **TC-03** | ثبت Retry (چندین تلاش) | `attempts > 1` | `AttemptCount` ثبت شه، تاریخچه حفظ شه |
| **TC-04** | رد درخواست بدون احراز هویت | بدون JWT | HTTP 401 Unauthorized |
| **TC-05** | امنیت اطلاعات حساس | پاسخ حاوی توکن/رمز | **هیچ Token/Password/Secret/Authorization Header ذخیره نشه** |
| **TC-06** | رد درخواست نامعتبر | فیلدهای اجباری خالی | HTTP 400 Bad Request |

---

## 📝 قرارداد درخواست (Real Core Contract)

**Endpoint:** `POST /api/edge/operational-results`

**Request (OperationalResultRequest):**
```json
{
  "correlationId": "string (required)",      // برای ردیابی توزیع‌شده
  "parcelBarcode": "string | null",          // بارکد مرسوله (اختیاری)
  "callResult": "string (required)",         // نام عملیات: RegisterInbound، PrintLabel، BagClose، ...
  "success": "boolean (required)",           // وضعیت کلی موفقیت/موفقیت
  "errorCode": "string | null",              // کد خطا (در صورت شکست)
  "errorMessage": "string | null",           // پیام خطا (Sanitized)
  "calledAtUtc": "date-time (required)",     // زمان فراخوانی عملیات
  "respondedAtUtc": "date-time (required)",  // زمان دریافت پاسخ
  "attempts": "integer (required)",          // تعداد تلاش‌ها (Retry)
  "finalStatus": "string (required)"         // وضعیت نهایی: Success، Failure، Partial
}
```

**Response:** `200 OK` (بدون بدنه خاص - فقط تأیید دریافت)

---

## 🏗️ معماری کد (Code Structure)

```
assertions/
└── operational_result_assertions.py      # Assertionهای قرارداد Core

flows/operational_result/
└── cps86_operational_result_flow.py      # Flow اصلی ۶ سناریوی BDD

tests/unit/
└── test_cps86_core.py                    # ۶ تست واحد کامل

config/
├── settings.py                            # تنظیمات CPS-86
└── test.env.example                       # متغیرهای محیطی نمونه
```

---

## 🚀 دستورات اجرا

### تست‌های واحد (Unit Tests - کاملاً آفلاین):
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps86_core.py -q -s
```

### تست‌های ترکیبی CPS-20 + CPS-65 + CPS-80 + CPS-86:
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_cps20_core.py tests/unit/test_cps65_status_evaluator.py tests/unit/test_cps80_core.py tests/unit/test_cps86_core.py -q
```

### اجرای همه تست‌های واحد:
```powershell
.venv\Scripts\python.exe -m pytest tests/unit -q
```

---

## 🔧 پیکربندی (Configuration)

### در `config/settings.py`:
```python
# CPS-86: Operational Result Storage settings
core_operational_results_path: str = os.getenv(
    "CORE_OPERATIONAL_RESULTS_PATH", "/api/edge/operational-results"
)
cps86_correlation_id: str = os.getenv("CPS86_CORRELATION_ID", "")
cps86_parcel_barcode: str = os.getenv(
    "CPS86_PARCEL_BARCODE", "860000000000000000000001"
)
cps86_call_result: str = os.getenv(
    "CPS86_CALL_RESULT", "RegisterInbound_Success"
)
cps86_error_code: str = os.getenv("CPS86_ERROR_CODE", "")
cps86_error_message: str = os.getenv("CPS86_ERROR_MESSAGE", "")
cps86_attempts: int = int(os.getenv("CPS86_ATTEMPTS", "1"))
cps86_final_status: str = os.getenv("CPS86_FINAL_STATUS", "Success")
```

### در `.env` یا Environment Variables:
```bash
CORE_OPERATIONAL_RESULTS_PATH=/api/edge/operational-results
CPS86_CORRELATION_ID=
CPS86_PARCEL_BARCODE=860000000000000000000001
CPS86_CALL_RESULT=RegisterInbound_Success
CPS86_ERROR_CODE=
CPS86_ERROR_MESSAGE=
CPS86_ATTEMPTS=1
CPS86_FINAL_STATUS=Success
```

---

## 💡 مثال استفاده در کد

```python
from flows.operational_result.cps86_operational_result_flow import (
    OperationalResultCase,
    build_cps86_cases,
    run_cps86_flow,
)
from clients.http_client import HttpClient
from config.settings import settings
from datetime import datetime, timezone

# ۱. ساخت HttpClient واقعی (برای E2E)
client = HttpClient(
    base_url=settings.core_base_url,
    timeout=settings.core_timeout_seconds,
)

# ۲. اجرای تمام ۶ سناریوی BDD
result = run_cps86_flow(
    client_factory=lambda: client,
    run_settings=settings,
)

# ۳. بررسی نتایج
print(f"Passed: {result.report.summary()['PASSED']}")
print(f"Failed: {result.report.summary()['FAILED']}")

# هر رکورد شامل payloadSent و responseReceived دقیق است
for record in result.report.records:
    print(f"{record.name}: {record.status.value}")
    print(f"  Payload: {record.payload_sent}")
    print(f"  Response: {record.response_received}")
```

---

## 📊 خروجی تست واحد (نمونه)

```text
Execution report: CPS-86 Operational Result Storage Flow
01. [PASS] TC-01: Successful operation result stored
    payloadSent: {"method": "POST", "url": "http://192.168.20.196:5080/api/edge/operational-results", "payload": {"correlationId": "corr-86-success-001", "parcelBarcode": "860000000000000000000001", "callResult": "RegisterInbound_Success", "success": true, "errorCode": null, "errorMessage": null, "calledAtUtc": "2025-01-15T10:00:00Z", "respondedAtUtc": "2025-01-15T10:00:01Z", "attempts": 1, "finalStatus": "Success"}, "headers": {"Content-Type": "application/json", "X-Correlation-ID": "...", "Authorization": "<redacted>"}}
    responseReceived: {"statusCode": 200, "body": {}}
    expected: PASS

02. [PASS] TC-02: Failed operation result stored with error details
    payloadSent: {... "success": false, "errorCode": "POSTAL_API_TIMEOUT", "errorMessage": "Postal API did not respond within timeout", "finalStatus": "Failure" ...}
    responseReceived: {"statusCode": 200, "body": {}}
    expected: PASS

03. [PASS] TC-03: Retry operation result stored with attempt count
    payloadSent: {... "attempts": 3, "finalStatus": "Success" ...}
    responseReceived: {"statusCode": 200, "body": {}}
    expected: PASS

04. [PASS] TC-04: Unauthorized request rejected
    payloadSent: {... "headers": {"Content-Type": "application/json", "X-Correlation-ID": "..."}}  # بدون Authorization
    responseReceived: {"statusCode": 401, "body": {"title": "Unauthorized", "status": 401, "detail": "Missing or invalid JWT authorization token"}}
    expected: PASS

05. [PASS] TC-05: No sensitive data leaked in response
    ...
    expected: PASS

06. [PASS] TC-06: Invalid request rejected (missing required fields)
    payloadSent: {... "correlationId": "", ...}
    responseReceived: {"statusCode": 400, "body": {"title": "Bad Request", "status": 400, "detail": "correlationId is required"}}
    expected: PASS

Result: PASS=6, FAIL=0, NOT_CHECKED=0
```

---

## 🔗 ارتباط با سایر تسک‌ها

| تسک | ارتباط |
|:---|:---|
| **CPS-20** (Inbound Query) | Edge پس از ثبت مرسوله، نتیجه را از طریق CPS-86 در Core ذخیره می‌کند |
| **CPS-65** (Status Evaluation) | موتور تشخیص وضعیت، نتیجه ارزیابی را می‌تواند به عنوان `OperationalResult` ثبت کند |
| **CPS-80** (Pre-signed URL) | نتیجه آپلود عکس به Object Storage ثبت می‌شود |
| **EPS-113** (Central Event) | رویدادهای مرکزی می‌توانند از OperationalResult برای ممیزی استفاده کنند |
| **EPS-68** (Core Status Override) | تغییر وضعیت توسط Core ثبت می‌شود |

---

## 🔐 امنیت و لاگینگ

* **بدون Token در لاگ**: Authorization Header در گزارش‌های تست `<redacted>` نمایش داده می‌شود
* **Sanitize ErrorMessage**: پیام‌های خطا باید قبل از ذخیره از اطلاعات حساس (PII، Token، Password) پاک‌سازی شوند
* **Structured Log**: شامل `Correlation-ID`، `EdgeId`، `OperationType`، `ResultStatus`، `ProcessingTime`
* **Metrics پیشنهادی**:
  - تعداد عملیات موفق / ناموفق
  - نرخ خطا
  - میانگین زمان اجرای عملیات
  - تعداد Retryها
  - تعداد عملیات بر حسب نوع (`RegisterInbound`، `PrintLabel`، `BagClose`، ...)

---

## 📝 نکات مهم پیاده‌سازی

1. **Append-Only**: رکوردها هرگز حذف یا به‌روزرسانی نمی‌شوند (Immutable)
2. **Independence**: Core هیچ کال مستقیمی به سامانه‌های پستی ندارد — فقط نتیجه را ذخیره می‌کند
3. **Non-blocking**: ثبت نتیجه باید سبک و غیرمسدودکننده باشد تا بر عملکرد مسیر بلادرنگ تأثیر نگذارد
4. **Correlation-ID**: کلید اصلی برای اتصال لاگ‌های Edge، Core و سامانه‌های پستی
5. **Configuration-driven**: تمام محدودیت‌ها و سیاست‌ها قابل تنظیم از Config هستند
6. **Scalability**: طراحی شده برای ثبت همزمان هزاران نتیجه عملیات