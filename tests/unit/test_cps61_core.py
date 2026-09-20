"""Unit tests for CPS-61: Asynchronous Attachment Metadata Linking.

Validates the full attachment linking flow and edge cases with Mock client.
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from assertions.cps61_attachment_assertions import (
    assert_correlation_id_preserved,
    assert_dossier_has_attachment,
    assert_idempotent_metadata_replay,
    assert_metadata_linked_successfully,
    assert_metadata_validation_rejected,
    assert_out_of_order_metadata_queued,
)
from clients.http_client import HttpClient
from flows.images.cps61_attachment_link_flow import (
    AttachmentLinkCase,
    run_cps61_attachment_flow,
)


@pytest.mark.unit
@pytest.mark.cps61
def test_cps61_assertions_unit():
    """Verify individual CPS-61 assertion functions."""
    # TC-01 Success
    assert_metadata_linked_successfully({"status": "Accepted"}, 202, "parcels/1/face.jpg")

    # TC-02 Out of order
    assert_out_of_order_metadata_queued(202, {"status": "QueuedForRetry"})

    # TC-03 Idempotent replay
    first_resp = {"attachmentId": "att-1", "readingId": "read-1"}
    replay_resp = {"attachmentId": "att-1", "readingId": "read-1"}
    assert_idempotent_metadata_replay(first_resp, replay_resp, 202, 202)

    # TC-04 Validation error
    assert_metadata_validation_rejected(400, {"error": "Invalid barcode"})

    # TC-05 Dossier attachment verification
    dossier = {
        "parcelBarcode": "PK123",
        "attachments": [{"objectKey": "parcels/123/face.jpg", "type": "ParcelFace"}],
    }
    assert_dossier_has_attachment(dossier, "parcels/123/face.jpg", "PK123")

    # TC-06 Correlation-ID preserved
    assert_correlation_id_preserved({"correlationId": "corr-test-1"}, "corr-test-1")


@pytest.mark.unit
@pytest.mark.cps61
def test_cps61_flow_with_mock_client():
    """Verify that run_cps61_attachment_flow executes all registered steps cleanly with Mock."""
    mock_client = MagicMock(spec=HttpClient)
    mock_client.last_exchange = {}

    def mock_post(path, payload=None, headers=None):
        mock_resp = MagicMock()
        # TC-04 is expected to fail validation
        if not payload or not payload.get("parcelBarcode"):
            mock_resp.status_code = 400
            mock_resp.text = '{"error": "Validation failed"}'
            mock_resp.json.return_value = {"error": "Validation failed"}
        else:
            mock_resp.status_code = 202
            corr = headers.get("X-Correlation-ID") if headers else "corr-default"
            mock_resp.text = f'{{"status": "Accepted", "correlationId": "{corr}"}}'
            mock_resp.json.return_value = {"status": "Accepted", "correlationId": corr}
        return mock_resp

    mock_client.post.side_effect = mock_post

    result = run_cps61_attachment_flow(client_factory=lambda: mock_client)

    assert result is not None
    assert result.report is not None
    from utils.step_report import StepStatus

    assert len(result.report.records) == 4
    for record in result.report.records:
        assert record.status == StepStatus.PASSED, f"Step {record.name} failed: {record.error}"
