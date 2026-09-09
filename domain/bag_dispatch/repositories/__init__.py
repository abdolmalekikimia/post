from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Any

from domain.bag_dispatch.value_objects import (
    BagBarcode,
    DispatchId,
    ExchangeCenterCode,
)


@dataclass(frozen=True)
class BagSpec:
    """
    Specification pattern for Bag queries
    """
    bag_barcode: Optional[BagBarcode] = None
    origin_center: Optional[ExchangeCenterCode] = None
    dest_center: Optional[ExchangeCenterCode] = None
    transport_type: Optional[str] = None
    correlation_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    # Pagination
    page: int = 1
    page_size: int = 50

    def __post_init__(self) -> None:
        if self.page < 1:
            object.__setattr__(self, "page", 1)
        if self.page_size < 1 or self.page_size > 1000:
            object.__setattr__(self, "page_size", 50)


@dataclass(frozen=True)
class DispatchSpec:
    """
    Specification pattern for Dispatch queries
    """
    dispatch_id: Optional[DispatchId] = None
    origin_center: Optional[ExchangeCenterCode] = None
    dest_center: Optional[ExchangeCenterCode] = None
    transport_type: Optional[str] = None
    correlation_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    # Pagination
    page: int = 1
    page_size: int = 50

    def __post_init__(self) -> None:
        if self.page < 1:
            object.__setattr__(self, "page", 1)
        if self.page_size < 1 or self.page_size > 1000:
            object.__setattr__(self, "page_size", 50)


@dataclass(frozen=True)
class PagedResult:
    """Paged result"""
    items: List[Any]
    total_count: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 0
        return (self.total_count + self.page_size - 1) // self.page_size


class BagRepository(ABC):
    """
    Repository interface for Bag storage in Core

    Implementations:
    - SqlBagRepository (Infrastructure)
    - InMemoryBagRepository (Testing)
    """

    @abstractmethod
    def save(self, bag: "Bag") -> None:
        """
        Save new Bag

        Raises:
            BagAlreadyExistsError: if bag_barcode already exists
        """
        ...

    @abstractmethod
    def find_by_bag_barcode(
        self, bag_barcode: BagBarcode
    ) -> Optional["Bag"]:
        """Find Bag by barcode"""
        ...

    @abstractmethod
    def find_by_bag_barcode_list(
        self, bag_barcodes: List[BagBarcode]
    ) -> List["Bag"]:
        """Find all Bags by list of barcodes"""
        ...

    @abstractmethod
    def find_by_spec(self, spec: BagSpec) -> PagedResult:
        """Advanced search with Specification"""
        ...

    @abstractmethod
    def exists_by_bag_barcode(
        self, bag_barcode: BagBarcode
    ) -> bool:
        """Check if Bag exists by barcode"""
        ...

    @abstractmethod
    def count_by_origin_dest(
        self,
        origin_center: ExchangeCenterCode,
        dest_center: ExchangeCenterCode,
    ) -> int:
        """Count Bags between two centers"""
        ...


class DispatchRepository(ABC):
    """
    Repository interface for Dispatch storage in Core

    Implementations:
    - SqlDispatchRepository (Infrastructure)
    - InMemoryDispatchRepository (Testing)
    """

    @abstractmethod
    def save(self, dispatch: "Dispatch") -> None:
        """
        Save new Dispatch

        Raises:
            DispatchAlreadyExistsError: if dispatch_id already exists
        """
        ...

    @abstractmethod
    def find_by_dispatch_id(
        self, dispatch_id: DispatchId
    ) -> Optional["Dispatch"]:
        """Find Dispatch by ID"""
        ...

    @abstractmethod
    def find_by_dispatch_id_list(
        self, dispatch_ids: List[DispatchId]
    ) -> List["Dispatch"]:
        """Find all Dispatches by list of IDs"""
        ...

    @abstractmethod
    def find_by_spec(self, spec: DispatchSpec) -> PagedResult:
        """Advanced search with Specification"""
        ...

    @abstractmethod
    def exists_by_dispatch_id(
        self, dispatch_id: DispatchId
    ) -> bool:
        """Check if Dispatch exists by ID"""
        ...

    @abstractmethod
    def count_by_origin_dest(
        self,
        origin_center: ExchangeCenterCode,
        dest_center: ExchangeCenterCode,
    ) -> int:
        """Count Dispatches between two centers"""
        ...