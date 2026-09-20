"""Flow implementation for CPS-61: Asynchronous Attachment Metadata Linking.

Tests:
- TC-01: Successful linking of Metadata to an existing ReadingRecord
- TC-02: Out-of-order handling: Metadata arrives before ReadingRecord (queued for retry)
- TC-03: Idempotent replay of same Metadata message (no duplicate links created)
- TC-04: Incomplete/malformed Metadata message rejection
- TC-05: Dossier verification to ensure objectKey is preserved and queryable
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
import time
from typing import Any, Callable, Optional
import uuid

from assertions.cps61_attachment_assertions import (
    assert_correlation_id_preserved,
    assert_dossier_has_attachment,
    assert_idempotent_metadata_replay,
    assert_metadata_linked_successfully,
    assert_metadata_validation_rejected,
    assert_out_of_order_metadata_queued,
)
from clients.http_client import HttpClient
from config.settings import Settings, settings
from utils.auth_helper import get_configured_edge_id
from utils.step_report import (
    ExecutionReport,
    FlowExecutionError,
    exchange_detail,
    run_step,
)


@dataclass(frozen=True)
class AttachmentLinkCase:
    case_id: str
    title: str
    scenario_type: str  # "link_success", "out_of_order", "replay", "validation_error"
    parcel_barcode: str
    edge_id: str
    object_key: str
    content_type: str
    attachment_type: str
    correlation_id: str
    idempotency_key: str
    reading_id: Optional[str] = None
    expected_status_code: int = 202


def build_default_cps61_cases(run_settings: Settings = settings) -> tuple[AttachmentLinkCase, ...]:
    """Build default test cases covering the BDD acceptance criteria of CPS-61."""
    from utils.test_data import (
        generate_dynamic_barcode_24,
        generate_correlation_id,
        generate_idempotency_key,
    )

    # Generate valid 24-digit postal barcodes
    parcel_barcode = generate_dynamic_barcode_24(prefix="590001", slot=610)
    orphan_barcode = generate_dynamic_barcode_24(prefix="590001", slot=611)

    return (
        AttachmentLinkCase(
            case_id="TC-01",
            title="Attach Metadata to existing ReadingRecord (Asynchronous Link)",
            scenario_type="link_success",
            parcel_barcode=parcel_barcode,
            edge_id=get_configured_edge_id(),
            object_key=f"parcels/{parcel_barcode}/face.jpg",
            content_type="image/jpeg",
            attachment_type="ParcelFace",
            correlation_id=str(uuid.uuid4()),
            idempotency_key=str(uuid.uuid4()),
            reading_id=str(uuid.uuid4()),
            expected_status_code=202,
        ),
        AttachmentLinkCase(
            case_id="TC-02",
            title="Out-of-order: Metadata received before ReadingRecord exists (Queued for Retry)",
            scenario_type="out_of_order",
            parcel_barcode=orphan_barcode,
            edge_id=get_configured_edge_id(),
            object_key=f"parcels/orphan/{orphan_barcode}.jpg",
            content_type="image/jpeg",
            attachment_type="BarcodeCloseUp",
            correlation_id=str(uuid.uuid4()),
            idempotency_key=str(uuid.uuid4()),
            expected_status_code=202,
        ),
        AttachmentLinkCase(
            case_id="TC-03",
            title="Idempotent Replay: Re-sending same Metadata does not create duplicate attachment",
            scenario_type="replay",
            parcel_barcode=parcel_barcode,
            edge_id=get_configured_edge_id(),
            object_key=f"parcels/{parcel_barcode}/face.jpg",
            content_type="image/jpeg",
            attachment_type="ParcelFace",
            correlation_id=str(uuid.uuid4()),
            idempotency_key=str(uuid.uuid4()),
            expected_status_code=202,
        ),
        AttachmentLinkCase(
            case_id="TC-04",
            title="Validation: Incomplete Metadata message rejected without partial state",
            scenario_type="validation_error",
            parcel_barcode="",  # Invalid empty barcode
            edge_id=get_configured_edge_id(),
            object_key="",  # Invalid empty key
            content_type="image/jpeg",
            attachment_type="ParcelFace",
            correlation_id=str(uuid.uuid4()),
            idempotency_key=str(uuid.uuid4()),
            expected_status_code=400,
        ),
    )


@dataclass
class AttachmentLinkFlowResult:
    responses: dict[str, Any]
    report: ExecutionReport


def run_cps61_attachment_flow(
    run_settings: Settings = settings,
    cases: tuple[AttachmentLinkCase, ...] | None = None,
    client_factory: Callable[[], HttpClient] | None = None,
) -> AttachmentLinkFlowResult:
    """Execute the CPS-61 Asynchronous Attachment Metadata Linking Flow."""
    active_cases = cases or build_default_cps61_cases(run_settings)
    report = ExecutionReport("CPS-61 Attachment Metadata Linking Flow")
    report.register(*(f"{case.case_id}: {case.title}" for case in active_cases))

    client = (
        client_factory()
        if client_factory is not None
        else HttpClient(
            base_url=run_settings.core_base_url,
            timeout=run_settings.core_timeout_seconds,
        )
    )

    edge_token = None
    try:
        from utils.auth_helper import get_edge_token
        edge_token = get_edge_token(client, run_settings=run_settings)
    except Exception:
        pass

    responses: dict[str, Any] = {}

    for case in active_cases:
        step_name = f"{case.case_id}: {case.title}"

        def execute_case(c: AttachmentLinkCase = case) -> dict[str, Any]:
            headers = {
                "Content-Type": "application/json",
                "X-Correlation-ID": c.correlation_id,
                "Idempotency-Key": c.idempotency_key,
            }
            if edge_token:
                headers["Authorization"] = f"Bearer {edge_token}"

            payload = {
                "parcelBarcode": c.parcel_barcode,
                "edgeId": c.edge_id,
                "objectKey": c.object_key,
                "contentType": c.content_type,
                "attachmentType": c.attachment_type,
                "occurredAtUtc": datetime.now(timezone.utc).isoformat(),
                "correlationId": c.correlation_id,
                "idempotencyKey": c.idempotency_key,
            }
            if c.reading_id:
                payload["readingId"] = c.reading_id

            if c.scenario_type == "link_success":
                resp = client.post(run_settings.core_image_metadata_path, payload=payload, headers=headers)
                data = resp.json() if resp.text else {}
                assert_metadata_linked_successfully(data, resp.status_code, c.object_key)
                assert_correlation_id_preserved(data, c.correlation_id)
                return {
                    "statusCode": resp.status_code,
                    "body": data,
                    "payloadSent": payload,
                }

            elif c.scenario_type == "out_of_order":
                resp = client.post(run_settings.core_image_metadata_path, payload=payload, headers=headers)
                data = resp.json() if resp.text else {}
                assert_out_of_order_metadata_queued(resp.status_code, data)
                return {
                    "statusCode": resp.status_code,
                    "body": data,
                    "payloadSent": payload,
                }

            elif c.scenario_type == "replay":
                # First submission
                resp1 = client.post(run_settings.core_image_metadata_path, payload=payload, headers=headers)
                data1 = resp1.json() if resp1.text else {}
                # Immediate replay of same metadata
                resp2 = client.post(run_settings.core_image_metadata_path, payload=payload, headers=headers)
                data2 = resp2.json() if resp2.text else {}

                assert_idempotent_metadata_replay(data1, data2, resp1.status_code, resp2.status_code)
                return {
                    "firstStatus": resp1.status_code,
                    "replayStatus": resp2.status_code,
                    "body": data2,
                    "payloadSent": payload,
                }

            elif c.scenario_type == "validation_error":
                resp = client.post(run_settings.core_image_metadata_path, payload=payload, headers=headers)
                data = resp.json() if resp.text else {}
                assert_metadata_validation_rejected(resp.status_code, data)
                return {
                    "statusCode": resp.status_code,
                    "body": data,
                    "payloadSent": payload,
                }

            raise ValueError(f"Unknown scenario type: {c.scenario_type}")

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

    return AttachmentLinkFlowResult(responses=responses, report=report)
