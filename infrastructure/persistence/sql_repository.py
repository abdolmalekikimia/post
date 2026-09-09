from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from domain.image_metadata.entities import SupplementaryAttachment
from domain.image_metadata.repositories import (
    ImageMetadataRepository,
    ImageMetadataSpec,
    PagedResult,
)
from domain.image_metadata.value_objects import (
    AttachmentId,
    AttachmentType,
    CenterId,
    DeviceId,
    EdgeId,
    IdempotencyKey,
    ObjectKey,
    ParcelBarcode,
    ReadingRecordId,
)


class SqlImageMetadataRepository(ImageMetadataRepository):
    """
    SQL Server implementation برای Production
    
    Table Schema (SupplementaryAttachments):
    - AttachmentId (UNIQUEIDENTIFIER, PK)
    - ParcelBarcode (VARCHAR(24), NOT NULL, INDEX)
    - EdgeId (VARCHAR(64), NOT NULL)
    - DeviceId (VARCHAR(64), NOT NULL)
    - CenterId (VARCHAR(5), NOT NULL)
    - ObjectKey (VARCHAR(1024), NOT NULL, UNIQUE)
    - BucketName (VARCHAR(63), NOT NULL)
    - ContentType (VARCHAR(100), NOT NULL)
    - FileSizeBytes (BIGINT, NOT NULL)
    - AttachmentType (VARCHAR(50), NOT NULL)
    - CorrelationId (UNIQUEIDENTIFIER, NOT NULL)
    - IdempotencyKey (VARCHAR(128), NOT NULL, UNIQUE INDEX)
    - OccurredAtUtc (DATETIMEOFFSET, NOT NULL)
    - ReadingRecordId (UNIQUEIDENTIFIER, NULL, INDEX)
    - ChecksumSha256 (VARCHAR(64), NULL)
    - EventType (VARCHAR(100), NOT NULL)
    - CreatedAtUtc (DATETIMEOFFSET, NOT NULL)
    - UpdatedAtUtc (DATETIMEOFFSET, NULL)
    
    Indexes:
    - IX_ParcelBarcode_OccurredAtUtc (ParcelBarcode, OccurredAtUtc DESC)
    - IX_EdgeId (EdgeId)
    - IX_CorrelationId (CorrelationId)
    - IX_ReadingRecordId (ReadingRecordId)
    - IX_ObjectKey (ObjectKey) UNIQUE
    - IX_IdempotencyKey (IdempotencyKey) UNIQUE
    """
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        # در واقعیت: import pyodbc / sqlalchemy
        # self._conn = pyodbc.connect(connection_string)
        raise NotImplementedError(
            "SqlImageMetadataRepository requires pyodbc/sqlalchemy. "
            "Implement with your preferred SQL library."
        )
    
    def _get_connection(self):
        """Get database connection"""
        # return pyodbc.connect(self.connection_string)
        pass
    
    def _map_row_to_entity(self, row) -> SupplementaryAttachment:
        """Map database row to Entity"""
        return SupplementaryAttachment(
            attachment_id=AttachmentId(row.AttachmentId),
            parcel_barcode=ParcelBarcode(row.ParcelBarcode),
            edge_id=EdgeId(row.EdgeId),
            device_id=DeviceId(row.DeviceId),
            center_id=CenterId(row.CenterId),
            object_key=ObjectKey(row.ObjectKey),
            bucket_name=row.BucketName,
            content_type=row.ContentType,
            file_size_bytes=row.FileSizeBytes,
            attachment_type=AttachmentType(row.AttachmentType),
            correlation_id=CorrelationId(row.CorrelationId),
            idempotency_key=IdempotencyKey(row.IdempotencyKey),
            occurred_at_utc=row.OccurredAtUtc,
            reading_record_id=ReadingRecordId(row.ReadingRecordId) if row.ReadingRecordId else None,
            checksum_sha256=row.ChecksumSha256,
            event_type=row.EventType,
            created_at_utc=row.CreatedAtUtc,
            updated_at_utc=row.UpdatedAtUtc,
        )
    
    def _build_where_clause(self, spec: ImageMetadataSpec) -> tuple[str, list]:
        """Build WHERE clause from spec"""
        conditions = []
        params = []
        
        if spec.parcel_barcode:
            conditions.append("ParcelBarcode = ?")
            params.append(str(spec.parcel_barcode))
        if spec.edge_id:
            conditions.append("EdgeId = ?")
            params.append(str(spec.edge_id))
        if spec.device_id:
            conditions.append("DeviceId = ?")
            params.append(str(spec.device_id))
        if spec.center_id:
            conditions.append("CenterId = ?")
            params.append(str(spec.center_id))
        if spec.attachment_type:
            conditions.append("AttachmentType = ?")
            params.append(spec.attachment_type.value)
        if spec.object_key:
            conditions.append("ObjectKey = ?")
            params.append(str(spec.object_key))
        if spec.reading_record_id:
            conditions.append("ReadingRecordId = ?")
            params.append(str(spec.reading_record_id))
        if spec.date_from:
            conditions.append("OccurredAtUtc >= ?")
            params.append(spec.date_from)
        if spec.date_to:
            conditions.append("OccurredAtUtc <= ?")
            params.append(spec.date_to)
        if spec.correlation_id:
            conditions.append("CorrelationId = ?")
            params.append(spec.correlation_id)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        return where_clause, params
    
    def save(self, attachment: SupplementaryAttachment) -> None:
        """
        INSERT INTO SupplementaryAttachments (...) VALUES (...)
        ON CONFLICT (IdempotencyKey) DO NOTHING -- یا UPDATE
        """
        sql = """
        INSERT INTO SupplementaryAttachments (
            AttachmentId, ParcelBarcode, EdgeId, DeviceId, CenterId,
            ObjectKey, BucketName, ContentType, FileSizeBytes, AttachmentType,
            CorrelationId, IdempotencyKey, OccurredAtUtc, ReadingRecordId,
            ChecksumSha256, EventType, CreatedAtUtc, UpdatedAtUtc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            str(attachment.attachment_id),
            str(attachment.parcel_barcode),
            str(attachment.edge_id),
            str(attachment.device_id),
            str(attachment.center_id),
            str(attachment.object_key),
            attachment.bucket_name,
            attachment.content_type,
            attachment.file_size_bytes,
            attachment.attachment_type.value,
            str(attachment.correlation_id),
            str(attachment.idempotency_key),
            attachment.occurred_at_utc,
            str(attachment.reading_record_id) if attachment.reading_record_id else None,
            attachment.checksum_sha256,
            attachment.event_type,
            attachment.created_at_utc,
            attachment.updated_at_utc,
        )
        # with self._get_connection() as conn:
        #     cursor = conn.cursor()
        #     try:
        #         cursor.execute(sql, params)
        #         conn.commit()
        #     except pyodbc.IntegrityError as e:
        #         if "IdempotencyKey" in str(e):
        #             raise DuplicateIdempotencyKeyError(str(attachment.idempotency_key))
        #         raise
    
    def find_by_id(self, attachment_id: AttachmentId) -> Optional[SupplementaryAttachment]:
        sql = "SELECT * FROM SupplementaryAttachments WHERE AttachmentId = ?"
        # with self._get_connection() as conn:
        #     cursor = conn.cursor()
        #     cursor.execute(sql, str(attachment_id))
        #     row = cursor.fetchone()
        #     return self._map_row_to_entity(row) if row else None
        return None
    
    def find_by_idempotency_key(self, idempotency_key: IdempotencyKey) -> Optional[SupplementaryAttachment]:
        sql = "SELECT * FROM SupplementaryAttachments WHERE IdempotencyKey = ?"
        # with self._get_connection() as conn:
        #     cursor = conn.cursor()
        #     cursor.execute(sql, str(idempotency_key))
        #     row = cursor.fetchone()
        #     return self._map_row_to_entity(row) if row else None
        return None
    
    def find_by_object_key(self, object_key: ObjectKey) -> Optional[SupplementaryAttachment]:
        sql = "SELECT * FROM SupplementaryAttachments WHERE ObjectKey = ?"
        # with self._get_connection() as conn:
        #     cursor = conn.cursor()
        #     cursor.execute(sql, str(object_key))
        #     row = cursor.fetchone()
        #     return self._map_row_to_entity(row) if row else None
        return None
    
    def find_by_spec(self, spec: ImageMetadataSpec) -> PagedResult:
        where_clause, params = self._build_where_clause(spec)
        
        # Count total
        count_sql = f"SELECT COUNT(*) FROM SupplementaryAttachments {where_clause}"
        # total_count = ...
        
        # Paged query
        offset = (spec.page - 1) * spec.page_size
        data_sql = f"""
        SELECT * FROM SupplementaryAttachments {where_clause}
        ORDER BY OccurredAtUtc DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        params.extend([offset, spec.page_size])
        # items = ...
        
        return PagedResult(
            items=[],  # mapped items
            total_count=0,
            page=spec.page,
            page_size=spec.page_size,
        )
    
    def find_by_parcel_barcode(
        self, 
        parcel_barcode: ParcelBarcode, 
        page: int = 1, 
        page_size: int = 50
    ) -> PagedResult:
        sql = """
        SELECT * FROM SupplementaryAttachments 
        WHERE ParcelBarcode = ?
        ORDER BY OccurredAtUtc DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        count_sql = "SELECT COUNT(*) FROM SupplementaryAttachments WHERE ParcelBarcode = ?"
        # execute both...
        return PagedResult(items=[], total_count=0, page=page, page_size=page_size)
    
    def exists_by_idempotency_key(self, idempotency_key: IdempotencyKey) -> bool:
        sql = "SELECT 1 FROM SupplementaryAttachments WHERE IdempotencyKey = ?"
        # with self._get_connection() as conn:
        #     cursor = conn.cursor()
        #     cursor.execute(sql, str(idempotency_key))
        #     return cursor.fetchone() is not None
        return False
    
    def count_by_parcel_barcode(self, parcel_barcode: ParcelBarcode) -> int:
        sql = "SELECT COUNT(*) FROM SupplementaryAttachments WHERE ParcelBarcode = ?"
        # with self._get_connection() as conn:
        #     cursor = conn.cursor()
        #     cursor.execute(sql, str(parcel_barcode))
        #     return cursor.fetchone()[0]
        return 0


# مثال Connection String برای SQL Server
SQL_SERVER_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=your-server.database.windows.net;"
    "DATABASE=CorePostSorting;"
    "UID=your-username;"
    "PWD=your-password;"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)