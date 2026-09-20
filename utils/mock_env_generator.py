"""Mock Environment Variable Generator for Negative Testing (EPS-181).

Generates ASP.NET Core environment variable definitions for Mock CoreApi and PostalApi
services to facilitate negative QA testing (Timeout, Rejected, Unavailable, Invalid Config,
Discrepancy, Inactive Device, Parcel Bag Error).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence


@dataclass(frozen=True)
class NegativeScenarioDefinition:
    scenario_id: str
    name: str
    target_service: str  # "PostalApi" | "CoreApi" | "EdgeConfig"
    category: str        # "timeout", "rejection", "unavailable", "validation", "discrepancy"
    description: str
    expected_edge_status: int
    expected_error_contains: str
    qa_test_data: Dict[str, Any]
    env_vars: Dict[str, str]


class MockEnvGenerator:
    """Generates structured ASP.NET Core environment variables for negative testing."""

    def __init__(self, exchange_center: str = "59544") -> None:
        self.exchange_center = exchange_center

    def generate_all_negative_scenarios(self) -> List[NegativeScenarioDefinition]:
        """Generate definitions and environment variables for all required negative scenarios."""
        scenarios: List[NegativeScenarioDefinition] = []

        # 1. Postal API Timeout (EPS-55 / EPS-60)
        timeout_barcode = "200000000000000000000003"
        scenarios.append(
            NegativeScenarioDefinition(
                scenario_id="NEG-POSTAL-01",
                name="postal_timeout",
                target_service="PostalApi",
                category="timeout",
                description="PostalApi mock simulates upstream HTTP timeout during registration/lookup.",
                expected_edge_status=2,
                expected_error_contains="timeout",
                qa_test_data={"barcode": timeout_barcode, "operation": "inbound.register"},
                env_vars={
                    f"Integrations__PostalApi__Mock__ScenarioOverrides__{timeout_barcode}": "Timeout",
                    "Integrations__PostalApi__RegistrationPolling__TimeoutMs": "2000",
                },
            )
        )

        # 2. Postal API Rejected (EPS-55 / EPS-60)
        rejected_barcode = "200000000000000000000002"
        scenarios.append(
            NegativeScenarioDefinition(
                scenario_id="NEG-POSTAL-02",
                name="postal_rejected",
                target_service="PostalApi",
                category="rejection",
                description="PostalApi mock returns an explicit Rejected response for parcel.",
                expected_edge_status=2,
                expected_error_contains="rejected",
                qa_test_data={"barcode": rejected_barcode, "operation": "inbound.register"},
                env_vars={
                    f"Integrations__PostalApi__Mock__ScenarioOverrides__{rejected_barcode}": "Rejected",
                },
            )
        )

        # 3. Postal API Service Unavailable (EPS-55 / EPS-60)
        unavail_barcode = "200000000000000000000004"
        scenarios.append(
            NegativeScenarioDefinition(
                scenario_id="NEG-POSTAL-03",
                name="postal_unavailable",
                target_service="PostalApi",
                category="unavailable",
                description="PostalApi mock responds with HTTP 503 Service Unavailable.",
                expected_edge_status=2,
                expected_error_contains="unavailable",
                qa_test_data={"barcode": unavail_barcode, "operation": "inbound.register"},
                env_vars={
                    f"Integrations__PostalApi__Mock__ScenarioOverrides__{unavail_barcode}": "Unavailable",
                },
            )
        )

        # 4. Postal API Pending with Resolution Delay (EPS-55 / EPS-60)
        pending_barcode = "200000000000000000000005"
        scenarios.append(
            NegativeScenarioDefinition(
                scenario_id="NEG-POSTAL-04",
                name="postal_pending",
                target_service="PostalApi",
                category="timeout",
                description="PostalApi returns Pending status and resolution exceeds polling window.",
                expected_edge_status=2,
                expected_error_contains="pending",
                qa_test_data={"barcode": pending_barcode, "operation": "inbound.register"},
                env_vars={
                    f"Integrations__PostalApi__Mock__ScenarioOverrides__{pending_barcode}": "Pending",
                    "Integrations__PostalApi__Mock__RegistrationResolutionDelay": "00:00:10",
                    "Integrations__PostalApi__RegistrationPolling__TimeoutMs": "3000",
                },
            )
        )

        # 5. Core History Record: Rejected (EPS-53 / EPS-68)
        core_rej_bc = "100000000000000000000004"
        scenarios.append(
            NegativeScenarioDefinition(
                scenario_id="NEG-CORE-01",
                name="core_history_rejected",
                target_service="CoreApi",
                category="rejection",
                description="Core history record marks parcel as Rejected, forcing refusal destination override.",
                expected_edge_status=2,
                expected_error_contains="rejected",
                qa_test_data={"barcode": core_rej_bc, "originCenter": self.exchange_center},
                env_vars={
                    f"Integrations__CoreApi__Mock__HistoryRecords__{core_rej_bc}__Status": "Rejected",
                    f"Integrations__CoreApi__Mock__HistoryRecords__{core_rej_bc}__RecordedOriginCode": self.exchange_center,
                    f"Integrations__CoreApi__Mock__RefusalDestinationOverrides__{self.exchange_center}": "11369",
                },
            )
        )

        # 6. Core History Record: Timeout (EPS-53)
        core_timeout_bc = "100000000000000000000007"
        scenarios.append(
            NegativeScenarioDefinition(
                scenario_id="NEG-CORE-02",
                name="core_history_timeout",
                target_service="CoreApi",
                category="timeout",
                description="Core history inquiry times out; Edge falls back to local fallback policy.",
                expected_edge_status=2,
                expected_error_contains="timeout",
                qa_test_data={"barcode": core_timeout_bc},
                env_vars={
                    f"Integrations__CoreApi__Mock__ScenarioOverrides__{core_timeout_bc}": "Timeout",
                },
            )
        )

        # 7. Core History Record: Unavailable (EPS-53)
        core_unavail_bc = "100000000000000000000008"
        scenarios.append(
            NegativeScenarioDefinition(
                scenario_id="NEG-CORE-03",
                name="core_history_unavailable",
                target_service="CoreApi",
                category="unavailable",
                description="Core API is unreachable or returns 503; verifies local fallback behavior.",
                expected_edge_status=2,
                expected_error_contains="unavailable",
                qa_test_data={"barcode": core_unavail_bc},
                env_vars={
                    f"Integrations__CoreApi__Mock__ScenarioOverrides__{core_unavail_bc}": "Unavailable",
                },
            )
        )

        # 8. Core History Discrepancy (EPS-53)
        discrepancy_bc = "100000000000000000000002"
        scenarios.append(
            NegativeScenarioDefinition(
                scenario_id="NEG-CORE-04",
                name="core_history_discrepancy",
                target_service="CoreApi",
                category="discrepancy",
                description="Discrepancy detected between measured parcel weight/dimensions and Core history record.",
                expected_edge_status=1,
                expected_error_contains="discrepancy",
                qa_test_data={"barcode": discrepancy_bc, "measuredWeight": 1500, "historyWeight": 500},
                env_vars={
                    f"Integrations__CoreApi__Mock__HistoryRecords__{discrepancy_bc}__Status": "Success",
                    f"Integrations__CoreApi__Mock__HistoryRecords__{discrepancy_bc}__DiscrepancyDetected": "true",
                    f"Integrations__CoreApi__Mock__HistoryRecords__{discrepancy_bc}__DiscrepancyDetails": "weight mismatch",
                    f"Integrations__CoreApi__Mock__HistoryRecords__{discrepancy_bc}__WeightDiscrepancy": "true",
                },
            )
        )

        # 9. AutoDispatchPolicy Invalid Deadline (EPS-46)
        scenarios.append(
            NegativeScenarioDefinition(
                scenario_id="NEG-CONFIG-01",
                name="autodispatch_invalid_deadline",
                target_service="EdgeConfig",
                category="validation",
                description="AutoDispatchPolicy contains negative deadline (-01:00:00); Edge rejects snapshot sync.",
                expected_edge_status=2,
                expected_error_contains="deadline",
                qa_test_data={"centerCode": self.exchange_center, "policy": "AutoDispatchPolicy"},
                env_vars={
                    f"Integrations__CoreApi__Mock__ConfigSnapshots__{self.exchange_center}__AutoDispatchPolicy__IsEnabled": "true",
                    f"Integrations__CoreApi__Mock__ConfigSnapshots__{self.exchange_center}__AutoDispatchPolicy__AllowedDeadline": "-01:00:00",
                },
            )
        )

        # 10. Inactive Device Auth Rejection (EPS-40 / EPS-49)
        inactive_device_id = "EPS40-INACTIVE-001"
        scenarios.append(
            NegativeScenarioDefinition(
                scenario_id="NEG-AUTH-01",
                name="device_inactive",
                target_service="EdgeConfig",
                category="validation",
                description="Inactive device attempts authentication; connection is rejected with 403/Unauthorized.",
                expected_edge_status=2,
                expected_error_contains="inactive",
                qa_test_data={"deviceId": inactive_device_id, "token": "eps40-inactive-token"},
                env_vars={
                    f"Integrations__CoreApi__Mock__ConfigSnapshots__{self.exchange_center}__Devices__1__DeviceId": inactive_device_id,
                    f"Integrations__CoreApi__Mock__ConfigSnapshots__{self.exchange_center}__Devices__1__DeviceToken": "eps40-inactive-token",
                    f"Integrations__CoreApi__Mock__ConfigSnapshots__{self.exchange_center}__Devices__1__ActivationStatus": "Inactive",
                },
            )
        )

        # 11. Bag Parcel Error Override (EPS-79 / EPS-87 / EPS-89)
        error_bag_bc = "790000000000000000000001"
        scenarios.append(
            NegativeScenarioDefinition(
                scenario_id="NEG-BAG-01",
                name="parcel_bag_error",
                target_service="PostalApi",
                category="validation",
                description="Parcel marked with ParcelErrorOverrides in mock postal causes bag.close failure.",
                expected_edge_status=2,
                expected_error_contains="parcel error",
                qa_test_data={"bagBarcode": "BAG-001", "failedParcelBarcode": error_bag_bc},
                env_vars={
                    f"Integrations__PostalApi__Mock__ParcelErrorOverrides__{error_bag_bc}": "true",
                },
            )
        )

        return scenarios

    def get_profile_dict(self) -> Dict[str, Dict[str, str]]:
        """Return a mapping of profile_name -> env_vars dict."""
        scenarios = self.generate_all_negative_scenarios()
        return {s.name: s.env_vars for s in scenarios}

    def render_env_file(self, scenario_name: str | None = None) -> str:
        """Render environment variables as .env formatted text."""
        scenarios = self.generate_all_negative_scenarios()
        if scenario_name:
            scenarios = [s for s in scenarios if s.name == scenario_name]
            if not scenarios:
                raise ValueError(f"Unknown negative scenario '{scenario_name}'")

        lines: List[str] = [
            "# ===========================================================================",
            "# ASP.NET Core Mock Environment Variables for Negative Testing (EPS-181)",
            "# Apply to Edge / Backend Mock Service and restart to activate.",
            "# ===========================================================================",
            "",
        ]

        for s in scenarios:
            lines.append(f"# ---------------------------------------------------------------------------")
            lines.append(f"# [{s.scenario_id}] {s.name} ({s.target_service} / {s.category})")
            lines.append(f"# Description: {s.description}")
            lines.append(f"# Expected: status={s.expected_edge_status}, error contains '{s.expected_error_contains}'")
            lines.append(f"# ---------------------------------------------------------------------------")
            for k, v in s.env_vars.items():
                lines.append(f"{k}={v}")
            lines.append("")

        return "\n".join(lines)
