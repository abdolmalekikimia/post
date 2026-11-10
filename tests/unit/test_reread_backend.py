import pytest

from config.settings import Settings
from services.reread_backend import build_reread_backend_plan


def _settings() -> Settings:
    return Settings(
        reread_same_destination_barcode="660000000000000000000001",
        reread_destination_change_barcode="660000000000000000000002",
        reread_closed_bag_barcode="660000000000000000000003",
        reread_timestamp_barcode="660000000000000000000004",
        reread_retry_barcode="660000000000000000000005",
        reread_origin_code="59544",
        reread_initial_destination_code="71956",
    )


def test_reread_mock_plan_contains_history_and_postal_fixtures(monkeypatch):
    monkeypatch.setenv("REREAD_BACKEND_MODE", "mock")

    plan = build_reread_backend_plan(_settings())

    assert plan.mode == "mock"
    assert plan.requires_external_state is True
    assert any("HistoryRecords__660000000000000000000001" in line for line in plan.mock_env)
    assert "Integrations__CoreApi__Mock__Scenario=Success" in plan.mock_env
    assert "Integrations__PostalApi__Mock__Scenario=Success" in plan.mock_env


def test_reread_core_plan_does_not_apply_mock_overrides(monkeypatch):
    monkeypatch.setenv("REREAD_BACKEND_MODE", "core")
    settings = Settings(reread_core_ready=True)

    plan = build_reread_backend_plan(settings)

    assert plan.mode == "core"
    assert plan.mock_env == ()
    assert "real core" in plan.description.casefold()


def test_reread_core_mode_requires_explicit_readiness(monkeypatch):
    monkeypatch.setenv("REREAD_BACKEND_MODE", "core")
    settings = Settings(reread_core_ready=False)

    with pytest.raises(RuntimeError, match="REREAD_CORE_READY=1"):
        build_reread_backend_plan(settings)
