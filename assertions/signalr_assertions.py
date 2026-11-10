from datetime import datetime
from typing import Any
from uuid import UUID


def response_payload(response: dict[str, Any]) -> dict[str, Any]:
    payload = response.get("payload")
    return payload if isinstance(payload, dict) else response


def response_field(response: dict[str, Any], field: str) -> Any:
    if field in response:
        return response[field]

    return response_payload(response).get(field)


def assert_success_response(response: dict[str, Any], operation: str) -> None:
    status = response_field(response, "status")
    assert status in (0, "0"), (
        f"{operation} failed: expected status=0, response={response}"
    )
    error_message = response_payload(response).get("errorMessage")
    assert error_message in (None, ""), (
        f"{operation} returned status=0 with errorMessage="
        f"{error_message!r}; response={response}"
    )


def assert_completed_inbound_precondition(response: dict[str, Any], operation: str) -> None:
    """Require a final successful inbound result before dependent scenarios run.

    Pending is an observed first response, not proof that the parcel has been
    registered. The final state needs a separate, correlation-bound query.
    """
    if response_field(response, "status") in (1, "1"):
        from utils.inbound_completion import CompletedInboundResponse
        if isinstance(response, CompletedInboundResponse):
            response.assert_verified()
            return
        from utils.step_report import UnverifiedPreconditionError

        raise UnverifiedPreconditionError(
            f"{operation}: inbound returned Pending (status=1); final registration "
            "was not verified, so dependent assertions cannot run"
        )
    assert_success_response(response, operation)


def assert_successful_auth_wire_contract(response: dict[str, Any]) -> None:
    """Validate successful Auth under the agreed device acceptance policy.

    Base: Edge Docs / protocol/schemas/auth.schema.json, with the explicit
    null-errorMessage exception below. The original response is preserved
    for reporting; this is not strict conformance to the unchanged Schema.
    """
    payload = response_payload(response)
    assert isinstance(payload, dict), "Auth result must contain a JSON object payload"
    assert set(payload) <= {"status", "sessionId", "edgeServerTime", "errorMessage"}, (
        f"Auth response has fields outside auth.schema.json: {set(payload) - {'status', 'sessionId', 'edgeServerTime', 'errorMessage'}}"
    )
    assert type(payload.get("status")) is int and payload["status"] == 0, (
        f"Auth success schema requires numeric status=0; got {payload.get('status')!r}"
    )
    session_id = payload.get("sessionId")
    assert isinstance(session_id, str), "Auth success schema requires string sessionId"
    try:
        UUID(session_id)
    except ValueError as exc:
        raise AssertionError("Auth success schema requires UUID sessionId") from exc
    edge_time = payload.get("edgeServerTime")
    assert isinstance(edge_time, str), "Auth success schema requires string edgeServerTime"
    try:
        parsed_time = datetime.fromisoformat(edge_time.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError("Auth success schema requires date-time edgeServerTime") from exc
    assert parsed_time.tzinfo is not None, (
        "Auth success schema requires date-time edgeServerTime with UTC offset"
    )
    # Acceptance decision, 2026-10-26: the user confirmed that the device
    # decides Auth success from status and ignores errorMessage:null.
    # Tolerate only this null on successful Auth; keep status/session/time
    # checks and reject other non-string errorMessage values. Do not extend
    # this exception to error responses or unrelated nullable fields.
    if "errorMessage" in payload and payload["errorMessage"] is not None:
        assert isinstance(payload["errorMessage"], str), (
            "Auth success: errorMessage must be a string or the agreed null value"
        )
