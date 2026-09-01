from __future__ import annotations

from config.settings import Settings


def numeric_barcode(
    configured_barcode: str,
    run_settings: Settings,
    slot: int = 0,
) -> str:
    """Return a valid 24-digit barcode, unique when run data is enabled."""
    if not run_settings.unique_run_data:
        return configured_barcode

    digits = "".join(character for character in configured_barcode if character.isdigit())
    prefix = digits[:18].ljust(18, "0")
    try:
        seed = int(run_settings.test_run_id)
    except ValueError:
        seed = 100_000
    suffix = (seed + slot) % 1_000_000
    return f"{prefix}{suffix:06d}"
