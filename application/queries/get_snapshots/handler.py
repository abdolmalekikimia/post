from __future__ import annotations

from typing import Sequence

from application.queries.get_snapshots import GetSnapshotsQuery, SnapshotSummaryDTO
from domain.bootstrap_config.repositories import ConfigurationSnapshotRepository


class GetSnapshotsHandler:
    """
    Handler for GetSnapshotsQuery (admin-facing).

    Returns paged snapshot summaries ordered by generated_at_utc DESC.
    """

    def __init__(self, repository: ConfigurationSnapshotRepository):
        self.repository = repository

    def handle(self, query: GetSnapshotsQuery) -> tuple[list[SnapshotSummaryDTO], int]:
        """
        Execute snapshots list query.

        Returns:
            (items, total_count) where items are SnapshotSummaryDTOs.
        """
        entities, total_count = self.repository.find_all(
            center_code=query.exchange_center_code,
            status=query.status,
            page=query.page,
            page_size=query.page_size,
        )
        items = [SnapshotSummaryDTO.from_entity(e) for e in entities]
        return items, total_count
