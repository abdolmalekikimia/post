"""Flow implementation for CPS-63: Inbound Event Structural & Barcode Set Validation.

Tests Core Gateway / Ingestion Pipeline:
- TC-01: Valid single 24-digit barcode accepted
- TC-02: Valid single 14-digit barcode accepted
- TC-03: Valid consistent barcode set (24-digit + 37-digit matching prefix) accepted
- TC-04: Invalid barcode length/format rejected (e.g. 10-digit or non-numeric)
- TC-05: Inconsistent barcode set (24-digit and 37-digit prefix mismatch) rejected
- TC-06: Inconsistent barcode set (14-digit combined with 24-digit) rejected
- TC-07: Incomplete event payload (missing required fields) rejected
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from typing import Any, Callable, Optional, Sequence
import uuid

from assertions.cps63_validation_assertions import (
    assert_correlation_id_preserved,
    assert_event_accepted,
    assert_event_validation_rejected,
    validate_barcode_set_consistency,
)
from clients.http_client import HttpClient
from config.settings import Settings, settings
from flows.bag.bag_flow_support import (
    PRECONDITION_STEPS,
    setup_authenticated_context,
    wait_between_calls,
)
from utils.auth_helper import get_configured_edge_id
from utils.step_report import (
    ExecutionReport,
    FlowExecutionError,
    exchange_detail,
    run_step,
)


@dataclass(frozen=True)
class BarcodeValidationCase:
    case_id: str
    title: str
    category: str  # "valid_single", "valid_set", "invalid_format", "mismatch_set", "incompatible_14", "missing_fields"
    barcodes: tuple[str, ...]
    primary_barcode: str
    edge_id: str | None = None
    exchange_center_code: str = "11111"
    device_id: str = "DEVICE-TEST-001"
    correlation_id: str = ""
    expected_status_code: int = 200
    expected_error_keyword: Optional[str] = None

    def __post_init__(self):
        if self.edge_id is None:
            object.__setattr__(self, 'edge_id', get_configured_edge_id())


def build_default_cps63_cases(run_settings: Settings = settings) -> tuple[BarcodeValidationCase, ...]:
    """Build default test cases covering all 7 BDD scenarios for CPS-63 with dynamic barcodes."""
    from utils.test_data import (
        generate_dynamic_barcode_14,
        generate_dynamic_barcode_24,
        generate_dynamic_barcode_37,
        generate_correlation_id,
    )

    # Generate fresh dynamic barcodes per run
    b24 = generate_dynamic_barcode_24(slot=0)
    b37_matching = generate_dynamic_barcode_37(b24, slot=0)
    b37_mismatch = generate_dynamic_barcode_37(slot=99)  # Different base, so prefix won't match
    b14 = generate_dynamic_barcode_14(slot=0)

    return (
        BarcodeValidationCase(
            case_id="TC-01",
            title="Accept valid single 24-digit barcode event",
            category="valid_single",
            primary_barcode=b24,
            barcodes=(b24,),
            correlation_id=generate_correlation_id("cps63-tc01"),
            expected_status_code=200,
        ),
        BarcodeValidationCase(
            case_id="TC-02",
            title="Accept valid single 14-digit barcode event",
            category="valid_single",
            primary_barcode=b14,
            barcodes=(b14,),
            correlation_id=generate_correlation_id("cps63-tc02"),
            expected_status_code=200,
        ),
        BarcodeValidationCase(
            case_id="TC-03",
            title="Accept consistent barcode set (24-digit + 37-digit with matching prefix)",
            category="valid_set",
            primary_barcode=b24,
            barcodes=(b24, b37_matching),
            correlation_id=generate_correlation_id("cps63-tc03"),
            expected_status_code=200,
        ),
        BarcodeValidationCase(
            case_id="TC-04",
            title="Reject invalid barcode length (e.g. 10-digit non-standard barcode)",
            category="invalid_format",
            primary_barcode="1234567890",  # Only 10 digits
            barcodes=("1234567890",),
            correlation_id=generate_correlation_id("cps63-tc04"),
            expected_status_code=400,
            expected_error_keyword="barcode",
        ),
        BarcodeValidationCase(
            case_id="TC-05",
            title="Reject mismatch between 24-digit barcode and 37-digit prefix",
            category="mismatch_set",
            primary_barcode=b24,
            barcodes=(b24, b37_mismatch),
            correlation_id=generate_correlation_id("cps63-tc05"),
            expected_status_code=400,
            expected_error_keyword="inconsistent",
        ),
        BarcodeValidationCase(
            case_id="TC-06",
            title="Reject inconsistent combination of 14-digit and 24-digit barcodes",
            category="incompatible_14",
            primary_barcode=b14,
            barcodes=(b14, b24),
            correlation_id=generate_correlation_id("cps63-tc06"),
            expected_status_code=400,
            expected_error_keyword="inconsistent",
        ),
        BarcodeValidationCase(
            case_id="TC-07",
            title="Reject incomplete event missing required primary barcode",
            category="missing_fields",
            primary_barcode="",
            barcodes=(),
            correlation_id=generate_correlation_id("cps63-tc07"),
            expected_status_code=400,
            expected_error_keyword="required",
        ),
    )


@dataclass
class BarcodeValidationFlowResult:
    responses: dict[str, Any]
    report: ExecutionReport


def run_cps63_barcode_validation_flow(
    run_settings: Settings = settings,
    cases: tuple[BarcodeValidationCase, ...] | None = None,
    client_factory: Callable[[], HttpClient] | None = None,
) -> BarcodeValidationFlowResult:
    """Execute the CPS-63 Barcode Validation and Event Ingestion Flow."""
    active_cases = cases or build_default_cps63_cases(run_settings)
    report = ExecutionReport("CPS-63 Inbound Event Structural & Barcode Validation Flow")

    if client_factory is not None:
        report.register(*(f"{case.case_id}: {case.title}" for case in active_cases))
        client = client_factory()
        edge_token = None
        try:
            from utils.auth_helper import get_edge_token
            edge_token = get_edge_token(client, run_settings=run_settings)
        except Exception:
            pass

        responses: dict[str, Any] = {}
        for case in active_cases:
            step_name = f"{case.case_id}: {case.title}"

            def execute_case(c: BarcodeValidationCase = case) -> dict[str, Any]:
                is_consistent, consistency_msg = (
                    validate_barcode_set_consistency(c.barcodes)
                    if c.barcodes
                    else (False, "Empty barcodes")
                )
                headers = {
                    "Content-Type": "application/json",
                    "X-Correlation-ID": c.correlation_id,
                    "Idempotency-Key": str(uuid.uuid4()),
                }
                if edge_token:
                    headers["Authorization"] = f"Bearer {edge_token}"
                payload = {
                    "parcelBarcode": c.primary_barcode,
                    "barcodes": list(c.barcodes),
                    "edgeId": c.edge_id or get_configured_edge_id(),
                    "exchangeCenterCode": c.exchange_center_code or "11111",
                    "deviceId": c.device_id or "DEVICE-TEST-001",
                    "scannedAtUtc": datetime.now(timezone.utc).isoformat(),
                    "physicalOriginCode": "11111",
                    "physicalDestinationCode": "11369",
                    "physicalWeightGrams": 1000.0,
                    "physicalLengthCm": 30.0,
                    "physicalWidthCm": 20.0,
                    "physicalHeightCm": 10.0,
                }
                resp = client.post(
                    run_settings.core_inbound_query_path,
                    payload=payload,
                    headers=headers,
                )
                data = resp.json() if resp.text else {}
                if c.category in ("valid_single", "valid_set"):
                    assert is_consistent, f"Test setup error: expected valid case was inconsistent: {consistency_msg}"
                    assert_event_accepted(data, resp.status_code, operation_name=c.case_id)
                    assert_correlation_id_preserved(data, c.correlation_id)
                else:
                    assert_event_validation_rejected(
                        data,
                        resp.status_code,
                        expected_error_keyword=c.expected_error_keyword,
                        operation_name=c.case_id,
                    )
                return {
                    "statusCode": resp.status_code,
                    "body": data,
                    "payloadSent": payload,
                    "isConsistentLocally": is_consistent,
                }

            run_step(
                report,
                step_name,
                execute_case,
                detail=lambda _: exchange_detail(client.last_exchange),
                error_detail=lambda err: {
                    "error": f"{type(err).__name__}: {err}",
                    **exchange_detail(client.last_exchange),
                },
            )
            responses[case.case_id] = responses.get(case.case_id, {})
        return BarcodeValidationFlowResult(responses=responses, report=report)

    # Real Edge SignalR integration flow
    report.register(
        *PRECONDITION_STEPS,
        *(f"{case.case_id}: {case.title}" for case in active_cases),
    )
    context = setup_authenticated_context(
        report,
        run_settings,
        flow_label="CPS-63",
    )
    responses: dict[str, Any] = {}
    try:
        for case in active_cases:
            wait_between_calls(run_settings)
            step_name = f"{case.case_id}: {case.title}"

            def execute_edge_case(c: BarcodeValidationCase = case) -> dict[str, Any]:
                is_consistent, consistency_msg = (
                    validate_barcode_set_consistency(c.barcodes)
                    if c.barcodes
                    else (False, "Empty barcodes")
                )
                resp = context.device.register_inbound_barcodes(
                    barcodes=list(c.barcodes),
                    read_timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    correlation_id=c.correlation_id,
                    timeout_ms=int(run_settings.inbound_timeout_ms),
                )
                if c.category in ("valid_single", "valid_set"):
                    assert is_consistent, f"Test setup error: expected valid case was inconsistent: {consistency_msg}"
                    assert_event_accepted(resp, operation_name=c.case_id)
                    assert_correlation_id_preserved(resp, c.correlation_id)
                else:
                    assert_event_validation_rejected(
                        resp,
                        expected_error_keyword=c.expected_error_keyword,
                        operation_name=c.case_id,
                    )
                return resp

            run_step(
                report,
                step_name,
                execute_edge_case,
                detail=lambda _: exchange_detail(context.ws.last_exchange),
                error_detail=lambda err: {
                    "error": f"{type(err).__name__}: {err}",
                    **exchange_detail(context.ws.last_exchange),
                },
                mark_remaining_on_error=False,
            )
            responses[case.case_id] = responses.get(case.case_id, {})
    finally:
        context.ws.close()
        context.rest_client.close()

    return BarcodeValidationFlowResult(responses=responses, report=report)
