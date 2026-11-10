# Full Multi-Domain QA Report Generator, including cross-domain success and smoke suites.
# Captures raw pytest verbose output (with payload/URL/response) and generates HTML report.

import ast, subprocess, sys, os, re, time, html as html_mod, json
import tempfile
import threading
from types import SimpleNamespace
from pathlib import Path
from datetime import datetime
from dotenv import dotenv_values
from urllib.parse import urlsplit, urlunsplit
from scripts.report_catalog import describe as describe_scenario
from utils.deployment_info import edge_deployment_identity
from scripts.report_steps import STEPS_CSS, mask_text, render_steps, split_output
from scripts.report_summary import SUMMARY_CSS, render_summary

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Direct execution (python scripts/generate_full_report.py) otherwise puts only
# scripts/ on sys.path; the preflight imports root-level project packages.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
REPORT_DIR = PROJECT_ROOT / "reports"
PYTHON = sys.executable
TEST_TIMEOUT_SECONDS = int(os.getenv("REPORT_TEST_TIMEOUT_SECONDS", "600"))


def local_setting(name, default=""):
    """Process env first, then ignored config/test.env.

    The launcher runs before config.settings loads test.env, but the pytest subprocess does load it. Reading only
    os.environ made the long Postal-fault group timeout (3600 s) silently fall back to 600 s whenever the fixture
    flag lived only in test.env, which killed Domain 4 mid-case (TC-06 sat in Pending until the kill).
    """
    value = os.getenv(name)
    if value is None or value == "":
        value = dotenv_values(PROJECT_ROOT / "config" / "test.env").get(name)
    return value if value not in (None, "") else default


def prepare_primary_device_profile():
    """Use the existing live Edge and device at center 59544 for the full run."""
    profile = os.getenv("POST_REPORT_DEVICE_PROFILE", "qa59544").strip().lower()
    if profile != "qa59544":
        raise RuntimeError(f"Unsupported comprehensive-report device profile: {profile}")
    local = dotenv_values(PROJECT_ROOT / "config" / "test.env")
    required = (
        "DEVICE_ID", "DEVICE_TOKEN", "WS_URL", "BASE_URL",
        "CORE_BASE_URL", "CORE_ADMIN_USERNAME", "CORE_ADMIN_PASSWORD",
    )
    missing = [name for name in required if not (os.getenv(name) or local.get(name))]
    if missing:
        raise RuntimeError(
            "Center 59544 report is blocked: missing " + ", ".join(missing)
        )

    def value(name):
        return str(os.getenv(name) or local.get(name)).strip()

    ws_url = value("WS_URL")
    parsed = urlsplit(ws_url)
    if parsed.scheme not in {"ws", "wss"} or not parsed.hostname:
        raise RuntimeError("WS_URL must be a live ws:// or wss:// URL")
    base_url = value("BASE_URL")

    # Verify the selected Edge has actually synchronized and is online in Core.
    # Keep credentials and tokens out of error messages and the HTML report.
    import requests
    core_url = value("CORE_BASE_URL").rstrip("/")
    try:
        login = requests.post(
            core_url + "/api/auth/token",
            json={"userName": value("CORE_ADMIN_USERNAME"),
                  "password": value("CORE_ADMIN_PASSWORD")}, timeout=15,
        )
        login.raise_for_status()
        bearer = login.json().get("accessToken") or login.json().get("token")
        if not bearer:
            raise RuntimeError("Core admin login returned no token")
        health = requests.get(
            core_url + "/api/admin/edges/health",
            headers={"Authorization": f"Bearer {bearer}"}, timeout=15,
        )
        health.raise_for_status()
        payload = health.json()
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError(
            "Center 59544 report is blocked: Core Edge-health preflight failed "
            f"({type(exc).__name__})."
        ) from exc
    rows = payload if isinstance(payload, list) else payload.get("items", [])
    target_edge_id = str(os.getenv("QA_59544_EDGE_ID") or local.get("QA_59544_EDGE_ID") or "EDGE-TEST-001").strip()
    edge = next((row for row in rows if isinstance(row, dict)
                 and row.get("edgeId") == target_edge_id
                 and row.get("exchangeCenterCode") == "59544"), None)
    if not edge or edge.get("connectionStatus") != "Connected" or not edge.get("lastSuccessfulSyncUtc"):
        raise RuntimeError(
            "Center 59544 report is blocked: its selected Edge has no connected, "
            "synchronized health record in Core."
        )

    # The device must authenticate to the selected Edge before any domain test
    # can be attributed to it. A failed Auth is reported as a blocked preflight.
    from assertions.signalr_assertions import response_field
    from clients.signalr_client import DeviceWebSocketClient
    from services.device_service import DeviceService
    os.environ["SSL_VERIFY"] = str(os.getenv("SSL_VERIFY") or local.get("SSL_VERIFY") or "1")
    client = DeviceWebSocketClient(ws_url, 10)
    try:
        client.connect()
        reply = DeviceService(client).auth(value("DEVICE_ID"), value("DEVICE_TOKEN"))
        if response_field(reply, "status") not in (0, "0"):
            raise RuntimeError("Center 59544 report is blocked: selected device Auth was rejected by its Edge")
    except Exception as exc:
        if isinstance(exc, RuntimeError) and str(exc).startswith("Center 59544 report is blocked"):
            raise
        raise RuntimeError(
            "Center 59544 report is blocked: selected device could not authenticate "
            f"to its Edge ({type(exc).__name__})."
        ) from exc
    finally:
        client.close()

    overrides = {
        "DEVICE_ID": value("DEVICE_ID"),
        "DEVICE_TOKEN": value("DEVICE_TOKEN"),
        "WS_URL": ws_url,
        "BASE_URL": base_url,
        "CONFIG_SYNC_ACTIVE_DEVICE_ID": value("DEVICE_ID"),
        "CONFIG_SYNC_ACTIVE_DEVICE_TOKEN": value("DEVICE_TOKEN"),
        "CONFIG_SYNC_TARGET_EDGE_ID": target_edge_id,
        "IP_BINDING_DEVICE_ID": value("DEVICE_ID"),
        "IP_BINDING_DEVICE_TOKEN": value("DEVICE_TOKEN"),
    }
    os.environ.update(overrides)
    return {"profile": profile, "center": "59544", "deviceId": overrides["DEVICE_ID"]}


def write_blocked_preflight_report(reason):
    """Keep one reviewable report even when the 59544 preflight blocks."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    local = dotenv_values(PROJECT_ROOT / "config" / "test.env")
    device_id = os.getenv("DEVICE_ID") or local.get("DEVICE_ID") or "not recorded"
    timestamp = datetime.now()
    path = REPORT_DIR / f"CPS_Full_Report_{timestamp:%Y%m%d_%H%M%S}.html"
    path.write_text(f"""<!doctype html>
<html lang="en" dir="ltr"><head><meta charset="utf-8"><title>Full report - run blocked</title>
<style>body{{font-family:Tahoma,Arial,sans-serif;max-width:850px;margin:3rem auto;padding:0 1rem;
background:#111827;color:#f9fafb;line-height:1.9}}section{{background:#1f2937;border:1px solid #b45309;
border-radius:12px;padding:1.5rem}}strong{{color:#fbbf24}}code{{direction:ltr;unicode-bidi:embed}}</style>
</head><body><section><h1>Full report - BLOCKED</h1>
<p><strong>No test was run.</strong> This file is neither a pass nor a fail of the system.</p>
<p>Time: {timestamp:%Y-%m-%d %H:%M:%S} | Target center: <code>59544</code> |
Target device: <code>{html_mod.escape(str(device_id))}</code></p>
<p>Blocker before the run: {html_mod.escape(str(reason))}</p>
<p>No domain runs before the device is authenticated successfully on the Edge of center 59544.
After the blocker is fixed, run the same command again.</p>
</section></body></html>""", encoding="utf-8")
    return path

DOMAINS = {
    "0": {"name": "Security", "folder": "tests/0_security", "markers": ("security",)},
    "0A": {"name": "ip binding Device IP Binding", "folder": "tests/1_device_lifecycle/test_ip_binding.py",
           "markers": ("ip_binding",)},
    "0B": {"name": "two lines Two Sorting Lines", "folder": "tests/1_device_lifecycle/test_two_lines.py",
           "markers": ("two_lines",)},
    "1": {"name": "Device Lifecycle & Auth",  "folder": "tests/1_device_lifecycle"},
    "2": {"name": "Inbound & Verification",   "folder": "tests/2_inbound"},
    "3": {"name": "Destination & Chute",      "folder": "tests/3_destination"},
    "4": {"name": "Bagging & Labeling",       "folder": "tests/4_bagging"},
    "5": {"name": "Monitoring & Telemetry",   "folder": "tests/5_monitoring"},
    "6": {"name": "Cross-domain Success", "folder": "tests/success", "markers": ("success",)},
    "7": {"name": "Cross-domain Smoke", "folder": "tests/smoke", "markers": ("smoke and e2e",)},
}

# These are the ten independent, single-host checks from run-ip_binding.ps1 spoof.
# The other ip binding phases require a second real source IP or a dedicated device
# and must not appear as artificial SKIPs in the comprehensive report.
IP_BINDING_COMPREHENSIVE_CASES = (
    "test_ip_binding_allowed_source_authenticates",
    "test_ip_binding_unregistered_source_rejected_without_forwarded_header",
    "test_ip_binding_spoofed_forwarded_ip_cannot_override_actual_source",
    "test_ip_binding_allowed_source_ignores_forged_forwarded_ip",
    "test_ip_binding_allowed_source_rejects_wrong_token",
    "test_ip_binding_allowed_source_rejects_unknown_device",
    "test_ip_binding_unauthenticated_close_bag_is_rejected",
    "test_ip_binding_auth_recovers_after_binding_restored",
    "test_ip_binding_ip_update_requires_admin_token",
    "test_ip_binding_invalid_ip_update_is_rejected",
)


def report_domains():
    """Leave the TLS security suite and the opt-in two lines two-line suite out of default reports."""
    def enabled(name):
        return os.getenv(name, "0").strip().lower() in {"1", "true", "yes", "on"}
    include_security, include_two_lines = enabled("REPORT_INCLUDE_SECURITY"), enabled("REPORT_INCLUDE_TWO_LINES")
    return {domain_id: domain for domain_id, domain in DOMAINS.items()
            if (include_security or domain_id != "0") and (include_two_lines or domain_id != "0B")}

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(s):
    return ANSI_RE.sub("", s)


def pytest_result_counts(raw):
    """Count pytest's final summary, never digits in payloads or step headings."""
    patterns = {"passed": "passed", "failed": "failed", "skipped": "skipped",
                "errors": "errors?", "xfailed": "xfailed", "xpassed": "xpassed"}
    token = r"\d+[ \t]+(?:passed|failed|skipped|errors?|xfailed|xpassed|deselected|warnings?)"
    summary = re.compile(token + r"(?:,[ \t]*" + token + r")*(?:[ \t]+(?:in[ \t]+[\d.]+[smh](?:[ \t]+\([^)]*\))?|during collection))?")
    for line in reversed(raw.splitlines()):
        text = line.strip().strip("=").strip()
        if not summary.fullmatch(text):
            continue
        return {key: int(match.group(1)) if (match := re.search(r"(\d+)[ \t]+" + pattern + r"\b", text)) else 0
                for key, pattern in patterns.items()}
    # Interrupted runs may have no final summary. Retain only actual node outcomes.
    from collections import Counter
    outcomes = Counter(case["status"] for case in parse_pytest_cases(raw))
    names = {"passed": "PASSED", "failed": "FAILED", "skipped": "SKIPPED", "errors": "ERROR",
             "xfailed": "XFAIL", "xpassed": "XPASS"}
    return {key: outcomes[name] for key, name in names.items()}


class InterruptedPytest(KeyboardInterrupt):
    def __init__(self, output):
        self.output = output


def progress_line(text):
    """Echo only explicit, safe progress fields, never raw auth/payload output."""
    if "QA_INBOUND_WAIT " in text:
        try:
            data = json.loads(text.split("QA_INBOUND_WAIT ", 1)[1])
            if isinstance(data, dict):
                return (f"Inbound setup: barcode={data.get('barcode')}; Edge state={data.get('edgeState')}; "
                        f"observation remaining={data.get('remainingSeconds')}s")
        except (ValueError, TypeError):
            return None
    if "QA_PROGRESS " not in text:
        return None
    try:
        data = json.loads(text.split("QA_PROGRESS ", 1)[1])
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or data.get("kind") != "config_sync_sync":
        return None
    return (f"config sync {data.get('phase')}: waiting for Edge snapshot "
            f"{data.get('targetVersion')}; observed={data.get('observedVersion')}; "
            f"elapsed={data.get('elapsedSeconds')}s; remaining={data.get('remainingSeconds')}s")


def run_with_progress(cmd, *, env, timeout, label):
    """Spool full evidence while showing bounded progress during long waits."""
    interval = max(1.0, float(os.getenv("REPORT_PROGRESS_INTERVAL_SECONDS", "15")))
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="post-report-") as temporary:
        output = Path(temporary) / "pytest-output.txt"
        output.touch()
        stop = threading.Event()

        def monitor():
            offset, pending, last_test = 0, "", "collecting / setup"
            next_heartbeat = started + interval
            while not stop.wait(min(1.0, interval)):
                try:
                    with output.open("rb") as stream:
                        stream.seek(offset)
                        chunk = stream.read()
                        offset = stream.tell()
                    pending += chunk.decode("utf-8", errors="replace")
                    found = re.findall(r"tests[/\\][^\s\r\n]*::[^\s\r\n]+", pending)
                    if found:
                        last_test = found[-1]
                    lines = pending.split("\n")
                    pending = lines.pop()[-8192:]
                    for line in lines:
                        message = progress_line(line)
                        if message:
                            print("\n    " + message, flush=True)
                    now = time.monotonic()
                    if now >= next_heartbeat:
                        print(f"\n    [{label}] running {now-started:.0f}s / limit {timeout}s; {last_test}", flush=True)
                        next_heartbeat = now + interval
                except OSError:
                    # A display problem must not stop pytest or its evidence capture.
                    pass

        watcher = threading.Thread(target=monitor, daemon=True)
        watcher.start()
        try:
            with output.open("wb") as stream:
                try:
                    result = subprocess.run(cmd, stdout=stream, stderr=subprocess.STDOUT,
                                            text=False, timeout=timeout, cwd=str(PROJECT_ROOT), env=env)
                except subprocess.TimeoutExpired as exc:
                    # Keep whatever the exception already carries when nothing reached the capture file.
                    exc.output = output.read_bytes() or exc.output or b""
                    exc.stderr = exc.stderr or b""
                    raise
                except KeyboardInterrupt:
                    raise InterruptedPytest(output.read_bytes()) from None
            # Existing callers/test doubles may return their own captured bytes.
            return SimpleNamespace(returncode=result.returncode,
                                   stdout=result.stdout if result.stdout is not None else output.read_bytes(),
                                   stderr=result.stderr or b"")
        finally:
            stop.set()
            watcher.join(timeout=2)


def run_domain(domain_id, folder, marker, timeout=180):
    # Flow reports print their per-step evidence to stdout, including on PASS.
    # Keep -rs for exact skip reasons. -vv may wrap and overwrite long reasons
    # in the Windows terminal stream, corrupting the node outcome line.
    if marker == "ip_binding":
        cmd = [PYTHON, "-m", "pytest",
               *(f"{folder}::{name}" for name in IP_BINDING_COMPREHENSIVE_CASES),
               "-v", "-s", "-rs", "--tb=short"]
    else:
        cmd = [PYTHON, "-m", "pytest", folder, "-m", marker,
               "-v", "-s", "-rs", "--tb=short"]
    env = os.environ.copy()
    env["RUN_E2E"] = "1"
    env["RUN_SUCCESS"] = "1"
    env["RUN_NEGATIVE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    if marker == "ip_binding":
        env["RUN_IP_BINDING"] = "1"
        env["IP_BINDING_PHASE"] = "spoof"
    if marker == "two_lines":
        env["RUN_TWO_LINES"] = "1"
    # discrepancies's old 20-barcode data set assumes synthetic Core acceptance
    # records. The live environment no longer provides those records.
    if marker == "security":
        # The security suite must validate TLS even when other QA traffic uses
        # an explicitly unverified internal endpoint.
        env["SSL_VERIFY"] = "1"
        # The report launcher runs before config.settings loads test.env.
        # Read the CA setting here as well, while keeping process env precedence.
        ca_bundle = str(os.getenv("POST_TLS_CA_BUNDLE", dotenv_values(
            PROJECT_ROOT / "config" / "test.env"
        ).get("POST_TLS_CA_BUNDLE") or "")).strip()
        if ca_bundle:
            ca_path = Path(ca_bundle).expanduser()
            if not ca_path.is_absolute():
                ca_path = PROJECT_ROOT / ca_path
            env["REQUESTS_CA_BUNDLE"] = str(ca_path)
            env["SSL_CERT_FILE"] = str(ca_path)
    start = time.perf_counter()
    returncode = None
    execution_error = None
    def decode(value):
        return strip_ansi(value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or "")
    try:
        r = run_with_progress(cmd, env=env, timeout=timeout, label=f"Domain {domain_id}/{marker}")
        returncode = r.returncode
        full = decode(r.stdout) + "\n" + decode(r.stderr)
        if returncode == 2 and "KeyboardInterrupt" in full:
            execution_error = "INTERRUPTED"
    except subprocess.TimeoutExpired as exc:
        execution_error = "TIMEOUT"
        full = decode(exc.stdout) + "\n" + decode(exc.stderr) + (
            f"\nTIMEOUT after {timeout}s; counts below are partial and the remaining tests were not evaluated."
        )
    except InterruptedPytest as exc:
        execution_error = "INTERRUPTED"
        full = decode(exc.output) + ("\nINTERRUPTED by user; counts are partial. "
                                   "Remaining tests and fixture cleanup were not independently verified.")
    except OSError as exc:
        execution_error = "EXECUTION ERROR"
        full = str(exc)
    if (execution_error and marker=='negative' and '4_bagging' in folder
            and local_setting('QA_POSTAL_FAULT_FIXTURES','false').lower()=='true'):
        try:
            from config.settings import settings
            from utils.postal_fault_fixture import recover_abandoned_postal_fixture
            restored=recover_abandoned_postal_fixture(settings)
            full+='\nQA_POSTAL_RECOVERY '+json.dumps({'restored':restored,'liveOwnerLeasesWereNotTouched':True})
        except Exception as error:
            full+='\nQA_POSTAL_RECOVERY_FAILED '+type(error).__name__+': '+str(error)
    counts = pytest_result_counts(full)
    if execution_error:
        status = execution_error
    elif counts["failed"] or counts["errors"] or returncode not in (0, 5):
        status = "FAILED"
    elif returncode == 5 or not any(counts.values()):
        status = "NO TESTS"
    elif counts["skipped"] or counts["xfailed"] or counts["xpassed"]:
        status = "INCOMPLETE"
    else:
        status = "PASSED"
    return {**counts, "marker": marker, "status": status, "returncode": returncode,
            "elapsed": round(time.perf_counter() - start, 1), "raw": full}


def all_passed(results):
    return bool(results) and all(d.get("status") == "PASSED" for d in results.values())


def display_status(result):
    """Distinguish an incomplete suite from one with failed tests."""
    states = {part.strip() for part in str(result.get("status", "")).split(" / ")}
    if result.get("failed", 0) or result.get("errors", 0) or states & {
        "FAILED", "TIMEOUT", "EXECUTION ERROR",
    }:
        return "fail"
    if result.get("status") == "PASSED":
        return "pass"
    return "incomplete"


def combine_results(*runs):
    return {
        **{key: sum(r[key] for r in runs) for key in ("passed", "failed", "skipped", "errors")},
        "elapsed": round(sum(r["elapsed"] for r in runs), 1),
        "raw": "\n".join(r["raw"] for r in runs),
        # Keep pytest invocations separate: the same node can be selected by
        # both success and negative markers and has different step evidence.
        "runs": list(runs),
        "status": "PASSED" if all(r["status"] == "PASSED" for r in runs)
                  else " / ".join(dict.fromkeys(r["status"] for r in runs if r["status"] != "PASSED")),
    }


def _safe_endpoint(value):
    """Show a target endpoint without URL credentials, query strings or fragments."""
    if not value:
        return "not recorded"
    try:
        parsed = urlsplit(str(value))
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return "not recorded"
    if parsed.scheme not in {"http", "https", "ws", "wss"} or not host:
        return "not recorded"
    if ":" in host:
        host = f"[{host}]"
    if port:
        host += f":{port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def collect_report_metadata():
    """Record reproducible local inputs, leaving deployed versions unverified."""
    local_env = dotenv_values(PROJECT_ROOT / "config" / "test.env")

    def setting(name, fallback=""):
        return os.getenv(name) or local_env.get(name) or fallback

    def git_value(*args):
        try:
            result = subprocess.run(
                ["git", *args], cwd=str(PROJECT_ROOT), capture_output=True,
                text=True, timeout=5, check=True,
            )
            return result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return "not recorded"

    tree_status = git_value("status", "--porcelain")
    if tree_status == "not recorded":
        tree_label = "local changes unknown"
    elif tree_status:
        tree_label = "local changes (%d files)" % len(tree_status.splitlines())
    else:
        tree_label = "no local changes"

    return {
        "testCommit": git_value("rev-parse", "HEAD") or "not recorded",
        "testBranch": git_value("branch", "--show-current") or "not recorded",
        "testTree": tree_label,
        "python": sys.version.split()[0],
        "coreTarget": _safe_endpoint(setting("CORE_BASE_URL", "http://core.example.test")),
        "edgeTarget": _safe_endpoint(setting("WS_URL", "wss://edge.example.test")),
        "primaryCenter": setting("REPORT_PRIMARY_CENTER", "not recorded"),
        "primaryDeviceId": setting("DEVICE_ID", "not recorded"),
        "coreVersion": setting("REPORT_CORE_VERSION", "not recorded"),
        "edgeVersion": setting("REPORT_EDGE_VERSION", "not recorded"),
        "edgeDeployment": (None if os.getenv("REPORT_SKIP_DEPLOYMENT_PROBE", "0") == "1"
                           else edge_deployment_identity(setting("WS_URL", ""))),
    }


def summarize_test_identity(domain_results):
    """Count executions separately from node IDs; node IDs are not business cases."""
    cases = [case for domain in domain_results.values()
             for run in domain.get("runs", [domain])
             for case in parse_pytest_cases(run.get("raw", ""))]
    expected = sum(domain.get(key, 0) for domain in domain_results.values()
                   for key in ("passed", "failed", "skipped", "errors"))
    if len(cases) != expected:
        return None
    nodeids = [case["nodeid"] for case in cases]
    return {"executions": len(nodeids), "uniqueNodes": len(set(nodeids)),
            "repeatedNodes": len(nodeids) - len(set(nodeids))}


def format_json_pretty(obj):
    """Try to pretty-print JSON strings."""
    if isinstance(obj, str):
        try:
            parsed = json.loads(obj)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, ValueError):
            return obj
    return json.dumps(obj, indent=2, ensure_ascii=False)


def build_html(domain_results, ts, total_elapsed, metadata=None):
    page = _build_html_base(domain_results, ts, total_elapsed, metadata)
    return page.replace("</style>", STEPS_CSS + SUMMARY_CSS + "</style>", 1)


def _build_html_base(domain_results, ts, total_elapsed, metadata=None):
    metadata = metadata or {}
    t_passed = sum(d["passed"] for d in domain_results.values())
    t_failed = sum(d["failed"] for d in domain_results.values())
    t_skipped = sum(d["skipped"] for d in domain_results.values())
    t_errors = sum(d.get("errors", 0) for d in domain_results.values())
    t_total = t_passed + t_failed + t_skipped + t_errors
    pct = round((t_passed / t_total * 100) if t_total else 0, 1)
    identity = summarize_test_identity(domain_results)
    identity_note = (
        f"{identity['executions']} test executions, {identity['uniqueNodes']} unique test ids, "
        f"{identity['repeatedNodes']} repeated executions of an id; a unique id is not necessarily an independent scenario."
        if identity else "The unique-id count is not reliable; compare the test list with the full pytest output."
    )
    provenance = (
        '<div class="provenance">'
        f'<div>{html_mod.escape(identity_note)}</div>'
        f'<div>Primary device of the report: center {html_mod.escape(str(metadata.get("primaryCenter", "not recorded")))}, '
        f'id {html_mod.escape(str(metadata.get("primaryDeviceId", "not recorded")))}. '
        'These details were checked after the same device authenticated successfully on the Edge; '
        'scenarios with a dedicated fixture may use another device or center.</div>'
        '<div>These numbers are test-run results, not a count of product bugs or a coverage figure. '
        'Failed is not necessarily a product bug, and Errors=0 does not prove there was no timeout or exception inside Failed tests.</div>'
        f'<div>Test code: branch {html_mod.escape(str(metadata.get("testBranch", "not recorded")))}, '
        f'commit {html_mod.escape(str(metadata.get("testCommit", "not recorded")))}, '
        f'{html_mod.escape(str(metadata.get("testTree", "not recorded")))}</div>'
        f'<div>Python {html_mod.escape(str(metadata.get("python", "not recorded")))}; '
        f'Core {html_mod.escape(str(metadata.get("coreTarget", "not recorded")))} '
        f'(declared version: {html_mod.escape(str(metadata.get("coreVersion", "not recorded")))}); '
        f'Edge {html_mod.escape(str(metadata.get("edgeTarget", "not recorded")))} '
        f'(declared version: {html_mod.escape(str(metadata.get("edgeVersion", "not recorded")))})</div>'
        + (f'<div>Deployed Edge identity (read-only, from Docker on the Edge host): '
           f'{html_mod.escape(str(metadata["edgeDeployment"]))}. The Core version cannot be read from the API and '
           'is not independently confirmed; REPORT_CORE_VERSION is a manual declaration only.</div>'
           if metadata.get("edgeDeployment") else
           '<div>The deployed Edge/Core versions are not independently confirmed from the services.</div>')
        + '</div>'
    )
    summary_html = render_summary(domain_results, parse_pytest_cases, t_passed, t_failed, t_skipped, t_total,
                                  describe_scenario)
    overall_display = "fail" if any(display_status(d) == "fail" for d in domain_results.values()) else (
        "incomplete" if any(display_status(d) == "incomplete" for d in domain_results.values()) else "pass"
    )
    status_text = {"pass": "ALL PASSED", "fail": "FAILED", "incomplete": "INCOMPLETE"}[overall_display]

    # Domain cards
    dom_cards = ""
    for did in sorted(domain_results.keys()):
        d = domain_results[did]
        dc = {"pass": "#10b981", "fail": "#ef4444", "incomplete": "#f59e0b"}[display_status(d)]
        dom_cards += '''
        <div class="stat-card">
            <div class="stat-num" style="color:%s">%s</div>
            <div class="stat-label">%s</div>
            <div class="stat-detail">%dP / %dF / %dE / %dS - %.0fs — %s</div>
        </div>''' % (dc, did, DOMAINS[did]["name"], d["passed"], d["failed"], d.get("errors", 0), d["skipped"], d["elapsed"], html_mod.escape(d.get("status", "UNKNOWN")))

    # Detailed test case sections per domain
    detail_sections = ""
    for did in sorted(domain_results.keys()):
        d = domain_results[did]
        if not d["raw"].strip():
            continue

        tc_html = "".join(render_pytest_run(run) for run in d.get("runs", [d]))
        if did == "0A":
            tc_html += ('<div class="tc-result">Scope of this run: ten device-IP-binding scenarios from this host. '
                        'The IP shown is the local IP of the test socket; the value the Edge sees after NAT/proxy is not known from this '
                        'report alone. In the mismatched-IP tests the binding is changed to another IP '
                        'but the device does not connect from a second host. The scenario with two real source IPs '
                        'and a device with no binding is not checked in this run and is not counted as a pass.</div>')

        detail_sections += '''
        <div class="domain-block">
            <div class="domain-header" onclick="this.parentElement.classList.toggle('collapsed')">
                <span class="domain-icon">%s</span>
                <span class="domain-title">%s %s: %s</span>
                <span class="domain-stats">%dP / %dF / %dE / %dS</span>
                <span class="domain-time">%.0fs</span>
                <span class="toggle-arrow">&#9660;</span>
            </div>
            <div class="domain-body">%s</div>
        </div>''' % (
            {"pass": "&#10004;", "fail": "&#10008;", "incomplete": "&#9888;"}[display_status(d)],
            "Domain" if did in "012345" else "Suite", did, DOMAINS[did]["name"],
            d["passed"], d["failed"], d.get("errors", 0), d["skipped"],
            d["elapsed"], tc_html
        )

    return '''<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8">
<title>CPS Full QA Report</title>
<style>
:root {
    --bg: #111827; --bg2: #1f2937; --bg3: #374151;
    --text: #f9fafb; --text2: #d1d5db; --text3: #9ca3af;
    --accent: #3b82f6; --green: #10b981; --red: #ef4444;
    --yellow: #f59e0b; --blue: #60a5fa; --pink: #f472b6;
    --border: #374151; --radius: 12px;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: 'Segoe UI', Tahoma, sans-serif; background: var(--bg); color: var(--text); line-height: 1.7; }
.container { max-width: 1200px; margin: 0 auto; padding: 30px 20px; }

/* Header */
.report-header { text-align: center; margin-bottom: 36px; padding: 32px; background: linear-gradient(135deg, #1e3a5f, #1f2937); border-radius: var(--radius); border: 1px solid var(--border); }
.report-header h1 { font-size: 28px; color: var(--accent); margin-bottom: 8px; }
.report-header .meta { color: var(--text3); font-size: 13px; }
.report-header .meta span { margin: 0 12px; }
.provenance { margin: -18px 0 30px; padding: 14px 18px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg2); color: var(--text2); font-size: 12px; }

/* Stats Grid */
.stats-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 32px; }
.stat-card { background: var(--bg2); border-radius: var(--radius); padding: 18px; text-align: center; border: 1px solid var(--border); transition: transform 0.2s; }
.stat-card:hover { transform: translateY(-2px); }
.stat-num { font-size: 36px; font-weight: 700; }
.stat-label { font-size: 11px; color: var(--text3); margin-top: 2px; }
.stat-detail { font-size: 11px; color: var(--text3); margin-top: 4px; }

/* Overall Status */
.overall-status { text-align: center; padding: 20px; border-radius: var(--radius); margin-bottom: 32px; font-size: 20px; font-weight: 700; }
.overall-status.pass { background: #064e3b; color: #6ee7b7; border: 1px solid #065f46; }
.overall-status.fail { background: #7f1d1d; color: #fca5a5; border: 1px solid #991b1b; }
.overall-status.incomplete { background: #78350f; color: #fcd34d; border: 1px solid #92400e; }

/* Domain Blocks */
.domain-block { background: var(--bg2); border-radius: var(--radius); margin-bottom: 16px; border: 1px solid var(--border); overflow: hidden; }
.domain-header { display: flex; align-items: center; padding: 14px 20px; cursor: pointer; user-select: none; transition: background 0.2s; gap: 12px; }
.domain-header:hover { background: var(--bg3); }
.domain-icon { font-size: 18px; width: 28px; text-align: center; }
.domain-title { font-weight: 600; font-size: 15px; flex: 1; }
.domain-stats { font-size: 12px; color: var(--text3); background: var(--bg); padding: 4px 10px; border-radius: 6px; }
.domain-time { font-size: 12px; color: var(--text3); }
.toggle-arrow { font-size: 12px; color: var(--text3); transition: transform 0.3s; }
.domain-block.collapsed .toggle-arrow { transform: rotate(-90deg); }
.domain-block.collapsed .domain-body { display: none; }
.domain-body { padding: 0 16px 16px; }
.domain-body details { margin-top: 12px; padding: 12px; }
.domain-body pre { margin-top: 10px; padding: 12px; background: var(--bg); white-space: pre-wrap; overflow-wrap: anywhere; direction: ltr; text-align: left; }

/* Test Case Cards */
.tc-card { background: var(--bg); border-radius: 10px; margin: 10px 0; border: 1px solid var(--border); overflow: hidden; }
.tc-card.pass { border-right: 4px solid var(--green); }
.tc-card.fail { border-right: 4px solid var(--red); }
.tc-card.unverified { border-right: 4px solid #f59e0b; }
.tc-card.skip { border-right: 4px solid var(--yellow); }
.tc-card.setup { border-right: 4px solid var(--blue); }
.tc-card.not_checked { border-right: 4px solid var(--text3); }

.tc-header { display: flex; align-items: center; padding: 12px 16px; gap: 10px; cursor: pointer; user-select: none; }
.tc-header:hover { background: var(--bg2); }
.tc-header:not(.expandable) { cursor: default; }
.tc-evidence-note { color: var(--text3); font-size: 11px; }
.step-evidence { border-top: 1px solid var(--border); padding: 10px 16px 14px; }
.step-caption { color: var(--text3); font-size: 11px; margin-bottom: 6px; }
.step-evidence .tc-card { margin: 8px 0; }
.orphan-logs { padding: 12px; border: 1px solid var(--border); border-radius: 8px; }
.tc-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; min-width: 50px; text-align: center; }
.tc-badge.pass { background: #064e3b; color: #6ee7b7; }
.tc-badge.fail { background: #7f1d1d; color: #fca5a5; }
.tc-badge.unverified { background: #78350f; color: #fcd34d; }
.tc-badge.skip { background: #78350f; color: #fcd34d; }
.tc-badge.setup { background: #1e3a5f; color: #93c5fd; }
.tc-badge.not_checked { background: #374151; color: #9ca3af; }
.tc-title { font-size: 13px; flex: 1; }
.tc-num { font-size: 12px; color: var(--text3); min-width: 28px; }

.tc-scenario { padding: 6px 12px; font-size: 12px; color: var(--text2); }
.tc-scenario b { color: var(--accent); }
.tc-what { color: var(--text3); font-size: 11px; }
.tc-details { padding: 0 16px 14px; display: none; }
.tc-card.expanded > .tc-details { display: block; }
.run-heading { margin: 16px 0 8px; color: var(--text2); font-size: 13px; }

.tc-detail-row { margin: 6px 0; }
.tc-detail-label { font-size: 11px; color: var(--text3); margin-bottom: 2px; font-weight: 600; }
.tc-detail-value { font-size: 12px; background: var(--bg2); padding: 8px 12px; border-radius: 6px; font-family: 'Cascadia Code', 'Fira Code', Consolas, monospace; white-space: pre-wrap; word-break: break-all; line-height: 1.5; color: var(--text2); border: 1px solid var(--border); }

/* JSON syntax coloring */
.json-key { color: var(--blue); }
.json-str { color: #86efac; }
.json-num { color: var(--pink); }
.json-bool { color: var(--yellow); }
.json-null { color: var(--text3); }

.tc-error { background: #1c0a0a; border: 1px solid #991b1b; border-radius: 6px; padding: 8px 12px; margin-top: 6px; color: #fca5a5; font-size: 12px; font-family: 'Cascadia Code', Consolas, monospace; }

.tc-result { font-size: 11px; color: var(--yellow); padding: 6px 12px; background: var(--bg2); border-radius: 4px; margin-top: 8px; font-weight: 600; }

/* Footer */
.footer { text-align: center; margin-top: 40px; padding: 20px; color: var(--text3); font-size: 11px; border-top: 1px solid var(--border); }

/* Scrollbar */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--bg3); border-radius: 4px; }
</style>
</head>
<body>
<div class="container">

<div class="report-header">
    <h1>CPS Full QA Report</h1>
    <div class="meta">
        <span>%s</span>
        <span>|</span>
        <span>Duration: %.0fs</span>
        <span>|</span>
        <span>Core: %s</span>
        <span>|</span>
        <span>Edge: %s</span>
    </div>
</div>

<div class="overall-status %s">%s &mdash; %d passed / %d failed / %d errors / %d skipped / %d total</div>

%s

<div class="stats-grid">%s</div>

<h2 style="color:var(--text2);margin-bottom:16px;font-size:16px">Test Details</h2>

%s

<div class="footer">Core Post Sorting QA Framework</div>
</div>

<script>
document.querySelectorAll('.tc-header.expandable').forEach(h => {
    h.addEventListener('click', () => h.closest('.tc-card').classList.toggle('expanded'));
});
</script>
</body></html>''' % (
        ts, total_elapsed,
        html_mod.escape(str(metadata.get("coreTarget", "not recorded"))),
        html_mod.escape(str(metadata.get("edgeTarget", "not recorded"))),
        overall_display,
        status_text, t_passed, t_failed, t_errors, t_skipped, t_total,
        summary_html + provenance,
        dom_cards,
        detail_sections
    )


PYTEST_NODE_RE = re.compile(r"^(tests/\S+::\S+)(?:\s+(.*))?$")
PYTEST_OUTCOME_RE = re.compile(r"^(PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)(.*)$")


def parse_pytest_cases(raw):
    """Read every verbose pytest outcome, including tests with no flow log."""
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    cases = []
    pending = None
    pending_output = []
    wrapped_skip = None
    in_results = True
    for line in raw.splitlines():
        stripped = line.strip()
        if "test session starts" in stripped:
            in_results = True
            pending = None
            pending_output = []
            wrapped_skip = None
            continue
        if "warnings summary" in stripped or "short test summary info" in stripped:
            in_results = False
            pending = None
            pending_output = []
            wrapped_skip = None
            continue
        if not in_results:
            continue
        match = PYTEST_NODE_RE.match(stripped)
        if match:
            wrapped_skip = None
            tail = match.group(2) or ""
            outcome = PYTEST_OUTCOME_RE.match(tail)
            if outcome:
                cases.append({"nodeid": match.group(1), "status": outcome.group(1),
                              "reason": outcome.group(2).strip(), "output": ""})
                if outcome.group(1) == "SKIPPED" and cases[-1]["reason"].startswith("(") \
                        and not cases[-1]["reason"].endswith(")"):
                    wrapped_skip = cases[-1]
                pending = None
            else:
                pending = match.group(1)
                pending_output = [tail] if tail else []
            continue
        if pending:
            outcome = PYTEST_OUTCOME_RE.match(stripped)
            if outcome:
                cases.append({"nodeid": pending, "status": outcome.group(1),
                              "reason": outcome.group(2).strip(),
                              "output": "\n".join(pending_output).strip()})
                if outcome.group(1) == "SKIPPED" and cases[-1]["reason"].startswith("(") \
                        and not cases[-1]["reason"].endswith(")"):
                    wrapped_skip = cases[-1]
                pending = None
                pending_output = []
            else:
                pending_output.append(line)
        elif wrapped_skip and stripped:
            wrapped_skip["reason"] += " " + stripped
            if stripped.endswith(")"):
                wrapped_skip = None
    # Attach pytest assertion text to failed tests that did not print a flow
    # report. A clickable failure card should explain its own failure.
    failure_sections = re.split(r"^_+\s+(test_[A-Za-z0-9_]+)\s+_+\s*$", raw, flags=re.MULTILINE)
    failure_reasons = {}
    for index in range(1, len(failure_sections) - 1, 2):
        errors = [line.strip()[2:].strip() for line in failure_sections[index + 1].splitlines()
                  if line.lstrip().startswith("E ")]
        if errors:
            failure_reasons[failure_sections[index]] = " | ".join(errors[:3])[:700]
    for case in cases:
        if case["status"] in {"FAILED", "ERROR"} and not case["reason"]:
            case["reason"] = failure_reasons.get(case["nodeid"].rsplit("::", 1)[-1], "")
    _attach_skip_reasons(raw, cases)
    return cases


def _attach_skip_reasons(raw, cases):
    """Distribute summary occurrences once; never overwrite every parameter with the last reason."""
    from collections import defaultdict
    skipped = [case for case in cases if case["status"] == "SKIPPED"]
    assigned = set()
    for line in raw.splitlines():
        if not line.startswith("QA_SKIP_JSON="):
            continue
        try:
            entry = json.loads(line[len("QA_SKIP_JSON="):])
        except (ValueError, TypeError):
            continue
        if not isinstance(entry, dict) or not isinstance(entry.get("reason"), str):
            continue
        for case in skipped:
            if case["nodeid"] == entry.get("nodeid"):
                case["reason"] = entry["reason"]
                assigned.add(id(case))
    groups = defaultdict(list)
    for match in re.finditer(r"^SKIPPED \[(\d+)\] (.+?):(\d+): (.+)$", raw, re.MULTILINE):
        groups[(match.group(2).replace("\\", "/"), int(match.group(3)))].append((int(match.group(1)), match.group(4).strip()))
    for (source, line), summaries in groups.items():
        try:
            tree = ast.parse((PROJECT_ROOT / source).read_text(encoding="utf-8"))
            names = {node.name for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and min([node.lineno, *(d.lineno for d in node.decorator_list)]) <= line <= node.end_lineno}
        except (OSError, SyntaxError, UnicodeError):
            names = set()
        candidates = [case for case in skipped if id(case) not in assigned
            and case["nodeid"].split("::", 1)[0] == source
            and case["nodeid"].split("::", 1)[-1].split("[", 1)[0] in names]
        if not candidates:
            same_file = [case for case in skipped if id(case) not in assigned and case["nodeid"].split("::", 1)[0] == source]
            if len(same_file) == sum(count for count, _ in summaries):
                candidates = same_file
        if len(candidates) != sum(count for count, _ in summaries):
            # Old reports may refer to different source line numbers. Do not guess.
            continue
        cursor = 0
        for count, reason in summaries:
            for case in candidates[cursor:cursor+count]:
                if not case["reason"]:
                    case["reason"] = reason
                assigned.add(id(case))
            cursor += count


def render_pytest_case(case, blocks=()):
    status = case["status"].lower()
    badge_class = {"passed": "pass", "failed": "fail", "skipped": "skip",
                   "error": "fail", "xfail": "skip", "xpass": "unverified"}.get(status, "skip")
    scenario = describe_scenario(case["nodeid"])
    scenario_html = ""
    if scenario:
        _, code, title, what = scenario
        scenario_html = ('<div class="tc-scenario"><b>%s</b> %s<div class="tc-what">%s</div></div>'
                         % (html_mod.escape(code), html_mod.escape(title), html_mod.escape(what)))
    if blocks:
        # Keep step cards visible under their pytest result.  Each step then
        # needs only one click to show its request, response and error.
        reason = ('<div class="tc-result">%s</div>' % html_mod.escape(mask_text(case["reason"]))) \
            if case["reason"] else ""
        reason = scenario_html + reason
        steps = ('<div class="step-evidence"><div class="step-caption">'
                 'Step details of this test; not counted twice in the test totals'
                 '</div>%s</div>' % "".join(render_test_block(block) for block in blocks))
        return ('<div class="tc-card %s"><div class="tc-header">'
                '<span class="tc-badge %s">%s</span><span class="tc-title" dir="ltr">%s</span>'
                '</div>%s%s</div>' % (badge_class, badge_class,
                                    html_mod.escape(case["status"]),
                                    html_mod.escape(case["nodeid"]), reason, steps))

    evidence = []
    if scenario_html:
        evidence.append(scenario_html)
    if case["reason"]:
        evidence.append('<div class="tc-result">%s</div>' % html_mod.escape(mask_text(case["reason"])))
    steps, other_output = split_output(case.get("output") or "")
    if steps:
        evidence.append(render_steps(steps))
    if other_output:
        evidence.append('<div class="step-evidence"><div class="step-caption">'
                        'Recorded output of this test</div><pre>%s</pre></div>'
                        % html_mod.escape(mask_text(other_output)))
    if not evidence:
        evidence.append('<div class="tc-result">This test did not record a step log or '
                        'a separate payload/response.</div>')
    details = '<div class="tc-details">%s</div>' % "".join(evidence) if evidence else ""
    header_class = "tc-header expandable" if evidence else "tc-header"
    no_evidence = "" if blocks or steps or other_output else '<span class="tc-evidence-note">No step log</span>'
    return ('<div class="tc-card %s"><div class="%s">'
            '<span class="tc-badge %s">%s</span><span class="tc-title" dir="ltr">%s</span>'
            '%s</div>%s</div>' % (badge_class, header_class, badge_class,
                                 html_mod.escape(case["status"]),
                                 html_mod.escape(case["nodeid"]), no_evidence, details))


# When a list, the full pytest output of every run is collected there and written to a side file by main().
RAW_SIDECAR = None


def render_pytest_run(run):
    """Render one pytest invocation without mixing its evidence with another."""
    raw = run["raw"]
    cases = parse_pytest_cases(raw)
    blocks = parse_test_blocks(raw)
    blocks_by_node = {}
    for block in blocks:
        if block.get("nodeid"):
            blocks_by_node.setdefault(block["nodeid"], []).append(block)
    label = html_mod.escape(str(run.get("marker", "pytest")))
    parts = [f'<div class="run-heading">Run: {label}</div>']
    parts.extend(render_pytest_case(case, blocks_by_node.get(case["nodeid"], []))
                 for case in cases)
    expected = sum(run.get(key, 0) for key in ("passed", "failed", "skipped", "errors"))
    if len(cases) != expected:
        parts.append('<div class="tc-result">The test list was extracted incompletely: '
                     '%d of %d; check the full pytest output.</div>'
                     % (len(cases), expected))
    orphans = [block for block in blocks if not block.get("nodeid")]
    if orphans:
        parts.append('<details class="orphan-logs"><summary>Step logs with no matching test'
                     '</summary>%s</details>' % "".join(render_test_block(block) for block in orphans))
    if RAW_SIDECAR is not None:
        RAW_SIDECAR.append("=" * 20 + " pytest output, marker %s " % run.get("marker", "pytest") + "=" * 20 + "\n" + mask_text(raw))
        parts.append('<div class="tc-result">The full pytest output of this run is saved in a separate file next to this report '
                     '(*_Raw_*.txt) to keep this page small.</div>')
    else:
        parts.append('<details class="tc-card"><summary>Full pytest output of this run</summary>'
                     '<pre>%s</pre></details>' % html_mod.escape(mask_text(raw)))
    return "".join(parts)


def parse_test_blocks(raw):
    """Parse raw pytest output into individual test case blocks."""
    blocks = []
    lines = raw.splitlines()
    current_block = None
    current_node = None
    in_results = True

    for line in lines:
        stripped = line.strip()

        if "test session starts" in stripped:
            in_results = True
            current_node = None
        if re.match(r"^=+\s+(?:FAILURES|ERRORS|warnings summary|short test summary info)\s+=+", stripped):
            in_results = False
            if current_block:
                blocks.append(current_block)
                current_block = None
            current_node = None
        if not in_results:
            continue

        node_match = PYTEST_NODE_RE.match(stripped)
        if node_match:
            current_node = node_match.group(1)

        # New execution report
        report_match = re.search(r"(?:^|\s)Execution report:\s*(.*)$", stripped)
        if report_match:
            if current_block:
                blocks.append(current_block)
            current_block = {"report_name": report_match.group(1), "nodeid": current_node,
                             "cases": [], "result_line": ""}
            continue

        if not current_block:
            continue

        # Test case header: "01. [PASS] TC-01: Title"
        tc_match = re.match(r"(\d+)\.\s+\[(PASS|FAIL|UNVERIFIED|SETUP|NOT_CHECKED)\]\s+(.*)", stripped)
        if tc_match:
            current_block["cases"].append({
                "num": tc_match.group(1),
                "status": tc_match.group(2).lower(),
                "title": tc_match.group(3),
                "payload": "",
                "response": "",
                "error": "",
                "evidence": "",
            })
            continue

        if not current_block["cases"]:
            continue

        tc = current_block["cases"][-1]

        if stripped.startswith("payloadSent:"):
            tc["payload"] = stripped[len("payloadSent:"):].strip()
        elif stripped.startswith("responseReceived:"):
            tc["response"] = stripped[len("responseReceived:"):].strip()
        elif stripped.startswith("[onError]:"):
            tc["error"] = stripped[len("[onError]:"):].strip()
        elif stripped.startswith("evidence:"):
            tc["evidence"] = stripped[len("evidence:"):].strip()
        elif stripped.startswith("Result:"):
            current_block["result_line"] = stripped

    if current_block:
        blocks.append(current_block)

    unique = {}
    for block in blocks:
        key = (block.get("nodeid"), block["report_name"])
        previous = unique.get(key)
        if previous is None or _block_completeness(block) >= _block_completeness(previous):
            unique[key] = block
    return list(unique.values())


def _block_completeness(block):
    """Keep the final, fullest print of a flow after intermediate failures."""
    cases = block["cases"]
    completed = sum(case["status"] != "not_checked" for case in cases)
    evidence = sum(bool(case["payload"] or case["response"] or case["error"] or case.get("evidence"))
                   for case in cases)
    return completed, evidence, len(cases)


def syntax_highlight_json(text):
    """Simple JSON syntax highlighting."""
    if not text:
        return ""
    # Highlight keys
    text = re.sub(r'"([^"]+)":', r'<span class="json-key">"\1"</span>:', text)
    # Highlight string values
    text = re.sub(r': "([^"]*)"', r': <span class="json-string">"\1"</span>', text)
    # Highlight numbers
    text = re.sub(r': (\d+\.?\d*)', r': <span class="json-num">\1</span>', text)
    # Highlight booleans
    text = re.sub(r': (true|false)', r': <span class="json-bool">\1</span>', text)
    # Highlight null
    text = re.sub(r': null', r': <span class="json-null">null</span>', text)
    # Highlight URLs
    text = re.sub(r'(https?://[^\s<"]+)', r'<span style="color:#60a5fa">\1</span>', text)
    # Highlight IP addresses
    text = re.sub(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', r'<span style="color:#f472b6;font-weight:600">\1</span>', text)
    return text


def _server_evidence_links(text):
    """Link only collector files inside this report's supporting-artifact folder."""
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return ""
    root = (REPORT_DIR / "server_evidence").resolve()
    found = set()

    def visit(node):
        if isinstance(node, dict):
            path = node.get("artifactPath")
            if isinstance(path, str):
                try:
                    target = Path(path).resolve()
                    if target.is_relative_to(root) and target.suffix == ".json" and target.is_file():
                        found.add(target.relative_to(REPORT_DIR.resolve()).as_posix())
                except (OSError, ValueError):
                    pass
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)
    visit(value)
    from urllib.parse import quote
    return "".join('<div class="tc-detail-row"><a href="%s" target="_blank" rel="noopener">Evidence file of this read</a></div>'
                   % html_mod.escape(quote(path, safe="/"), quote=True) for path in sorted(found))


def render_test_block(block):
    """Render a single execution report block into HTML."""
    html_parts = []
    for case in block["cases"]:
        status = case["status"]
        badge_class = {"pass": "pass", "fail": "fail", "unverified": "unverified", "setup": "setup", "not_checked": "skip"}.get(status, "skip")
        badge_text = {"pass": "PASS", "fail": "FAIL", "unverified": "PRECONDITION?", "setup": "SETUP", "not_checked": "-"}.get(status, status.upper())

        # Credentials are always masked in the report, whatever REPORT_SHOW_SECRETS says for other tools.
        payload_html = syntax_highlight_json(html_mod.escape(mask_text(case["payload"]))) if case["payload"] else '<span style="color:var(--text3)">-</span>'
        response_html = syntax_highlight_json(html_mod.escape(mask_text(case["response"]))) if case["response"] else '<span style="color:var(--text3)">-</span>'

        error_html = ""
        if case["error"]:
            error_html = '<div class="tc-error">[Error] %s</div>' % syntax_highlight_json(html_mod.escape(mask_text(case["error"])))

        details = ""
        if case["payload"] or case["response"] or case["error"] or case.get("evidence"):
            details = '<div class="tc-details">'
            # CSS (grid on .tc-details) puts payload and response side by side; narrow screens stack them.
            if case["payload"]:
                details += '<div class="tc-detail-row"><div class="tc-detail-label">Payload Sent</div><div class="tc-detail-value">%s</div></div>' % payload_html
            if case["response"]:
                details += '<div class="tc-detail-row tc-resp"><div class="tc-detail-label">Response Received</div><div class="tc-detail-value">%s</div></div>' % response_html
            if case.get("evidence"):
                details += '<div class="tc-detail-row tc-full"><div class="tc-detail-label">Scenario Evidence</div><div class="tc-detail-value">%s</div></div>' % syntax_highlight_json(html_mod.escape(mask_text(case["evidence"])))
                details += _server_evidence_links(case["evidence"])
            details += error_html
            details += '</div>'

        header_class = "tc-header expandable" if details else "tc-header"
        html_parts.append('''
        <div class="tc-card %s">
            <div class="%s">
                <span class="tc-num">%s.</span>
                <span class="tc-badge %s">%s</span>
                <span class="tc-title">%s</span>
            </div>
            %s
        </div>''' % (status, header_class, case["num"], badge_class, badge_text,
                      html_mod.escape(case["title"]), details))

    # Result line
    if block.get("result_line"):
        html_parts.append('<div class="tc-result">%s</div>' % html_mod.escape(block["result_line"]))

    return "\n".join(html_parts)


def write_report_checkpoint(path, results, timestamp, elapsed, metadata, note="", title=None):
    global RAW_SIDECAR
    RAW_SIDECAR = []
    try:
        page = build_html(results, timestamp, elapsed, metadata)
        raw_text = "\n\n".join(RAW_SIDECAR)
    finally:
        RAW_SIDECAR = None
    if title:
        page = page.replace("<title>CPS Full QA Report</title>", "<title>%s</title>" % html_mod.escape(title), 1)
        page = page.replace("<h1>CPS Full QA Report</h1>", "<h1>%s</h1>" % html_mod.escape(title), 1)
    raw_path = path.with_name(path.name.replace("CPS_Full_Report_", "CPS_Full_Raw_").replace("_Report_", "_Raw_")
                              .replace(".html", ".txt"))
    raw_path.write_text(raw_text, encoding="utf-8")
    if note:
        page = page.replace("<body>", '<body><div role="status" dir="ltr" style="padding:20px;background:#713f12;color:white">'
                            + html_mod.escape(note) + "</div>", 1)
        page = page.replace("ALL PASSED", "INCOMPLETE")
    path.write_text(page, encoding="utf-8")


def main():
    try:
        target = prepare_primary_device_profile()
    except RuntimeError as exc:
        print(f"Full report preflight: {exc}", file=sys.stderr)
        report_path = write_blocked_preflight_report(exc)
        print(f"  BLOCKED HTML report: {report_path}")
        return 2
    os.environ["REPORT_PRIMARY_CENTER"] = target["center"]
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ts_display = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 60)
    print("  CPS Full QA Report -- Domains, Cross-Domain Success, and Smoke")
    print("  Timestamp:", ts_display)
    print("  Primary device:", target["deviceId"], "center", target["center"])
    print("=" * 60)

    domain_results = {}
    metadata = collect_report_metadata()
    grand_start = time.perf_counter()
    report_path = REPORT_DIR / ("CPS_Full_Report_%s.html" % ts)
    write_report_checkpoint(report_path, domain_results, ts_display, 0, metadata,
                            "The run has started; this report is not final yet. Domains not shown have not run yet.")
    print("  Live HTML report:", report_path, flush=True)

    for did, dinfo in report_domains().items():
        print("\n> Domain %s: %s" % (did, dinfo["name"]))
        runs = []
        for marker in dinfo.get("markers", ("success", "negative")):
            print("  + Running %s tests ..." % marker.upper(), end=" ", flush=True)
            timeout = TEST_TIMEOUT_SECONDS
            if (marker == 'negative' and '4_bagging' in dinfo['folder']
                    and local_setting('QA_POSTAL_FAULT_FIXTURES','false').lower() == 'true'):
                timeout=max(timeout,int(local_setting('REPORT_POSTAL_FAULT_GROUP_TIMEOUT_SECONDS','3600')))
                print('\n    Controlled Postal adapter faults run sequentially and restore QA settings after each case.',flush=True)
            if marker == "negative" and "1_device_lifecycle" in dinfo["folder"]:
                # config sync observes two real default 15-minute configuration syncs.
                # A 600-second kill would abort the test before its precondition.
                timeout = max(timeout, int(2 * float(os.getenv("CONFIG_SYNC_SYNC_WAIT_SECONDS", "960")) + 300))
                print("\n    config sync may wait for two configuration syncs (up to %.0f minutes each)." %
                      (float(os.getenv("CONFIG_SYNC_SYNC_WAIT_SECONDS", "960")) / 60), flush=True)
            run = run_domain(did, dinfo["folder"], marker, timeout=timeout)
            runs.append(run)
            domain_results[did] = combine_results(*runs)
            stopped = run["status"] == "INTERRUPTED"
            note = ("The run stopped early; the numbers are incomplete and the remaining tests and device cleanup are unconfirmed."
                    if stopped else "The run is still going; the current numbers are not final. Domains not shown have not run yet.")
            write_report_checkpoint(report_path, domain_results, ts_display,
                                    round(time.perf_counter()-grand_start, 1), metadata, note)
            print("%dP / %dF / %dE / %dS (%.1fs)" % (run["passed"], run["failed"], run["errors"], run["skipped"], run["elapsed"]))
            if stopped:
                print("  INTERRUPTED. Partial HTML report:", report_path, flush=True)
                return 130

        combined = combine_results(*runs)
        domain_results[did] = combined
        icon = "+" if combined["status"] == "PASSED" else "!"
        print("  Status:", combined["status"])
        print("  [%s] Domain %s Total: %dP / %dF / %dS" % (icon, did, combined["passed"], combined["failed"], combined["skipped"]))

    grand_elapsed = round(time.perf_counter() - grand_start, 1)

    report_path = REPORT_DIR / ("CPS_Full_Report_%s.html" % ts)
    write_report_checkpoint(report_path, domain_results, ts_display, grand_elapsed, metadata)

    t_passed = sum(d["passed"] for d in domain_results.values())
    t_failed = sum(d["failed"] for d in domain_results.values())
    t_skipped = sum(d["skipped"] for d in domain_results.values())
    t_errors = sum(d.get("errors", 0) for d in domain_results.values())
    t_total = t_passed + t_failed + t_skipped + t_errors
    pct = round((t_passed / t_total * 100) if t_total else 0, 1)

    print("\n" + "=" * 60)
    print("  FINAL SUMMARY")
    print("=" * 60)
    print("  Total: %d  |  Passed: %d  |  Failed: %d  |  Errors: %d  |  Skipped: %d" % (t_total, t_passed, t_failed, t_errors, t_skipped))
    print("  Success Rate: %.1f%%  |  Duration: %.1fs" % (pct, grand_elapsed))
    print("  HTML Report:  %s" % report_path)
    print("=" * 60)

    return 0 if all_passed(domain_results) else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
