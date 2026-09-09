from __future__ import annotations

from typing import Optional

from application.queries.get_bootstrap import GetBootstrapQuery, BootstrapDTO
from domain.bootstrap_config.repositories import ConfigurationSnapshotRepository
from domain.bootstrap_config.value_objects import PublicationStatus


class GetBootstrapHandler:
    """
    Handler for GetBootstrapQuery.

    Edge devices call this to get their latest published bootstrap configuration.
    Business Rule: Only PUBLISHED snapshots are exposed to Edge.
    """

    def __init__(self, repository: ConfigurationSnapshotRepository):
        self.repository = repository

    def handle(self, query: GetBootstrapQuery) -> Optional[BootstrapDTO]:
        """
        Execute bootstrap query.

        If version is specified, find that specific PUBLISHED snapshot.
        Otherwise, find the latest PUBLISHED snapshot for the center.

        Returns:
            BootstrapDTO if found and published, None otherwise.
        """
        if query.version is not None:
            # Specific version requested
            snapshot = self.repository.find_by_center_and_version(
                query.exchange_center_code,
                query.version,
            )
            if snapshot and snapshot.publication_status == PublicationStatus.PUBLISHED:
                return BootstrapDTO.from_entity(snapshot)
            return None
        else:
            # Latest published requested
            snapshot = self.repository.find_latest_published(query.exchange_center_code)
            if snapshot and snapshot.publication_status == PublicationStatus.PUBLISHED:
                return BootstrapDTO.from_entity(snapshot)
            return None
