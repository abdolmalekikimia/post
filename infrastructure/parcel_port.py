from __future__ import annotations

import logging
from typing import Optional

import requests

from application.ports import ParcelDossierPort
from domain.image_metadata.value_objects import (
    AttachmentId,
    EdgeId,
    ParcelBarcode,
    ReadingRecordId,
)

logger = logging.getLogger(__name__)


class HttpParcelDossierPort(ParcelDossierPort):
    """
    HTTP Client implementation برای ارتباط با Parcel Service
    
    endpoints مورد انتظار در Parcel Service:
    - GET /api/parcels/{barcode}/exists
    - GET /api/parcels/{barcode}/reading-records/{readingRecordId}/exists
    - GET /api/parcels/{barcode}/authorized?edgeId={edgeId}
    - GET /api/parcels/{barcode}/center-id
    - POST /api/parcels/{barcode}/attachments/link
    """
    
    def __init__(
        self,
        base_url: str,
        timeout_seconds: int = 5,
        auth_token: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds
        self.session = requests.Session()
        if auth_token:
            self.session.headers.update({"Authorization": f"Bearer {auth_token}"})
        self.session.headers.update({"Content-Type": "application/json"})
    
    def _make_request(self, method: str, path: str, **kwargs) -> Optional[dict]:
        """Helper برای درخواست HTTP"""
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.warning(f"Parcel service error: {response.status_code} - {response.text}")
                return None
        except requests.RequestException as e:
            logger.error(f"Parcel service request failed: {e}")
            return None
    
    async def exists(self, parcel_barcode: ParcelBarcode) -> bool:
        """بررسی وجود مرسوله"""
        result = self._make_request("GET", f"/api/parcels/{parcel_barcode}/exists")
        return result is not None and result.get("exists", False)
    
    async def reading_record_exists(self, reading_record_id: ReadingRecordId) -> bool:
        """بررسی وجود رکورد خوانش"""
        result = self._make_request(
            "GET", 
            f"/api/reading-records/{reading_record_id}/exists"
        )
        return result is not None and result.get("exists", False)
    
    async def is_edge_authorized(self, parcel_barcode: ParcelBarcode, edge_id: EdgeId) -> bool:
        """بررسی مجوز دسترسی Edge به مرسوله"""
        result = self._make_request(
            "GET",
            f"/api/parcels/{parcel_barcode}/authorized",
            params={"edgeId": str(edge_id)}
        )
        return result is not None and result.get("authorized", False)
    
    async def get_parcel_center_id(self, parcel_barcode: ParcelBarcode) -> Optional[str]:
        """دریافت کد مرکز تبادل مرسوله"""
        result = self._make_request("GET", f"/api/parcels/{parcel_barcode}/center-id")
        if result:
            return result.get("centerId") or result.get("exchangeCenterCode")
        return None
    
    async def link_attachment_to_parcel(
        self, 
        parcel_barcode: ParcelBarcode, 
        attachment_id: AttachmentId
    ) -> bool:
        """لینک کردن attachment به پرونده مرسوله"""
        result = self._make_request(
            "POST",
            f"/api/parcels/{parcel_barcode}/attachments/link",
            json={"attachmentId": str(attachment_id)}
        )
        return result is not None and result.get("success", False)


class InMemoryParcelDossierPort(ParcelDossierPort):
    """
    In-Memory implementation برای Testing
    """
    
    def __init__(self):
        # Mock data for testing
        self._parcels = {
            "590001234567890123456789": {"center_id": "59544", "authorized_edges": ["EDGE-TEST-001"]},
            "590001234567890123456788": {"center_id": "59544", "authorized_edges": ["EDGE-TEST-001"]},
            "590001234567890123456787": {"center_id": "59544", "authorized_edges": ["EDGE-TEST-001"]},
        }
        self._reading_records = {
            "11111111-1111-1111-1111-111111111111": True,
            "22222222-2222-2222-2222-222222222222": True,
            "33333333-3333-3333-3333-333333333333": True,
        }
        self._linked_attachments = set()
    
    async def exists(self, parcel_barcode: ParcelBarcode) -> bool:
        return str(parcel_barcode) in self._parcels
    
    async def reading_record_exists(self, reading_record_id: ReadingRecordId) -> bool:
        return str(reading_record_id) in self._reading_records
    
    async def is_edge_authorized(self, parcel_barcode: ParcelBarcode, edge_id: EdgeId) -> bool:
        parcel = self._parcels.get(str(parcel_barcode))
        if parcel:
            return str(edge_id) in parcel.get("authorized_edges", [])
        return False
    
    async def get_parcel_center_id(self, parcel_barcode: ParcelBarcode) -> Optional[str]:
        parcel = self._parcels.get(str(parcel_barcode))
        if parcel:
            return parcel.get("center_id")
        return None
    
    async def link_attachment_to_parcel(
        self, 
        parcel_barcode: ParcelBarcode, 
        attachment_id: AttachmentId
    ) -> bool:
        key = (str(parcel_barcode), str(attachment_id))
        if key in self._linked_attachments:
            return True
        self._linked_attachments.add(key)
        return True