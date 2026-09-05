import pytest

from config.scenario_catalog import SCENARIO_COVERAGE, coverage_for


def test_scenario_catalog_contains_unique_supported_families():
    names = [entry.scenario for entry in SCENARIO_COVERAGE]

    assert names == [
        "configuration_sync",
        "policy_sync",
        "device_lifecycle",
        "history_backend",
        "delivery_merge",
        "destination_lookup",
        "lazy_upload",
        "status_override",
        "destination_assignment",
        "destination_update",
        "container_selection",
        "export_before_container",
        "container_response",
        "physical_container_audit",
    ]
    assert len(names) == len(set(names))


def test_scenario_catalog_exposes_protocol_and_dependency_status():
    device = coverage_for("DEVICE_LIFECYCLE")

    assert device.protocol == "Mixed"
    assert device.dependency_status == "Ready"
    assert device.positive == "Implemented"
    assert device.negative == "Implemented"


def test_scenario_catalog_rejects_unknown_family():
    with pytest.raises(KeyError, match="Unknown scenario"):
        coverage_for("unknown-family")
