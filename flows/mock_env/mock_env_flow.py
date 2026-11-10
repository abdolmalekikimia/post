"""Flow implementation for mock env: Negative Test Mock Environment Variables.

Implements BDD scenarios:
  TC-01: PostalApi negative mock profiles (timeout, rejected, unavailable, pending, parcel error)
  TC-02: CoreApi negative mock profiles (history rejected, history timeout, unavailable, discrepancy)
  TC-03: Edge Config negative mock profiles (invalid deadline, inactive device)
  TC-04: Full negative profile coverage verification
  TC-05: Render and export formatted .env text for QA team
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from assertions.mock_env_assertions import (
    assert_mock_env_profile_valid,
    assert_negative_scenario_profile_coverage,
)
from utils.mock_env_generator import MockEnvGenerator, NegativeScenarioDefinition
from utils.step_report import ExecutionReport, run_step


# ---------------------------------------------------------------------------
# BDD case catalogue
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MockEnvCase:
    case_id: str
    title: str
    category: str


MOCK_ENV_CASES: tuple[MockEnvCase, ...] = (
    MockEnvCase("TC-01", "Generate and validate PostalApi negative mock profiles", "postal_mock"),
    MockEnvCase("TC-02", "Generate and validate CoreApi negative mock profiles", "core_mock"),
    MockEnvCase("TC-03", "Generate and validate Edge Config negative mock profiles", "config_mock"),
    MockEnvCase("TC-04", "Verify full negative scenario profile coverage", "coverage_verify"),
    MockEnvCase("TC-05", "Render and export formatted .env text for QA team", "export_env"),
)


def build_mock_env_cases() -> tuple[MockEnvCase, ...]:
    return MOCK_ENV_CASES


# ---------------------------------------------------------------------------
# Result class
# ---------------------------------------------------------------------------

@dataclass
class MockEnvResult:
    case: MockEnvCase
    report: ExecutionReport
    summary: Dict[str, Any] = field(default_factory=dict)


def _step(
    report: ExecutionReport,
    name: str,
    action: Callable[[], Any],
    success_msg: str,
) -> Any:
    report.register(name)
    return run_step(report, name, action, success_msg)


# ---------------------------------------------------------------------------
# Flow runners (one per scenario)
# ---------------------------------------------------------------------------

def run_tc01_postal_profiles(*, report: ExecutionReport | None = None) -> MockEnvResult:
    """TC-01: PostalApi negative mock profiles."""
    report = report or ExecutionReport("mock env/TC-01: PostalApi negative mock profiles")
    case = MOCK_ENV_CASES[0]
    gen = MockEnvGenerator()
    scenarios = [s for s in gen.generate_all_negative_scenarios() if s.target_service == "PostalApi"]

    for s in scenarios:
        _step(
            report,
            f"validate_{s.name}_env_keys",
            lambda _s=s: assert_mock_env_profile_valid(_s.name, _s.env_vars),
            f"Profile '{s.name}' ({len(s.env_vars)} keys) validated",
        )

    report.print()
    return MockEnvResult(
        case=case,
        report=report,
        summary={"postal_scenarios_count": len(scenarios)},
    )


def run_tc02_core_profiles(*, report: ExecutionReport | None = None) -> MockEnvResult:
    """TC-02: CoreApi negative mock profiles."""
    report = report or ExecutionReport("mock env/TC-02: CoreApi negative mock profiles")
    case = MOCK_ENV_CASES[1]
    gen = MockEnvGenerator()
    scenarios = [s for s in gen.generate_all_negative_scenarios() if s.target_service == "CoreApi"]

    for s in scenarios:
        _step(
            report,
            f"validate_{s.name}_env_keys",
            lambda _s=s: assert_mock_env_profile_valid(_s.name, _s.env_vars),
            f"Profile '{s.name}' ({len(s.env_vars)} keys) validated",
        )

    report.print()
    return MockEnvResult(
        case=case,
        report=report,
        summary={"core_scenarios_count": len(scenarios)},
    )


def run_tc03_config_profiles(*, report: ExecutionReport | None = None) -> MockEnvResult:
    """TC-03: Edge Config negative mock profiles."""
    report = report or ExecutionReport("mock env/TC-03: Edge Config negative mock profiles")
    case = MOCK_ENV_CASES[2]
    gen = MockEnvGenerator()
    scenarios = [s for s in gen.generate_all_negative_scenarios() if s.target_service == "EdgeConfig"]

    for s in scenarios:
        _step(
            report,
            f"validate_{s.name}_env_keys",
            lambda _s=s: assert_mock_env_profile_valid(_s.name, _s.env_vars),
            f"Profile '{s.name}' ({len(s.env_vars)} keys) validated",
        )

    report.print()
    return MockEnvResult(
        case=case,
        report=report,
        summary={"config_scenarios_count": len(scenarios)},
    )


def run_tc04_coverage_verify(*, report: ExecutionReport | None = None) -> MockEnvResult:
    """TC-04: Full negative profile coverage verification."""
    report = report or ExecutionReport("mock env/TC-04: Full negative profile coverage verification")
    case = MOCK_ENV_CASES[3]
    gen = MockEnvGenerator()
    profiles = gen.get_profile_dict()

    _step(
        report,
        "verify_all_required_negative_profiles_present",
        lambda: assert_negative_scenario_profile_coverage(profiles),
        f"All {len(profiles)} required negative mock profiles covered",
    )

    report.print()
    return MockEnvResult(
        case=case,
        report=report,
        summary={"total_negative_profiles": len(profiles)},
    )


def run_tc05_export_env(*, report: ExecutionReport | None = None) -> MockEnvResult:
    """TC-05: Render and export formatted .env text for QA team."""
    report = report or ExecutionReport("mock env/TC-05: Render and export formatted .env text for QA team")
    case = MOCK_ENV_CASES[4]
    gen = MockEnvGenerator()

    rendered = _step(
        report,
        "render_all_profiles_as_env_text",
        lambda: gen.render_env_file(),
        "Rendered .env formatted configuration",
    )

    report.print()
    return MockEnvResult(
        case=case,
        report=report,
        summary={"rendered_length_chars": len(rendered), "line_count": len(rendered.splitlines())},
    )


def run_mock_env_flow() -> List[MockEnvResult]:
    """Execute all five mock env scenarios and return results."""
    return [
        run_tc01_postal_profiles(),
        run_tc02_core_profiles(),
        run_tc03_config_profiles(),
        run_tc04_coverage_verify(),
        run_tc05_export_env(),
    ]
