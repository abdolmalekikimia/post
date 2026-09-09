r"""Run all Core (CPS) unit tests with one command.

Usage:
    Set-Location C:\Users\AdminArka\PycharmProjects\post
    & .venv\Scripts\python.exe scripts/run_core_tests.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable

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
DEFAULT_RUN_TIMEOUT_SECONDS = 120


def _enable_color() -> bool:
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
    timeout_seconds: float = 60.0


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
            self.passed + self.failed + self.skipped
            + self.xfailed + self.xpassed + self.errors
        )


def build_core_test_matrix() -> list[TestRun]:
    """Define all Core (CPS) unit test runs."""
    runs: list[TestRun] = [
        # CPS-20: Inbound Query
        TestRun(
            label="Core / CPS-20 Inbound Query",
            target="tests/unit/test_cps20_core.py",
            timeout_seconds=30,
        ),
        # CPS-65: Status Evaluator
        TestRun(
            label="Core / CPS-65 Status Evaluator",
            target="tests/unit/test_cps65_status_evaluator.py",
            timeout_seconds=30,
        ),
        # CPS-80: Pre-signed URL
        TestRun(
            label="Core / CPS-80 Pre-signed URL",
            target="tests/unit/test_cps80_core.py",
            timeout_seconds=30,
        ),
        # CPS-86: Operational Results
        TestRun(
            label="Core / CPS-86 Operational Results",
            target="tests/unit/test_cps86_core.py",
            timeout_seconds=30,
        ),
        # CPS-58: Image Metadata
        TestRun(
            label="Core / CPS-58 Image Metadata",
            target="tests/unit/test_cps58_core.py",
            timeout_seconds=60,
        ),
        # CPS-67: Bag & Dispatch Storage
        TestRun(
            label="Core / CPS-67 Bag & Dispatch",
            target="tests/unit/test_cps67_core.py",
            timeout_seconds=60,
        ),
        # CPS-74: Sorting Device Management
        TestRun(
            label="Core / CPS-74 Device Management",
            target="tests/unit/test_cps74_core.py",
            timeout_seconds=60,
        ),
        # CPS-77: Bootstrap Configuration
        TestRun(
            label="Core / CPS-77 Bootstrap Config",
            target="tests/unit/test_cps77_core.py",
            timeout_seconds=60,
        ),
        # CPS-82: Edge Health Monitoring
        TestRun(
            label="Core / CPS-82 Edge Health",
            target="tests/unit/test_cps82_core.py",
            timeout_seconds=60,
        ),
        # Full Core unit suite (catches import errors + regressions)
        TestRun(
            label="Core / Full Unit Suite",
            target="tests/unit",
            timeout_seconds=60,
        ),
    ]
    return runs


def _pytest_counts(output: str) -> dict[str, int]:
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

    for match in re.finditer(
        r"FlowExecutionError:\s*([^\n\r]+?)\s+stopped at\s+'([^']+)'",
        output,
    ):
        flow_name = match.group(1).strip()
        failed_step = match.group(2).strip()
        flow_name = re.sub(r"^[\w\.]*FlowExecutionError:\s*", "", flow_name)
        item = f"{flow_name} (stopped at '{failed_step}')"
        if item not in seen:
            seen.add(item)
            failures.append(item)

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


def _classify(result: subprocess.CompletedProcess[str]) -> RunOutcome:
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
    command = [*PYTEST, *test_run.target.split()]
    if test_run.marker:
        command.extend(["-m", test_run.marker])
    if test_run.extra_args:
        command.extend(test_run.extra_args)
    command.extend(["-q", "-rf", "--tb=line", "--no-header", "--disable-warnings"])

    timeout_seconds = float(
        os.getenv("TEST_RUN_TIMEOUT_SECONDS", str(test_run.timeout_seconds))
    )
    try:
        proc = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout_seconds)
        stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
        stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
        result = subprocess.CompletedProcess(
            args=command,
            returncode=proc.returncode,
            stdout=stdout,
            stderr=stderr,
        )
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        return RunOutcome(
            status="FAIL",
            failed=1,
            errors=1,
            timed_out=True,
            failures=(f"{test_run.label}: Timed out (after {timeout_seconds:.0f}s)",),
        )
    return _classify(result)


def main() -> int:
    colored = _enable_color()
    results: list[tuple[str, RunOutcome]] = []

    print("=" * 60, flush=True)
    print("  Core Post Sorting - Unit Test Runner (CPS-*)", flush=True)
    print("=" * 60, flush=True)
    print()

    for test_run in build_core_test_matrix():
        outcome = run_one(test_run)
        results.append((test_run.label, outcome))
        print(
            f"  {_status_text(outcome.status, colored=colored)} {test_run.label}",
            flush=True,
        )
        if outcome.status == "FAIL" and outcome.failures:
            for failure in outcome.failures:
                print(
                    f"      {_status_text('FAIL', colored=colored)} {failure}",
                    flush=True,
                )

    counts = {
        "PASS": sum(outcome.passed + outcome.xpassed for _, outcome in results),
        "FAIL": sum(outcome.failed + outcome.errors for _, outcome in results),
        "SKIP": sum(outcome.skipped + outcome.xfailed for _, outcome in results),
    }
    total = sum(counts.values())

    def percentage(status: str) -> float:
        return counts[status] * 100 / total if total else 0.0

    print()
    print("=" * 60, flush=True)
    print(
        "  Summary: "
        f"{_status_text('PASS', colored=colored)} "
        f"{counts['PASS']}/{total} ({percentage('PASS'):.1f}%) | "
        f"{_status_text('FAIL', colored=colored)} "
        f"{counts['FAIL']}/{total} ({percentage('FAIL'):.1f}%) | "
        f"{_status_text('SKIP', colored=colored)} "
        f"{counts['SKIP']}/{total} ({percentage('SKIP'):.1f}%)",
        flush=True,
    )
    print("=" * 60, flush=True)
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
