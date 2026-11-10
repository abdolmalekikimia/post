"""postal contracts Postal adapter contracts. Live: needs RUN_E2E=1.

PC-01 (exact upstream code reaches the device) runs inside the label S3b fault-fixture test,
which carries the postal_contracts marker. This file covers Mock visibility (PC-03) and records the
scenarios that need a contract or the delivered Postal SP.
"""

from __future__ import annotations

import json
import os

import pytest

from assertions.connectivity_assertions import assert_connectivity_response, mock_dependencies
from assertions.signalr_assertions import response_field
from clients.signalr_client import DeviceWebSocketClient
from config.settings import settings
from dataclasses import replace
from flows.bag.label_flow import POSTAL_CONTRACTS_FIDELITY_CASE, POSTAL_CONTRACTS_MIXED_CASE, run_label_flow
from services.device_service import DeviceService


@pytest.mark.e2e
@pytest.mark.postal_contracts
@pytest.mark.success
@pytest.mark.websocket
def test_postal_contracts_03_mock_or_real_mode_of_every_dependency_is_visible() -> None:
    if os.getenv("RUN_E2E") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Edge service")
    client = DeviceWebSocketClient(settings.ws_url, settings.timeout_seconds)
    try:
        client.connect()
        service = DeviceService(client)
        auth = service.auth(settings.device_id, settings.device_token)
        assert response_field(auth, "status") in (0, "0"), f"Auth failed: {auth}"
        payload = assert_connectivity_response(service.check_connectivity(), operation="PC-03")
        mocks = mock_dependencies(payload)
        modes = {c["name"]: ("Mock" if c["status"] == "Mock" else "Real") for c in payload["checks"]}
        print("POSTAL_CONTRACTS_MODES " + json.dumps({"modes": modes, "mockDependencies": mocks}, ensure_ascii=True), flush=True)
        # Mock is reported, never counted as real reachability of the Postal service.
        assert set(modes) >= {"postal.incoming-sql", "postal.export-sql", "postal.rest-token", "postal.soap-parcel-info"}
    finally:
        client.close()


@pytest.mark.e2e
@pytest.mark.postal_contracts
@pytest.mark.negative
def test_postal_contracts_02_leading_zero_code_is_kept_exactly() -> None:
    """Controlled Postal adapter codes '0042' and '42' must reach the device unchanged and as strings.

    Needs RUN_E2E=1, RUN_NEGATIVE=1 and QA_POSTAL_FAULT_FIXTURES=true. The postal contracts answer confirms a leading
    zero is allowed and must be kept exactly, so '0042' arriving as '42' is a failure (live 2026-11-01: lost).
    """
    if os.getenv("RUN_E2E") != "1" or os.getenv("RUN_NEGATIVE") != "1":
        pytest.skip("Set RUN_E2E=1 and RUN_NEGATIVE=1")
    from utils.postal_fault_fixture import PostalFaultFixture
    case = POSTAL_CONTRACTS_FIDELITY_CASE
    with PostalFaultFixture("label", case, replace(settings, label_case=case.case_id)) as fixture:
        result = run_label_flow(fixture.settings, cases=(case,))
    assert set(result.responses) == {case.case_id}


@pytest.mark.e2e
@pytest.mark.postal_contracts
@pytest.mark.success
@pytest.mark.websocket
def test_postal_contracts_04_contract_set_on_the_mock_adapter_is_labelled_mock_not_real() -> None:
    """No real SP will be delivered: the contract set is run on the Mock adapter and labelled as such.

    The injected-code checks are PC-01/02 (fixture tests). This test guards the labelling: a green run on
    Mock must say so, and it is not acceptance of the real Postal SP.
    """
    if os.getenv("RUN_E2E") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Edge service")
    client = DeviceWebSocketClient(settings.ws_url, settings.timeout_seconds)
    try:
        client.connect()
        service = DeviceService(client)
        assert response_field(service.auth(settings.device_id, settings.device_token), "status") in (0, "0")
        payload = assert_connectivity_response(service.check_connectivity(), operation="PC-04")
        postal = [c for c in payload["checks"] if c["name"].startswith("postal.")]
        real = [c["name"] for c in postal if c["status"] != "Mock"]
        verdict = "MOCK_ONLY" if not real else ("REAL_ADAPTER" if len(real) == len(postal) else "MIXED")
        print("POSTAL_CONTRACTS_ADAPTER_VERDICT " + json.dumps({"verdict": verdict, "realDependencies": real,
              "note": "MOCK_ONLY is not acceptance of the real Postal SP"}, ensure_ascii=True), flush=True)
        # No real SP will be delivered, so Postal must stay Mock. Set POSTAL_CONTRACTS_EXPECTED_ADAPTER=REAL_ADAPTER only
        # after the SP is delivered; a silent switch in either direction is a finding.
        expected = os.getenv("POSTAL_CONTRACTS_EXPECTED_ADAPTER", "MOCK_ONLY")
        assert verdict == expected, f"PC-04: Postal adapter mode is {verdict} (real: {real}), expected {expected}"
    finally:
        client.close()


@pytest.mark.e2e
@pytest.mark.postal_contracts
@pytest.mark.negative
def test_postal_contracts_01b_different_codes_in_one_bag_stay_on_their_own_parcels() -> None:
    """Needs RUN_E2E=1, RUN_NEGATIVE=1 and QA_POSTAL_FAULT_FIXTURES=true (controlled Mock, not real Postal)."""
    if os.getenv("RUN_E2E") != "1" or os.getenv("RUN_NEGATIVE") != "1":
        pytest.skip("Set RUN_E2E=1 and RUN_NEGATIVE=1")
    from utils.postal_fault_fixture import PostalFaultFixture
    case = POSTAL_CONTRACTS_MIXED_CASE
    with PostalFaultFixture("label", case, replace(settings, label_case=case.case_id)) as fixture:
        result = run_label_flow(fixture.settings, cases=(case,))
    assert set(result.responses) == {case.case_id}


@pytest.mark.postal_contracts
@pytest.mark.negative
@pytest.mark.parametrize("scenario,reason", [
    ("05", "answered, but not testable here: (1) the official Postal error list is still with Postal (rule meanwhile: all "
           "Postal errors go to the device as they are, only network errors are re-sent, related item item 9); (2) the answer says a "
           "timeout/disconnect gives the device NO reply, but live Edge returns resultType=Error 'operation timed out' "
           "(label S4/S7, ADR related item): contradiction to settle; (3) invalid Postal tariff reply handling "
           "(empty = error, first row wins, success = status=true and message='ok', related item items 1 and 3) lives in the Core "
           "tariff adapter, not on the device wire; (4) Core traceability criterion is the error code in Grafana logs, "
           "but Loki returned no Edge/Core log lines at all for the last 48 hours."),
])
def test_postal_contracts_scenarios_blocked_by_missing_contract(scenario: str, reason: str) -> None:
    pytest.skip(f"POSTAL_CONTRACTS-{scenario}: {reason}")
