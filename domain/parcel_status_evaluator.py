from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from config.settings import Settings, settings


class ParcelHistoryStatus(str, Enum):
    """وضعیت تاریخی مرسوله بر اساس CPS-65"""
    NOT_FOUND = "not_found"           # مرسوله جدید، سابقه‌ای ندارد
    DUPLICATE_READ = "duplicate_read"  # خوانش مجدد (< 6 ساعت)
    RETURNING = "returning"            # مرسوله بازگشتی (6-72 ساعت)
    RETURN_TO_ORIGIN = "return_to_origin"  # مرجوع به مبدأ (> 72 ساعت)


@dataclass(frozen=True)
class ParcelReading:
    """یک رکورد خوانش مرسوله"""
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
    """نتیجه ارزیابی وضعیت مرسوله"""
    status: ParcelHistoryStatus
    elapsed_hours: float
    threshold_applied: str
    previous_reading: Optional[ParcelReading] = None
    rule_description: str = ""


class ParcelStatusEvaluator:
    """
    Domain Service برای ارزیابی وضعیت مرسوله بر اساس قوانین زمانی CPS-65.
    
    قوانین (از Configuration):
    - کمتر از DuplicateReadThreshold ساعت: خوانش مجدد (Duplicate Read)
    - از DuplicateReadThreshold تا ReturnedThreshold ساعت: مرسوله بازگشتی (Returning) -> Status 3
    - بیشتر از ReturnToOriginThreshold ساعت: مرجوع به مبدأ (Return to Origin) -> Status 4
    
    هیچ مقداری Hard-code نشده و همه از Settings قابل تنظیم است.
    """

    def __init__(self, run_settings: Settings = settings):
        self.duplicate_threshold_hours = run_settings.cps65_duplicate_read_threshold_hours
        self.returned_threshold_hours = run_settings.cps65_returned_threshold_hours
        self.return_to_origin_threshold_hours = run_settings.cps65_return_to_origin_threshold_hours

        # اعتبارسنجی مقادیر Configuration
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
        ارزیابی وضعیت مرسوله بر اساس آخرین خوانش قبلی.
        
        Args:
            barcode: بارکد مرسوله
            current_scan_time: زمان خوانش فعلی (UTC)
            previous_readings: لیست تمام خوانش‌های قبلی این بارکد (مرتب شده از جدید به قدیم)
        
        Returns:
            StatusEvaluationResult شامل وضعیت محاسبه‌شده و جزئیات
        """
        if not previous_readings:
            return StatusEvaluationResult(
                status=ParcelHistoryStatus.NOT_FOUND,
                elapsed_hours=0.0,
                threshold_applied="N/A - No previous readings",
                rule_description="No history found for parcel, treated as new parcel",
            )

        # آخرین خوانش قبلی
        last_reading = previous_readings[0]
        elapsed = current_scan_time - last_reading.scanned_at_utc
        elapsed_hours = elapsed.total_seconds() / 3600.0

        # اعمال قوانین زمانی
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
        """تبدیل وضعیت به کد عددی برای پاسخ RegisterInbound/InboundQuery"""
        mapping = {
            ParcelHistoryStatus.NOT_FOUND: 0,      # موفق/جدید
            ParcelHistoryStatus.DUPLICATE_READ: 1, # خوانش مجدد
            ParcelHistoryStatus.RETURNING: 3,      # مرسوله بازگشتی (Status 3)
            ParcelHistoryStatus.RETURN_TO_ORIGIN: 4, # مرجوع به مبدأ (Status 4)
        }
        return mapping.get(status, 0)

    def get_core_to_edge_status(self, status: ParcelHistoryStatus) -> str:
        """تبدیل وضعیت به enum CoreToEdgeStatus برای پاسخ InboundQuery"""
        mapping = {
            ParcelHistoryStatus.NOT_FOUND: "success",
            ParcelHistoryStatus.DUPLICATE_READ: "success",
            ParcelHistoryStatus.RETURNING: "returning",
            ParcelHistoryStatus.RETURN_TO_ORIGIN: "rejected",  # یا returning بسته به منطق
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