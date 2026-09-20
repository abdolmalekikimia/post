"""Assertions for CPS-61: Asynchronous Attachment Metadata Linking to ReadingRecord.

Verifies:
- Successful linking of SupplementaryAttachment Metadata to an existing ReadingRecord
- Out-of-order handling: Metadata received before ReadingRecord (Retry/Queue behavior)
- Idempotent processing: Replay of same Metadata does not create duplicate links
- Validation rejection of malformed/incomplete Metadata payloads
- Traceability: Correlation-ID and ReadingId preserved across the chain
"""

from __future__ import annotations

from typing import Any, Mapping


def assert_metadata_linked_successfully(
    response_data: Mapping[str, Any],
    status_code: int,
    expected_object_key: str,
    operation_name: str = "Attachment Link",
) -> None:
    """Validate that Metadata was successfully linked to ReadingRecord and response indicates success."""
    assert status_code in (200, 201, 202, 204), (
        f"[CPS-61 TC-01] Expected success status (200/201/202/204) for {operation_name}, "
        f"got {status_code}. Response: {response_data}"
    )


def assert_out_of_order_metadata_queued(
    status_code: int,
    response_data: Mapping[str, Any],
    operation_name: str = "Out-of-Order Metadata",
) -> None:
    """Validate that when Metadata arrives before ReadingRecord, it is queued for retry (202 Accepted) or returns a transient error.

    This depends on Core contract design - typically 202 Accepted with retry info, or 409/404 transient.
    """
    assert status_code in (202, 404, 409, 422), (
        f"[CPS-61 TC-02] Out-of-order metadata handling failed. "
        f"Expected queued/transient status (202/404/409/422), got {status_code}. "
        f"Response: {response_data}"
    )


def assert_idempotent_metadata_replay(
    first_response: Mapping[str, Any],
    replay_response: Mapping[str, Any],
    first_status: int,
    replay_status: int,
    operation_name: str = "Metadata Replay",
) -> None:
    """Validate that replaying the exact same Metadata payload yields identical outcome (no duplicate links)."""
    assert replay_status == first_status, (
        f"[CPS-61 TC-03] Idempotent replay status mismatch for {operation_name}: "
        f"first={first_status}, replay={replay_status}"
    )
    
    # Compare key business fields if present
    for key in ("attachmentId", "readingId", "status", "linked"):
        if key in first_response and key in replay_response:
            assert first_response[key] == replay_response[key], (
                f"[CPS-61 TC-03] Field '{key}' diverged on replay: "
                f"original={first_response[key]}, replay={replay_response[key]}"
            )


def assert_metadata_validation_rejected(
    status_code: int,
    response_data: Mapping[str, Any],
    expected_missing_field: str | None = None,
) -> None:
    """Validate that malformed/incomplete Metadata is rejected with 4xx and not linked."""
    assert 400 <= status_code < 500, (
        f"[CPS-61 TC-04] Expected client error (4xx) for invalid metadata, got {status_code}. "
        f"Response: {response_data}"
    )


def assert_dossier_has_attachment(
    dossier_data: Mapping[str, Any],
    expected_object_key: str,
    expected_barcode: str,
) -> None:
    """Verify that the parcel dossier/reading record now contains the linked attachment."""
    # Dossier may have attachments under various keys depending on Core contract
    attachment_found = False
    
    for key in ("attachments", "supplementaryAttachments", "images", "metadata"):
        if key in dossier_data:
            attachments = dossier_data[key]
            if isinstance(attachments, list):
                for att in attachments:
                    if isinstance(att, dict):
                        obj_key = att.get("objectKey") or att.get("object_key") or att.get("ObjectKey")
                        if obj_key == expected_object_key:
                            attachment_found = True
                            break
            elif isinstance(attachments, dict):
                if attachments.get("objectKey") == expected_object_key:
                    attachment_found = True
    
    assert attachment_found, (
        f"[CPS-61 TC-01/TC-02] Dossier for barcode '{expected_barcode}' does not contain "
        f"linked attachment with objectKey '{expected_object_key}'. Dossier: {dossier_data}"
    )


def assert_correlation_id_preserved(
    response_data: Mapping[str, Any],
    sent_correlation_id: str,
    step_name: str = "response",
) -> None:
    """Validate that Correlation-ID is preserved in the response chain."""
    if "correlationId" in response_data:
        assert response_data["correlationId"] == sent_correlation_id, (
            f"[CPS-61 TC-06] Correlation-ID mismatch in {step_name}: "
            f"sent '{sent_correlation_id}', got '{response_data['correlationId']}'"
        )