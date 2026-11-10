r"""E2E Stage Patch Verification Test Suite for stage patch.

Tests Core services on stage server (stage.example.test) after patch deployment:
- Identity Service Authentication with stage-admin credentials
- Core Inbound Query API
- MinIO Presigned URL generation
- Bag & Dispatch Storage
- Operational Results Storage
- Edge Health Monitoring & Heartbeat Ingestion
- Sorting Device Management Registration

Run live with:
  $env:RUN_STAGE="1"
  .venv\Scripts\python.exe -m pytest tests/stage/test_stage_patch.py -v -s
"""

from __future__ import annotations

import os
import pytest

from config.settings import settings
from flows.stage.stage_patch_flow import run_stage_patch_flow


@pytest.mark.stage
@pytest.mark.stage_patch
def test_stage_patch_verification():
    """Verify all 8 Core API endpoints on the stage server (stage.example.test) post-patch."""
    if not os.getenv("RUN_STAGE") and not os.getenv("STAGE_SERVER_URL"):
        pytest.skip(
            "Stage test skipped: Set RUN_STAGE=1 or STAGE_SERVER_URL to execute against live stage server (stage.example.test)"
        )

    result = run_stage_patch_flow(run_settings=settings)

    assert result is not None
    assert result.report is not None
    assert result.report.summary()["FAILED"] == 0, f"Stage patch verification failed: {result.report.summary()}"
    assert result.report.summary()["PASSED"] == 8
