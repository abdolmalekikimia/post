from assertions.bag_assertions import (
    assert_bag_count,
    assert_bag_count_at_least,
)
from config.settings import Settings
from flows.destination.destination_update_success_flow import (
    run_destination_update_success_cases,
    success_step_names,
)
from services.device_service import DeviceService
from utils.step_report import ExecutionReport


class FakeDestinationUpdateClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[dict[str, object]]]] = []
        self.last_exchange: dict[str, object] = {}

    def invoke(
        self,
        target: str,
        arguments: list[dict[str, object]],
        invocation_id: str | None = None,
    ) -> dict[str, object]:
        self.calls.append((target, arguments))
        payload = arguments[0]["payload"]
        if target == "RegisterItem":
            response: dict[str, object] = {"status": 0}
        elif target == "AssignRoute":
            response = {"status": 1, "payload": {"errorMessage": None}}
        else:
            destination = payload["destinationCenterCode"]
            chute_ids = payload.get("chuteIds")
            count = 1
            if destination == "11111" and chute_ids is None:
                count = 0
            if destination == "22222" and chute_ids == ["CH-A"]:
                count = 0
            if destination == "11111" and chute_ids == ["CH-Z"]:
                count = 0
            response = {"status": 0, "payload": {"counts": {"n": count}}}
        self.last_exchange = {
            "request": {
                "target": target,
                "arguments": arguments,
                "invocationId": invocation_id,
            },
            "result": response,
        }
        return response


def test_destination_update_success_flow_registers_all_positive_steps():
    names = success_step_names(10)

    assert len(names) == 19
    assert names[0] == (
        "10. [Destination Update] TC-01 RegisterItem - before destination change"
    )
    assert names[-1] == (
        "28. [Destination Update] TC-04 container.close - original chute must contain parcel"
    )


def test_bag_count_assertions_validate_counts_n():
    response = {"status": 0, "payload": {"counts": {"n": 1}}}

    assert_bag_count(response, 1, "Destination Update test")
    assert_bag_count_at_least(response, 1, "Destination Update test")


def test_destination_update_success_flow_executes_all_four_cases():
    client = FakeDestinationUpdateClient()
    report = ExecutionReport("Destination Update positive cases")
    report.register(*success_step_names(10))
    run_settings = Settings(
        api_delay_seconds=0,
        destination_update_initial_destination_code="11111",
        destination_update_new_destination_code="22222",
        destination_update_initial_chute="CH-A",
        destination_update_new_chute="CH-B",
        destination_update_alternate_chute="CH-Z",
        destination_update_barcode_prefix="730000000000000000",
        destination_update_inbound_timeout_ms=3000,
        destination_update_transport_type="road",
    )

    result = run_destination_update_success_cases(
        device=DeviceService(client),  # type: ignore[arg-type]
        run_settings=run_settings,
        report=report,
        wait_between_steps=lambda _: None,
    )

    assert set(result.responses) == {"TC-01", "TC-02", "TC-03", "TC-04"}
    assert len(client.calls) == 19
    assert [target for target, _ in client.calls].count("RegisterItem") == 4
    assert [target for target, _ in client.calls].count("AssignRoute") == 8
    assert [target for target, _ in client.calls].count("CloseContainer") == 7
    assert all(record.expectation == "PASS" for record in report.records)
