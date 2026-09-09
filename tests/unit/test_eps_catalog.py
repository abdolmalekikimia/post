import pytest

from config.eps_catalog import EPS_COVERAGE, coverage_for


def test_eps_catalog_contains_all_supported_eps_once():
    eps_ids = [entry.eps for entry in EPS_COVERAGE]

    assert eps_ids == [
        "EPS-40",
        "EPS-46",
        "EPS-49",
        "EPS-53",
        "EPS-55",
        "EPS-60",
        "EPS-64",
        "EPS-66",
        "EPS-68",
        "EPS-71",
        "EPS-73",
        "EPS-76",
        "EPS-79",
        "EPS-83",
        "EPS-87",
        "EPS-89",
        "EPS-113",
    ]
    assert len(eps_ids) == len(set(eps_ids))


def test_eps_catalog_exposes_protocol_and_dependency_status():
    eps49 = coverage_for("eps-49")

    assert eps49.protocol == "Mixed"
    assert eps49.dependency_status == "Ready"
    assert eps49.positive == "Implemented"
    assert eps49.negative == "Implemented"

    eps55 = coverage_for("EPS-55")
    assert eps55.positive == "Implemented"

    eps66 = coverage_for("EPS-66")
    assert eps66.positive == "Partial / External Dependency"
    assert eps66.negative == "Partial / External Dependency"


def test_eps_catalog_rejects_unknown_eps():
    with pytest.raises(KeyError, match="Unknown EPS"):
        coverage_for("EPS-999")
