from config.settings import Settings
from flows.destination.destination_assignment_success_flow_v2 import success_step_names
from flows.destination.destination_assignment_success_flow_v2 import run_destination_assignment_success_cases
from services.device_service import DeviceService
from utils.step_report import ExecutionReport


class FakeDeviceClient:
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
        response: dict[str, object]
        if target == "RegisterInbound":
            response = {"status": 0}
        else:
            response = {"status": 1, "payload": {"errorMessage": None}}
        self.last_exchange = {
            "request": {
                "target": target,
                "arguments": arguments,
                "invocationId": invocation_id,
            },
            "result": response,
        }
        return response


def test_destination_assignment_success_cases_have_explicit_report_steps():
    assert success_step_names(6) == (
        "6. [destination assignment] RegisterInbound - TC-01 with chute",
        "7. [destination assignment] destination.assign - TC-01 with chute",
        "8. [destination assignment] RegisterInbound - TC-02 without chute",
        "9. [destination assignment] destination.assign - TC-02 without chute",
    )


def test_destination_assignment_success_cases_send_with_and_without_chute_payloads():
    client = FakeDeviceClient()
    report = ExecutionReport("destination assignment positive cases")
    report.register(*success_step_names())
    run_settings = Settings(
        api_delay_seconds=0,
        unique_run_data=False,
        destination_assignment_valid_barcode="710000000000000000000001",
        destination_assignment_second_valid_barcode="710000000000000000000002",
        destination_assignment_destination_code="59544",
        destination_assignment_default_chute="CH-04",
    )

    result = run_destination_assignment_success_cases(
        device=DeviceService(client),  # type: ignore[arg-type]
        run_settings=run_settings,
        report=report,
        wait_between_steps=lambda _: None,
    )

    assert [target for target, _ in client.calls] == [
        "RegisterInbound",
        "AssignDestination",
        "RegisterInbound",
        "AssignDestination",
    ]
    assert client.calls[1][1][0]["payload"] == {
        "barcode": "710000000000000000000001",
        "destinationCenterCode": run_settings.destination_assignment_destination_code,
        "chuteId": "CH-04",
    }
    assert client.calls[3][1][0]["payload"] == {
        "barcode": "710000000000000000000002",
        "destinationCenterCode": run_settings.destination_assignment_destination_code,
    }
    assert result.responses == {
        "TC-01_with_chute": {"status": 1, "payload": {"errorMessage": None}},
        "TC-02_without_chute": {
            "status": 1,
            "payload": {"errorMessage": None},
        },
    }
    assert all(record.expectation == "PASS" for record in report.records)
