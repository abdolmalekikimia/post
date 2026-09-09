from __future__ import annotations

from dataclasses import replace
from typing import Any

from config.settings import Settings, settings
from flows.bag.eps76_negative_flow import (
    Eps76Result,
    run_eps76_negative_flow,
)
from flows.bag.eps79_negative_flow import (
    Eps79Result,
    run_eps79_negative_flow,
)
from flows.bag.eps87_response_flow import (
    Eps87Result,
    run_eps87_response_flow,
)
from flows.bag.eps89_audit_flow import (
    Eps89Result,
    run_eps89_audit_flow,
)
from flows.success.task_success_flows import (
    BagSuccessResult,
    run_bag_success_flow,
)


PACKING_EPS = ("EPS-76", "EPS-79", "EPS-87", "EPS-89")


def run_packing_success_flow(
    eps: str,
    run_settings: Settings = settings,
) -> BagSuccessResult:
    """Run the common successful RegisterInbound → assign → bag.close path."""
    normalized = eps.upper()
    configurations = {
        "EPS-76": (
            run_settings.eps76_destination_code,
            run_settings.eps76_barcode_prefix,
            run_settings.eps76_default_chute,
            False,
        ),
        "EPS-79": (
            run_settings.eps79_destination_code,
            run_settings.eps79_barcode_prefix,
            run_settings.eps79_chute,
            False,
        ),
        "EPS-87": (
            run_settings.eps87_destination_code,
            run_settings.eps87_barcode_prefix,
            run_settings.eps87_chute,
            True,
        ),
        "EPS-89": (
            run_settings.eps89_destination_code,
            run_settings.eps89_barcode_prefix,
            run_settings.eps89_chute,
            False,
        ),
    }
    if normalized not in configurations:
        available = ", ".join(PACKING_EPS)
        raise ValueError(f"Unknown packing EPS {eps!r}; available: {available}")

    destination, barcode_prefix, chute, require_identity = configurations[normalized]
    return run_bag_success_flow(
        normalized,
        run_settings,
        destination=destination,
        barcode_prefix=barcode_prefix,
        chute=chute,
        require_identity=require_identity,
    )


def run_packing_negative_flow(
    eps: str,
    run_settings: Settings = settings,
) -> Eps76Result | Eps79Result | Eps87Result | Eps89Result:
    """Dispatch one EPS-specific negative packing contract flow."""
    normalized = eps.upper()
    if normalized == "EPS-76":
        return run_eps76_negative_flow(run_settings)
    if normalized == "EPS-79":
        return run_eps79_negative_flow(run_settings)
    if normalized == "EPS-87":
        return run_eps87_response_flow(run_settings)
    if normalized == "EPS-89":
        return run_eps89_audit_flow(run_settings)

    available = ", ".join(PACKING_EPS)
    raise ValueError(f"Unknown packing EPS {eps!r}; available: {available}")


def packing_negative_settings(
    eps: str,
    case: str,
    run_settings: Settings = settings,
) -> Settings:
    """Select a case without mutating the process-wide settings object."""
    normalized = eps.upper()
    fields: dict[str, Any] = {
        "EPS-76": {"eps76_case": case},
        "EPS-79": {"eps79_case": case},
        "EPS-87": {"eps87_case": case},
        "EPS-89": {"eps89_case": case},
    }
    if normalized not in fields:
        available = ", ".join(PACKING_EPS)
        raise ValueError(f"Unknown packing EPS {eps!r}; available: {available}")
    return replace(run_settings, **fields[normalized])
