from __future__ import annotations

from dataclasses import replace
from typing import Any

from config.settings import Settings, settings
from flows.bag.bag_selection_negative_flow_v2 import (
    BagSelectionResult,
    run_bag_selection_negative_flow,
)
from flows.bag.export_before_container_negative_flow_v2 import (
    ExportBeforeContainerResult,
    run_export_before_container_negative_flow,
)
from flows.bag.container_response_response_flow import (
    ContainerResponseResult,
    run_container_response_response_flow,
)
from flows.bag.physical_audit_audit_flow import (
    PhysicalAuditResult,
    run_physical_audit_audit_flow,
)
from flows.success.task_success_flows import (
    BagSuccessResult,
    run_bag_success_flow,
)


PACKING_EPS = ("bag selection", "export before container", "container response", "physical audit")


def run_packing_success_flow(
    eps: str,
    run_settings: Settings = settings,
) -> BagSuccessResult:
    """Run the common successful RegisterInbound → assign → bag.close path."""
    normalized = eps.upper()
    configurations = {
        "bag selection": (
            run_settings.bag_selection_destination_code,
            run_settings.bag_selection_barcode_prefix,
            run_settings.bag_selection_default_chute,
            False,
        ),
        "export before container": (
            run_settings.export_before_container_destination_code,
            run_settings.export_before_container_barcode_prefix,
            run_settings.export_before_container_chute,
            False,
        ),
        "container response": (
            run_settings.container_response_destination_code,
            run_settings.container_response_barcode_prefix,
            run_settings.container_response_chute,
            True,
        ),
        "physical audit": (
            run_settings.physical_audit_destination_code,
            run_settings.physical_audit_barcode_prefix,
            run_settings.physical_audit_chute,
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
) -> BagSelectionResult | ExportBeforeContainerResult | ContainerResponseResult | PhysicalAuditResult:
    """Dispatch one EPS-specific negative packing contract flow."""
    normalized = eps.upper()
    if normalized == "bag selection":
        return run_bag_selection_negative_flow(run_settings)
    if normalized == "export before container":
        return run_export_before_container_negative_flow(run_settings)
    if normalized == "container response":
        return run_container_response_response_flow(run_settings)
    if normalized == "physical audit":
        return run_physical_audit_audit_flow(run_settings)

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
        "bag selection": {"bag_selection_case": case},
        "export before container": {"export_before_container_case": case},
        "container response": {"container_response_case": case},
        "physical audit": {"physical_audit_case": case},
    }
    if normalized not in fields:
        available = ", ".join(PACKING_EPS)
        raise ValueError(f"Unknown packing EPS {eps!r}; available: {available}")
    return replace(run_settings, **fields[normalized])
