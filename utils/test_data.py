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


def generate_dynamic_barcode_24(prefix: str = "590001", slot: int = 0) -> str:
    """Generate a valid, globally unique 24-digit numeric postal barcode with Luhn check digit."""
    clean_prefix = "".join(c for c in prefix if c.isdigit())[:6] or "590001"
    # 6 digits prefix + 12 digits timestamp/seed + 5 digits random/slot = 23 digits
    timestamp_part = str(int(time.time() * 1000) % 1_000_000_000_000).zfill(12)
    uuid_part = str((uuid.uuid4().int + slot) % 100_000).zfill(5)
    first_23 = f"{clean_prefix}{timestamp_part}{uuid_part}"[:23]
    check = calculate_luhn_mod10(first_23)
    return f"{first_23}{check}"


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
