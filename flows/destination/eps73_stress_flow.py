from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Barrier
import time
from typing import Any

from assertions.bag_assertions import (
    assert_destination_assignment_success,
    bag_count,
)
from assertions.signalr_assertions import (
    assert_success_response,
    response_field,
    response_payload,
)
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.stress import StressSample, StressSummary


@dataclass
class Eps73StressResult:
    warmup_response: dict[str, Any]
    samples: list[StressSample]
    flow_name: str = "EPS-73 stress"

    @property
    def summary(self) -> StressSummary:
        return StressSummary(self.samples)

    def render(self) -> str:
        return self.summary.render(self.flow_name)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _barcode(run_settings: Settings, iteration: int) -> str:
    prefix = "".join(
        character
        for character in run_settings.eps73_barcode_prefix
        if character.isdigit()
    )
    return f"{prefix}{100000 + iteration:06d}"[-24:]


def _exchange_detail(exchange: dict[str, Any]) -> dict[str, Any]:
    return {
        "payloadSent": exchange.get("request"),
        "responseReceived": exchange.get(
            "result",
            exchange.get("response"),
        ),
    }


def _correlation_id(exchange: dict[str, Any]) -> str | None:
    request = exchange.get("request")
    if not isinstance(request, dict):
        return None
    arguments = request.get("arguments")
    if not isinstance(arguments, list) or not arguments:
        return None
    envelope = arguments[0]
    if not isinstance(envelope, dict):
        return None
    value = envelope.get("correlationId")
    return str(value) if value is not None else None


def _wait(run_settings: Settings) -> None:
    if run_settings.stress_delay_seconds > 0:
        time.sleep(run_settings.stress_delay_seconds)


def _register(
    device: DeviceService,
    run_settings: Settings,
    barcode: str,
) -> dict[str, Any]:
    response = device.register_inbound(
        barcode=barcode,
        timeout_ms=run_settings.eps73_inbound_timeout_ms,
        physical_attributes={
            "weightGrams": 850,
            "dimensions": {
                "lengthMm": 300,
                "widthMm": 200,
                "heightMm": 100,
            },
        },
        parcel_type="packet",
        supplementary_data={"appearanceStatus": "intact"},
        read_timestamp=_timestamp(),
    )
    assert_success_response(response, "EPS-73 stress RegisterInbound")
    return response


def _assign_initial(
    device: DeviceService,
    run_settings: Settings,
    barcode: str,
) -> dict[str, Any]:
    response = device.assign_destination(
        barcode=barcode,
        destination_center_code=run_settings.eps73_initial_destination_code,
        chute_id=run_settings.eps73_initial_chute,
    )
    assert_destination_assignment_success(
        response,
        "EPS-73 stress initial destination.assign",
    )
    return response


def _auth(device: DeviceService, run_settings: Settings) -> dict[str, Any]:
    response = device.auth(run_settings.device_id, run_settings.device_token)
    assert_success_response(response, "EPS-73 stress Auth")
    return response


def _race_worker(
    operation: str,
    run_settings: Settings,
    barcode: str,
    barrier: Barrier,
) -> dict[str, Any]:
    client = DeviceWebSocketClient(
        run_settings.ws_url,
        run_settings.timeout_seconds,
    )
    try:
        client.connect()
        device = DeviceService(client)
        _auth(device, run_settings)
        barrier.wait(timeout=run_settings.timeout_seconds)
        if operation == "bag_close":
            response = device.close_bag(
                destination_center_code=(
                    run_settings.eps73_initial_destination_code
                ),
                seal_number=f"SEAL-EPS73-STRESS-{barcode[-6:]}",
                transport_type=run_settings.eps73_transport_type,
            )
        else:
            response = device.assign_destination(
                barcode=barcode,
                destination_center_code=run_settings.eps73_new_destination_code,
                chute_id=run_settings.eps73_new_chute,
            )
        return {
            "response": response,
            "exchange": dict(client.last_exchange),
        }
    except Exception as exc:
        return {
            "response": None,
            "exchange": dict(client.last_exchange),
            "error": f"{type(exc).__name__}: {exc}",
            "error_kind": type(exc).__name__,
        }
    finally:
        client.close()


def evaluate_race_result(
    bag_response: dict[str, Any] | None,
    assignment_response: dict[str, Any] | None,
) -> tuple[bool, str]:
    """Validate one EPS-73 TC-06 race outcome."""
    if bag_response is None or assignment_response is None:
        return False, "One of the concurrent responses is missing"

    bag_status = response_field(bag_response, "status")
    assignment_status = response_field(assignment_response, "status")
    if bag_status not in (0, "0"):
        return False, f"expected bag.close status=0, got {bag_status!r}"

    payload = response_payload(bag_response)
    counts = payload.get("counts")
    if not isinstance(counts, dict) or "n" not in counts:
        return False, "bag.close response does not contain counts.n"
    selected_count = bag_count(bag_response)

    if assignment_status in (1, "1"):
        if selected_count != 0:
            return (
                False,
                "race condition: destination changed successfully while "
                f"bag.close selected {selected_count} parcel(s)",
            )
        return True, ""

    if assignment_status in (2, "2"):
        error_message = str(
            response_payload(assignment_response).get("errorMessage") or ""
        )
        if not error_message.strip():
            return False, "rejected assignment has no errorMessage"
        if selected_count < 1:
            return (
                False,
                "assignment was rejected after bag close, but bag.close "
                "did not select the parcel",
            )
        return True, ""

    return (
        False,
        "expected destination.assign status=1 or status=2, "
        f"got {assignment_status!r}",
    )


def _run_iteration(
    run_settings: Settings,
    iteration: int,
) -> StressSample:
    barcode = _barcode(run_settings, iteration)
    sample = StressSample(
        iteration=iteration,
        case_name="TC-06 concurrent bag.close and destination.assign",
        expected_status=(
            "bag.close=0 and destination.assign=1 with counts.n=0 "
            "or destination.assign=2 after bag close"
        ),
    )
    started = time.monotonic()
    setup_client = DeviceWebSocketClient(
        run_settings.ws_url,
        run_settings.timeout_seconds,
    )
    setup_exchanges: dict[str, dict[str, Any]] = {}
    race_results: dict[str, dict[str, Any]] = {}
    try:
        setup_client.connect()
        setup_device = DeviceService(setup_client)
        _auth(setup_device, run_settings)
        register_response = _register(setup_device, run_settings, barcode)
        setup_exchanges["register"] = dict(setup_client.last_exchange)
        _wait(run_settings)
        initial_assign_response = _assign_initial(
            setup_device,
            run_settings,
            barcode,
        )
        setup_exchanges["initialAssign"] = dict(setup_client.last_exchange)
        _wait(run_settings)
        barrier = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as executor:
            bag_future = executor.submit(
                _race_worker,
                "bag_close",
                run_settings,
                barcode,
                barrier,
            )
            assign_future = executor.submit(
                _race_worker,
                "destination_assign",
                run_settings,
                barcode,
                barrier,
            )
            race_results["bagClose"] = bag_future.result()
            race_results["destinationAssign"] = assign_future.result()

        bag_result = race_results["bagClose"]
        assignment_result = race_results["destinationAssign"]
        bag_response = bag_result.get("response")
        assignment_response = assignment_result.get("response")
        sample.actual_status = {
            "bagClose": (
                response_field(bag_response, "status")
                if isinstance(bag_response, dict)
                else None
            ),
            "destinationAssign": (
                response_field(assignment_response, "status")
                if isinstance(assignment_response, dict)
                else None
            ),
        }
        sample.payload_sent = {
            "setup": {
                "register": _exchange_detail(setup_exchanges["register"])[
                    "payloadSent"
                ],
                "initialAssign": _exchange_detail(
                    setup_exchanges["initialAssign"]
                )["payloadSent"],
            },
            "race": {
                key: _exchange_detail(value["exchange"])["payloadSent"]
                for key, value in race_results.items()
            },
        }
        sample.response_received = {
            "setup": {
                "register": _exchange_detail(setup_exchanges["register"])[
                    "responseReceived"
                ],
                "initialAssign": _exchange_detail(
                    setup_exchanges["initialAssign"]
                )["responseReceived"],
            },
            "race": {
                key: _exchange_detail(value["exchange"])["responseReceived"]
                for key, value in race_results.items()
            },
        }
        correlation_ids = {
            key: _correlation_id(value["exchange"])
            for key, value in race_results.items()
        }
        sample.correlation_id = str(correlation_ids)

        errors = [
            value
            for value in race_results.values()
            if value.get("error")
        ]
        if errors:
            sample.error_kind = str(errors[0].get("error_kind", "Error"))
            sample.error = str(errors[0]["error"])
        else:
            sample.passed, sample.error = evaluate_race_result(
                bag_response,
                assignment_response,
            )
            for key, race_result in race_results.items():
                sent_id = _correlation_id(race_result["exchange"])
                received = race_result.get("response")
                received_id = (
                    received.get("correlationId")
                    if isinstance(received, dict)
                    else None
                )
                if (
                    received_id is not None
                    and sent_id is not None
                    and str(received_id) != sent_id
                ):
                    sample.passed = False
                    sample.error = (
                        f"{key} correlationId mismatch: "
                        f"sent={sent_id!r}, received={received_id!r}"
                    )
                    break
    except Exception as exc:
        sample.error_kind = type(exc).__name__
        sample.error = f"{type(exc).__name__}: {exc}"
        sample.payload_sent = {
            key: _exchange_detail(value)["payloadSent"]
            for key, value in setup_exchanges.items()
        }
        sample.response_received = {
            key: _exchange_detail(value)["responseReceived"]
            for key, value in setup_exchanges.items()
        }
    finally:
        sample.latency_seconds = time.monotonic() - started
        setup_client.close()
    return sample


def run_eps73_stress_flow(
    run_settings: Settings = settings,
) -> Eps73StressResult:
    if run_settings.stress_iterations <= 0:
        raise ValueError("STRESS_ITERATIONS must be greater than zero")
    if run_settings.stress_workers != 1:
        raise ValueError(
            "EPS-73 TC-06 requires STRESS_WORKERS=1; each iteration already "
            "runs bag.close and destination.assign concurrently"
        )

    rest_client = RestClient(
        run_settings.base_url,
        run_settings.timeout_seconds,
    )
    admin = AdminService(rest_client)
    admin_token = admin.login(
        run_settings.admin_username,
        run_settings.admin_password,
    )
    _wait(run_settings)
    admin.update_device_ip(
        run_settings.device_id,
        run_settings.device_ip,
        admin_token,
    )
    _wait(run_settings)

    warmup_client = DeviceWebSocketClient(
        run_settings.ws_url,
        run_settings.timeout_seconds,
    )
    try:
        warmup_client.connect()
        warmup_device = DeviceService(warmup_client)
        _auth(warmup_device, run_settings)
        warmup_response = _register(
            warmup_device,
            run_settings,
            _barcode(run_settings, 0),
        )
    finally:
        warmup_client.close()

    samples: list[StressSample] = []
    for iteration in range(1, run_settings.stress_iterations + 1):
        sample = _run_iteration(run_settings, iteration)
        samples.append(sample)
        if not sample.passed and run_settings.stress_fail_fast:
            break
        _wait(run_settings)

    result = Eps73StressResult(
        warmup_response=warmup_response,
        samples=sorted(samples, key=lambda item: item.iteration),
    )
    print(result.render())
    return result


if __name__ == "__main__":
    run_eps73_stress_flow()
