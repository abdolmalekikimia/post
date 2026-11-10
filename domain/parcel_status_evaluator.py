from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from config.settings import Settings, settings


class ParcelHistoryStatus(str, Enum):
    """Historical status of a parcel, by the history rules"""
    NOT_FOUND = "not_found"           # new parcel, no history
    DUPLICATE_READ = "duplicate_read"  # re-read (< 6 hours)
    RETURNING = "returning"            # returning parcel (6-72 hours)
    RETURN_TO_ORIGIN = "return_to_origin"  # returned to origin (> 72 hours)


@dataclass(frozen=True)
class ParcelReading:
    """One parcel reading record"""
    reading_id: str
    barcode: str
    scanned_at_utc: datetime
    edge_id: str
    exchange_center_code: str
    device_id: str
    physical_origin_code: Optional[str] = None
    physical_destination_code: Optional[str] = None


@dataclass(frozen=True)
class StatusEvaluationResult:
    """Result of evaluating a parcel's status"""
    status: ParcelHistoryStatus
    elapsed_hours: float
    threshold_applied: str
    previous_reading: Optional[ParcelReading] = None
    rule_description: str = ""


class ParcelStatusEvaluator:
    """
    Domain Service that evaluates a parcel's status from the time-based history rules.
    
    Rules (from Configuration):
    - less than DuplicateReadThreshold hours: re-read (Duplicate Read)
    - from DuplicateReadThreshold to ReturnedThreshold hours: returning parcel (Returning) -> Status 3
    - more than ReturnToOriginThreshold hours: returned to origin (Return to Origin) -> Status 4
    
    No value is hard-coded; everything is configurable from Settings.
    """

    def __init__(self, run_settings: Settings = settings):
        self.duplicate_threshold_hours = run_settings.status_evaluator_duplicate_read_threshold_hours
        self.returned_threshold_hours = run_settings.status_evaluator_returned_threshold_hours
        self.return_to_origin_threshold_hours = run_settings.status_evaluator_return_to_origin_threshold_hours

        # Validate the Configuration values
        if self.duplicate_threshold_hours <= 0:
            raise ValueError("DuplicateReadThreshold must be positive")
        if self.returned_threshold_hours <= self.duplicate_threshold_hours:
            raise ValueError("ReturnedThreshold must be greater than DuplicateReadThreshold")
        if self.return_to_origin_threshold_hours < self.returned_threshold_hours:
            raise ValueError("ReturnToOriginThreshold must be greater than or equal to ReturnedThreshold")

    def evaluate(
        self,
        barcode: str,
        current_scan_time: datetime,
        previous_readings: list[ParcelReading],
    ) -> StatusEvaluationResult:
        """
        Evaluate a parcel's status from the latest earlier reading.
        
        Args:
            barcode: the parcel barcode
            current_scan_time: the current reading time (UTC)
            previous_readings: list of all earlier readings of this barcode (newest first)
        
        Returns:
            StatusEvaluationResult with the computed status and details
        """
        if not previous_readings:
            return StatusEvaluationResult(
                status=ParcelHistoryStatus.NOT_FOUND,
                elapsed_hours=0.0,
                threshold_applied="N/A - No previous readings",
                rule_description="No history found for parcel, treated as new parcel",
            )

        # The latest earlier reading
        last_reading = previous_readings[0]
        elapsed = current_scan_time - last_reading.scanned_at_utc
        elapsed_hours = elapsed.total_seconds() / 3600.0

        # Apply the time rules
        if elapsed_hours < self.duplicate_threshold_hours:
            return StatusEvaluationResult(
                status=ParcelHistoryStatus.DUPLICATE_READ,
                elapsed_hours=elapsed_hours,
                threshold_applied=f"< {self.duplicate_threshold_hours}h (DuplicateReadThreshold)",
                previous_reading=last_reading,
                rule_description=f"Elapsed {elapsed_hours:.2f}h < {self.duplicate_threshold_hours}h -> Duplicate Read",
            )
        elif elapsed_hours <= self.returned_threshold_hours:
            return StatusEvaluationResult(
                status=ParcelHistoryStatus.RETURNING,
                elapsed_hours=elapsed_hours,
                threshold_applied=f"{self.duplicate_threshold_hours}h - {self.returned_threshold_hours}h (ReturnedThreshold)",
                previous_reading=last_reading,
                rule_description=f"Elapsed {elapsed_hours:.2f}h in range [{self.duplicate_threshold_hours}h, {self.returned_threshold_hours}h] -> Returning (Status 3)",
            )
        else:
            return StatusEvaluationResult(
                status=ParcelHistoryStatus.RETURN_TO_ORIGIN,
                elapsed_hours=elapsed_hours,
                threshold_applied=f"> {self.return_to_origin_threshold_hours}h (ReturnToOriginThreshold)",
                previous_reading=last_reading,
                rule_description=f"Elapsed {elapsed_hours:.2f}h > {self.return_to_origin_threshold_hours}h -> Return to Origin (Status 4)",
            )

    def get_status_code(self, status: ParcelHistoryStatus) -> int:
        """Convert the status to a numeric code for the RegisterInbound/InboundQuery reply"""
        mapping = {
            ParcelHistoryStatus.NOT_FOUND: 0,      # success/new
            ParcelHistoryStatus.DUPLICATE_READ: 1, # re-read
            ParcelHistoryStatus.RETURNING: 3,      # returning parcel (Status 3)
            ParcelHistoryStatus.RETURN_TO_ORIGIN: 4, # returned to origin (Status 4)
        }
        return mapping.get(status, 0)

    def get_core_to_edge_status(self, status: ParcelHistoryStatus) -> str:
        """Convert the status to the CoreToEdgeStatus enum for the InboundQuery reply"""
        mapping = {
            ParcelHistoryStatus.NOT_FOUND: "success",
            ParcelHistoryStatus.DUPLICATE_READ: "success",
            ParcelHistoryStatus.RETURNING: "returning",
            ParcelHistoryStatus.RETURN_TO_ORIGIN: "rejected",  # or returning, depending on the logic
        }
        return mapping.get(status, "success")


def create_evaluator(run_settings: Settings = settings) -> ParcelStatusEvaluator:
    """Factory function for creating ParcelStatusEvaluator"""
    return ParcelStatusEvaluator(run_settings)


# convenience functions for backward compatibility
def evaluate_parcel_status(
    barcode: str,
    current_scan_time: datetime,
    previous_readings: list[ParcelReading],
    run_settings: Settings = settings,
) -> StatusEvaluationResult:
    """Evaluate parcel status using configured thresholds."""
    evaluator = ParcelStatusEvaluator(run_settings)
    return evaluator.evaluate(barcode, current_scan_time, previous_readings)