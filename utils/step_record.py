"""One shared way for any test to record a step (payload sent / response received) for the QA HTML reports.

    from utils.step_record import record_step
    record_step("Auth 8f1e2b3a", client.last_exchange)      # WebSocket or HTTP client exchange
    record_step("Edge SQLite read", {"request": {...}, "response": [...]})

Prints one `QA_STEP {json}` line that scripts/generate_full_report.py and scripts/generate_two_lines_report.py render as
side-by-side Payload / Response cards. Credentials are masked here (never trust the reader to do it), whatever
REPORT_SHOW_SECRETS says elsewhere.
"""

from __future__ import annotations

import sys

from utils.step_report import exchange_detail, format_detail

SECRET_KEYS = ("token", "password", "secret", "authorization", "apikey", "api_key")


STATUS_WORDS = {"mock", "real", "ok", "failed", "degraded", "unknown", "connected", "disconnected"}


def is_status_value(key, value) -> bool:
    """A dotted dependency name such as postal.rest-token with a plain status word holds no credential."""
    return "." in str(key) and str(value).strip().lower() in STATUS_WORDS


def mask(value):
    """Return a copy with the value of every credential-looking key replaced by <redacted>."""
    if isinstance(value, dict):
        return {key: "<redacted>" if any(name in str(key).lower() for name in SECRET_KEYS) and not is_status_value(key, item)
                else mask(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [mask(item) for item in value]
    return value


def record_step(step: str, exchange: dict) -> None:
    line = "QA_STEP " + format_detail(mask({"step": step, **exchange_detail(exchange)}))
    # A Windows console/pipe can be cp1252: non-ASCII text must not crash the test. backslashreplace emits \uXXXX,
    # which is still valid inside the JSON string the report parser reads.
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    print(line.encode(encoding, errors="backslashreplace").decode(encoding), flush=True)
