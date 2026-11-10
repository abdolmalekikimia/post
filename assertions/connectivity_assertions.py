"""connectivity.check response checks (Edge Docs protocol/schemas/connectivity.check.schema.json)."""
from __future__ import annotations

from typing import Any

from assertions.signalr_assertions import response_payload

CHECK_NAMES = {
    "postal.incoming-sql": "SqlInsert",
    "postal.export-sql": "StoredProcedure",
    "postal.rest-token": "RestApi",
    "postal.soap-parcel-info": "Soap",
    "core.api": "CoreApi",
}
CHECK_STATUSES = {"Ok", "Denied", "Unreachable", "Mock"}
_SECRET_MARKERS = ("password", "token=", "bearer ", "secret", "connectionstring", "pwd=")


def assert_connectivity_response(response: dict[str, Any], correlation_id: str | None = None,
                                 operation: str = "connectivity.check") -> dict[str, Any]:
    """status=0 means the probes completed; overallStatus may still be Failed."""
    if correlation_id is not None:
        assert response.get("correlationId") == correlation_id, f"{operation}: correlationId was not echoed"
    assert response.get("messageType") == "connectivity.check", f"{operation}: wrong messageType {response.get('messageType')!r}"
    payload = response_payload(response)
    assert type(payload.get("status")) is int and payload["status"] == 0, (
        f"{operation}: expected status=0, got {payload.get('status')!r}; errorMessage={payload.get('errorMessage')!r}")
    checks = payload.get("checks")
    assert isinstance(checks, list) and checks, f"{operation}: checks[] is required"
    names = [c.get("name") for c in checks if isinstance(c, dict)]
    assert sorted(names) == sorted(CHECK_NAMES), f"{operation}: checks differ from the contract set: {names}"
    for check in checks:
        name = check["name"]
        assert check.get("kind") == CHECK_NAMES[name], f"{operation}: {name} kind {check.get('kind')!r}"
        assert check.get("status") in CHECK_STATUSES, f"{operation}: {name} status {check.get('status')!r}"
        latency = check.get("latencyMs")
        assert type(latency) is int and latency >= 0, f"{operation}: {name} latencyMs {latency!r}"
        detail = str(check.get("detail") or "").lower()
        assert not any(marker in detail for marker in _SECRET_MARKERS), f"{operation}: {name} detail may leak a credential"
    expected = "Ok" if all(c["status"] in ("Ok", "Mock") for c in checks) else "Failed"
    assert payload.get("overallStatus") == expected, (
        f"{operation}: overallStatus {payload.get('overallStatus')!r} contradicts checks (expected {expected})")
    return payload


def mock_dependencies(payload: dict[str, Any]) -> list[str]:
    """Dependencies reported as Mock; a Mock is explicitly not real reachability."""
    return sorted(c["name"] for c in payload.get("checks", []) if c.get("status") == "Mock")


def assert_error_codes_preserved(response: dict[str, Any], injected: dict[str, str], operation: str,
                                 *, keep_leading_zeros: bool = True) -> None:
    """Each injected upstream code must reach the device unchanged; the schema types errorCode as a string.

    keep_leading_zeros=False compares the digits only ('0042' ~ '42'): type and value are checked, the zero
    padding is not.
    """
    errors = response_payload(response).get("errors") or []
    by_barcode = {e.get("barcode"): e for e in errors if isinstance(e, dict)}
    for barcode, code in injected.items():
        assert barcode in by_barcode, f"{operation}: no error item for {barcode}"
        actual = by_barcode[barcode].get("errorCode")
        assert isinstance(actual, str), (
            f"{operation}: errorCode must be a string per bag.close.schema.json, got {type(actual).__name__} {actual!r}")
        same = actual == code if keep_leading_zeros else (actual.lstrip("0") or "0") == (code.lstrip("0") or "0")
        assert same, f"{operation}: upstream code {code!r} reached the device as {actual!r}"


# core-docs p2-t09-health-systemerror-contract.md §4 and §8 (device wire is a PROPOSAL pending Q-22/Q-32).
SYSTEM_ERROR_KINDS = {"dependency-unreachable", "dependency-timeout", "dependency-denied",
                      "configuration-invalid", "internal-failure"}


def assert_system_error_reply(response: dict[str, Any], operation: str, capability: str | None = None) -> dict[str, Any]:
    """Infrastructure failure = status 2 WITH systemError{kind,capability,retryable}."""
    payload = response_payload(response)
    assert payload.get("status") == 2, f"{operation}: infrastructure failure must be status=2, got {payload.get('status')!r}"
    error = payload.get("systemError")
    assert isinstance(error, dict), f"{operation}: status=2 without systemError cannot be told apart from a domain error"
    assert error.get("kind") in SYSTEM_ERROR_KINDS, f"{operation}: unknown systemError.kind {error.get('kind')!r}"
    assert error.get("capability") in CHECK_NAMES, f"{operation}: unknown systemError.capability {error.get('capability')!r}"
    if capability is not None:
        assert error["capability"] == capability, f"{operation}: wrong capability {error['capability']!r}, expected {capability!r}"
    assert type(error.get("retryable")) is bool, f"{operation}: systemError.retryable must be a boolean"
    return error


def assert_not_system_error(response: dict[str, Any], operation: str) -> None:
    """Pending and domain outcomes (returned/refused/validation) never carry systemError."""
    payload = response_payload(response)
    assert "systemError" not in payload or payload["systemError"] is None, (
        f"{operation}: status={payload.get('status')!r} must not be reported as an infrastructure SystemError")


def classify_check_outcome(outcome: Any) -> tuple[str, str, str | None]:
    """Return ("ok"|"rejected", text, protocol-error code) for a reply or a raised hub error.

    ok means a status=0 reply that ran probes; anything else (protocol.error, status=2, exception) is rejected.
    """
    if isinstance(outcome, BaseException):
        text = f"{type(outcome).__name__}: {outcome}"
        payload: dict[str, Any] = {}
    else:
        text = __import__("json").dumps(outcome, ensure_ascii=True, default=str)
        payload = response_payload(outcome) if isinstance(outcome, dict) else {}
    code = payload.get("code") if isinstance(payload.get("code"), str) else None
    if code is None:
        for known in ("MALFORMED_JSON", "MISSING_REQUIRED_FIELD", "UNKNOWN_MESSAGE_TYPE",
                      "UNSUPPORTED_PROTOCOL_VERSION", "VALIDATION_ERROR"):
            if known in text:
                code = known
                break
    ran_probes = payload.get("status") == 0 and isinstance(payload.get("checks"), list) and bool(payload["checks"])
    return ("ok" if ran_probes else "rejected"), text, code


REVIEW_BY = __import__("datetime").date(2026, 12, 1)


def unverified_until_review(message: str, *, review_by=REVIEW_BY, today=None) -> None:
    """Unverified findings must not hide forever: after review_by they fail instead of skipping."""
    from datetime import date
    from utils.step_report import UnverifiedPreconditionError
    if (today or date.today()) > review_by:
        raise AssertionError(f"{message} [open finding past its review date {review_by}; resolve or re-date it]")
    raise UnverifiedPreconditionError(f"{message} [review by {review_by}]")


def dependency_is_healthy(check_response: dict[str, Any]) -> bool:
    """health check answer: one successful connectivity.check is enough to call the dependencies healthy again."""
    payload = response_payload(check_response)
    return payload.get("status") == 0 and payload.get("overallStatus") == "Ok"
