from __future__ import annotations

from config.settings import Settings, settings
from flows.inbound.eps53_stress_flow import barcode24
from flows.inbound.stress_flow import (
    InboundStressCase,
    InboundStressInput,
    InboundStressResult,
    run_inbound_stress_flow,
)


def barcode14(iteration: int) -> str:
    return barcode24("", iteration)[-14:]


def build_eps55_stress_cases() -> tuple[InboundStressCase, ...]:
    return (
        InboundStressCase(
            "barcode_mismatch", 2,
            lambda i: InboundStressInput(
                (barcode24("30000", i), barcode24("99999", i)),
            ),
            weight=20,
        ),
        InboundStressCase(
            "postal_rejected", 2,
            lambda i: InboundStressInput((barcode24("20002", i),)),
            weight=20,
        ),
        InboundStressCase(
            "postal_timeout", 2,
            lambda i: InboundStressInput((barcode24("20003", i),)),
            weight=15,
        ),
        InboundStressCase(
            "postal_unavailable", 2,
            lambda i: InboundStressInput((barcode24("20004", i),)),
            weight=15,
        ),
        InboundStressCase(
            "destination_error", 2,
            lambda i: InboundStressInput((barcode14(i),)),
            weight=15,
        ),
        InboundStressCase(
            "returning", 3,
            lambda i: InboundStressInput((barcode14(i),)),
            weight=15,
        ),
    )


def run_eps55_stress_flow(
    run_settings: Settings = settings,
) -> InboundStressResult:
    return run_inbound_stress_flow(
        run_settings, build_eps55_stress_cases(), "EPS-55 stress"
    )
