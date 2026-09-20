r"""E2E Stage Patch Verification Test Suite for CPS-164.

Tests Core services on stage server (192.168.20.160) after patch deployment:
- Identity Service Authentication with national.manager credentials
- Core Inbound Query API
- MinIO Presigned URL generation
- Bag & Dispatch Storage
- Operational Results Storage
- Edge Health Monitoring & Heartbeat Ingestion
- Sorting Device Management Registration

Run live with:
  $env:RUN_STAGE="1"
  .venv\Scripts\python.exe -m pytest tests/stage/test_cps164_stage_patch.py -v -s
"""

from __future__ import annotations

import os
import pytest

from config.settings import settings
from flows.stage.cps164_stage_patch_flow import run_cps164_stage_patch_flow


@pytest.mark.stage
@pytest.mark.cps164
def test_cps164_stage_patch_verification():
    """Verify all 8 Core API endpoints on the stage server (192.168.20.160) post-patch."""
    if not os.getenv("RUN_STAGE") and not os.getenv("STAGE_SERVER_URL"):
        pytest.skip(
            "Stage test skipped: Set RUN_STAGE=1 or STAGE_SERVER_URL to execute against live stage server (192.168.20.160)"
        )

    result = run_cps164_stage_patch_flow(run_settings=settings)

    assert result is not None
    assert result.report is not None
    assert result.report.summary()["FAILED"] == 0, f"Stage patch verification failed: {result.report.summary()}"
    assert result.report.summary()["PASSED"] == 8
