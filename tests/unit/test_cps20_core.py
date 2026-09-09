from typing import Any, Optional
import json
import pytest

from flows.inbound.cps20_inbound_query_flow import (
    InboundQueryCase,
    build_cps20_cases,
    run_cps20_flow,
)
from utils.step_report import FlowExecutionError


class FakeResponse:
    def __init__(self, status_code: int, data: dict[str, Any]):
        self.status_code = status_code
        self._data = data
        self.text = json.dumps(data)

    def json(self) -> dict[str, Any]:
        return self._data


class SimulatedCoreHttpClient:
    """Simulates Core REST API for CPS-20 Inbound Query with real Core contract."""
    def __init__(self, should_fail_on: Optional[str] = None):
        self.base_url = "http://192.168.20.196:5080"
        self.last_exchange: dict[str, Any] = {}
        self.should_fail_on = should_fail_on

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        token: str | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> FakeResponse:
        url = f"{self.base_url}{path}"
        barcode = (payload or {}).get("parcelBarcode", "")
        correlation_id = (headers or {}).get("X-Correlation-ID", "corr-test-id")

        if self.should_fail_on and self.should_fail_on in barcode:
            resp_data = {
                "status": "error",
                "recordedOriginCode": None,
                "recordedDestinationCode": None,
                "discrepancyDetected": False,
                "discrepancyDetails": "Internal Core simulation error: database timeout",
                "discrepancies": [],
                "readingId": "00000000-0000-0000-0000-000000000000",
            }
            resp = FakeResponse(500, resp_data)
        elif barcode == "590001234567890123456789":  # TC-01 & TC-05 - Normal
            resp_data = {
                "status": "success",
                "recordedOriginCode": "59544",
                "recordedDestinationCode": "11369",
                "discrepancyDetected": False,
                "discrepancyDetails": None,
                "discrepancies": [],
                "readingId": "11111111-1111-1111-1111-111111111111",
            }
            resp = FakeResponse(200, resp_data)
        elif barcode == "590001234567890123456788":  # TC-02 Returning
            resp_data = {
                "status": "returning",
                "recordedOriginCode": "59544",
                "recordedDestinationCode": "11369",
                "discrepancyDetected": True,
                "discrepancyDetails": "Parcel returned after 24h",
                "discrepancies": [{"discrepancyType": "time_threshold", "description": "Returning", "comparisonRef": "6h"}],
                "readingId": "22222222-2222-2222-2222-222222222222",
            }
            resp = FakeResponse(200, resp_data)
        elif barcode == "590001234567890123456787":  # TC-03 Return to Origin
            resp_data = {
                "status": "rejected",
                "recordedOriginCode": "59544",
                "recordedDestinationCode": "59544",
                "discrepancyDetected": True,
                "discrepancyDetails": "Parcel return to origin after 100h",
                "discrepancies": [{"discrepancyType": "time_threshold", "description": "ReturnToOrigin", "comparisonRef": "72h"}],
                "readingId": "33333333-3333-3333-3333-333333333333",
            }
            resp = FakeResponse(200, resp_data)
        elif barcode == "590009999999999999999999":  # TC-04 Not Found
            resp_data = {
                "status": "success",
                "recordedOriginCode": None,
                "recordedDestinationCode": None,
                "discrepancyDetected": False,
                "discrepancyDetails": None,
                "discrepancies": [],
                "readingId": "44444444-4444-4444-4444-444444444444",
            }
            resp = FakeResponse(200, resp_data)
        else:
            resp_data = {
                "status": "success",
                "recordedOriginCode": "59544",
                "recordedDestinationCode": "11369",
                "discrepancyDetected": False,
                "discrepancyDetails": None,
                "discrepancies": [],
                "readingId": "55555555-5555-5555-5555-555555555555",
            }
            resp = FakeResponse(200, resp_data)

        # ضبط دقیق exchange جفت Request/Response
        self.last_exchange = {
            "request": {
                "method": method,
                "url": url,
                "payload": payload,
                "headers": headers,
            },
            "response": {
                "statusCode": resp.status_code,
                "body": resp_data,
            },
        }
        return resp

    def close(self) -> None:
        pass


def test_cps20_flow_success_execution_prints_payload_and_response():
    """
    اجرای کامل سناریوهای ۵گانه CPS-20 در حالت موفقیت.
    بررسی اینکه هم در حالت PASS گزارش دهی شامل تمام فیلدهای payloadSent و responseReceived است.
    """
    client = SimulatedCoreHttpClient()
    result = run_cps20_flow(client_factory=lambda: client)

    assert len(result.responses) == 5
    report = result.report
    assert report.summary()["PASSED"] == 5
    assert report.summary()["FAILED"] == 0

    # اعتبارسنجی اینکه هر مرحله دارای payload_sent و response_received است
    for record in report.records:
        assert record.payload_sent is not None, f"{record.name} missing payloadSent"
        assert record.response_received is not None, f"{record.name} missing responseReceived"
        assert record.status.value == "PASSED"


def test_cps20_flow_failure_execution_prints_payload_and_response():
    """
    بررسی اینکه در حالت FAIL (شکست یا خطای سرویس Core) نیز
    گزارش‌دهی کامل با ثبت دقیق payloadSent و responseReceived و متن خطا چاپ می‌شود.
    """
    # شبیه‌سازی خطا روی بارکد TC-02
    client = SimulatedCoreHttpClient(should_fail_on="590001234567890123456788")

    with pytest.raises(FlowExecutionError) as exc_info:
        run_cps20_flow(client_factory=lambda: client)

    report = exc_info.value.report
    # TC-01 passed
    assert report.records[0].status.value == "PASSED"
    assert report.records[0].payload_sent is not None
    assert report.records[0].response_received is not None

    # TC-02 failed with captured payloadSent, responseReceived, and error message
    failed_record = report.records[1]
    assert failed_record.status.value == "FAILED"
    assert failed_record.payload_sent is not None, "Failed record must have payloadSent"
    assert failed_record.response_received is not None, "Failed record must have responseReceived"
    assert failed_record.error != "", "Failed record must have error message"

    # Remaining cases were NOT skipped (no NOT_CHECKED)
    assert report.records[2].status.value == "PASSED"
    assert report.records[3].status.value == "PASSED"
    assert report.records[4].status.value == "PASSED"
    assert report.summary().get("NOT_EXECUTED", 0) == 0


def test_cps20_cases_definitions():
    """تست تعریف سناریوهای CPS-20 با قرارداد جدید"""
    cases = build_cps20_cases()
    assert len(cases) == 5
    case_ids = [c.case_id for c in cases]
    assert case_ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05"]
    
    # بررسی فیلدهای قرارداد جدید
    tc1 = cases[0]
    assert tc1.parcel_barcode == "590001234567890123456789"
    assert tc1.expected_core_status == "success"
    assert tc1.expected_recorded_origin_code == "59544"
    assert tc1.expected_recorded_destination_code == "11369"
    assert hasattr(tc1, 'edge_id')
    assert hasattr(tc1, 'physical_weight_grams')