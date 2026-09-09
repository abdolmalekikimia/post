from __future__ import annotations

from config.settings import Settings, settings
from flows.inbound.eps53_stress_flow import barcode24
from flows.inbound.stress_flow import (
    InboundStressCase,
    InboundStressInput,
    InboundStressResult,
    run_inbound_stress_flow,
)


def build_eps55_stress_cases(
    run_settings: Settings = settings,
) -> tuple[InboundStressCase, ...]:
    cases = (
        InboundStressCase(
            "barcode_mismatch", 2,
            lambda i: InboundStressInput(
                (barcode24("30000", i), barcode24("99999", i)),
            ),
            weight=20,
        ),
        InboundStressCase(
            "postal_rejected", 2,
            lambda _i: InboundStressInput(
                ("200000000000000000000002",)
            ),
            weight=20,
            fixture_required=True,
        ),
        InboundStressCase(
            "postal_timeout", 2,
            lambda _i: InboundStressInput(
                ("200000000000000000000003",)
            ),
            weight=15,
            fixture_required=True,
        ),
        InboundStressCase(
            "postal_unavailable", 2,
            lambda _i: InboundStressInput(
                ("200000000000000000000004",)
            ),
            weight=15,
            fixture_required=True,
        ),
        InboundStressCase(
            "destination_error", 2,
            lambda _i: InboundStressInput(("20000000000003",)),
            weight=15,
            fixture_required=True,
        ),
        InboundStressCase(
            "returning", 3,
            lambda _i: InboundStressInput(("20000000000006",)),
            weight=15,
            fixture_required=True,
        ),
    )
    if run_settings.eps55_stress_fixtures_ready:
        return cases
    return tuple(case for case in cases if not case.fixture_required)


def run_eps55_stress_flow(
    run_settings: Settings = settings,
) -> InboundStressResult:
    return run_inbound_stress_flow(
        run_settings,
        build_eps55_stress_cases(run_settings),
        "EPS-55 stress",
    )
