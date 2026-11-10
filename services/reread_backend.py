"""Backend fixture selection for the state-driven reread tests.

The device flow is deliberately identical in Mock and Core modes.  Only the
fixture preparation changes: Mock mode documents the Core Mock overrides that
must be active, while Core mode assumes that the real Core has been prepared
by the environment owner.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Literal

from config.settings import Settings


RereadBackendMode = Literal["mock", "core"]


@dataclass(frozen=True)
class RereadBackendPlan:
    mode: RereadBackendMode
    mock_env: tuple[str, ...]
    fixture_barcodes: tuple[str, ...]
    requires_external_state: bool
    description: str

    @property
    def is_mock(self) -> bool:
        return self.mode == "mock"

    @property
    def is_core(self) -> bool:
        return self.mode == "core"


def _mode() -> RereadBackendMode:
    value = os.getenv("REREAD_BACKEND_MODE", "mock").strip().casefold()
    if value not in {"mock", "core"}:
        raise ValueError(
            "REREAD_BACKEND_MODE must be 'mock' or 'core', "
            f"got {value!r}"
        )
    return value  # type: ignore[return-value]


def build_reread_backend_plan(
    run_settings: Settings,
) -> RereadBackendPlan:
    """Return the fixture contract without making any network call."""
    barcodes = (
        run_settings.reread_same_destination_barcode,
        run_settings.reread_destination_change_barcode,
        run_settings.reread_closed_bag_barcode,
        run_settings.reread_timestamp_barcode,
        run_settings.reread_retry_barcode,
    )
    mode = _mode()
    if mode == "core":
        if not run_settings.reread_core_ready:
            raise RuntimeError(
                "reread Core mode requires REREAD_CORE_READY=1 after the "
                "real Core and local Edge state have been prepared."
            )
        return RereadBackendPlan(
            mode="core",
            mock_env=(),
            fixture_barcodes=barcodes,
            requires_external_state=True,
            description=(
                "Real Core mode: no Core Mock override is applied; "
                "HistoryRecords and local parcel state must exist externally."
            ),
        )

    origin = run_settings.reread_origin_code
    destination = run_settings.reread_initial_destination_code
    mock_env: list[str] = []
    for barcode in barcodes:
        mock_env.extend(
            (
                f"Integrations__CoreApi__Mock__HistoryRecords__{barcode}__Status=Success",
                f"Integrations__CoreApi__Mock__HistoryRecords__{barcode}__RecordedOriginCode={origin}",
                f"Integrations__CoreApi__Mock__HistoryRecords__{barcode}__RecordedDestinationCode={destination}",
            )
        )
    mock_env.extend(
        (
            "Integrations__CoreApi__Mock__Scenario=Success",
            "Integrations__PostalApi__Mock__Scenario=Success",
        )
    )
    return RereadBackendPlan(
        mode="mock",
        mock_env=tuple(mock_env),
        fixture_barcodes=barcodes,
        requires_external_state=True,
        description=(
            "Mock mode: Core HistoryRecords and Postal Success overrides are "
            "required; EdgeParcel/BagCloseAttempt state is created by the flow."
        ),
    )


def reread_backend_mode() -> RereadBackendMode:
    """Expose the selected mode for test reporting and skip messages."""
    return _mode()
