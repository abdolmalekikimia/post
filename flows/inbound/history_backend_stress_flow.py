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


def build_history_backend_stress_cases(
    run_settings: Settings = settings,
) -> tuple[InboundStressCase, ...]:
    cases = (
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
            "upstream_rejected", 4,
            lambda _i: InboundStressInput(
                ("100000000000000000000004",)
            ),
            weight=20,
            fixture_required=True,
        ),
        InboundStressCase(
            "upstream_timeout", 0,
            lambda _i: InboundStressInput(
                ("100000000000000000000007",)
            ),
            weight=15,
            fixture_required=True,
        ),
        InboundStressCase(
            "upstream_unavailable", 0,
            lambda _i: InboundStressInput(
                ("100000000000000000000008",)
            ),
            weight=15,
            fixture_required=True,
        ),
    )
    if run_settings.history_backend_stress_fixtures_ready:
        return cases
    return tuple(case for case in cases if not case.fixture_required)


def run_history_backend_stress_flow(
    run_settings: Settings = settings,
) -> InboundStressResult:
    return run_inbound_stress_flow(
        run_settings,
        build_history_backend_stress_cases(run_settings),
        "History Backend stress",
    )
