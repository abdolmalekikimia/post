from subprocess import CompletedProcess

from config.settings import Settings
from scripts.run_all_tests import _classify, _extract_failures, build_test_matrix


def test_runner_counts_individual_pytest_outcomes():
    result = CompletedProcess(
        args=[],
        returncode=1,
        stdout="7 passed, 2 failed, 3 skipped, 1 error in 0.2s",
        stderr="",
    )

    outcome = _classify(result)

    assert outcome.status == "FAIL"
    assert outcome.passed == 7
    assert outcome.failed == 2
    assert outcome.skipped == 3
    assert outcome.errors == 1
    assert outcome.total == 13


def test_runner_extracts_flow_execution_failures():
    result = CompletedProcess(
        args=[],
        returncode=1,
        stdout="""Execution report: policy sync - TC-03: Enabled policy with zero deadline rejects the full sync
01. [FAIL] 1. [policy sync] Valid Admin Login - precondition
    error: ReadTimeout
    expected: FAIL
Result: PASS=0, FAIL=1, NOT_CHECKED=3
1 failed, 1 passed in 1.42s""",
        stderr="",
    )

    outcome = _classify(result)

    assert outcome.status == "FAIL"
    assert len(outcome.failures) >= 1
    assert any("policy sync" in f and "Valid Admin Login" in f for f in outcome.failures)


def test_runner_extracts_pytest_failed_summary():
    result = CompletedProcess(
        args=[],
        returncode=1,
        stdout="FAILED tests/negative/test_policy_sync_negative.py::test_policy_sync_negative_case",
        stderr="",
    )

    outcome = _classify(result)

    assert outcome.status == "FAIL"
    assert len(outcome.failures) >= 1
    assert any("test_policy_sync_negative_case" in f for f in outcome.failures)


def test_settings_reads_environment_when_instantiated(monkeypatch):
    monkeypatch.setenv("BASE_URL", "http://changed-during-process")

    assert Settings().base_url == "http://changed-during-process"


def test_runner_matrix_contains_catalogs_success_and_negative():
    runs = build_test_matrix()
    labels = [test_run.label for test_run in runs]

    assert "Catalogs and unit" in labels
    assert "Success / destination update" in labels
    assert "Negative / policy sync" in labels
    assert "Negative / destination update" in labels
    destination_update_neg = next(r for r in runs if r.label == "Negative / destination update")
    assert destination_update_neg.marker == "destination_update_negative"
    assert destination_update_neg.environment.get("DESTINATION_UPDATE_CASE") == "all"
    assert destination_update_neg.environment.get("RUN_DESTINATION_UPDATE_NEGATIVE") == "1"
