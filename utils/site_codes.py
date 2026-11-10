from __future__ import annotations

import secrets
from collections.abc import Iterable


VALID_EXCHANGE_CENTER_CODES = (
    "11111",
    "22222",
    "33333",
    "10001",
    "10002",
    "10003",
    "10004",
    "10005",
)


def random_exchange_center_code(
    excluded: Iterable[str] = (),
) -> str:
    """Return one valid exchange-center code, optionally excluding values."""
    excluded_codes = {str(code) for code in excluded}
    candidates = tuple(
        code
        for code in VALID_EXCHANGE_CENTER_CODES
        if code not in excluded_codes
    )
    if not candidates:
        raise ValueError("No valid exchange-center code is available")
    return secrets.choice(candidates)


def configured_or_random_exchange_center_code(
    configured: str | None,
    excluded: Iterable[str] = (),
) -> str:
    """Keep a valid explicit code; replace legacy/invalid values randomly."""
    normalized = str(configured or "").strip()
    excluded_codes = {str(code) for code in excluded}
    if (
        normalized in VALID_EXCHANGE_CENTER_CODES
        and normalized not in excluded_codes
    ):
        return normalized
    return random_exchange_center_code(excluded_codes)
