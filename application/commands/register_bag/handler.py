from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from application.commands.register_bag import (
    RegisterBagCommand,
    RegisterBagResult,
)
from domain.bag_dispatch.entities import Bag
from domain.bag_dispatch.events import BagRegistered
from domain.bag_dispatch.repositories import BagRepository
from domain.bag_dispatch.exceptions import (
    BagAlreadyExistsError,
    BagDispatchDomainError,
    DuplicateIdempotencyKeyError,
)
from application.ports import EventPublisherPort


@dataclass
class RegisterBagHandler:
    """
    Handler for processing RegisterBagCommand

    Responsibilities:
    1. Check idempotency (prevent duplicate registration)
    2. Create Bag entity
    3. Save to Repository
    4. Publish Event (Async)
    """
    repository: BagRepository
    event_publisher: EventPublisherPort

    async def handle(self, command: RegisterBagCommand) -> RegisterBagResult:
        """
        Execute RegisterBagCommand

        Returns:
            RegisterBagResult with bag_barcode on success
        """
        try:
            # 1. Check Idempotency - prevent duplicate registration
            # In Phase 1, we don't have a direct idempotency check in BagRepository
            # The BagAlreadyExistsError will be caught if bag_barcode already exists
            if self.repository.exists_by_bag_barcode(command.bag_barcode):
                existing = self.repository.find_by_bag_barcode(command.bag_barcode)
                if existing:
                    # Idempotent: return existing result without error
                    return RegisterBagResult(
                        bag_barcode=existing.bag_barcode,
                        success=True,
                    )

            # 2. Create Entity
            bag = Bag.create(
                bag_barcode=command.bag_barcode,
                member_barcodes=command.member_barcodes,
                origin_center=command.origin_center,
                dest_center=command.dest_center,
                seal_number=command.seal_number,
                transport_type=command.transport_type,
                closed_at_utc=command.closed_at_utc,
                correlation_id=command.correlation_id,
                idempotency_key=command.idempotency_key,
                created_by_device_id=command.created_by_device_id,
            )

            # 3. Save to Repository
            self.repository.save(bag)

            # 4. Publish Event (Async - fire and forget)
            event = BagRegistered.from_bag(bag)
            await self.event_publisher.publish(event)

            return RegisterBagResult(
                bag_barcode=bag.bag_barcode,
                success=True,
            )

        except BagDispatchDomainError as e:
            # Domain errors - return as Result (no throw for better Controller control)
            return RegisterBagResult(
                bag_barcode=command.bag_barcode,
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )
        except Exception as e:
            # Unexpected errors
            return RegisterBagResult(
                bag_barcode=command.bag_barcode,
                success=False,
                error_code="INTERNAL_ERROR",
                error_message=f"Unexpected error: {type(e).__name__}: {e}",
            )