"""Backend fixture selection for the state-driven EPS-66 tests.

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


Eps66BackendMode = Literal["mock", "core"]


@dataclass(frozen=True)
class Eps66BackendPlan:
    mode: Eps66BackendMode
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


def _mode() -> Eps66BackendMode:
    value = os.getenv("EPS66_BACKEND_MODE", "mock").strip().casefold()
    if value not in {"mock", "core"}:
        raise ValueError(
            "EPS66_BACKEND_MODE must be 'mock' or 'core', "
            f"got {value!r}"
        )
    return value  # type: ignore[return-value]


def build_eps66_backend_plan(
    run_settings: Settings,
) -> Eps66BackendPlan:
    """Return the fixture contract without making any network call."""
    barcodes = (
        run_settings.eps66_same_destination_barcode,
        run_settings.eps66_destination_change_barcode,
        run_settings.eps66_closed_bag_barcode,
        run_settings.eps66_timestamp_barcode,
        run_settings.eps66_retry_barcode,
    )
    mode = _mode()
    if mode == "core":
        if not run_settings.eps66_core_ready:
            raise RuntimeError(
                "EPS-66 Core mode requires EPS66_CORE_READY=1 after the "
                "real Core and local Edge state have been prepared."
            )
        return Eps66BackendPlan(
            mode="core",
            mock_env=(),
            fixture_barcodes=barcodes,
            requires_external_state=True,
            description=(
                "Real Core mode: no Core Mock override is applied; "
                "HistoryRecords and local parcel state must exist externally."
            ),
        )

    origin = run_settings.eps66_origin_code
    destination = run_settings.eps66_initial_destination_code
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
    return Eps66BackendPlan(
        mode="mock",
        mock_env=tuple(mock_env),
        fixture_barcodes=barcodes,
        requires_external_state=True,
        description=(
            "Mock mode: Core HistoryRecords and Postal Success overrides are "
            "required; EdgeParcel/BagCloseAttempt state is created by the flow."
        ),
    )


def eps66_backend_mode() -> Eps66BackendMode:
    """Expose the selected mode for test reporting and skip messages."""
    return _mode()
