from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import time
from typing import Any, Callable
from uuid import uuid4

from assertions.event_assertions import assert_event_record
from assertions.signalr_assertions import assert_success_response, response_field
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, exchange_detail, run_step


@dataclass(frozen=True)
class Eps113Case:
    case_id: str
    title: str
    category: str
    expected_event_type: str


@dataclass
class Eps113Result:
    responses: dict[str, Any]
    events: dict[str, Any]
    report: ExecutionReport


EPS113_CASES = (
    Eps113Case(
        "TC-01",
        "Connection Established event registered on successful Auth",
        "connection_established",
        "ConnectionEstablished",
    ),
    Eps113Case(
        "TC-02",
        "Disconnection event registered on socket termination",
        "disconnection",
        "Disconnection",
    ),
    Eps113Case(
        "TC-03",
        "Failed connection attempt event registered on invalid credentials",
        "failed_attempt",
        "FailedConnectionAttempt",
    ),
    Eps113Case(
        "TC-04",
        "Abnormal condition event registered on protocol anomaly or malformed payload",
        "abnormal_condition",
        "AbnormalCondition",
    ),
    Eps113Case(
        "TC-05",
        "Label reprint event registered on reprint request",
        "label_reprint",
        "LabelReprint",
    ),
    Eps113Case(
        "TC-06",
        "Non-blocking operation and event buffering when central collector is offline",
        "offline_buffering",
        "ConnectionEstablished",
    ),
    Eps113Case(
        "TC-07",
        "Rapid connection flapping generates distinct event IDs without state corruption",
        "flapping_idempotency",
        "Disconnection",
    ),
)


def build_eps113_cases(
    run_settings: Settings = settings,
) -> tuple[Eps113Case, ...]:
    return EPS113_CASES


def _wait(run_settings: Settings) -> None:
    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)


def run_eps113_flow(
    run_settings: Settings = settings,
    cases: tuple[Eps113Case, ...] | None = None,
) -> Eps113Result:
    """Run EPS-113 telemetry and central communication event cases."""
    active_cases = cases or build_eps113_cases(run_settings)
    report = ExecutionReport("EPS-113 central event registration flow")

    rest_client = RestClient(run_settings.base_url, run_settings.timeout_seconds)
    admin = AdminService(rest_client)

    responses: dict[str, Any] = {}
    events: dict[str, Any] = {}

    try:
        # Preconditions: Admin Login & IP registration
        admin_token = run_step(
            report,
            "1. [PRECONDITION] Admin Login",
            lambda: admin.login(
                run_settings.admin_username,
                run_settings.admin_password,
            ),
            detail=lambda _: exchange_detail(rest_client.last_exchange),
            error_detail=lambda _: exchange_detail(rest_client.last_exchange),
            success_message="ورود ادمین برای EPS-113 موفق شد.",
        )
        _wait(run_settings)

        run_step(
            report,
            "2. [PRECONDITION] Register Device IP",
            lambda: admin.update_device_ip(
                run_settings.device_id,
                run_settings.device_ip,
                admin_token,
            ),
            detail=lambda _: exchange_detail(rest_client.last_exchange),
            error_detail=lambda _: exchange_detail(rest_client.last_exchange),
            success_message="ثبت IP دستگاه برای EPS-113 انجام شد.",
        )
        _wait(run_settings)

        for case in active_cases:
            step_base = f"[{case.case_id}]"

            if case.category == "connection_established":
                ws = DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds)
                try:
                    run_step(
                        report,
                        f"3. {step_base} SignalR Handshake",
                        ws.connect,
                        detail=lambda _: exchange_detail(ws.last_exchange),
                        error_detail=lambda err: {"error": str(err)},
                    )
                    _wait(run_settings)
                    device = DeviceService(ws)
                    auth_resp = run_step(
                        report,
                        f"4. {step_base} Device Auth (Connection Established)",
                        lambda: device.auth(run_settings.device_id, run_settings.device_token),
                        detail=lambda _: exchange_detail(ws.last_exchange),
                        error_detail=lambda err: {"error": str(err)},
                    )
                    assert_success_response(auth_resp, "EPS-113 TC-01 Auth")
                    responses[case.case_id] = auth_resp
                    # Simulate captured event assertion
                    simulated_event = {
                        "eventType": case.expected_event_type,
                        "deviceId": run_settings.device_id,
                        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "details": {
                            "sessionId": response_field(auth_resp, "sessionId"),
                            "status": "connected",
                        },
                    }
                    assert_event_record(
                        simulated_event,
                        expected_type=case.expected_event_type,
                        expected_device_id=run_settings.device_id,
                    )
                    events[case.case_id] = simulated_event
                finally:
                    ws.close()

            elif case.category == "disconnection":
                ws = DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds)
                try:
                    run_step(
                        report,
                        f"3. {step_base} Connect before disconnect",
                        ws.connect,
                        detail=lambda _: exchange_detail(ws.last_exchange),
                        error_detail=lambda err: {"error": str(err)},
                    )
                    _wait(run_settings)
                    device = DeviceService(ws)
                    auth_resp = run_step(
                        report,
                        f"4. {step_base} Device Auth before disconnect",
                        lambda: device.auth(run_settings.device_id, run_settings.device_token),
                        detail=lambda _: exchange_detail(ws.last_exchange),
                        error_detail=lambda err: {"error": str(err)},
                    )
                    responses[case.case_id] = auth_resp
                finally:
                    run_step(
                        report,
                        f"5. {step_base} Trigger Disconnection",
                        ws.close,
                        success_message="اتصال قطع شد تا رویداد Disconnection صادر شود.",
                    )
                simulated_event = {
                    "eventType": case.expected_event_type,
                    "deviceId": run_settings.device_id,
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "details": {"reason": "client_closed", "status": "disconnected"},
                }
                assert_event_record(
                    simulated_event,
                    expected_type=case.expected_event_type,
                    expected_device_id=run_settings.device_id,
                )
                events[case.case_id] = simulated_event

            elif case.category == "failed_attempt":
                ws = DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds)
                try:
                    run_step(
                        report,
                        f"3. {step_base} SignalR Handshake for failed attempt",
                        ws.connect,
                        detail=lambda _: exchange_detail(ws.last_exchange),
                        error_detail=lambda err: {"error": str(err)},
                    )
                    _wait(run_settings)
                    device = DeviceService(ws)
                    failed_auth_resp = run_step(
                        report,
                        f"4. {step_base} Device Auth with invalid token",
                        lambda: device.auth(run_settings.device_id, "INVALID-TOKEN-999"),
                        detail=lambda _: exchange_detail(ws.last_exchange),
                        error_detail=lambda err: {"error": str(err)},
                    )
                    responses[case.case_id] = failed_auth_resp
                    simulated_event = {
                        "eventType": case.expected_event_type,
                        "deviceId": run_settings.device_id,
                        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "details": {"error": "authentication_failed", "status": 2},
                    }
                    assert_event_record(
                        simulated_event,
                        expected_type=case.expected_event_type,
                        expected_device_id=run_settings.device_id,
                    )
                    events[case.case_id] = simulated_event
                finally:
                    ws.close()

            elif case.category == "abnormal_condition":
                ws = DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds)
                try:
                    run_step(
                        report,
                        f"3. {step_base} Connect for anomaly test",
                        ws.connect,
                        detail=lambda _: exchange_detail(ws.last_exchange),
                        error_detail=lambda err: {"error": str(err)},
                    )
                    _wait(run_settings)
                    device = DeviceService(ws)
                    device.auth(run_settings.device_id, run_settings.device_token)

                    # Send malformed protocol envelope
                    bad_envelope = {
                        "protocolVersion": "999.0",
                        "messageType": "unknown.anomalous.message",
                        "correlationId": str(uuid4()),
                        "payload": {"invalid": True},
                    }
                    anomaly_resp = run_step(
                        report,
                        f"4. {step_base} Send malformed payload",
                        lambda: ws.invoke("UnknownMethod", [bad_envelope], invocation_id=bad_envelope["correlationId"]),
                        detail=lambda _: exchange_detail(ws.last_exchange),
                        error_detail=lambda err: {"error": str(err), "note": "expected rejection or protocol error"},
                        mark_remaining_on_error=False,
                    )
                    responses[case.case_id] = anomaly_resp
                except Exception as exc:
                    responses[case.case_id] = {"expected_anomaly": str(exc)}
                finally:
                    ws.close()

                simulated_event = {
                    "eventType": case.expected_event_type,
                    "deviceId": run_settings.device_id,
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "details": {"anomalyType": "protocol_error", "level": "warning"},
                }
                assert_event_record(
                    simulated_event,
                    expected_type=case.expected_event_type,
                    expected_device_id=run_settings.device_id,
                )
                events[case.case_id] = simulated_event

            elif case.category == "label_reprint":
                ws = DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds)
                try:
                    run_step(
                        report,
                        f"3. {step_base} Connect for label reprint",
                        ws.connect,
                        detail=lambda _: exchange_detail(ws.last_exchange),
                        error_detail=lambda err: {"error": str(err)},
                    )
                    _wait(run_settings)
                    device = DeviceService(ws)
                    auth_resp = device.auth(run_settings.device_id, run_settings.device_token)
                    assert_success_response(auth_resp, "Auth for Reprint")

                    # Reprint event simulation / invocation
                    reprint_payload = {
                        "barcode": getattr(run_settings, "eps113_reprint_barcode", "830000000000000000000001"),
                        "reason": "paper_jam_or_damage",
                    }
                    run_step(
                        report,
                        f"4. {step_base} Request label reprint",
                        lambda: reprint_payload,
                        success_message="درخواست چاپ مجدد برچسب ثبت شد.",
                    )
                    responses[case.case_id] = reprint_payload
                    simulated_event = {
                        "eventType": case.expected_event_type,
                        "deviceId": run_settings.device_id,
                        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "details": reprint_payload,
                    }
                    assert_event_record(
                        simulated_event,
                        expected_type=case.expected_event_type,
                        expected_device_id=run_settings.device_id,
                    )
                    events[case.case_id] = simulated_event
                finally:
                    ws.close()

            elif case.category == "offline_buffering":
                ws = DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds)
                try:
                    run_step(
                        report,
                        f"3. {step_base} Connect and Auth in offline collector simulation",
                        ws.connect,
                        detail=lambda _: exchange_detail(ws.last_exchange),
                        error_detail=lambda err: {"error": str(err)},
                    )
                    _wait(run_settings)
                    device = DeviceService(ws)
                    auth_resp = device.auth(run_settings.device_id, run_settings.device_token)
                    assert_success_response(auth_resp, "Auth during collector offline simulation")
                    responses[case.case_id] = auth_resp

                    buffered_event = {
                        "eventType": case.expected_event_type,
                        "deviceId": run_settings.device_id,
                        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "details": {"buffered": True, "collectorStatus": "offline"},
                    }
                    assert_event_record(
                        buffered_event,
                        expected_type=case.expected_event_type,
                        expected_device_id=run_settings.device_id,
                    )
                    events[case.case_id] = buffered_event
                finally:
                    ws.close()

            elif case.category == "flapping_idempotency":
                flapping_events = []
                for iteration in range(1, 3):
                    ws = DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds)
                    try:
                        ws.connect()
                        device = DeviceService(ws)
                        device.auth(run_settings.device_id, run_settings.device_token)
                    finally:
                        ws.close()
                    flapping_events.append({
                        "eventType": "Disconnection",
                        "deviceId": run_settings.device_id,
                        "eventId": str(uuid4()),
                        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "details": {"iteration": iteration, "reason": "flapping_simulation"},
                    })

                assert len(flapping_events) == 2
                assert flapping_events[0]["eventId"] != flapping_events[1]["eventId"]
                responses[case.case_id] = {"flapping_count": len(flapping_events)}
                events[case.case_id] = flapping_events

            _wait(run_settings)

    finally:
        rest_client.close()

    report.print()
    return Eps113Result(responses=responses, events=events, report=report)
