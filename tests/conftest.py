"""Keep missing independent evidence distinct from an observed product failure."""

import os
import sys
import json
import re
import warnings

import pytest

from utils.step_report import FlowExecutionError, UnverifiedPreconditionError


_STORY_FILE = re.compile(r"test_((?:eps|cps)\d+)")
_STORY_MARK = re.compile(r"^((?:eps|cps)\d+)(?:_[a-z]+)?$")


def story_markers(item) -> set[str]:
    """Story id(s) of a test: epsNN / cpsNN from its file name and from epsNN_success / epsNN_negative style markers."""
    stories = set()
    name = getattr(getattr(item, "path", None), "name", None)
    match = _STORY_FILE.match(name) if isinstance(name, str) else None
    if match:
        stories.add(match.group(1))
    try:
        names = [mark.name for mark in item.iter_markers()]
    except (TypeError, AttributeError):  # not a real collected item (unit tests call the hook with mocks)
        names = []
    for mark_name in names:
        found = _STORY_MARK.match(mark_name) if isinstance(mark_name, str) else None
        if found:
            stories.add(found.group(1))
    return stories


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    """One marker per story (-m destination_assignment runs that story's success, negative and load tests together), added
    automatically before -m selection; then keep the retired center profile opt-in without counting it as a Skip."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", pytest.PytestUnknownMarkWarning)  # story ids are derived, not listed in pytest.ini
        for item in items:
            for story in sorted(story_markers(item)):
                if not item.get_closest_marker(story):
                    item.add_marker(story)
    explicit = (os.getenv("RUN_QA00519") == "1"
                or "qa00519" in str(config.option.markexpr)
                or any("test_qa_center_00519" in str(arg) for arg in config.args))
    if explicit:
        return
    retired = [item for item in items if item.get_closest_marker("qa00519")]
    if retired:
        items[:] = [item for item in items if item not in retired]
        config.hook.pytest_deselected(items=retired)


_SKIPPED_NODES: set[str] = set()


def pytest_sessionstart(session):
    """Live runs first ask again about parcels that stayed Pending in earlier runs (24h watch, utils/pending_watch.py)."""
    for stream in (sys.stdout, sys.stderr):  # non-ASCII text in a printed reply must not crash a test on a cp1252 console
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if os.getenv("RUN_E2E") != "1" or os.getenv("QA_PENDING_WATCH_RECHECK", "1") == "0":
        return
    try:
        from config.settings import settings
        from utils import pending_watch
        pending_watch.print_recheck(pending_watch.recheck_due(settings))
    except Exception:
        pass  # a watch problem must never stop a test run


def pytest_sessionfinish(session, exitstatus):
    """QA_MAX_SKIPS=N turns a run with more than N skipped tests into a failure instead of a green exit."""
    cap = os.getenv("QA_MAX_SKIPS", "").strip()
    if cap.isdigit() and len(_SKIPPED_NODES) > int(cap) and exitstatus == 0:
        print(f"\nQA_SKIP_BUDGET exceeded: {len(_SKIPPED_NODES)} skipped > QA_MAX_SKIPS={cap}", flush=True)
        session.exitstatus = 1


def pytest_runtest_logreport(report):
    """Give the HTML generator an exact node-to-reason mapping, including parameters."""
    if report.skipped and report.when in {"setup", "call"}:
        _SKIPPED_NODES.add(report.nodeid)
        reason = report.longrepr[2] if isinstance(report.longrepr, tuple) else str(report.longrepr)
        print("\nQA_SKIP_JSON=" + json.dumps({"nodeid": report.nodeid, "reason": reason}, ensure_ascii=True))


def unverified_prerequisite_only(error: BaseException) -> bool:
    """Never hide a failed assertion behind a later unverified observation."""
    if isinstance(error, FlowExecutionError):
        return (
            isinstance(error.cause, UnverifiedPreconditionError)
            and error.report.summary().get("FAILED", 0) == 0
        )
    return isinstance(error, UnverifiedPreconditionError)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if call.when != "call" or call.excinfo is None:
        return
    error = call.excinfo.value
    if not unverified_prerequisite_only(error):
        return
    cause = error.cause if isinstance(error, FlowExecutionError) else error
    report.outcome = "skipped"
    report.longrepr = (
        str(item.fspath),
        item.location[1],
        f"Unverified prerequisite: {cause}",
    )
