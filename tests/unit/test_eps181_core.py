"""Unit tests for EPS-181: Mock Environment Variable Generation for Negative Testing."""

import pytest

from assertions.eps181_mock_env_assertions import (
    ASPNET_ENV_KEY_RE,
    REQUIRED_NEGATIVE_PROFILES,
    assert_aspnet_env_key_format,
    assert_autodispatch_negative_deadline,
    assert_core_history_status,
    assert_mock_env_profile_valid,
    assert_negative_scenario_profile_coverage,
    assert_postal_scenario_override,
)
from flows.mock_env.eps181_mock_env_flow import (
    EPS181_CASES,
    build_eps181_cases,
    run_eps181_flow,
    run_tc01_postal_profiles,
    run_tc02_core_profiles,
    run_tc03_config_profiles,
    run_tc04_coverage_verify,
    run_tc05_export_env,
)
from utils.mock_env_generator import MockEnvGenerator, NegativeScenarioDefinition


# ---------------------------------------------------------------------------
# TC-1: Case catalogue completeness
# ---------------------------------------------------------------------------

def test_eps181_case_catalog_contains_five_scenarios():
    cases = build_eps181_cases()
    case_ids = [c.case_id for c in cases]
    assert case_ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05"]
    assert len(case_ids) == len(set(case_ids))


def test_eps181_case_categories_match():
    cats = {c.case_id: c.category for c in EPS181_CASES}
    assert cats["TC-01"] == "postal_mock"
    assert cats["TC-02"] == "core_mock"
    assert cats["TC-03"] == "config_mock"
    assert cats["TC-04"] == "coverage_verify"
    assert cats["TC-05"] == "export_env"


# ---------------------------------------------------------------------------
# TC-2: ASP.NET Core environment variable format assertions
# ---------------------------------------------------------------------------

def test_valid_aspnet_env_key_passes():
    assert_aspnet_env_key_format("Integrations__CoreApi__Mock__Scenario")
    assert_aspnet_env_key_format("Section__SubSection__Property__0__Key")


def test_invalid_aspnet_env_key_rejected():
    with pytest.raises(AssertionError, match="not a valid ASP.NET Core env key"):
        assert_aspnet_env_key_format("SingleWord")

    with pytest.raises(AssertionError, match="not a valid ASP.NET Core env key"):
        assert_aspnet_env_key_format("Section:SubSection:Key")

    with pytest.raises(AssertionError, match="key must be a string"):
        assert_aspnet_env_key_format(12345)


def test_mock_env_profile_valid():
    valid_profile = {
        "Integrations__PostalApi__Mock__Scenario": "Timeout",
        "Integrations__PostalApi__RegistrationPolling__TimeoutMs": "5000",
    }
    assert_mock_env_profile_valid("test_profile", valid_profile)


def test_empty_mock_env_profile_rejected():
    with pytest.raises(AssertionError, match="must contain at least one environment variable"):
        assert_mock_env_profile_valid("empty_profile", {})


def test_mock_env_profile_with_none_value_rejected():
    with pytest.raises(AssertionError, match="must not be None"):
        assert_mock_env_profile_valid("bad_profile", {"Integrations__Key__Val": None})


# ---------------------------------------------------------------------------
# TC-3: Negative profile coverage
# ---------------------------------------------------------------------------

def test_negative_scenario_coverage_passes():
    gen = MockEnvGenerator()
    profiles = gen.get_profile_dict()
    assert_negative_scenario_profile_coverage(profiles)


def test_negative_scenario_coverage_fails_on_missing_profile():
    incomplete = {"postal_timeout": {"Integrations__Key": "Val"}}
    with pytest.raises(AssertionError, match="missing required negative mock profiles"):
        assert_negative_scenario_profile_coverage(incomplete)


# ---------------------------------------------------------------------------
# TC-4: Specific scenario assertions
# ---------------------------------------------------------------------------

def test_postal_scenario_override_assertion():
    bc = "200000000000000000000003"
    env_vars = {f"Integrations__PostalApi__Mock__ScenarioOverrides__{bc}": "Timeout"}
    assert_postal_scenario_override(env_vars, bc, "Timeout")

    with pytest.raises(AssertionError, match="expected"):
        assert_postal_scenario_override(env_vars, bc, "Rejected")


def test_core_history_status_assertion():
    bc = "100000000000000000000004"
    env_vars = {f"Integrations__CoreApi__Mock__HistoryRecords__{bc}__Status": "Rejected"}
    assert_core_history_status(env_vars, bc, "Rejected")

    with pytest.raises(AssertionError, match="expected"):
        assert_core_history_status(env_vars, bc, "Success")


def test_autodispatch_negative_deadline_assertion():
    negative_deadline_env = {
        "Integrations__CoreApi__Mock__ConfigSnapshots__59544__AutoDispatchPolicy__AllowedDeadline": "-01:00:00"
    }
    assert_autodispatch_negative_deadline(negative_deadline_env, "59544")

    zero_deadline_env = {
        "Integrations__CoreApi__Mock__ConfigSnapshots__59544__AutoDispatchPolicy__AllowedDeadline": "00:00:00"
    }
    assert_autodispatch_negative_deadline(zero_deadline_env, "59544")

    positive_deadline_env = {
        "Integrations__CoreApi__Mock__ConfigSnapshots__59544__AutoDispatchPolicy__AllowedDeadline": "02:00:00"
    }
    with pytest.raises(AssertionError, match="not a negative or zero duration"):
        assert_autodispatch_negative_deadline(positive_deadline_env, "59544")


# ---------------------------------------------------------------------------
# TC-5: MockEnvGenerator functionality
# ---------------------------------------------------------------------------

def test_mock_env_generator_produces_all_scenarios():
    gen = MockEnvGenerator(exchange_center="59544")
    scenarios = gen.generate_all_negative_scenarios()
    assert len(scenarios) >= 11

    names = {s.name for s in scenarios}
    for req in REQUIRED_NEGATIVE_PROFILES:
        assert req in names

    # Verify each scenario has required fields
    for s in scenarios:
        assert s.scenario_id.startswith("NEG-")
        assert s.target_service in ("PostalApi", "CoreApi", "EdgeConfig")
        assert s.category in ("timeout", "rejection", "unavailable", "validation", "discrepancy")
        assert s.expected_edge_status in (1, 2)
        assert len(s.expected_error_contains) > 0
        assert len(s.env_vars) > 0


def test_mock_env_generator_renders_formatted_env():
    gen = MockEnvGenerator()
    text = gen.render_env_file()
    assert "# ASP.NET Core Mock Environment Variables" in text
    assert "Integrations__PostalApi__Mock__ScenarioOverrides__" in text
    assert "Integrations__CoreApi__Mock__HistoryRecords__" in text

    # Filter by specific scenario
    single_scenario_text = gen.render_env_file("postal_timeout")
    assert "NEG-POSTAL-01" in single_scenario_text
    assert "postal_timeout" in single_scenario_text
    assert "NEG-CORE-01" not in single_scenario_text


# ---------------------------------------------------------------------------
# TC-6: BDD flow execution (mock / unit)
# ---------------------------------------------------------------------------

def test_tc01_postal_profiles_runs():
    res = run_tc01_postal_profiles()
    assert res.case.case_id == "TC-01"
    assert res.summary["postal_scenarios_count"] >= 4
    assert len(res.report.records) >= 4


def test_tc02_core_profiles_runs():
    res = run_tc02_core_profiles()
    assert res.case.case_id == "TC-02"
    assert res.summary["core_scenarios_count"] >= 4
    assert len(res.report.records) >= 4


def test_tc03_config_profiles_runs():
    res = run_tc03_config_profiles()
    assert res.case.case_id == "TC-03"
    assert res.summary["config_scenarios_count"] >= 2
    assert len(res.report.records) >= 2


def test_tc04_coverage_verify_runs():
    res = run_tc04_coverage_verify()
    assert res.case.case_id == "TC-04"
    assert res.summary["total_negative_profiles"] >= 11


def test_tc05_export_env_runs():
    res = run_tc05_export_env()
    assert res.case.case_id == "TC-05"
    assert res.summary["rendered_length_chars"] > 500
    assert res.summary["line_count"] > 20


def test_unified_flow_runs_all_five():
    results = run_eps181_flow()
    assert len(results) == 5
    ids = [r.case.case_id for r in results]
    assert ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05"]
