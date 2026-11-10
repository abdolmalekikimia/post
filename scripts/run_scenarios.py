"""Run the complete active test matrix with one command.

The E2E tests use environment variables to select a case. This runner owns
that matrix so users do not need to invoke pytest once per case manually.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import argparse
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable

from config.scenario_catalog import SCENARIO_COVERAGE

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTEST = [sys.executable, "-m", "pytest"]
RESET = "\033[0m"
STATUS_COLORS = {
    "PASS": "\033[32m",
    "FAIL": "\033[31m",
    "SKIP": "\033[33m",
}
DEFAULT_RUN_TIMEOUT_SECONDS = 300


def _enable_color() -> bool:
    """Enable ANSI colors in supported terminals, including Windows."""
    if os.getenv("NO_COLOR") is not None or not sys.stdout.isatty():
        return False
    if os.name != "nt":
        return True

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return False
        return kernel32.SetConsoleMode(handle, mode.value | 0x0004) != 0
    except (AttributeError, OSError):
        return False


def _status_text(status: str, *, colored: bool) -> str:
    text = f"[{status}]"
    if not colored:
        return text
    return f"{STATUS_COLORS[status]}{text}{RESET}"


@dataclass(frozen=True)
class TestRun:
    label: str
    target: str
    marker: str | None = None
    environment: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RunOutcome:
    status: str
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    xfailed: int = 0
    xpassed: int = 0
    errors: int = 0
    timed_out: bool = False

    @property
    def total(self) -> int:
        return (
            self.passed
            + self.failed
            + self.skipped
            + self.xfailed
            + self.xpassed
            + self.errors
        )


def _case_runs(
    *,
    label: str,
    target: str,
    marker: str,
    variable: str,
    cases: Iterable[str],
    flag: str,
) -> list[TestRun]:
    return [
        TestRun(
            label=f"{label}/{case}",
            target=target,
            marker=marker,
            environment={flag: "1", variable: case},
        )
        for case in cases
    ]


def build_test_matrix() -> list[TestRun]:
    runs: list[TestRun] = [
        TestRun(
            label="Catalogs and unit",
            target="tests/unit",
            marker="not e2e",
        ),
        TestRun(
            label="Success/all",
            target="tests/success",
            marker="success and not device_lifecycle_success",
        ),
        TestRun(
            label="device_lifecycle/success",
            target="tests/success/test_task_success.py",
            marker="device_lifecycle_success",
        ),
    ]

    runs.extend(
        _case_runs(
            label="configuration_sync",
            target="tests/negative/test_configuration_sync_negative.py",
            marker="configuration_sync_negative",
            variable="CONFIGURATION_SYNC_CASE",
            flag="RUN_CONFIGURATION_SYNC_NEGATIVE",
            cases=("TC-02", "TC-03", "TC-04", "TC-06", "TC-07"),
        )
    )
    runs.extend(
        _case_runs(
            label="policy_sync",
            target="tests/negative/test_policy_sync_negative.py",
            marker="policy_sync_negative",
            variable="POLICY_SYNC_CASE",
            flag="RUN_POLICY_SYNC_NEGATIVE",
            cases=("TC-03", "TC-04", "TC-05"),
        )
    )

    whole_suite_runs = (
        (
            "device_lifecycle/negative",
            "tests/negative/test_device_lifecycle_negative.py",
            "device_lifecycle_negative",
            "RUN_device_lifecycle_NEGATIVE",
        ),
        (
            "history_backend/all",
            "tests/negative/test_history_backend_negative.py",
            "history_backend_negative",
            "RUN_HISTORY_BACKEND_NEGATIVE",
        ),
        (
            "delivery_merge/all",
            "tests/negative/test_delivery_merge_negative.py",
            "delivery_merge_negative",
            "RUN_DELIVERY_MERGE_NEGATIVE",
        ),
    )
    runs.extend(
        TestRun(
            label=label,
            target=target,
            marker=marker,
            environment={flag: "1"},
        )
        for label, target, marker, flag in whole_suite_runs
    )

    runs.extend(
        _case_runs(
            label="destination_lookup",
            target="tests/negative/test_destination_lookup_negative.py",
            marker="destination_lookup_negative",
            variable="DESTINATION_LOOKUP_CASE",
            flag="RUN_DESTINATION_LOOKUP_NEGATIVE",
            cases=tuple(f"TC-{index:02d}" for index in range(1, 11)),
        )
    )
    runs.extend(
        _case_runs(
            label="lazy_upload",
            target="tests/negative/test_lazy_upload_negative.py",
            marker="lazy_upload_negative",
            variable="LAZY_UPLOAD_NEGATIVE_CASE",
            flag="RUN_LAZY_UPLOAD_NEGATIVE",
            cases=(
                "invalid_barcode",
                "image_missing_image_id",
                "image_missing_content",
                "image_invalid_mime_type",
                "supplementary_data_incomplete",
                "image_rejected",
                "image_timeout",
                "image_unavailable",
            ),
        )
    )
    runs.extend(
        _case_runs(
            label="status_override",
            target="tests/negative/test_status_override_negative.py",
            marker="status_override_negative",
            variable="STATUS_OVERRIDE_CASE",
            flag="RUN_STATUS_OVERRIDE_NEGATIVE",
            cases=tuple(f"TC-{index:02d}" for index in range(1, 5)),
        )
    )
    runs.extend(
        _case_runs(
            label="destination_assignment",
            target="tests/negative/test_destination_assignment_negative.py",
            marker="destination_assignment_negative",
            variable="DESTINATION_ASSIGNMENT_CASE",
            flag="RUN_DESTINATION_ASSIGNMENT_NEGATIVE",
            cases=(
                "TC-03-missing",
                "TC-03-empty",
                "TC-04-missing",
                "TC-04-empty",
                "TC-05-short",
                "TC-05-long",
                "TC-06",
                "TC-07",
                "TC-08",
                "TC-09",
                "TC-13",
            ),
        )
    )
    runs.extend(
        _case_runs(
            label="destination_update",
            target="tests/negative/test_destination_update_negative.py",
            marker="destination_update_negative",
            variable="DESTINATION_UPDATE_CASE",
            flag="RUN_DESTINATION_UPDATE_NEGATIVE",
            cases=("TC-05",),
        )
    )

    packing_cases = (
        (
            "container_selection",
            "container_selection_negative",
            "CONTAINER_SELECTION_CASE",
            (
                "TC-08",
                "TC-09",
                "TC-10",
                "TC-11",
                "TC-12-chuteIds",
                "TC-12-parcelTypes",
                "TC-12-serviceTypes",
                "TC-13",
                "TC-14",
                "TC-15",
                "TC-15-empty",
                "TC-16",
                "TC-17",
                "TC-18",
            ),
        ),
        (
            "export_before_container",
            "export_before_container_negative",
            "EXPORT_BEFORE_CONTAINER_CASE",
            (
                "TC-03",
                "TC-04",
                "TC-05",
                "TC-06",
                "TC-07",
                "TC-08",
                "TC-11",
                "TC-12",
                "TC-13",
                "TC-14",
                "TC-15",
                "TC-16",
                "TC-17",
                "TC-18",
                "TC-19",
            ),
        ),
        (
            "container_response",
            "container_response_response",
            "CONTAINER_RESPONSE_CASE",
            tuple(f"TC-{index:02d}" for index in range(1, 11)),
        ),
        (
            "physical_container_audit",
            "physical_container_audit_negative",
            "PHYSICAL_CONTAINER_AUDIT_CASE",
            tuple(f"TC-{index:02d}" for index in range(1, 7)),
        ),
    )
    for label, marker, variable, cases in packing_cases:
        runs.extend(
            _case_runs(
                label=label,
                target="tests/negative/test_packing_negative.py",
                marker=marker,
                variable=variable,
                cases=cases,
                flag="RUN_PACKING_NEGATIVE",
            )
        )

    _validate_scenario_labels(runs)
    return runs


def _validate_scenario_labels(runs: list[TestRun]) -> None:
    """Ensure every scenario execution label has coverage metadata."""
    known_scenarios = {entry.scenario for entry in SCENARIO_COVERAGE}
    matrix_scenarios = {
        label.split("/", maxsplit=1)[0]
        for label in (test_run.label for test_run in runs)
        if label.split("/", maxsplit=1)[0] in known_scenarios
    }
    unknown = sorted(matrix_scenarios - known_scenarios)
    if unknown:
        raise ValueError(
            "Test matrix contains scenario labels without coverage metadata: "
            + ", ".join(unknown)
        )


def _pytest_counts(output: str) -> dict[str, int]:
    """Extract pytest's actual test outcome counts from its short summary."""
    patterns = {
        "passed": r"passed",
        "failed": r"failed",
        "skipped": r"skipped",
        "xfailed": r"xfailed",
        "xpassed": r"xpassed",
        "errors": r"errors?",
    }
    counts = {key: 0 for key in patterns}
    for key, pattern in patterns.items():
        match = re.search(rf"(\d+)\s+{pattern}", output, re.IGNORECASE)
        if match:
            counts[key] = int(match.group(1))
    return counts


def _classify(
    result: subprocess.CompletedProcess[str],
) -> RunOutcome:
    output = f"{result.stdout}\n{result.stderr}"
    counts = _pytest_counts(output)
    if result.returncode != 0 and not any(counts.values()):
        return RunOutcome(status="FAIL", failed=1, errors=1)

    if counts["failed"] or counts["errors"] or result.returncode != 0:
        status = "FAIL"
    elif counts["passed"] or counts["xpassed"]:
        status = "PASS"
    else:
        status = "SKIP"
    return RunOutcome(status=status, **counts)


def run_one(test_run: TestRun) -> RunOutcome:
    environment = os.environ.copy()
    environment["RUN_E2E"] = "1"
    environment.update(test_run.environment)

    command = [*PYTEST, *test_run.target.split()]
    if test_run.marker:
        command.extend(["-m", test_run.marker])
    command.extend(["-q", "--tb=no", "--no-header", "--disable-warnings"])

    timeout_seconds = float(
        os.getenv(
            "TEST_RUN_TIMEOUT_SECONDS",
            str(DEFAULT_RUN_TIMEOUT_SECONDS),
        )
    )
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return RunOutcome(
            status="FAIL",
            failed=1,
            errors=1,
            timed_out=True,
        )
    return _classify(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the public scenario execution matrix."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list matrix entries without running end-to-end tests",
    )
    args = parser.parse_args(argv)
    matrix = build_test_matrix()
    if args.list:
        for test_run in matrix:
            print(test_run.label)
        return 0

    colored = _enable_color()
    results: list[tuple[str, RunOutcome]] = []
    for test_run in matrix:
        outcome = run_one(test_run)
        results.append((test_run.label, outcome))
        print(
            f"{_status_text(outcome.status, colored=colored)} {test_run.label}",
            flush=True,
        )

    # Percentages represent individual pytest outcomes, not matrix commands.
    counts = {
        "PASS": sum(outcome.passed + outcome.xpassed for _, outcome in results),
        "FAIL": sum(outcome.failed + outcome.errors for _, outcome in results),
        "SKIP": sum(outcome.skipped + outcome.xfailed for _, outcome in results),
    }
    total = sum(counts.values())

    def percentage(status: str) -> float:
        return counts[status] * 100 / total if total else 0.0

    print(
        "\nSummary: "
        f"{_status_text('PASS', colored=colored)} "
        f"{counts['PASS']}/{total} ({percentage('PASS'):.2f}%) | "
        f"{_status_text('FAIL', colored=colored)} "
        f"{counts['FAIL']}/{total} ({percentage('FAIL'):.2f}%) | "
        f"{_status_text('SKIP', colored=colored)} "
        f"{counts['SKIP']}/{total} ({percentage('SKIP'):.2f}%)",
        flush=True,
    )
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

