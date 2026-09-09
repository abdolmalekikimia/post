from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from domain.bootstrap_config.entities import ConfigurationSnapshot
from domain.bootstrap_config.repositories import ConfigurationSnapshotRepository
from domain.bootstrap_config.value_objects import (
    ConfigVersion,
    ExchangeCenterCode,
    PublicationStatus,
    SnapshotId,
)


class InMemoryConfigurationSnapshotRepository(ConfigurationSnapshotRepository):
    """
    In-Memory implementation for Testing and Development.

    Production should use SqlConfigurationSnapshotRepository.

    Indexes maintained:
    - _by_id: SnapshotId -> ConfigurationSnapshot
    - _by_center_version: (center_code, version) -> ConfigurationSnapshot
    """

    def __init__(self) -> None:
        self._snapshots: dict[str, ConfigurationSnapshot] = {}  # snapshot_id -> snapshot
        self._by_center_version: dict[tuple[str, int], str] = {}  # (center, version) -> snapshot_id

    def _key(self, center_code: ExchangeCenterCode, version: ConfigVersion) -> tuple[str, int]:
        return (str(center_code), int(version))

    def save(self, snapshot: ConfigurationSnapshot) -> None:
        center = str(snapshot.exchange_center_code)
        version = int(snapshot.config_version)
        snapshot_id = str(snapshot.snapshot_id)

        composite = self._key(snapshot.exchange_center_code, snapshot.config_version)
        if composite in self._by_center_version:
            existing_id = self._by_center_version[composite]
            if existing_id != snapshot_id:
                from domain.bootstrap_config.exceptions import DuplicateSnapshotVersionError
                raise DuplicateSnapshotVersionError(center, version)

        self._snapshots[snapshot_id] = snapshot
        self._by_center_version[composite] = snapshot_id

    def update(self, snapshot: ConfigurationSnapshot) -> None:
        snapshot_id = str(snapshot.snapshot_id)
        composite = self._key(snapshot.exchange_center_code, snapshot.config_version)

        if snapshot_id not in self._snapshots:
            from domain.bootstrap_config.exceptions import SnapshotNotFoundError
            raise SnapshotNotFoundError(snapshot_id)

        self._snapshots[snapshot_id] = snapshot
        self._by_center_version[composite] = snapshot_id

    def find_by_id(self, snapshot_id: SnapshotId) -> Optional[ConfigurationSnapshot]:
        return self._snapshots.get(str(snapshot_id))

    def find_by_center_and_version(
        self, center_code: ExchangeCenterCode, version: ConfigVersion
    ) -> Optional[ConfigurationSnapshot]:
        composite = self._key(center_code, version)
        sid = self._by_center_version.get(composite)
        if sid:
            return self._snapshots.get(sid)
        return None

    def find_latest_published(self, center_code: ExchangeCenterCode) -> Optional[ConfigurationSnapshot]:
        center_str = str(center_code)
        published: list[ConfigurationSnapshot] = []

        for snap in self._snapshots.values():
            if str(snap.exchange_center_code) == center_str and snap.publication_status == PublicationStatus.PUBLISHED:
                published.append(snap)

        if not published:
            return None

        published.sort(key=lambda s: int(s.config_version), reverse=True)
        return published[0]

    def find_all_for_center(
        self,
        center_code: ExchangeCenterCode,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[Sequence[ConfigurationSnapshot], int]:
        center_str = str(center_code)
        results = [s for s in self._snapshots.values() if str(s.exchange_center_code) == center_str]
        results.sort(key=lambda s: int(s.config_version), reverse=True)

        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        paged = results[start:end]

        return paged, total

    def find_published_for_center(
        self, center_code: ExchangeCenterCode,
    ) -> Optional[ConfigurationSnapshot]:
        return self.find_latest_published(center_code)

    def find_all(
        self,
        center_code: Optional[ExchangeCenterCode] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[Sequence[ConfigurationSnapshot], int]:
        results = list(self._snapshots.values())

        if center_code:
            results = [s for s in results if str(s.exchange_center_code) == str(center_code)]
        if status:
            results = [s for s in results if s.publication_status.value == status]

        results.sort(key=lambda s: s.generated_at_utc, reverse=True)

        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        paged = results[start:end]

        return paged, total

    def exists_for_center_and_version(
        self, center_code: ExchangeCenterCode, version: ConfigVersion
    ) -> bool:
        composite = self._key(center_code, version)
        return composite in self._by_center_version

    def get_max_version(self, center_code: ExchangeCenterCode) -> Optional[ConfigVersion]:
        center_str = str(center_code)
        max_ver = 0

        for composite in self._by_center_version.keys():
            if composite[0] == center_str and composite[1] > max_ver:
                max_ver = composite[1]

        return ConfigVersion(max_ver) if max_ver > 0 else None

    def clear(self) -> None:
        self._snapshots.clear()
        self._by_center_version.clear()
