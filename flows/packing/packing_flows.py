from __future__ import annotations

from dataclasses import replace
from typing import Any

from config.settings import Settings, settings
from flows.bag.bag_selection_negative_flow import (
    BagSelectionResult,
    run_bag_selection_negative_flow,
)
from flows.bag.export_before_container_negative_flow import (
    ExportBeforeContainerResult,
    run_export_before_container_negative_flow,
)
from flows.bag.container_response_contract_flow import (
    ContainerResponseResult,
    run_container_response_flow,
)
from flows.bag.physical_container_audit_flow import (
    PhysicalContainerAuditResult,
    run_physical_container_audit_flow,
)
from flows.success.task_success_flows import (
    BagSuccessResult,
    run_bag_success_flow,
)


PACKING_EPS = ("Container Selection", "Export Before Container", "Container Response", "Physical Container Audit")


def run_packing_success_flow(
    eps: str,
    run_settings: Settings = settings,
) -> BagSuccessResult:
    """Run the common successful RegisterItem → assign → container.close path."""
    normalized = eps.upper()
    configurations = {
        "Container Selection": (
            run_settings.container_selection_destination_code,
            run_settings.container_selection_barcode_prefix,
            run_settings.container_selection_default_chute,
            False,
        ),
        "Export Before Container": (
            run_settings.export_before_container_destination_code,
            run_settings.export_before_container_barcode_prefix,
            run_settings.export_before_container_chute,
            False,
        ),
        "Container Response": (
            run_settings.container_response_destination_code,
            run_settings.container_response_barcode_prefix,
            run_settings.container_response_chute,
            True,
        ),
        "Physical Container Audit": (
            run_settings.physical_container_audit_destination_code,
            run_settings.physical_container_audit_barcode_prefix,
            run_settings.physical_container_audit_chute,
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
) -> BagSelectionResult | ExportBeforeContainerResult | ContainerResponseResult | PhysicalContainerAuditResult:
    """Dispatch one EPS-specific negative packing contract flow."""
    normalized = eps.upper()
    if normalized == "Container Selection":
        return run_bag_selection_negative_flow(run_settings)
    if normalized == "Export Before Container":
        return run_export_before_container_negative_flow(run_settings)
    if normalized == "Container Response":
        return run_container_response_flow(run_settings)
    if normalized == "Physical Container Audit":
        return run_physical_container_audit_flow(run_settings)

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
        "Container Selection": {"container_selection_case": case},
        "Export Before Container": {"export_before_container_case": case},
        "Container Response": {"container_response_case": case},
        "Physical Container Audit": {"physical_container_audit_case": case},
    }
    if normalized not in fields:
        available = ", ".join(PACKING_EPS)
        raise ValueError(f"Unknown packing EPS {eps!r}; available: {available}")
    return replace(run_settings, **fields[normalized])
