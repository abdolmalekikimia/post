from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import time
from typing import Any, Callable
from uuid import uuid4

from assertions.signalr_assertions import assert_success_response
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import (
    ExecutionReport,
    FlowExecutionError,
    exchange_detail,
)


@dataclass
class Eps49NegativeResult:
    admin_token: str
    responses: dict[str, Any]
    report: ExecutionReport


def _status_code(exchange: dict[str, Any]) -> int | None:
    response = exchange.get("response")
    return response.get("statusCode") if isinstance(response, dict) else None


def _response_status(response: Any) -> Any:
    if not isinstance(response, dict):
        return None
    payload = response.get("payload")
    if isinstance(payload, dict):
        return payload.get("status", response.get("status"))
    return response.get("status")


def _negative_step(
    report: ExecutionReport,
    step_name: str,
    action: Callable[[], Any],
    exchange: Callable[[], dict[str, Any]],
    expected: str,
    response_is_expected: Callable[[Any], bool] | None = None,
    exception_is_expected: Callable[[Exception, dict[str, Any]], bool] | None = None,
    mark_remaining_on_error: bool = True,
) -> Any:
    started_at = time.monotonic()
    try:
        result = action()
    except Exception as exc:
        current_exchange = exchange()
        if exception_is_expected is not None and exception_is_expected(
            exc,
            current_exchange,
        ):
            detail = {
                **exchange_detail(current_exchange),
                "error": f"{type(exc).__name__}: {exc}",
            }
            report.passed(
                step_name,
                time.monotonic() - started_at,
                detail=detail,
            )
            return None

        detail = {
            **exchange_detail(current_exchange),
            "error": f"{type(exc).__name__}: {exc}",
        }
        report.failed(
            step_name,
            time.monotonic() - started_at,
            f"{type(exc).__name__}: {exc}",
            detail=detail,
        )
        if mark_remaining_on_error:
            report.mark_remaining_not_executed()
        report.print()
        raise FlowExecutionError(
            report.flow_name,
            step_name,
            exc,
            report,
        ) from exc

    current_exchange = exchange()
    if response_is_expected is not None and response_is_expected(result):
        report.passed(
            step_name,
            time.monotonic() - started_at,
            detail=exchange_detail(current_exchange),
        )
        return result

    unexpected = AssertionError(
        f"Negative scenario returned an unexpected response; "
        f"expected: {expected}; response={result!r}"
    )
    report.failed(
        step_name,
        time.monotonic() - started_at,
        str(unexpected),
        detail={
            **exchange_detail(current_exchange),
            "error": str(unexpected),
        },
    )
    if mark_remaining_on_error:
        report.mark_remaining_not_executed()
    report.print()
    raise FlowExecutionError(
        report.flow_name,
        step_name,
        unexpected,
        report,
    )


def _http_status_is(*statuses: int) -> Callable[[Exception, dict[str, Any]], bool]:
    return lambda _error, current_exchange: _status_code(current_exchange) in statuses


def _device_status_is(*statuses: int) -> Callable[[Any], bool]:
    return lambda response: _response_status(response) in statuses or str(
        _response_status(response)
    ) in {str(status) for status in statuses}


def _new_envelope(
    message_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    correlation_id = str(uuid4())
    return {
        "protocolVersion": "1.0",
        "messageType": message_type,
        "correlationId": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "payload": payload,
    }


def _run_ws_case(
    report: ExecutionReport,
    step_name: str,
    run_settings: Settings,
    action: Callable[[DeviceService, DeviceWebSocketClient], Any],
    expected: str,
    response_is_expected: Callable[[Any], bool] | None = None,
    exception_is_expected: Callable[[Exception, dict[str, Any]], bool] | None = None,
    protocol: dict[str, Any] | None = None,
    mark_remaining_on_error: bool = True,
) -> Any:
    ws = DeviceWebSocketClient(
        run_settings.ws_url,
        run_settings.timeout_seconds,
    )
    try:
        return _negative_step(
            report=report,
            step_name=step_name,
            action=lambda: _connect_and_run(
                ws,
                run_settings,
                action,
                protocol,
            ),
            exchange=lambda: ws.last_exchange,
            expected=expected,
            response_is_expected=response_is_expected,
            exception_is_expected=exception_is_expected,
            mark_remaining_on_error=mark_remaining_on_error,
        )
    except FlowExecutionError:
        raise
    finally:
        ws.close()


def run_eps49_negative_flow(
    run_settings: Settings = settings,
) -> Eps49NegativeResult:
    report = ExecutionReport("EPS-49 negative scenarios")
    report.register(
        "1. [PRECONDITION] Valid Admin Login",
        "2. [EPS-49] Admin Login - invalid username",
        "3. [EPS-49] Admin Login - invalid password",
        "4. [EPS-49] Admin Login - empty credentials",
        "5. [EPS-49] Update Device IP - invalid IP format",
        "6. [EPS-49] Update Device IP - unknown device (upsert)",
        "7. [EPS-49] Update Device IP - missing admin token",
        "8. [EPS-49] Auth - invalid deviceId",
        "9. [EPS-49] Auth - invalid deviceToken",
        "10. [EPS-49] Auth - empty deviceToken",
        "11. [EPS-49] WebSocket - invalid handshake protocol",
        "12. [EPS-49] RegisterInbound - before Auth",
        "13. [EPS-49] RegisterInbound - malformed payload",
        "14. [EPS-49] Auth - invocation after connection close",
    )

    rest_client = RestClient(
        run_settings.base_url,
        run_settings.timeout_seconds,
    )
    admin = AdminService(rest_client)
    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)

    admin_token = _negative_step(
        report,
        "1. [PRECONDITION] Valid Admin Login",
        lambda: admin.login(
            run_settings.admin_username,
            run_settings.admin_password,
        ),
        exchange=lambda: rest_client.last_exchange,
        expected="HTTP 2xx and a non-empty admin token",
        response_is_expected=lambda token: bool(token),
    )
    responses: dict[str, Any] = {}
    case_failures: list[FlowExecutionError] = []

    def run_http_case(
        step_name: str,
        case_name: str,
        action: Callable[[], Any],
        expected_statuses: tuple[int, ...],
        response_is_expected: Callable[[Any], bool] | None = None,
        expected: str | None = None,
    ) -> None:
        if run_settings.api_delay_seconds > 0:
            time.sleep(run_settings.api_delay_seconds)
        try:
            responses[case_name] = _negative_step(
                report=report,
                step_name=step_name,
                action=action,
                exchange=lambda: rest_client.last_exchange,
                expected=expected or f"HTTP status in {expected_statuses}",
                response_is_expected=response_is_expected,
                exception_is_expected=_http_status_is(*expected_statuses),
                mark_remaining_on_error=False,
            )
        except FlowExecutionError as error:
            case_failures.append(error)
            responses[case_name] = {"error": str(error)}

    run_http_case(
        "2. [EPS-49] Admin Login - invalid username",
        "invalid_username",
        lambda: admin.login("invalid-admin", run_settings.admin_password),
        (400, 401, 403),
    )
    run_http_case(
        "3. [EPS-49] Admin Login - invalid password",
        "invalid_password",
        lambda: admin.login(run_settings.admin_username, "wrong-password"),
        (400, 401, 403),
    )
    run_http_case(
        "4. [EPS-49] Admin Login - empty credentials",
        "empty_credentials",
        lambda: admin.login("", ""),
        (400, 401, 403),
    )
    run_http_case(
        "5. [EPS-49] Update Device IP - invalid IP format",
        "invalid_ip_format",
        lambda: admin.update_device_ip(
            run_settings.device_id,
            "999.999.999.999",
            admin_token,
        ),
        (400, 422),
    )
    run_http_case(
        "6. [EPS-49] Update Device IP - unknown device (upsert)",
        "unknown_device",
        # QA OPEN QUESTION (EPS-49): the current Edge-only environment
        # observes 200/upsert here. Re-validate after Edge-Core integration
        # and change this expectation if the official contract is known-only.
        lambda: admin.update_device_ip(
            "UNKNOWN-DEVICE-001",
            run_settings.device_ip,
            admin_token,
        ),
        (200,),
        response_is_expected=lambda response: (
            _status_code(rest_client.last_exchange) == 200
            and isinstance(response, dict)
            and response.get("deviceId") == "UNKNOWN-DEVICE-001"
            and response.get("ipAddress") == run_settings.device_ip
        ),
        expected="HTTP 200 with the requested deviceId and ipAddress",
    )
    run_http_case(
        "7. [EPS-49] Update Device IP - missing admin token",
        "missing_admin_token",
        lambda: admin.update_device_ip(
            run_settings.device_id,
            run_settings.device_ip,
            "",
        ),
        (401, 403),
    )

    def run_auth_case(
        step_name: str,
        case_name: str,
        device_id: str,
        device_token: str,
    ) -> None:
        try:
            responses[case_name] = _run_ws_case(
                report,
                step_name,
                run_settings,
                action=lambda device, _ws: device.auth(device_id, device_token),
                expected="device response status=2",
                response_is_expected=_device_status_is(2),
                mark_remaining_on_error=False,
            )
        except FlowExecutionError as error:
            case_failures.append(error)
            responses[case_name] = {"error": str(error)}

    run_auth_case(
        "8. [EPS-49] Auth - invalid deviceId",
        "invalid_device_id",
        "UNKNOWN-DEVICE-001",
        run_settings.device_token,
    )
    run_auth_case(
        "9. [EPS-49] Auth - invalid deviceToken",
        "invalid_device_token",
        run_settings.device_id,
        "wrong-device-token",
    )
    run_auth_case(
        "10. [EPS-49] Auth - empty deviceToken",
        "empty_device_token",
        run_settings.device_id,
        "",
    )

    try:
        responses["invalid_handshake_protocol"] = _run_invalid_handshake_case(
            report,
            run_settings,
            mark_remaining_on_error=False,
        )
    except FlowExecutionError as error:
        case_failures.append(error)
        responses["invalid_handshake_protocol"] = {"error": str(error)}

    try:
        responses["register_before_auth"] = _run_ws_case(
            report,
            "12. [EPS-49] RegisterInbound - before Auth",
            run_settings,
            action=lambda device, _ws: device.register_inbound(
                run_settings.barcode,
                run_settings.inbound_timeout_ms,
            ),
            expected="device response status=2 or an authorization error",
            response_is_expected=_device_status_is(2, 4),
            exception_is_expected=lambda error, _exchange: any(
                text in str(error).lower()
                for text in ("auth", "unauthorized", "not authenticated")
            ),
            mark_remaining_on_error=False,
        )
    except FlowExecutionError as error:
        case_failures.append(error)
        responses["register_before_auth"] = {"error": str(error)}

    try:
        responses["malformed_register_payload"] = _run_ws_case(
            report,
            "13. [EPS-49] RegisterInbound - malformed payload",
            run_settings,
            action=lambda device, ws: _run_malformed_register_payload(
                device,
                ws,
                run_settings,
            ),
            expected="device response status=2 or a SignalR invocation error",
            response_is_expected=_device_status_is(2),
            exception_is_expected=lambda error, _exchange: "registerinbound"
            in str(error).lower(),
            mark_remaining_on_error=False,
        )
    except FlowExecutionError as error:
        case_failures.append(error)
        responses["malformed_register_payload"] = {"error": str(error)}

    def invoke_after_close(device: DeviceService, ws: DeviceWebSocketClient) -> Any:
        ws.close()
        return device.auth(
            run_settings.device_id,
            run_settings.device_token,
        )

    try:
        responses["auth_after_connection_close"] = _run_ws_case(
            report,
            "14. [EPS-49] Auth - invocation after connection close",
            run_settings,
            action=invoke_after_close,
            expected="client must reject invocation on a closed socket",
            exception_is_expected=lambda error, _exchange: "not connected"
            in str(error).lower(),
            mark_remaining_on_error=False,
        )
    except FlowExecutionError as error:
        case_failures.append(error)
        responses["auth_after_connection_close"] = {"error": str(error)}

    rest_client.close()
    report.print()
    if case_failures:
        raise case_failures[0]
    return Eps49NegativeResult(
        admin_token=admin_token,
        responses=responses,
        report=report,
    )


def _connect_and_run(
    ws: DeviceWebSocketClient,
    run_settings: Settings,
    action: Callable[[DeviceService, DeviceWebSocketClient], Any],
    protocol: dict[str, Any] | None,
) -> Any:
    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)
    if protocol is not None:
        ws.JSON_PROTOCOL = protocol
    ws.connect()
    device = DeviceService(ws)
    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)
    return action(device, ws)


def _run_malformed_register_payload(
    device: DeviceService,
    ws: DeviceWebSocketClient,
    run_settings: Settings,
) -> Any:
    auth_response = device.auth(
        run_settings.device_id,
        run_settings.device_token,
    )
    assert_success_response(auth_response, "Auth precondition")
    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)
    return ws.invoke(
        "RegisterInbound",
        [_new_envelope("inbound.register", {})],
    )


def _run_invalid_handshake_case(
    report: ExecutionReport,
    run_settings: Settings,
    mark_remaining_on_error: bool = True,
) -> Any:
    ws = DeviceWebSocketClient(
        run_settings.ws_url,
        run_settings.timeout_seconds,
    )
    try:
        return _negative_step(
            report=report,
            step_name="11. [EPS-49] WebSocket - invalid handshake protocol",
            action=lambda: _connect_and_run(
                ws,
                run_settings,
                lambda _device, _ws: None,
                {"protocol": "unsupported", "version": 99},
            ),
            exchange=lambda: ws.last_exchange,
            expected="SignalR handshake must be rejected",
            exception_is_expected=lambda error, _exchange: any(
                text in str(error).lower()
                for text in ("handshake", "unsupported protocol")
            ),
            mark_remaining_on_error=mark_remaining_on_error,
        )
    finally:
        ws.close()
