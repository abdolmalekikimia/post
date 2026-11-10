import pytest

from config.eps_catalog import EPS_COVERAGE, coverage_for


def test_eps_catalog_contains_all_supported_eps_once():
    eps_ids = [entry.eps for entry in EPS_COVERAGE]

    assert eps_ids == [
        "config sync",
        "policy sync",
        "device lifecycle",
        "core history",
        "postal coordination",
        "destination lookup",
        "deferred status",
        "lazy upload",
        "reread",
        "status override",
        "destination assignment",
        "destination update",
        "bag selection",
        "export before container",
        "label",
        "container response",
        "physical audit",
        "operational events",
        "event provisioning",
        "doc gated",
        "chaos",
        "mock env",
        "installer update",
    ]
    assert len(eps_ids) == len(set(eps_ids))


def test_eps_catalog_exposes_protocol_and_dependency_status():
    device_lifecycle = coverage_for("device-lifecycle")

    assert device_lifecycle.protocol == "Mixed"
    assert device_lifecycle.dependency_status == "Ready"
    assert device_lifecycle.positive == "Implemented"
    assert device_lifecycle.negative == "Implemented"

    postal_coordination = coverage_for("postal coordination")
    assert postal_coordination.positive == "Implemented"

    reread = coverage_for("reread")
    assert reread.positive == "Partial / External Dependency"
    assert reread.negative == "Partial / External Dependency"


def test_eps_catalog_rejects_unknown_eps():
    with pytest.raises(KeyError, match="Unknown EPS"):
        coverage_for("unknown item")
