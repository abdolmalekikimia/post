"""First page of the full report: one verdict, the failures with their causes, skips grouped by reason.

A cause is never guessed. Failures are matched against CAUSES, a table written from root-cause work; a failure that
matches nothing is shown as "cause not investigated yet".
"""

from __future__ import annotations

import html
import re
from collections import Counter

BUG, TEST, WAIT, UNKNOWN = "bug", "test", "wait", "unknown"

KINDS = {
    BUG: ("🐞", "Probably a product bug or a contract conflict"),
    TEST: ("🔧", "Test or data weakness"),
    WAIT: ("⏸", "Waiting for input"),
    UNKNOWN: ("🔍", "Cause not investigated yet"),
}

# (regex on "node id + reason", kind, plain-English cause). First match wins.
CAUSES = [
    (r"'0\d+' is not a recognized exchange-center code", BUG,
     "The Edge center list has lost the leading zero of the codes, so a destination with a leading zero is rejected."),
    (r"is not a recognized exchange-center code", TEST,
     "The destination is not in the Edge center list; change the destination code used by the test."),
    (r"counts\.n=.*expected successful members|successful members, expected", TEST,
     "The bag member count was computed wrongly; the official formula is (n-m)+(p-q)."),
    (r"test_close_bag_08_", BUG,
     "String serviceTypes get no validation reply and end in \"error on the server\"."),
    (r"test_close_bag_01_", WAIT,
     "The Edge answers \"not supported\" for every serviceTypes number; service-type filtering is not built yet."),
    (r"test_health_check_08_", BUG,
     "A Core outage must not stop the device (only an outage of the Edge's own database does); if this test is red, registering a parcel returned SystemError."),
    (r"test_no_barcode_01_", BUG,
     "The Edge rejects an empty barcode; the requirement is that it is registered and routed to the disordered chute."),
    (r"test_no_barcode_03_", BUG,
     "The Edge treats a special chute code (even AABBB, which is in its configuration) as an invalid code; special chutes are not implemented in the deployed Edge."),
    (r"test_postal_contracts_02_|reached the device as '42'", BUG,
     "Error code 0042 reaches the device as 42; the leading zero is lost in the Edge database."),
]

# (title, keywords searched in the skip reason). First match wins.
SKIP_GROUPS = [
    # Root causes found 2026-11-07 (Core hands out the Docker-internal storage name core_minio:9000, so no image upload works).
    ("Core hands out a wrong image-storage address (MinIO); image upload does not work",
     ("core_minio", "Storage upload", "Storage endpoint", "No attachment on the Core Reading yet", "attachment on the target", "upload address")),
    ("Returned, rejected or deferred parcel data is not in Core; the test cannot create it",
     ("Returning/Rejected", "Core history fixture", "SIZE_CLASS_", "core_rejected", "Core Returning")),
    ("Waiting for the real 14-digit postal lookup service", ("REAL_POSTAL", "destination lookup", "postal lookup")),
    ("A fixture or test device we can build ourselves",
     ("dispatch", "DISPATCH_", "empty destination", "EMPTY_DESTINATION_", "Provision a distinct", "no Edge IP binding")),
    ("A setting or feature is missing in Core or the deployed Edge (the Edge is older than the documents, or Core does not publish it)",
     ("autoDispatchPolicy", "AutoDispatchPolicy", "CB-", "bagCloseFailurePolicy", "background bag-close")),
    ("Waiting for a real outage or a product decision (Edge health)", ("HEALTH_CHECK", "SystemError", "EDGE_LINK_PANEL")),
    ("Central events: no way to create or observe them",
     ("collector", "label-reprint", "telemetry-ingestion", "sensor-event", "protocol anomaly",
      "server event identities", "OPERATIONAL_EVENTS_EVENT")),
    ("Needs a dedicated Edge with a controlled Postal mock, or a real Postal outage",
     ("DESTINATION_LOOKUP_PENDING", "destination lookup timing", "real Postal failure", "label S5")),
    ("Needs more precise evidence from Core (full request body, sizes, call counter)",
     ("sourced", "not observable", "numeric outbound", "independently")),
    ("An open decision or contract, or real postal data",
     ("NO_BARCODE", "POSTAL_CONTRACTS", "deferred status", "discrepancies", "dot-segment", "worker failure", "background image-upload")),
]
OTHER_SKIPS = "Other reason (see each test's details)"


def classify(case: dict) -> tuple[str, str]:
    text = f"{case['nodeid']} {case.get('reason', '')} {case.get('output', '')}"
    for pattern, kind, cause in CAUSES:
        if re.search(pattern, text):
            return kind, cause
    return UNKNOWN, "The cause of this failure has not been investigated yet."


def skip_group(case: dict) -> str:
    reason = (case.get("reason") or "").lower()
    for title, keys in SKIP_GROUPS:
        if any(key.lower() in reason for key in keys):
            return title
    return OTHER_SKIPS


def _short(nodeid: str) -> str:
    return nodeid.split("/", 1)[-1] if nodeid.startswith("tests/") else nodeid


def summarize(domain_results: dict, parse_cases) -> dict:
    """Group failures by cause and skips by reason; the same node run by two markers is counted once per run."""
    failures: dict[tuple[str, str], list[str]] = {}
    skips: Counter = Counter()
    for domain in domain_results.values():
        for run in domain.get("runs", [domain]):
            for case in parse_cases(run.get("raw", "")):
                if case["status"] in ("FAILED", "ERROR"):
                    failures.setdefault(classify(case), []).append(_short(case["nodeid"]))
                elif case["status"] == "SKIPPED":
                    skips[skip_group(case)] += 1
    return {"failures": failures, "skips": skips}


def render_summary(domain_results: dict, parse_cases, passed: int, failed: int, skipped: int, total: int,
                   describe) -> str:
    data = summarize(domain_results, parse_cases)
    by_kind = Counter()
    for (kind, _), names in data["failures"].items():
        by_kind[kind] += len(names)
    classified = sum(by_kind.values())

    if failed + skipped == 0:
        verdict = "All executed tests passed."
    else:
        parts = []
        if by_kind[BUG]:
            parts.append(f"{by_kind[BUG]} probably a product bug or contract conflict")
        if by_kind[TEST]:
            parts.append(f"{by_kind[TEST]} a test or data weakness")
        if by_kind[UNKNOWN]:
            parts.append(f"{by_kind[UNKNOWN]} not investigated yet")
        verdict = (f"Of {failed} failures, " + "; ".join(parts) + "." if parts else f"{failed} failures recorded.")
        if skipped:
            verdict += f" {skipped} tests were skipped because a required input was missing."
    if classified != failed:
        verdict += f" (Note: {failed - classified} failures are not in the list below; see the full output.)"

    def card(value, label, color):
        return (f'<div class="sum-card"><b style="color:{color}">{value}</b><span>{html.escape(label)}</span></div>')

    cards = "".join([
        card(passed, "Passed", "var(--green)"),
        card(by_kind[BUG], "Probably a product bug", "var(--red)"),
        card(by_kind[TEST], "Test or data weakness", "var(--yellow)"),
        card(by_kind[UNKNOWN], "Not investigated", "var(--pink)"),
        card(skipped, "Skipped (waiting for input)", "var(--blue)"),
        card(total, "All tests", "var(--text)"),
    ])

    rows = []
    order = {BUG: 0, UNKNOWN: 1, TEST: 2, WAIT: 3}
    for (kind, cause), names in sorted(data["failures"].items(), key=lambda item: (order[item[0][0]], -len(item[1]))):
        icon, label = KINDS[kind]
        unique = list(dict.fromkeys(names))
        scenario = describe(unique[0].split("::")[-1])
        what = scenario[2] if scenario else ""
        listing = "".join(f'<div>{html.escape(name)}</div>' for name in unique)
        rows.append(
            f'<tr class="sum-{kind}"><td>{icon} {html.escape(label)}</td>'
            f'<td>{html.escape(what)}</td><td>{html.escape(cause)}</td>'
            f'<td>{len(names)}<details><summary>Tests</summary>{listing}</details></td></tr>')
    failure_table = (
        '<table class="sum-table"><tr><th>Type</th><th>What scenario it checks</th><th>Why it failed</th>'
        f'<th>Count</th></tr>{"".join(rows)}</table>' if rows else '<div class="sum-note">No failures recorded.</div>')

    skip_rows = "".join(f"<tr><td>{html.escape(title)}</td><td>{count}</td></tr>"
                        for title, count in data["skips"].most_common())
    skip_table = (f'<table class="sum-table"><tr><th>Reason</th><th>Count</th></tr>{skip_rows}</table>'
                  if skip_rows else "")

    try:
        from utils import pending_watch
        watch_html = pending_watch.render_section(pending_watch.rows())
    except Exception:
        watch_html = ""

    return _summary_body(verdict, cards, failure_table, skip_table) + watch_html


def _summary_body(verdict, cards, failure_table, skip_table) -> str:
    return f'''
<div class="sum-box">
<div class="sum-verdict"><b>Verdict:</b> {html.escape(verdict)}</div>
<div class="sum-cards">{cards}</div>
<h2 class="sum-h">Failures and their causes</h2>{failure_table}
<div class="sum-note">There is no comparison with a previous run yet; only this run is in the report.</div>
<h2 class="sum-h">Skipped tests, by reason</h2>{skip_table}
<div class="sum-note">Each failure's cause is read from the table of known causes (scripts/report_summary.py); a new failure stays "Not investigated" until it is looked into.</div>
</div>'''


SUMMARY_CSS = """
.sum-box { margin-bottom: 28px; }
.sum-verdict { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px 18px; font-size: 16px; margin-bottom: 14px; }
.sum-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 18px; }
.sum-card { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 12px 14px; }
.sum-card b { display: block; font-size: 26px; }
.sum-card span { color: var(--text3); font-size: 12px; }
.sum-h { font-size: 16px; color: var(--text2); margin: 18px 0 8px; }
.sum-table { width: 100%; border-collapse: collapse; background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; font-size: 13px; }
.sum-table th, .sum-table td { padding: 8px 10px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }
.sum-table th { color: var(--text3); font-weight: 600; }
.sum-table details summary { cursor: pointer; color: var(--accent); font-size: 12px; }
.sum-table details div { font-size: 11px; color: var(--text3); }
.sum-note { color: var(--text3); font-size: 12px; margin-top: 8px; }
@media (max-width: 560px) { .sum-table th, .sum-table td { padding: 6px; } }
"""
