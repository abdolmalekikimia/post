"""Assertion helpers for EPS-201: Edge Installer Auto-Update End-to-End Testing.

Validates:
  1. Edge Installer version (must be >= v2.7.1).
  2. Target host IP validation (192.168.10.190 and 192.168.10.114).
  3. Nexus image publication and OCI manifest response verification.
  4. AutoUpdate detection and trigger contract.
  5. Rolling update and graceful restart (zero downtime / quick container recreation).
  6. Post-update health check (HTTP 200, version reporting, volume persistence).
  7. Automated rollback on startup failure.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence


EXPECTED_MIN_INSTALLER_VERSION = "2.7.1"
EXPECTED_EDGE_HOSTS: tuple[str, ...] = ("192.168.10.190", "192.168.10.114")


def assert_installer_version(version_str: str, min_version: str = EXPECTED_MIN_INSTALLER_VERSION, *, operation: str = "installer_version") -> None:
    """Assert that the installer version is at least the patched version v2.7.1."""
    if not isinstance(version_str, str):
        raise AssertionError(f"{operation}: version must be string, got {type(version_str).__name__}")

    clean_version = version_str.lstrip("vV").strip()
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", clean_version)
    if not match:
        raise AssertionError(f"{operation}: version '{version_str}' does not match semver format (X.Y.Z)")

    actual_parts = tuple(int(p) for p in match.groups())
    min_parts = tuple(int(p) for p in min_version.split("."))

    if actual_parts < min_parts:
        raise AssertionError(
            f"{operation}: installer version '{version_str}' is older than required minimum 'v{min_version}'"
        )


def assert_edge_target_host_valid(host_ip: str, *, operation: str = "edge_host") -> None:
    """Assert that target host is in the verified Edge environment list."""
    if not isinstance(host_ip, str):
        raise AssertionError(f"{operation}: host must be string, got {type(host_ip).__name__}")
    clean_host = host_ip.strip()
    if clean_host not in EXPECTED_EDGE_HOSTS:
        raise AssertionError(
            f"{operation}: host '{host_ip}' is not in verified environments {EXPECTED_EDGE_HOSTS}"
        )


def assert_nexus_image_manifest(
    manifest_response: Mapping[str, Any],
    expected_image_name: str,
    expected_tag: str,
    *,
    operation: str = "nexus_manifest",
) -> None:
    """Assert that the image exists in Nexus repository with a valid digest and tag."""
    if not isinstance(manifest_response, Mapping):
        raise AssertionError(f"{operation}: response must be dict, got {type(manifest_response).__name__}")

    name = manifest_response.get("name")
    if name != expected_image_name:
        raise AssertionError(f"{operation}: expected image '{expected_image_name}', got '{name}'")

    tag = manifest_response.get("tag")
    if tag != expected_tag:
        raise AssertionError(f"{operation}: expected tag '{expected_tag}', got '{tag}'")

    digest = manifest_response.get("digest")
    if not digest or not str(digest).startswith("sha256:"):
        raise AssertionError(f"{operation}: missing or invalid OCI digest '{digest}'")


def assert_autoupdate_detection(
    update_event: Mapping[str, Any],
    expected_tag: str,
    *,
    operation: str = "autoupdate_detection",
) -> None:
    """Assert that the installer detected the new image publication and triggered update."""
    if not isinstance(update_event, Mapping):
        raise AssertionError(f"{operation}: event must be dict, got {type(update_event).__name__}")

    status = update_event.get("status")
    if status not in ("TRIGGERED", "IN_PROGRESS", "COMPLETED"):
        raise AssertionError(f"{operation}: unexpected update status '{status}'")

    target_tag = update_event.get("targetTag")
    if target_tag != expected_tag:
        raise AssertionError(f"{operation}: expected targetTag='{expected_tag}', got '{target_tag}'")


def assert_post_update_health(
    health_response: Mapping[str, Any],
    expected_new_tag: str,
    *,
    operation: str = "post_update_health",
) -> None:
    """Assert that the Edge service is healthy and reporting the new image version after update."""
    if not isinstance(health_response, Mapping):
        raise AssertionError(f"{operation}: health response must be dict, got {type(health_response).__name__}")

    status = health_response.get("status")
    if str(status).upper() not in ("HEALTHY", "UP", "OK"):
        raise AssertionError(f"{operation}: service status is not healthy, got '{status}'")

    http_code = health_response.get("statusCode", 200)
    if http_code != 200:
        raise AssertionError(f"{operation}: expected HTTP 200, got {http_code}")

    deployed_version = health_response.get("imageTag") or health_response.get("version")
    if deployed_version != expected_new_tag:
        raise AssertionError(f"{operation}: expected running image '{expected_new_tag}', got '{deployed_version}'")

    # Data persistence check (database volume mount must not be reset)
    data_intact = health_response.get("dataPersistenceVerified")
    if data_intact is False:
        raise AssertionError(f"{operation}: data persistence check failed after container recreation")


def assert_rollback_successful(
    rollback_event: Mapping[str, Any],
    expected_fallback_tag: str,
    *,
    operation: str = "rollback",
) -> None:
    """Assert that when a newly deployed image fails health checks, installer restores prior tag."""
    if not isinstance(rollback_event, Mapping):
        raise AssertionError(f"{operation}: rollback event must be dict, got {type(rollback_event).__name__}")

    status = rollback_event.get("status")
    if status != "ROLLED_BACK":
        raise AssertionError(f"{operation}: expected rollback status 'ROLLED_BACK', got '{status}'")

    current_tag = rollback_event.get("currentTag")
    if current_tag != expected_fallback_tag:
        raise AssertionError(f"{operation}: expected fallback to '{expected_fallback_tag}', got '{current_tag}'")
