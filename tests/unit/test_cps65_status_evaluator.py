from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from domain.parcel_status_evaluator import (
    ParcelReading,
    ParcelHistoryStatus,
    ParcelStatusEvaluator,
    StatusEvaluationResult,
    create_evaluator,
)
from config.settings import Settings


def make_reading(
    barcode: str = "590001234567890123456789",
    hours_ago: float = 1.0,
    reading_id: str = "reading-1",
    scanned_at: datetime | None = None,
) -> ParcelReading:
    """Helper to create a ParcelReading with a specific time in the past."""
    if scanned_at is None:
        scanned_at = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return ParcelReading(
        reading_id=reading_id,
        barcode=barcode,
        scanned_at_utc=scanned_at,
        edge_id="EDGE-001",
        exchange_center_code="59544",
        device_id="DEVICE-001",
    )


class TestParcelStatusEvaluator:
    """Unit tests for CPS-65 Parcel Status Evaluation logic."""

    def test_no_previous_readings_returns_not_found(self):
        """بدون سابقه -> Not Found (مرسوله جدید)"""
        evaluator = create_evaluator()
        now = datetime.now(timezone.utc)
        result = evaluator.evaluate("590001234567890123456789", now, [])
        
        assert result.status == ParcelHistoryStatus.NOT_FOUND
        assert result.elapsed_hours == 0.0
        assert result.previous_reading is None

    def test_duplicate_read_less_than_6_hours(self):
        """کمتر از 6 ساعت -> Duplicate Read"""
        # Default thresholds: 6h, 72h, 72h
        evaluator = create_evaluator()
        now = datetime.now(timezone.utc)
        previous = [make_reading(hours_ago=3.0)]  # 3 hours ago
        
        result = evaluator.evaluate("590001234567890123456789", now, previous)
        
        assert result.status == ParcelHistoryStatus.DUPLICATE_READ
        assert result.elapsed_hours == pytest.approx(3.0, abs=0.01)
        assert "Duplicate Read" in result.rule_description
        assert result.previous_reading is not None

    def test_returning_between_6_and_72_hours(self):
        """بین 6 تا 72 ساعت -> Returning (Status 3)"""
        evaluator = create_evaluator()
        now = datetime.now(timezone.utc)
        previous = [make_reading(hours_ago=24.0)]  # 24 hours ago
        
        result = evaluator.evaluate("590001234567890123456789", now, previous)
        
        assert result.status == ParcelHistoryStatus.RETURNING
        assert result.elapsed_hours == pytest.approx(24.0, abs=0.01)
        assert "Returning" in result.rule_description

    def test_return_to_origin_more_than_72_hours(self):
        """بیشتر از 72 ساعت -> Return to Origin (Status 4)"""
        evaluator = create_evaluator()
        now = datetime.now(timezone.utc)
        previous = [make_reading(hours_ago=100.0)]  # 100 hours ago
        
        result = evaluator.evaluate("590001234567890123456789", now, previous)
        
        assert result.status == ParcelHistoryStatus.RETURN_TO_ORIGIN
        assert result.elapsed_hours == pytest.approx(100.0, abs=0.01)
        assert "Return to Origin" in result.rule_description

    def test_boundary_exactly_6_hours_is_returning(self):
        """دقیقاً 6 ساعت -> Returning (شامل مرز بالا)"""
        evaluator = create_evaluator()
        now = datetime.now(timezone.utc)
        # استفاده از 6.001 برای اطمینان از دقت ممیز شناور
        previous = [make_reading(hours_ago=6.001)]
        
        result = evaluator.evaluate("590001234567890123456789", now, previous)
        
        assert result.status == ParcelHistoryStatus.RETURNING

    def test_boundary_exactly_72_hours_is_returning(self):
        """دقیقاً 72 ساعت -> Returning (شامل مرز بالا برای ReturnedThreshold)"""
        evaluator = create_evaluator()
        now = datetime.now(timezone.utc)
        previous = [make_reading(hours_ago=72.0)]  # دقیقاً 72 ساعت
        
        result = evaluator.evaluate("590001234567890123456789", now, previous)
        
        assert result.status == ParcelHistoryStatus.RETURNING

    def test_boundary_over_72_hours_is_return_to_origin(self):
        """بیشتر از 72 ساعت (مثلاً 72.01) -> Return to Origin"""
        evaluator = create_evaluator()
        now = datetime.now(timezone.utc)
        previous = [make_reading(hours_ago=72.01)]
        
        result = evaluator.evaluate("590001234567890123456789", now, previous)
        
        assert result.status == ParcelHistoryStatus.RETURN_TO_ORIGIN

    def test_uses_most_recent_reading_when_multiple_exist(self):
        """وقتی چند خوانش قبلی وجود دارد، از جدیدترین استفاده می‌کند"""
        evaluator = create_evaluator()
        now = datetime.now(timezone.utc)
        # دو خوانش: یکی 10 ساعت پیش، یکی 50 ساعت پیش
        # باید از 10 ساعت پیش استفاده کند -> Returning
        previous = [
            make_reading(hours_ago=10.0, reading_id="recent"),
            make_reading(hours_ago=50.0, reading_id="older"),
        ]
        
        result = evaluator.evaluate("590001234567890123456789", now, previous)
        
        assert result.status == ParcelHistoryStatus.RETURNING
        assert result.previous_reading.reading_id == "recent"

    def test_status_code_mapping(self):
        """تست نگاشت وضعیت به کد عددی"""
        evaluator = create_evaluator()
        
        assert evaluator.get_status_code(ParcelHistoryStatus.NOT_FOUND) == 0
        assert evaluator.get_status_code(ParcelHistoryStatus.DUPLICATE_READ) == 1
        assert evaluator.get_status_code(ParcelHistoryStatus.RETURNING) == 3
        assert evaluator.get_status_code(ParcelHistoryStatus.RETURN_TO_ORIGIN) == 4

    def test_core_to_edge_status_mapping(self):
        """تست نگاشت وضعیت به CoreToEdgeStatus"""
        evaluator = create_evaluator()
        
        assert evaluator.get_core_to_edge_status(ParcelHistoryStatus.NOT_FOUND) == "success"
        assert evaluator.get_core_to_edge_status(ParcelHistoryStatus.DUPLICATE_READ) == "success"
        assert evaluator.get_core_to_edge_status(ParcelHistoryStatus.RETURNING) == "returning"
        assert evaluator.get_core_to_edge_status(ParcelHistoryStatus.RETURN_TO_ORIGIN) == "rejected"

    def test_custom_thresholds_from_settings(self):
        """تست استفاده از آستانه‌های سفارشی از Settings"""
        custom_settings = Settings(
            cps65_duplicate_read_threshold_hours=2,   # 2 ساعت
            cps65_returned_threshold_hours=24,        # 24 ساعت
            cps65_return_to_origin_threshold_hours=48, # 48 ساعت
        )
        evaluator = ParcelStatusEvaluator(custom_settings)
        now = datetime.now(timezone.utc)
        
        # 3 ساعت پیش -> باید Returning باشد (بیشتر از 2، کمتر از 24)
        result = evaluator.evaluate("590001234567890123456789", now, [make_reading(hours_ago=3.0)])
        assert result.status == ParcelHistoryStatus.RETURNING
        
        # 30 ساعت پیش -> باید Return to Origin باشد (بیشتر از 24، کمتر از 48)
        result = evaluator.evaluate("590001234567890123456789", now, [make_reading(hours_ago=30.0)])
        assert result.status == ParcelHistoryStatus.RETURN_TO_ORIGIN

    def test_invalid_thresholds_raises_error(self):
        """مقادیر نامعتبر Configuration باید خطا دهند"""
        # Duplicate >= Returned
        with pytest.raises(ValueError, match="ReturnedThreshold must be greater"):
            ParcelStatusEvaluator(Settings(
                cps65_duplicate_read_threshold_hours=10,
                cps65_returned_threshold_hours=5,
                cps65_return_to_origin_threshold_hours=20,
            ))
        
        # Returned >= ReturnToOrigin
        with pytest.raises(ValueError, match="ReturnToOriginThreshold must be greater"):
            ParcelStatusEvaluator(Settings(
                cps65_duplicate_read_threshold_hours=5,
                cps65_returned_threshold_hours=10,
                cps65_return_to_origin_threshold_hours=8,
            ))

    def test_negative_threshold_raises_error(self):
        """آستانه منفی باید خطا دهد"""
        with pytest.raises(ValueError, match="DuplicateReadThreshold must be positive"):
            ParcelStatusEvaluator(Settings(
                cps65_duplicate_read_threshold_hours=-1,
                cps65_returned_threshold_hours=10,
                cps65_return_to_origin_threshold_hours=20,
            ))


class TestStatusEvaluationResult:
    """تست‌های مدل داده StatusEvaluationResult"""

    def test_result_contains_all_required_fields(self):
        evaluator = create_evaluator()
        now = datetime.now(timezone.utc)
        previous = [make_reading(hours_ago=10.0)]
        
        result = evaluator.evaluate("590001234567890123456789", now, previous)
        
        assert isinstance(result, StatusEvaluationResult)
        assert result.status in ParcelHistoryStatus
        assert isinstance(result.elapsed_hours, float)
        assert isinstance(result.threshold_applied, str)
        assert isinstance(result.rule_description, str)
        assert result.previous_reading is not None