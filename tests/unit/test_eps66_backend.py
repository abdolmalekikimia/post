import pytest

from config.settings import Settings
from services.eps66_backend import build_eps66_backend_plan


def _settings() -> Settings:
    return Settings(
        eps66_same_destination_barcode="660000000000000000000001",
        eps66_destination_change_barcode="660000000000000000000002",
        eps66_closed_bag_barcode="660000000000000000000003",
        eps66_timestamp_barcode="660000000000000000000004",
        eps66_retry_barcode="660000000000000000000005",
        eps66_origin_code="59544",
        eps66_initial_destination_code="71956",
    )


def test_eps66_mock_plan_contains_history_and_postal_fixtures(monkeypatch):
    monkeypatch.setenv("EPS66_BACKEND_MODE", "mock")

    plan = build_eps66_backend_plan(_settings())

    assert plan.mode == "mock"
    assert plan.requires_external_state is True
    assert any("HistoryRecords__660000000000000000000001" in line for line in plan.mock_env)
    assert "Integrations__CoreApi__Mock__Scenario=Success" in plan.mock_env
    assert "Integrations__PostalApi__Mock__Scenario=Success" in plan.mock_env


def test_eps66_core_plan_does_not_apply_mock_overrides(monkeypatch):
    monkeypatch.setenv("EPS66_BACKEND_MODE", "core")
    settings = Settings(eps66_core_ready=True)

    plan = build_eps66_backend_plan(settings)

    assert plan.mode == "core"
    assert plan.mock_env == ()
    assert "real core" in plan.description.casefold()


def test_eps66_core_mode_requires_explicit_readiness(monkeypatch):
    monkeypatch.setenv("EPS66_BACKEND_MODE", "core")
    settings = Settings(eps66_core_ready=False)

    with pytest.raises(RuntimeError, match="EPS66_CORE_READY=1"):
        build_eps66_backend_plan(settings)
