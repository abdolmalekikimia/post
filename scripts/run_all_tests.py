"""Run the complete active test matrix with one command.

The E2E tests use environment variables to select a case. This runner owns
that matrix so users do not need to invoke pytest once per case manually.

==============================================================================
CRITICAL REPORTING AND EXECUTION CONTRACT (DO NOT MODIFY WITHOUT APPROVAL):
------------------------------------------------------------------------------
1. Granular Per-EPS Execution:
   - Success and Negative test suites MUST be executed per-EPS/component
     rather than in a single monolithic batch.
   - This ensures that if a single EPS service/network call hangs or times out,
     it only fails that specific item without blocking or obscuring the others.

2. Explicit Scenario Failure Reporting:
   - Top-level line: `[PASS/FAIL/SKIP] <Category> / <EPS>` (e.g. `[FAIL] Negative / EPS-73`)
   - Indented sub-bullets on failure:
     `    - [FAIL] <Scenario/Flow Name> (stopped at '<Step Name>')`
     or `    - [FAIL] <EPS>: Timed out waiting for response (after Ns)`
   - NEVER collapse failures into an opaque generic `Test execution timed out`
     without identifying the specific failing EPS and scenario.
==============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable

# When this file is launched directly (for example, ``py scripts/run_all_tests.py``),
# Python puts ``scripts`` on ``sys.path`` rather than the project root. Add the
# repository root before importing project-local packages such as ``config``.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
    extra_args: tuple[str, ...] = ()
    environment: dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = 30.0


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
    failures: tuple[str, ...] = ()

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


# NOTE FOR DEVELOPERS & MAINTAINERS:
# The matrix below is intentionally decomposed per EPS/story rather than grouped
# into giant monolithic folders. This ensures bounded per-test execution timeouts
# and crystal-clear visibility into which exact EPS/TC is passing, failing, or timing out.
def build_test_matrix() -> list[TestRun]:
    runs: list[TestRun] = [
        TestRun(
            label="Catalogs and unit",
            target="tests/1_device_lifecycle tests/2_inbound tests/3_destination tests/4_bagging tests/5_monitoring tests/negative tests/unit",
            marker="not e2e",
            timeout_seconds=60.0,
        ),
        # Success runs per EPS / component
        TestRun(
            label="Success / Smoke & Base",
            target="tests/smoke/test_smoke_flows.py",
            marker="smoke",
            environment={"RUN_E2E": "1"},
        ),
        TestRun(
            label="Success / EPS-40",
            target="tests/1_device_lifecycle/test_device_lifecycle_and_auth.py",
            marker="eps40_success",
            environment={"RUN_E2E": "1", "RUN_EPS40_SUCCESS": "1"},
        ),
        TestRun(
            label="Success / EPS-46",
            target="tests/1_device_lifecycle/test_device_lifecycle_and_auth.py",
            marker="eps46_success",
            environment={"RUN_E2E": "1", "RUN_EPS46_SUCCESS": "1"},
        ),
        TestRun(
            label="Success / EPS-49",
            target="tests/1_device_lifecycle/test_device_lifecycle_and_auth.py",
            marker="eps49_success",
            environment={"RUN_E2E": "1", "RUN_EPS49_SUCCESS": "1"},
        ),
        TestRun(
            label="Success / EPS-53",
            target="tests/2_inbound/test_inbound_and_verification.py",
            marker="eps53_success",
            environment={"RUN_E2E": "1", "RUN_EPS53_SUCCESS": "1"},
        ),
        TestRun(
            label="Success / EPS-55",
            target="tests/2_inbound/test_inbound_and_verification.py",
            marker="eps55_success",
            environment={"RUN_E2E": "1", "RUN_EPS55_SUCCESS": "1"},
        ),
        TestRun(
            label="Success / EPS-60",
            target="tests/3_destination/test_destination_and_chute_assignment.py",
            marker="eps60_success",
            environment={"RUN_E2E": "1", "RUN_EPS60_SUCCESS": "1"},
        ),
        TestRun(
            label="Success / EPS-64",
            target="tests/2_inbound/test_inbound_and_verification.py",
            marker="eps64_success",
            environment={"RUN_E2E": "1", "RUN_EPS64_SUCCESS": "1"},
        ),
        TestRun(
            label="Success / EPS-66",
            target="tests/2_inbound/test_inbound_and_verification.py",
            marker="eps66_success",
            environment={"RUN_E2E": "1", "RUN_EPS66_SUCCESS": "1"},
        ),
        TestRun(
            label="Success / EPS-71",
            target="tests/3_destination/test_destination_and_chute_assignment.py",
            marker="eps71_success",
            environment={"RUN_E2E": "1", "RUN_EPS71_SUCCESS": "1"},
        ),
        TestRun(
            label="Success / EPS-73",
            target="tests/3_destination/test_destination_and_chute_assignment.py",
            marker="eps73_success",
            environment={"RUN_E2E": "1", "RUN_EPS73_SUCCESS": "1"},
        ),
        TestRun(
            label="Success / Packing (EPS-76/79/87/89)",
            target="tests/4_bagging/test_bagging_and_labeling.py",
            marker="packing_success",
            environment={
                "RUN_E2E": "1",
                "RUN_EPS76_SUCCESS": "1",
                "RUN_EPS79_SUCCESS": "1",
                "RUN_EPS87_SUCCESS": "1",
                "RUN_EPS89_SUCCESS": "1",
            },
        ),
        TestRun(
            label="Success / EPS-83",
            target="tests/4_bagging/test_bagging_and_labeling.py",
            marker="eps83_success",
            environment={"RUN_E2E": "1", "RUN_EPS83_SUCCESS": "1", "EPS83_CASE": "all"},
        ),
        TestRun(
            label="Success / EPS-113",
            target="tests/5_monitoring/test_telemetry_and_events.py",
            marker="eps113_success",
            environment={"RUN_E2E": "1", "RUN_EPS113_SUCCESS": "1", "EPS113_CASE": "all"},
        ),
        # Negative runs per EPS
        TestRun(
            label="Negative / EPS-40",
            target="tests/1_device_lifecycle/test_device_lifecycle_and_auth.py",
            marker="eps40_negative",
            environment={"RUN_E2E": "1", "RUN_EPS40_NEGATIVE": "1", "EPS40_CASE": "all"},
        ),
        TestRun(
            label="Negative / EPS-46",
            target="tests/1_device_lifecycle/test_device_lifecycle_and_auth.py",
            marker="eps46_negative",
            environment={"RUN_E2E": "1", "RUN_EPS46_NEGATIVE": "1", "EPS46_CASE": "all"},
        ),
        TestRun(
            label="Negative / EPS-49",
            target="tests/1_device_lifecycle/test_device_lifecycle_and_auth.py",
            marker="eps49_negative",
            environment={"RUN_E2E": "1", "RUN_EPS49_NEGATIVE": "1"},
        ),
        TestRun(
            label="Negative / EPS-53",
            target="tests/2_inbound/test_inbound_and_verification.py",
            marker="eps53_negative",
            environment={"RUN_E2E": "1", "RUN_EPS53_NEGATIVE": "1"},
        ),
        TestRun(
            label="Negative / EPS-55",
            target="tests/2_inbound/test_inbound_and_verification.py",
            marker="eps55_negative",
            environment={"RUN_E2E": "1", "RUN_EPS55_NEGATIVE": "1"},
        ),
        TestRun(
            label="Negative / EPS-60",
            target="tests/3_destination/test_destination_and_chute_assignment.py",
            marker="eps60_negative",
            environment={"RUN_E2E": "1", "RUN_EPS60_NEGATIVE": "1", "EPS60_CASE": "all"},
        ),
        TestRun(
            label="Negative / EPS-64",
            target="tests/2_inbound/test_inbound_and_verification.py",
            marker="eps64_negative",
            environment={"RUN_E2E": "1", "RUN_EPS64_NEGATIVE": "1", "EPS64_NEGATIVE_CASE": "all"},
        ),
        TestRun(
            label="Negative / EPS-66",
            target="tests/2_inbound/test_inbound_and_verification.py",
            marker="eps66_negative",
            environment={"RUN_E2E": "1", "RUN_EPS66_NEGATIVE": "1"},
        ),
        TestRun(
            label="Negative / EPS-68",
            target="tests/2_inbound/test_inbound_and_verification.py",
            marker="eps68_negative",
            environment={"RUN_E2E": "1", "RUN_EPS68_NEGATIVE": "1", "EPS68_CASE": "all"},
        ),
        TestRun(
            label="Negative / EPS-71",
            target="tests/3_destination/test_destination_and_chute_assignment.py",
            marker="eps71_negative",
            environment={"RUN_E2E": "1", "RUN_EPS71_NEGATIVE": "1", "EPS71_CASE": "all"},
        ),
        TestRun(
            label="Negative / EPS-73",
            target="tests/3_destination/test_destination_and_chute_assignment.py",
            marker="eps73_negative",
            environment={"RUN_E2E": "1", "RUN_EPS73_NEGATIVE": "1", "EPS73_CASE": "all"},
        ),
        TestRun(
            label="Negative / Packing (EPS-76/79/87/89)",
            target="tests/4_bagging/test_bagging_and_labeling.py",
            marker="packing_negative",
            environment={"RUN_E2E": "1", "RUN_PACKING_NEGATIVE": "1"},
        ),
        TestRun(
            label="Negative / EPS-83",
            target="tests/4_bagging/test_bagging_and_labeling.py",
            marker="eps83_negative",
            environment={"RUN_E2E": "1", "RUN_EPS83_NEGATIVE": "1", "EPS83_CASE": "all"},
        ),
        TestRun(
            label="Negative / EPS-113",
            target="tests/5_monitoring/test_telemetry_and_events.py",
            marker="eps113_negative",
            environment={"RUN_E2E": "1", "RUN_EPS113_NEGATIVE": "1", "EPS113_CASE": "all"},
        ),
    ]

    return runs


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


def _extract_failures(output: str) -> list[str]:
    failures: list[str] = []
    seen = set()

    # 1. Match FlowExecutionError: FlowName stopped at 'StepName'
    for match in re.finditer(
        r"FlowExecutionError:\s*([^\n\r]+?)\s+stopped at\s+'([^']+)'",
        output,
    ):
        flow_name = match.group(1).strip()
        failed_step = match.group(2).strip()
        # Clean up any exception prefix in flow_name
        flow_name = re.sub(r"^[\w\.]*FlowExecutionError:\s*", "", flow_name)
        item = f"{flow_name} (stopped at '{failed_step}')"
        if item not in seen:
            seen.add(item)
            failures.append(item)

    # 2. Match Execution report headers that have [FAIL]
    if not failures:
        for match in re.finditer(
            r"Execution report:\s*([^\n\r]+)(?:(?!Execution report).)*?\[FAIL\]\s+([^\n\r]+)",
            output,
            re.DOTALL,
        ):
            flow_name = match.group(1).strip()
            failed_step = match.group(2).strip()
            item = f"{flow_name} (stopped at '{failed_step}')"
            if item not in seen:
                seen.add(item)
                failures.append(item)

    # 3. Fallback: match pytest FAILED summary lines
    if not failures:
        for match in re.finditer(
            r"FAILED\s+([^\s:]+)::([^\s\-]+)(?:\s*-\s*([^\n\r]+))?",
            output,
        ):
            test_file = os.path.basename(match.group(1))
            test_func = match.group(2)
            reason = (match.group(3) or "").strip()
            item = f"{test_file}::{test_func}"
            if reason:
                item += f" ({reason})"
            if item not in seen:
                seen.add(item)
                failures.append(item)

    return failures


def _classify(
    result: subprocess.CompletedProcess[str],
) -> RunOutcome:
    output = f"{result.stdout}\n{result.stderr}"
    counts = _pytest_counts(output)
    failures = tuple(_extract_failures(output))
    if result.returncode != 0 and not any(counts.values()):
        return RunOutcome(status="FAIL", failed=1, errors=1, failures=failures)

    if counts["failed"] or counts["errors"] or result.returncode != 0:
        status = "FAIL"
    elif counts["passed"] or counts["xpassed"]:
        status = "PASS"
    else:
        status = "SKIP"
    return RunOutcome(status=status, failures=failures, **counts)


def run_one(test_run: TestRun) -> RunOutcome:
    environment = os.environ.copy()
    environment["RUN_E2E"] = "1"
    environment.update(test_run.environment)

    command = [*PYTEST, *test_run.target.split()]
    if test_run.marker:
        command.extend(["-m", test_run.marker])
    if test_run.extra_args:
        command.extend(test_run.extra_args)
    command.extend(["-q", "-rf", "--tb=line", "--no-header", "--disable-warnings"])

    timeout_seconds = float(
        os.getenv(
            "TEST_RUN_TIMEOUT_SECONDS",
            str(test_run.timeout_seconds),
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
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        failures = _extract_failures(output)
        if not failures:
            failures = [f"{test_run.label}: Timed out waiting for response (after {timeout_seconds:.0f}s)"]
        return RunOutcome(
            status="FAIL",
            failed=1,
            errors=1,
            timed_out=True,
            failures=tuple(failures),
        )
    return _classify(result)


def main() -> int:
    colored = _enable_color()
    results: list[tuple[str, RunOutcome]] = []
    for test_run in build_test_matrix():
        outcome = run_one(test_run)
        results.append((test_run.label, outcome))
        print(
            f"{_status_text(outcome.status, colored=colored)} {test_run.label}",
            flush=True,
        )
        if outcome.status == "FAIL" and outcome.failures:
            for failure in outcome.failures:
                print(f"    - {_status_text('FAIL', colored=colored)} {failure}", flush=True)

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
