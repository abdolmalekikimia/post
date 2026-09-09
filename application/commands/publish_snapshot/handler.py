from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from application.commands.publish_snapshot import PublishSnapshotCommand, PublishSnapshotResult
from application.ports import EventPublisherPort
from domain.bootstrap_config.entities import ConfigurationSnapshot
from domain.bootstrap_config.events import (
    ConfigurationSnapshotPublished,
    ConfigurationSnapshotArchived,
)
from domain.bootstrap_config.repositories import ConfigurationSnapshotRepository
from domain.bootstrap_config.exceptions import (
    BootstrapConfigDomainError,
    SnapshotNotFoundError,
    SnapshotAlreadyPublishedError,
    SnapshotCannotBeModifiedError,
)
from domain.bootstrap_config.value_objects import PublicationStatus


@dataclass
class PublishSnapshotHandler:
    """
    Handler for PublishSnapshotCommand.

    Business Rule: Only one PUBLISHED snapshot per exchange center.
    When publishing a new snapshot:
    1. Archive the currently published snapshot (if any) for that center
    2. Mark the target snapshot as PUBLISHED
    3. Publish domain events for both transitions
    """
    repository: ConfigurationSnapshotRepository
    event_publisher: EventPublisherPort

    async def handle(self, command: PublishSnapshotCommand) -> PublishSnapshotResult:
        try:
            # 1. Find the snapshot to publish
            snapshot = self.repository.find_by_id(command.snapshot_id)
            if not snapshot:
                raise SnapshotNotFoundError(str(command.snapshot_id))

            # 2. Check if already published
            if snapshot.publication_status == PublicationStatus.PUBLISHED:
                raise SnapshotAlreadyPublishedError(str(command.snapshot_id))

            # 3. Archive currently published snapshot for this center (if different)
            existing_published = self.repository.find_latest_published(snapshot.exchange_center_code)
            if existing_published and existing_published.snapshot_id != snapshot.snapshot_id:
                # Archive the old published snapshot
                archived_snapshot = existing_published.archive()
                self.repository.update(archived_snapshot)

                # Publish Archived event
                archived_event = ConfigurationSnapshotArchived(
                    snapshot_id=str(existing_published.snapshot_id),
                    exchange_center_code=str(existing_published.exchange_center_code),
                    config_version=int(existing_published.config_version),
                    archived_at_utc=datetime.now(timezone.utc),
                )
                await self.event_publisher.publish(archived_event)

            # 4. Publish the target snapshot
            published_snapshot = snapshot.publish()
            self.repository.update(published_snapshot)

            # 5. Publish Published event
            published_event = ConfigurationSnapshotPublished(
                snapshot_id=str(published_snapshot.snapshot_id),
                exchange_center_code=str(published_snapshot.exchange_center_code),
                config_version=int(published_snapshot.config_version),
                published_by=command.published_by,
                correlation_id=str(command.correlation_id),
                published_at_utc=published_snapshot.published_at_utc,
                previous_published_version=(
                    int(existing_published.config_version)
                    if existing_published
                    else None
                ),
            )
            await self.event_publisher.publish(published_event)

            # 6. Return success result
            return PublishSnapshotResult(
                snapshot_id=str(published_snapshot.snapshot_id),
                config_version=int(published_snapshot.config_version),
                exchange_center_code=str(published_snapshot.exchange_center_code),
                publication_status=published_snapshot.publication_status.value,
                published_at_utc=published_snapshot.published_at_utc.isoformat(),
                success=True,
            )

        except SnapshotNotFoundError as e:
            return PublishSnapshotResult(
                snapshot_id="",
                config_version=0,
                exchange_center_code="",
                publication_status="Draft",
                published_at_utc="",
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )

        except SnapshotAlreadyPublishedError as e:
            return PublishSnapshotResult(
                snapshot_id=e.snapshot_id,
                config_version=0,
                exchange_center_code="",
                publication_status="Published",
                published_at_utc="",
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )

        except SnapshotCannotBeModifiedError as e:
            return PublishSnapshotResult(
                snapshot_id="",
                config_version=0,
                exchange_center_code="",
                publication_status="Draft",
                published_at_utc="",
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )

        except BootstrapConfigDomainError as e:
            return PublishSnapshotResult(
                snapshot_id="",
                config_version=0,
                exchange_center_code="",
                publication_status="Draft",
                published_at_utc="",
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )

        except Exception as e:
            return PublishSnapshotResult(
                snapshot_id="",
                config_version=0,
                exchange_center_code="",
                publication_status="Draft",
                published_at_utc="",
                success=False,
                error_code="INTERNAL_ERROR",
                error_message=f"Unexpected error: {type(e).__name__}: {e}",
            )