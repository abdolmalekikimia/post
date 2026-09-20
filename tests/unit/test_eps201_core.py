"""Unit tests for EPS-201: Edge Installer Auto-Update End-to-End Testing."""

import pytest

from assertions.eps201_installer_assertions import (
    EXPECTED_EDGE_HOSTS,
    EXPECTED_MIN_INSTALLER_VERSION,
    assert_autoupdate_detection,
    assert_edge_target_host_valid,
    assert_installer_version,
    assert_nexus_image_manifest,
    assert_post_update_health,
    assert_rollback_successful,
)
from flows.installer.eps201_autoupdate_flow import (
    EPS201_CASES,
    build_eps201_cases,
    run_eps201_flow,
    run_tc01_version_and_hosts,
    run_tc02_nexus_manifest,
    run_tc03_primary_update,
    run_tc04_secondary_update,
    run_tc05_health_and_persistence,
    run_tc06_rollback_verification,
)


# ---------------------------------------------------------------------------
# TC-1: Case catalogue completeness
# ---------------------------------------------------------------------------

def test_eps201_case_catalog_contains_six_scenarios():
    cases = build_eps201_cases()
    case_ids = [c.case_id for c in cases]
    assert case_ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06"]
    assert len(case_ids) == len(set(case_ids))


def test_eps201_case_categories_match():
    cats = {c.case_id: c.category for c in EPS201_CASES}
    assert cats["TC-01"] == "version_check"
    assert cats["TC-02"] == "nexus_publish"
    assert cats["TC-03"] == "primary_update"
    assert cats["TC-04"] == "secondary_update"
    assert cats["TC-05"] == "health_persistence"
    assert cats["TC-06"] == "rollback_verify"


# ---------------------------------------------------------------------------
# TC-2: Installer version assertions
# ---------------------------------------------------------------------------

def test_installer_version_passes_for_v2_7_1():
    assert_installer_version("v2.7.1")
    assert_installer_version("2.7.1")
    assert_installer_version("v2.8.0")
    assert_installer_version("v3.0.0")


def test_installer_version_fails_for_older_versions():
    with pytest.raises(AssertionError, match="older than required minimum"):
        assert_installer_version("v2.7.0")

    with pytest.raises(AssertionError, match="older than required minimum"):
        assert_installer_version("v2.6.9")

    with pytest.raises(AssertionError, match="older than required minimum"):
        assert_installer_version("v1.9.9")


def test_installer_version_fails_for_invalid_format():
    with pytest.raises(AssertionError, match="does not match semver format"):
        assert_installer_version("invalid-version")

    with pytest.raises(AssertionError, match="must be string"):
        assert_installer_version(271)


# ---------------------------------------------------------------------------
# TC-3: Target host IP assertions
# ---------------------------------------------------------------------------

def test_edge_target_hosts_pass():
    assert_edge_target_host_valid("192.168.10.190")
    assert_edge_target_host_valid("192.168.10.114")


def test_edge_target_hosts_fail_for_unknown():
    with pytest.raises(AssertionError, match="not in verified environments"):
        assert_edge_target_host_valid("192.168.10.999")

    with pytest.raises(AssertionError, match="not in verified environments"):
        assert_edge_target_host_valid("10.0.0.99")


# ---------------------------------------------------------------------------
# TC-4: Nexus manifest assertions
# ---------------------------------------------------------------------------

def test_nexus_manifest_passes():
    manifest = {
        "name": "edge-core",
        "tag": "v2.7.1",
        "digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
    }
    assert_nexus_image_manifest(manifest, "edge-core", "v2.7.1")


def test_nexus_manifest_fails_on_tag_mismatch():
    manifest = {
        "name": "edge-core",
        "tag": "v2.7.0",
        "digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
    }
    with pytest.raises(AssertionError, match="expected tag"):
        assert_nexus_image_manifest(manifest, "edge-core", "v2.7.1")


def test_nexus_manifest_fails_on_missing_digest():
    manifest = {"name": "edge-core", "tag": "v2.7.1", "digest": "md5:123"}
    with pytest.raises(AssertionError, match="missing or invalid OCI digest"):
        assert_nexus_image_manifest(manifest, "edge-core", "v2.7.1")


# ---------------------------------------------------------------------------
# TC-5: AutoUpdate detection assertions
# ---------------------------------------------------------------------------

def test_autoupdate_detection_passes():
    event = {"status": "COMPLETED", "targetTag": "v2.7.1-patch1"}
    assert_autoupdate_detection(event, "v2.7.1-patch1")


def test_autoupdate_detection_fails_on_tag_mismatch():
    event = {"status": "COMPLETED", "targetTag": "v2.7.0"}
    with pytest.raises(AssertionError, match="expected targetTag"):
        assert_autoupdate_detection(event, "v2.7.1-patch1")


# ---------------------------------------------------------------------------
# TC-6: Post-update health and persistence assertions
# ---------------------------------------------------------------------------

def test_post_update_health_passes():
    health = {
        "status": "HEALTHY",
        "statusCode": 200,
        "imageTag": "v2.7.1-patch1",
        "dataPersistenceVerified": True,
    }
    assert_post_update_health(health, "v2.7.1-patch1")


def test_post_update_health_fails_on_unhealthy():
    health = {"status": "UNHEALTHY", "statusCode": 500, "imageTag": "v2.7.1-patch1"}
    with pytest.raises(AssertionError, match="service status is not healthy"):
        assert_post_update_health(health, "v2.7.1-patch1")


def test_post_update_health_fails_on_data_loss():
    health = {
        "status": "HEALTHY",
        "statusCode": 200,
        "imageTag": "v2.7.1-patch1",
        "dataPersistenceVerified": False,
    }
    with pytest.raises(AssertionError, match="data persistence check failed"):
        assert_post_update_health(health, "v2.7.1-patch1")


# ---------------------------------------------------------------------------
# TC-7: Rollback assertions
# ---------------------------------------------------------------------------

def test_rollback_passes():
    event = {"status": "ROLLED_BACK", "currentTag": "v2.7.0"}
    assert_rollback_successful(event, "v2.7.0")


def test_rollback_fails_on_wrong_tag():
    event = {"status": "ROLLED_BACK", "currentTag": "v2.7.1-broken"}
    with pytest.raises(AssertionError, match="expected fallback to"):
        assert_rollback_successful(event, "v2.7.0")


# ---------------------------------------------------------------------------
# TC-8: BDD flow execution (mock / unit)
# ---------------------------------------------------------------------------

def test_tc01_version_and_hosts_runs():
    res = run_tc01_version_and_hosts()
    assert res.case.case_id == "TC-01"
    assert res.summary["installer_version"] == "v2.7.1"
    assert len(res.report.records) == 3


def test_tc02_nexus_manifest_runs():
    res = run_tc02_nexus_manifest()
    assert res.case.case_id == "TC-02"
    assert res.summary["digest"].startswith("sha256:")
    assert len(res.report.records) == 1


def test_tc03_primary_update_runs():
    res = run_tc03_primary_update()
    assert res.case.case_id == "TC-03"
    assert res.summary["host"] in ("192.168.10.190", "localhost", "127.0.0.1")
    assert len(res.report.records) == 1


def test_tc04_secondary_update_runs():
    res = run_tc04_secondary_update()
    assert res.case.case_id == "TC-04"
    assert res.summary["host"] in ("192.168.10.114", "localhost", "127.0.0.1")
    assert len(res.report.records) == 1


def test_tc05_health_and_persistence_runs():
    res = run_tc05_health_and_persistence()
    assert res.case.case_id == "TC-05"
    assert res.summary["status"] == "HEALTHY"
    assert res.summary["data_persistence"] is True


def test_tc06_rollback_verification_runs():
    res = run_tc06_rollback_verification()
    assert res.case.case_id == "TC-06"
    assert res.summary["status"] == "ROLLED_BACK"


def test_unified_flow_runs_all_six():
    results = run_eps201_flow()
    assert len(results) == 6
    ids = [r.case.case_id for r in results]
    assert ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06"]
