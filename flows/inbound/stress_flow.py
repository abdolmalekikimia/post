from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import time
from typing import Any, Callable

from assertions.signalr_assertions import (
    assert_success_response,
    response_field,
    response_payload,
)
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.stress import (
    StressSample,
    StressSummary,
    classify_error,
)


@dataclass(frozen=True)
class InboundStressInput:
    barcodes: tuple[str, ...]
    physical_attributes: dict[str, Any] | None = None
    use_default_physical_attributes: bool = True


@dataclass(frozen=True)
class InboundStressCase:
    name: str
    expected_status: int
    build_input: Callable[[int], InboundStressInput]
    expected_error_contains: str | None = None
    weight: int = 1
    fixture_required: bool = False


@dataclass
class InboundStressResult:
    warmup_response: dict[str, Any]
    samples: list[StressSample]
    flow_name: str

    @property
    def summary(self) -> StressSummary:
        return StressSummary(self.samples)

    def render(self) -> str:
        return self.summary.render(self.flow_name)


def _validate(
    response: dict[str, Any],
    expected_status: int,
    expected_error_contains: str | None,
) -> tuple[bool, str]:
    actual_status = response_field(response, "status")
    if actual_status not in (expected_status, str(expected_status)):
        return False, f"expected status={expected_status}, got {actual_status!r}"
    if expected_error_contains:
        message = str(response_payload(response).get("errorMessage") or "")
        if expected_error_contains not in message:
            return False, (
                f"expected errorMessage containing {expected_error_contains!r}, "
                f"got {message!r}"
            )
    return True, ""


def _weighted(cases: tuple[InboundStressCase, ...]) -> tuple[InboundStressCase, ...]:
    result: list[InboundStressCase] = []
    for case in cases:
        result.extend([case] * max(1, case.weight))
    return tuple(result)


def _correlation_id(exchange: dict[str, Any]) -> str | None:
    request = exchange.get("request")
    if not isinstance(request, dict):
        return None
    arguments = request.get("arguments")
    if not isinstance(arguments, list) or not arguments:
        return None
    envelope = arguments[0]
    value = envelope.get("correlationId") if isinstance(envelope, dict) else None
    return str(value) if value is not None else None


def _run_worker(
    run_settings: Settings,
    cases: tuple[InboundStressCase, ...],
    worker_id: int,
    stop_event: Any,
) -> list[StressSample]:
    client = DeviceWebSocketClient(
        run_settings.ws_url,
        run_settings.timeout_seconds,
    )
    samples: list[StressSample] = []
    try:
        client.connect()
        device = DeviceService(client)
        auth = device.auth(run_settings.device_id, run_settings.device_token)
        assert_success_response(auth, "Stress worker Auth")
        weighted_cases = _weighted(cases)
        for iteration in range(
            worker_id,
            run_settings.stress_iterations,
            run_settings.stress_workers,
        ):
            if stop_event.is_set():
                break
            case = weighted_cases[iteration % len(weighted_cases)]
            request_input = case.build_input(iteration + 1)
            sample = StressSample(
                iteration=iteration + 1,
                case_name=case.name,
                expected_status=case.expected_status,
            )
            started = time.monotonic()
            try:
                response = device.register_inbound_barcodes(
                    barcodes=list(request_input.barcodes),
                    timeout_ms=run_settings.inbound_timeout_ms,
                    physical_attributes=request_input.physical_attributes,
                    use_default_physical_attributes=(
                        request_input.use_default_physical_attributes
                    ),
                )
                exchange = client.last_exchange
                sample.payload_sent = exchange.get("request")
                sample.response_received = exchange.get(
                    "result",
                    exchange.get("response"),
                )
                sample.actual_status = response_field(response, "status")
                sample.correlation_id = _correlation_id(exchange)
                received_id = response.get("correlationId")
                if received_id is not None and str(received_id) != sample.correlation_id:
                    sample.error = (
                        f"correlationId mismatch: sent={sample.correlation_id!r}, "
                        f"received={received_id!r}"
                    )
                else:
                    sample.passed, sample.error = _validate(
                        response,
                        case.expected_status,
                        case.expected_error_contains,
                    )
            except Exception as exc:
                sample.error_kind = type(exc).__name__
                sample.error_category = classify_error(exc)
                sample.error = f"{type(exc).__name__}: {exc}"
                sample.payload_sent = client.last_exchange.get("request")
                sample.response_received = client.last_exchange.get(
                    "result",
                    client.last_exchange.get("response"),
                )
                if run_settings.stress_fail_fast:
                    stop_event.set()
            finally:
                sample.latency_seconds = time.monotonic() - started
                samples.append(sample)
            if not sample.passed and run_settings.stress_fail_fast:
                stop_event.set()
            time.sleep(run_settings.stress_delay_seconds)
    except Exception as exc:
        samples.append(
            StressSample(
                iteration=worker_id,
                case_name=f"worker-{worker_id}-setup",
                expected_status=0,
                error_kind=type(exc).__name__,
                error_category=classify_error(exc),
                error=f"{type(exc).__name__}: {exc}",
            )
        )
        stop_event.set()
    finally:
        client.close()
    return samples


def run_inbound_stress_flow(
    run_settings: Settings,
    cases: tuple[InboundStressCase, ...],
    flow_name: str,
) -> InboundStressResult:
    if not cases:
        raise ValueError("At least one stress case is required")

    rest_client = RestClient(
        run_settings.base_url,
        run_settings.timeout_seconds,
    )
    admin = AdminService(rest_client)
    try:
        admin_token = admin.login(
            run_settings.admin_username,
            run_settings.admin_password,
        )
        time.sleep(run_settings.stress_delay_seconds)
        admin.update_device_ip(
            run_settings.device_id,
            run_settings.device_ip,
            admin_token,
        )
    except Exception:
        rest_client.close()
        raise
    rest_client.close()
    time.sleep(run_settings.stress_delay_seconds)

    warmup_client = DeviceWebSocketClient(
        run_settings.ws_url,
        run_settings.timeout_seconds,
    )
    try:
        warmup_client.connect()
        device = DeviceService(warmup_client)
        auth = device.auth(run_settings.device_id, run_settings.device_token)
        assert_success_response(auth, "Stress warm-up Auth")
        warmup_input = cases[0].build_input(0)
        warmup_response = device.register_inbound_barcodes(
            barcodes=list(warmup_input.barcodes),
            timeout_ms=run_settings.inbound_timeout_ms,
            physical_attributes=warmup_input.physical_attributes,
            use_default_physical_attributes=(
                warmup_input.use_default_physical_attributes
            ),
        )
        valid, error = _validate(
            warmup_response,
            cases[0].expected_status,
            cases[0].expected_error_contains,
        )
        if not valid:
            raise AssertionError(f"Warm-up RegisterInbound failed: {error}")
    finally:
        warmup_client.close()

    from threading import Event

    stop_event = Event()
    samples: list[StressSample] = []
    with ThreadPoolExecutor(max_workers=run_settings.stress_workers) as pool:
        futures = [
            pool.submit(_run_worker, run_settings, cases, worker_id, stop_event)
            for worker_id in range(run_settings.stress_workers)
        ]
        for future in as_completed(futures):
            samples.extend(future.result())

    result = InboundStressResult(
        warmup_response=warmup_response,
        samples=sorted(samples, key=lambda item: item.iteration),
        flow_name=flow_name,
    )
    print(result.render())
    return result
