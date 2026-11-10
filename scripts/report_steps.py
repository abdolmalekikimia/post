"""Shared rendering of recorded test steps (payload sent / response received) for the QA HTML reports.

Tests print one `TWO_LINES_STEP {json}` (or generic `QA_STEP {json}`) line per step: {step, payloadSent, responseReceived}.
Credentials are masked here as well, regardless of REPORT_SHOW_SECRETS.
"""

from __future__ import annotations

import html
import json
import re

from utils.step_record import SECRET_KEYS, is_status_value, mask  # noqa: F401

STEP_PREFIXES = ("TWO_LINES_STEP ", "QA_STEP ")
_NAMES = r"(?:token|password|secret|authorization|apikey|api_key)"
# JSON ("deviceToken": "...") and Python repr ('deviceToken': '...') forms
_SECRET_JSON = re.compile(r'("[^"\\]*' + _NAMES + r'[^"\\]*"\s*:\s*")((?:[^"\\]|\\.)*)(")', re.IGNORECASE)
_SECRET_REPR = re.compile(r"('[^'\\]*" + _NAMES + r"[^'\\]*'\s*:\s*')((?:[^'\\]|\\.)*)(')", re.IGNORECASE)

STEPS_CSS = """
.steps{margin-top:10px;border:1px solid var(--border);border-radius:8px;padding:8px 10px}
.steps-h{font-size:12px;color:var(--text3);margin-bottom:4px}
details.step{margin:4px 0}.io{display:grid;grid-template-columns:1fr 1fr;gap:10px}
@media(max-width:800px){.io{grid-template-columns:1fr}}
.lbl{font-size:11px;color:var(--accent)}
.steps pre{margin-top:6px;padding:10px;background:#0b1220;border-radius:8px;direction:ltr;text-align:left;
white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;color:var(--text2)}
.tc-card.expanded>.tc-details{display:grid;grid-template-columns:1fr 1fr;gap:0 10px}
.tc-details>*{grid-column:1/-1}
.tc-details>.tc-detail-row:first-child,.tc-details>.tc-detail-row.tc-resp{grid-column:auto}
.tc-details>.tc-detail-row.tc-full{grid-column:1/-1}
@media(max-width:800px){.tc-card.expanded>.tc-details{grid-template-columns:1fr}}
"""


_ANSI = re.compile(r"(?:\x1b|#x1B)\[[0-9;]*m")  # junit xml writes the escape character as the text "#x1B"


def mask_text(text: str) -> str:
    """Hide the value of any JSON key that looks like a credential, inside free text."""
    def hide(match):
        key = match.group(1).rsplit(":", 1)[0].strip().strip("\"'")
        if is_status_value(key, match.group(2)):
            return match.group(0)
        return match.group(1) + "<redacted>" + match.group(3)

    return _SECRET_REPR.sub(hide, _SECRET_JSON.sub(hide, text))


def split_output(text: str) -> tuple[list[dict], str]:
    """TWO_LINES_STEP lines hold {step, payloadSent, responseReceived} (secrets already masked); the rest is plain output."""
    steps, other = [], []
    for line in text.splitlines():
        if line.startswith(STEP_PREFIXES):
            try:
                steps.append(json.loads(line.split(" ", 1)[1]))
                continue
            except ValueError:
                pass
        if line.strip() and "Captured Out" not in line:
            other.append(line)
    waits = [i for i, line in enumerate(other) if line.startswith("QA_INBOUND_WAIT")]
    drop = set(waits[1:-1])  # a countdown line every 2 s: keep the first and the last only
    other = [line for i, line in enumerate(other) if i not in drop]
    # Collapsed in the report; the response of the failing step sits at the end of the flow output, so do not cut it short.
    return steps, mask_text(_ANSI.sub("", "\n".join(other)))[:60000]


def pretty(value) -> str:
    value = mask(value)
    return html.escape(json.dumps(value, ensure_ascii=False, indent=2, default=str)[:6000])


def render_steps(steps: list[dict]) -> str:
    rows = ""
    for number, step in enumerate(steps, start=1):
        rows += (f'<details class="step"><summary><b>{number}. {html.escape(str(step.get("step", "")))}</b></summary>'
                 f'<div class="io"><div><span class="lbl">Payload sent</span><pre>{pretty(step.get("payloadSent"))}</pre></div>'
                 f'<div><span class="lbl">Response received</span><pre>{pretty(step.get("responseReceived"))}</pre></div></div></details>')
    return f'<div class="steps"><div class="steps-h">Steps ({len(steps)}) with payload and response</div>{rows}</div>' if rows else ""
