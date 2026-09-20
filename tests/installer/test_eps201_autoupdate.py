"""End-to-End integration test suite for EPS-201: Edge Installer Auto-Update.

Gated by the ``RUN_INSTALLER_E2E=1`` environment variable. Requires a running
Nexus repository and target Edge Installer nodes (192.168.10.190 / 192.168.10.114).

Execution commands:
  Locally (skipped):
    pytest tests/installer/test_eps201_autoupdate.py -v

  With Live Nexus Image Publication:
    $env:RUN_INSTALLER_E2E="1"
    pytest tests/installer/test_eps201_autoupdate.py -v
"""

from __future__ import annotations

import os
import pytest

from flows.installer.eps201_autoupdate_flow import (
    run_eps201_flow,
    run_tc01_version_and_hosts,
    run_tc02_nexus_manifest,
    run_tc03_primary_update,
    run_tc04_secondary_update,
    run_tc05_health_and_persistence,
    run_tc06_rollback_verification,
)


_INSTALLER_E2E_ENABLED = os.getenv("RUN_INSTALLER_E2E", "0").lower() in {"1", "true", "yes", "on"}


def _skip_unless_enabled() -> None:
    if not _INSTALLER_E2E_ENABLED:
        pytest.skip(
            "EPS-201 Installer E2E test requires $env:RUN_INSTALLER_E2E=1 "
            "and live Nexus container image publication"
        )


@pytest.mark.installer
@pytest.mark.eps201
class TestEps201InstallerAutoUpdateE2E:
    """End-to-End test suite for Edge Installer v2.7.1 Auto-Update."""

    def test_tc01_installer_version_and_hosts(self):
        """TC-01: Verify installer version v2.7.1 and edge host environments."""
        _skip_unless_enabled()
        res = run_tc01_version_and_hosts()
        assert res.summary["installer_version"] == "v2.7.1"

    def test_tc02_nexus_image_published(self):
        """TC-02: Check image published on Nexus repository."""
        _skip_unless_enabled()
        res = run_tc02_nexus_manifest(image_tag="v2.7.1-patch1")
        assert res.summary["digest"].startswith("sha256:")

    def test_tc03_primary_node_autoupdate(self):
        """TC-03: Execute auto-update on primary host 192.168.10.190."""
        _skip_unless_enabled()
        res = run_tc03_primary_update(image_tag="v2.7.1-patch1")
        assert res.summary["host"] == "192.168.10.190"

    def test_tc04_secondary_node_autoupdate(self):
        """TC-04: Execute auto-update on secondary host 192.168.10.114."""
        _skip_unless_enabled()
        res = run_tc04_secondary_update(image_tag="v2.7.1-patch1")
        assert res.summary["host"] == "192.168.10.114"

    def test_tc05_health_and_persistent_volumes(self):
        """TC-05: Verify post-update health (HTTP 200) and persistent data intact."""
        _skip_unless_enabled()
        res = run_tc05_health_and_persistence(image_tag="v2.7.1-patch1")
        assert res.summary["status"] == "HEALTHY"
        assert res.summary["data_persistence"] is True

    def test_tc06_rollback_on_faulty_image(self):
        """TC-06: Verify automated rollback when container fails healthcheck."""
        _skip_unless_enabled()
        res = run_tc06_rollback_verification(prior_tag="v2.7.1")
        assert res.summary["status"] == "ROLLED_BACK"

    def test_unified_autoupdate_e2e_pipeline(self):
        """Run all 6 scenarios in sequence as complete E2E pipeline."""
        _skip_unless_enabled()
        results = run_eps201_flow()
        assert len(results) == 6
        for r in results:
            assert r.report.summary().get("FAILED", 0) == 0
