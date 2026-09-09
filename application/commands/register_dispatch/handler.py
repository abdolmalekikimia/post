from __future__ import annotations

from dataclasses import dataclass

from application.commands.register_dispatch import (
    RegisterDispatchCommand,
    RegisterDispatchResult,
)
from domain.bag_dispatch.entities import Dispatch
from domain.bag_dispatch.events import DispatchRegistered
from domain.bag_dispatch.repositories import DispatchRepository
from domain.bag_dispatch.exceptions import (
    DispatchAlreadyExistsError,
    BagDispatchDomainError,
)
from application.ports import EventPublisherPort


@dataclass
class RegisterDispatchHandler:
    """
    Handler for processing RegisterDispatchCommand

    Responsibilities:
    1. Check idempotency (prevent duplicate registration)
    2. Create Dispatch entity
    3. Save to Repository
    4. Publish Event (Async)
    """
    repository: DispatchRepository
    event_publisher: EventPublisherPort

    async def handle(self, command: RegisterDispatchCommand) -> RegisterDispatchResult:
        """
        Execute RegisterDispatchCommand

        Returns:
            RegisterDispatchResult with dispatch_id on success
        """
        try:
            # 1. Check Idempotency - prevent duplicate registration
            if self.repository.exists_by_dispatch_id(command.dispatch_id):
                existing = self.repository.find_by_dispatch_id(command.dispatch_id)
                if existing:
                    # Idempotent: return existing result without error
                    return RegisterDispatchResult(
                        dispatch_id=existing.dispatch_id,
                        success=True,
                    )

            # 2. Create Entity
            dispatch = Dispatch.create(
                dispatch_id=command.dispatch_id,
                bag_barcodes=command.bag_barcodes,
                origin_center=command.origin_center,
                dest_center=command.dest_center,
                transport_type=command.transport_type,
                scheduled_at_utc=command.scheduled_at_utc,
                correlation_id=command.correlation_id,
                idempotency_key=command.idempotency_key,
            )

            # 3. Save to Repository
            self.repository.save(dispatch)

            # 4. Publish Event (Async - fire and forget)
            event = DispatchRegistered.from_dispatch(dispatch)
            await self.event_publisher.publish(event)

            return RegisterDispatchResult(
                dispatch_id=dispatch.dispatch_id,
                success=True,
            )

        except BagDispatchDomainError as e:
            # Domain errors - return as Result (no throw for better Controller control)
            return RegisterDispatchResult(
                dispatch_id=command.dispatch_id,
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )
        except Exception as e:
            # Unexpected errors
            return RegisterDispatchResult(
                dispatch_id=command.dispatch_id,
                success=False,
                error_code="INTERNAL_ERROR",
                error_message=f"Unexpected error: {type(e).__name__}: {e}",
            )