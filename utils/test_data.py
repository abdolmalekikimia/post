from __future__ import annotations

import time
import uuid
import random
from config.settings import Settings, settings


def generate_dynamic_ip() -> str:
    """Generate a dynamic IP address in format 10.x.x.x"""
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def calculate_luhn_mod10(first_23_digits: str) -> int:
    """Calculate Luhn / Modulo-10 check digit for the 24th digit of a postal barcode."""
    digits = [int(d) for d in first_23_digits if d.isdigit()]
    for i in range(len(digits) - 1, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    total = sum(digits)
    return (10 - (total % 10)) % 10


def generate_dynamic_barcode_24(prefix: str = "590001", slot: int = 0,
                                service_code: str = "01") -> str:
    """Generate a unique 24-digit barcode with service suffix and Luhn check digit.

    Edge interprets the final two digits as a postal service code. The final
    digit also serves as the Luhn check digit, so the preceding variable digit
    is selected to satisfy both constraints. ``01`` is the default positive
    test service; callers may explicitly choose another code for negative cases.
    """
    digits_prefix = "".join(c for c in prefix if c.isascii() and c.isdigit())[:6]
    clean_prefix = digits_prefix.ljust(6, "0") if digits_prefix else "590001"
    # 6 prefix + 12 timestamp + 3 random = 21 digits. One more digit is
    # chosen to make the two-digit service suffix pass Luhn validation.
    timestamp_part = str(int(time.time() * 1000) % 1_000_000_000_000).zfill(12)
    uuid_part = str((uuid.uuid4().int + slot) % 1_000).zfill(3)
    first_21 = f"{clean_prefix}{timestamp_part}{uuid_part}"[:21]
    return complete_postal_barcode_24(first_21, service_code)


def complete_postal_barcode_24(first_21: str, service_code: str = "01") -> str:
    """Keep a 21-digit fixture identity while adding a valid service and check digit."""
    if len(first_21) != 21 or not first_21.isascii() or not first_21.isdigit():
        raise ValueError("first_21 must contain exactly 21 ASCII digits")
    if len(service_code) != 2 or not service_code.isascii() or not service_code.isdigit():
        raise ValueError("service_code must contain exactly two ASCII digits")
    for digit in "0123456789":
        first_23 = first_21 + digit + service_code[0]
        if calculate_luhn_mod10(first_23) == int(service_code[1]):
            return first_23 + service_code[1]
    raise AssertionError("No Luhn-compatible barcode could be generated")


def reread_runtime_barcode(base: str, test_run_id: str, unique_run_data: bool) -> str:
    """Derive the same service-valid reread barcode for flow and fixture plan."""
    if not unique_run_data:
        return base
    if len(base) != 24 or not base.isascii() or not base.isdigit():
        raise ValueError("reread fixture barcode must be 24 ASCII digits")
    run_digits = "".join(char for char in test_run_id if char.isascii() and char.isdigit())[-6:].zfill(6)
    first_21 = base[:13] + run_digits + base[-2:]
    return complete_postal_barcode_24(first_21)


def generate_discrepancies_fixture_barcode(sequence: int) -> str:
    """Build one of Core's synthetic discrepancies/related item fixture barcodes.

    The Core test data uses a four-digit sequence for exchange center 59544.
    Odd sequences represent weight discrepancies and even sequences represent
    box-size discrepancies. These are synthetic test identifiers, not customer
    tracking numbers.
    """
    if not 1 <= sequence <= 9999:
        raise ValueError("discrepancies fixture sequence must be between 1 and 9999")
    barcode = f"59544262718{sequence:04d}866789001"
    if len(barcode) != 24 or not barcode.isdigit():
        raise AssertionError(f"Invalid discrepancies fixture barcode: {barcode!r}")
    return barcode


def generate_dynamic_barcode_14(prefix: str = "14", slot: int = 0) -> str:
    """Generate a valid, unique 14-digit numeric barcode."""
    clean_prefix = "".join(c for c in prefix if c.isdigit())[:2] or "14"
    timestamp_part = str(int(time.time() * 1000) % 100_000_000).zfill(8)
    uuid_part = str((uuid.uuid4().int + slot) % 10_000).zfill(4)
    return f"{clean_prefix}{timestamp_part}{uuid_part}"[:14]


def generate_dynamic_barcode_37(b24: str | None = None, slot: int = 0) -> str:
    """Generate a valid 37-digit barcode whose first 24 digits match b24."""
    base_24 = b24 or generate_dynamic_barcode_24(slot=slot)
    suffix_13 = str((uuid.uuid4().int + slot) % 10_000_000_000_000).zfill(13)
    return f"{base_24}{suffix_13}"[:37]


def generate_dynamic_bag_barcode(center_code: str = "59544", slot: int = 0) -> str:
    """Generate a valid 24-digit bag barcode."""
    return generate_dynamic_barcode_24(prefix=f"67{center_code[:4]}", slot=slot)


def choose_provisioned_barcode(configured: str) -> str:
    """Pick a random barcode only from the Core history fixtures provisioned for a status.

    Comma-separated values let QA use a larger fixture pool without expecting
    a newly generated barcode to have a Returning/Rejected Core history.
    """
    candidates = [value.strip() for value in configured.split(",") if value.strip()]
    if not candidates or any(len(value) != 24 or not value.isascii() or not value.isdigit()
                             for value in candidates):
        raise ValueError("Core history fixture pool must contain 24-digit ASCII barcodes")
    # The deployed Edge in this QA environment accepts 01/02 for these fixtures.
    # Reject stale 87/88 values before they create a misleading related item failure.
    unsupported = [value for value in candidates if value[-2:] not in {"01", "02"}]
    if unsupported:
        raise ValueError("Core history fixture barcode must use an Edge-supported service code (01 or 02): "
                         + ", ".join(unsupported))
    return random.choice(candidates)


def generate_correlation_id(prefix: str = "corr") -> str:
    """Generate a fresh standard UUID v4 correlation ID for request tracing."""
    return str(uuid.uuid4())


def generate_idempotency_key(prefix: str = "idem") -> str:
    """Generate a fresh unique idempotency key."""
    return f"{prefix}-{uuid.uuid4().hex}"


def numeric_barcode(
    configured_barcode: str,
    run_settings: Settings | None = None,
    slot: int = 0,
) -> str:
    """Return a valid 24-digit barcode, dynamically generated and unique per run."""
    effective_settings = run_settings or settings
    if not effective_settings.unique_run_data:
        digits = "".join(c for c in configured_barcode if c.isdigit())
        if len(digits) == 24:
            return digits
        base = digits.ljust(24, "0")[:23]
        return f"{base}{calculate_luhn_mod10(base)}"

    digits = "".join(character for character in configured_barcode if character.isdigit())
    prefix = digits[:6].ljust(6, "0") if digits else "590001"
    return generate_dynamic_barcode_24(prefix=prefix, slot=slot)


def fixture_or_generated_barcode(
    configured_barcode: str,
    run_settings: Settings,
    prefix: str,
    slot: int,
) -> str:
    """Keep configured mock trigger barcodes stable; generate setup data otherwise."""
    if configured_barcode:
        return configured_barcode
    return numeric_barcode(prefix, run_settings, slot=slot)


def generated_barcode(
    prefix: str,
    run_settings: Settings,
    slot: int,
) -> str:
    return numeric_barcode(prefix, run_settings, slot=slot)
