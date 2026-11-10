from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from domain.bootstrap_config.value_objects import (
    ConfigVersion,
    ExchangeCenterCode,
)
from domain.bootstrap_config.entities import ConfigurationSnapshot


@dataclass(frozen=True)
class GetBootstrapQuery:
    """
    Query from Edge devices to fetch bootstrap configuration.

    If version is None: returns the latest PUBLISHED snapshot.
    If version is provided: returns that specific PUBLISHED snapshot version.
    """
    exchange_center_code: ExchangeCenterCode
    version: Optional[ConfigVersion] = None


@dataclass
class BootstrapDTO:
    """
    DTO for Edge Bootstrap Response (matches real core contract).
    """
    config_version: int
    exchange_center_code: str
    generated_at_utc: str
    published_at_utc: Optional[str]
    devices: list[dict[str, Any]]
    operational_settings: dict[str, Any]
    routing_codes: dict[str, Any]
    metadata: dict[str, Any]

    @classmethod
    def from_entity(cls, entity: ConfigurationSnapshot) -> "BootstrapDTO":
        return cls(
            config_version=int(entity.config_version),
            exchange_center_code=str(entity.exchange_center_code),
            generated_at_utc=entity.generated_at_utc.isoformat().replace("+00:00", "Z"),
            published_at_utc=(
                entity.published_at_utc.isoformat().replace("+00:00", "Z")
                if entity.published_at_utc
                else None
            ),
            devices=[d.to_dict() for d in entity.devices],
            operational_settings=entity.operational_settings.to_dict(),
            routing_codes=entity.routing_codes.to_dict(),
            metadata=entity.metadata.to_dict(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "configVersion": self.config_version,
            "exchangeCenterCode": self.exchange_center_code,
            "generatedAtUtc": self.generated_at_utc,
            "publishedAtUtc": self.published_at_utc,
            "devices": self.devices,
            "operationalSettings": self.operational_settings,
            "routingCodes": self.routing_codes,
            "metadata": self.metadata,
        }


__all__ = [
    "GetBootstrapQuery",
    "BootstrapDTO",
]
