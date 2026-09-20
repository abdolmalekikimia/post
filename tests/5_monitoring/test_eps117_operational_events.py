r"""E2E Test Suite for EPS-117: Provisioning raw operational event data for central reporting.

Tests delivery of all 10 raw operational events:
- TC-01: InboundRegistered  (enriched: barcode, weightGrams, dimensionsMm, postalOriginCode)
- TC-02: OutboundRegistered (enriched: barcode, assignedChute, destinationCode, sortStatus)
- TC-03: DestinationAssigned (enriched: barcode, chuteNumber, destinationCode, reason)
- TC-04: BagClosed          (enriched: bagBarcode, parcelCount, totalWeightGrams, destinationCode, sealNumber)
- TC-05: DispatchClosed     (enriched: dispatchBarcode, bagsCount, totalWeightGrams, transportType)
- TC-06: OperationalError   (enriched: errorCode, severity, componentId, message)
- TC-07: OperationalWarning (enriched: warningCode, severity, componentId, message)
- TC-08: Idempotency        (duplicate eventId acceptance without double-counting)
- TC-09: Offline Buffering  (batch ordering & chronological replay of queued events)
- TC-10: Ingestion Latency  (occurredAtUtc → ACK delta within 500 ms SLA)

Run with:
  $env:RUN_E2E="1"
  .venv\Scripts\python.exe -m pytest tests/5_monitoring/test_eps117_operational_events.py -v -s
"""

from __future__ import annotations

import os
import pytest

from config.settings import settings
from flows.reporting.eps117_operational_events_flow import (
    run_eps117_operational_events_flow,
)


@pytest.mark.monitoring
@pytest.mark.eps117
def test_eps117_operational_events():
    """Verify delivery of all 10 enriched operational events for central reporting."""
    if not os.getenv("RUN_E2E"):
        pytest.skip("E2E test skipped: Set RUN_E2E=1 to execute against live Edge server")

    result = run_eps117_operational_events_flow(run_settings=settings)

    assert result is not None
    assert result.report is not None

    summary = result.report.summary()
    assert summary["FAILED"] == 0, f"EPS-117 E2E had failures: {summary}"
    assert summary["PASSED"] >= 10, (
        f"Expected at least 10 passed steps, got {summary['PASSED']}"
    )
