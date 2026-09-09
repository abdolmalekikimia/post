from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from application.commands.create_snapshot import CreateSnapshotCommand, CreateSnapshotResult
from application.commands.create_snapshot.validator import CreateSnapshotValidator
from application.ports import EventPublisherPort
from domain.bootstrap_config.entities import ConfigurationSnapshot
from domain.bootstrap_config.events import ConfigurationSnapshotCreated
from domain.bootstrap_config.repositories import ConfigurationSnapshotRepository
from domain.bootstrap_config.exceptions import (
    BootstrapConfigDomainError,
    DuplicateSnapshotVersionError,
    InvalidExchangeCenterCodeError,
    SnapshotValidationError,
)
from domain.bootstrap_config.value_objects import (
    ConfigVersion,
    CorrelationId,
)


@dataclass
class CreateSnapshotHandler:
    """
    Handler for CreateSnapshotCommand.

    Responsibilities:
    1. Validate command (via validator)
    2. Get next version for exchange center
    3. Create new ConfigurationSnapshot entity (factory method)
    4. Save to repository
    5. Publish domain event (async)

    Returns CreateSnapshotResult with snapshot_id on success.
    """
    repository: ConfigurationSnapshotRepository
    event_publisher: EventPublisherPort

    async def handle(self, command: CreateSnapshotCommand) -> CreateSnapshotResult:
        try:
            # 1. Validate command
            CreateSnapshotValidator.validate_and_raise(command)

            # 2. Get next version for center
            current_max = self.repository.get_max_version(command.exchange_center_code)
            next_version = current_max.next() if current_max is not None else ConfigVersion(1)

            # 3. Create new snapshot entity (Draft)
            snapshot = ConfigurationSnapshot.create_new(
                exchange_center_code=command.exchange_center_code,
                devices=command.devices,
                operational_settings=command.operational_settings,
                routing_codes=command.routing_codes,
                metadata=command.metadata,
                next_version=next_version,
                correlation_id=command.correlation_id,
            )

            # 4. Save to repository
            self.repository.save(snapshot)

            # 5. Publish domain event
            event = ConfigurationSnapshotCreated(
                snapshot_id=str(snapshot.snapshot_id),
                exchange_center_code=str(snapshot.exchange_center_code),
                config_version=int(snapshot.config_version),
                publication_status=snapshot.publication_status.value,
                created_by=command.metadata.created_by,
                correlation_id=str(command.correlation_id),
                devices_count=len(command.devices),
                generated_at_utc=snapshot.generated_at_utc,
            )
            await self.event_publisher.publish(event)

            # 6. Return success result
            return CreateSnapshotResult(
                snapshot_id=str(snapshot.snapshot_id),
                config_version=int(snapshot.config_version),
                exchange_center_code=str(snapshot.exchange_center_code),
                publication_status=snapshot.publication_status.value,
                generated_at_utc=snapshot.generated_at_utc.isoformat(),
                success=True,
            )

        except SnapshotValidationError as e:
            return CreateSnapshotResult(
                snapshot_id="",
                config_version=0,
                exchange_center_code="",
                publication_status="Draft",
                generated_at_utc="",
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )

        except DuplicateSnapshotVersionError as e:
            return CreateSnapshotResult(
                snapshot_id="",
                config_version=e.version,
                exchange_center_code=e.center_code,
                publication_status="Draft",
                generated_at_utc="",
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )

        except InvalidExchangeCenterCodeError as e:
            return CreateSnapshotResult(
                snapshot_id="",
                config_version=0,
                exchange_center_code=e.center_code,
                publication_status="Draft",
                generated_at_utc="",
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )

        except BootstrapConfigDomainError as e:
            return CreateSnapshotResult(
                snapshot_id="",
                config_version=0,
                exchange_center_code="",
                publication_status="Draft",
                generated_at_utc="",
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )

        except Exception as e:
            return CreateSnapshotResult(
                snapshot_id="",
                config_version=0,
                exchange_center_code="",
                publication_status="Draft",
                generated_at_utc="",
                success=False,
                error_code="INTERNAL_ERROR",
                error_message=f"Unexpected error: {type(e).__name__}: {e}",
            )