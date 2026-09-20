"""QA execution test suite for EPS-181: Mock Environment Variables for Negative Testing.

Generates and verifies mock environment variables and test datasets for QA testers.
Integration execution against running mock/edge services is enabled via ``RUN_MOCK_ENV_TESTS=1``.
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from flows.mock_env.eps181_mock_env_flow import (
    run_eps181_flow,
    run_tc01_postal_profiles,
    run_tc02_core_profiles,
    run_tc03_config_profiles,
    run_tc04_coverage_verify,
    run_tc05_export_env,
)
from utils.mock_env_generator import MockEnvGenerator


@pytest.mark.mock_env
@pytest.mark.eps181
class TestEps181NegativeMockEnv:
    """Tests verifying generation and export of negative mock environment profiles."""

    def test_tc01_postal_mock_profiles(self):
        """TC-01: PostalApi negative mock profiles."""
        result = run_tc01_postal_profiles()
        assert result.case.case_id == "TC-01"
        assert result.summary["postal_scenarios_count"] >= 5
        assert len(result.report.records) >= 5

    def test_tc02_core_mock_profiles(self):
        """TC-02: CoreApi negative mock profiles."""
        result = run_tc02_core_profiles()
        assert result.case.case_id == "TC-02"
        assert result.summary["core_scenarios_count"] >= 4
        assert len(result.report.records) >= 4

    def test_tc03_config_mock_profiles(self):
        """TC-03: Edge Config negative mock profiles."""
        result = run_tc03_config_profiles()
        assert result.case.case_id == "TC-03"
        assert result.summary["config_scenarios_count"] >= 2
        assert len(result.report.records) >= 2

    def test_tc04_negative_profile_coverage(self):
        """TC-04: Full negative profile coverage verification."""
        result = run_tc04_coverage_verify()
        assert result.case.case_id == "TC-04"
        assert result.summary["total_negative_profiles"] >= 11
        assert len(result.report.records) == 1

    def test_tc05_export_env_file(self, tmp_path: Path):
        """TC-05: Render and export formatted .env text for QA team."""
        result = run_tc05_export_env()
        assert result.case.case_id == "TC-05"
        assert result.summary["line_count"] > 20
        assert len(result.report.records) == 1

        # Also verify writing to disk
        gen = MockEnvGenerator()
        rendered = gen.render_env_file()
        out_file = tmp_path / "negative_test_mock.env"
        out_file.write_text(rendered, encoding="utf-8")
        assert out_file.exists()
        assert "Integrations__PostalApi__Mock__ScenarioOverrides__" in out_file.read_text(encoding="utf-8")

    def test_unified_mock_env_flow_all_scenarios(self):
        """Execute the full BDD flow generating all 5 scenario results with ExecutionReport."""
        results = run_eps181_flow()
        assert len(results) == 5
        for res in results:
            summary = res.report.summary()
            assert summary.get("FAILED", 0) == 0
            assert summary.get("PASSED", 0) > 0
            assert len(res.report.records) > 0

    @pytest.mark.e2e
    def test_live_mock_service_validation_gated(self):
        """Live test verifying that mock service accepts generated environment variables.
        
        Gated by RUN_MOCK_ENV_TESTS=1.
        """
        if os.getenv("RUN_MOCK_ENV_TESTS", "0").lower() not in {"1", "true", "yes", "on"}:
            pytest.skip("Set RUN_MOCK_ENV_TESTS=1 to run against active Edge Mock backend")

        gen = MockEnvGenerator()
        profiles = gen.get_profile_dict()
        assert len(profiles) >= 11
