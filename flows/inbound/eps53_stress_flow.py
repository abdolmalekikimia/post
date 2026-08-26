from __future__ import annotations

from config.settings import Settings, settings
from flows.inbound.stress_flow import (
    InboundStressCase,
    InboundStressInput,
    InboundStressResult,
    run_inbound_stress_flow,
)


def barcode24(prefix: str, iteration: int) -> str:
    digits = "".join(character for character in prefix if character.isdigit())
    return (digits + str(iteration).zfill(24))[-24:]


def build_eps53_stress_cases() -> tuple[InboundStressCase, ...]:
    return (
        InboundStressCase(
            "invalid_barcode", 2,
            lambda i: InboundStressInput((f"bad-{i}",)), weight=30,
        ),
        InboundStressCase(
            "negative_weight", 2,
            lambda i: InboundStressInput(
                (barcode24("10000", i),),
                {"weightGrams": -1, "dimensions": None},
            ),
            weight=10,
        ),
        InboundStressCase(
            "invalid_dimensions", 2,
            lambda i: InboundStressInput(
                (barcode24("10000", i),),
                {"weightGrams": 1500, "dimensions": {"lengthMm": -1}},
            ),
            weight=10,
        ),
        InboundStressCase(
            "core_rejected", 4,
            lambda i: InboundStressInput((barcode24("10004", i),)),
            weight=20,
        ),
        InboundStressCase(
            "core_timeout", 0,
            lambda i: InboundStressInput((barcode24("10007", i),)),
            weight=15,
        ),
        InboundStressCase(
            "core_unavailable", 0,
            lambda i: InboundStressInput((barcode24("10008", i),)),
            weight=15,
        ),
    )


def run_eps53_stress_flow(
    run_settings: Settings = settings,
) -> InboundStressResult:
    return run_inbound_stress_flow(
        run_settings, build_eps53_stress_cases(), "EPS-53 stress"
    )
