"""Assertion helpers for EPS-181: Mock Environment Variable Generation for Negative Testing.

Validates:
  1. ASP.NET Core environment variable format (Double Underscores '__' for hierarchy).
  2. Completeness of mock negative profiles (PostalApi, CoreApi, AutoDispatchPolicy, Devices).
  3. Correct configuration values for negative conditions (Timeout, Rejected, Unavailable, Pending, Error, Discrepancy).
  4. Consistency of test data barcodes and parameters between env profiles and QA test cases.
"""

from __future__ import annotations

import re
from typing import Any, Mapping


# Standard ASP.NET Core configuration key regex (letters, numbers, and double underscores)
ASPNET_ENV_KEY_RE = re.compile(r"^[A-Za-z0-9]+(__[A-Za-z0-9]+)+$")

# Required negative scenarios defined for QA mock testing
REQUIRED_NEGATIVE_PROFILES: tuple[str, ...] = (
    "postal_timeout",
    "postal_rejected",
    "postal_unavailable",
    "postal_pending",
    "core_history_rejected",
    "core_history_timeout",
    "core_history_unavailable",
    "core_history_discrepancy",
    "autodispatch_invalid_deadline",
    "device_inactive",
    "parcel_bag_error",
)


def assert_aspnet_env_key_format(key: str, *, operation: str = "env_key") -> None:
    """Assert that a configuration key follows the ASP.NET Core environment variable naming convention."""
    if not isinstance(key, str):
        raise AssertionError(f"{operation}: key must be a string, got {type(key).__name__}")
    if not ASPNET_ENV_KEY_RE.match(key):
        raise AssertionError(
            f"{operation}: key '{key}' is not a valid ASP.NET Core env key. "
            f"Expected hierarchy separated by '__' (e.g., 'Integrations__CoreApi__Mock__Scenario')."
        )


def assert_mock_env_profile_valid(
    profile_name: str,
    env_vars: Mapping[str, str],
    *,
    operation: str = "mock_env_profile",
) -> None:
    """Assert that a mock environment variable profile is well-formed."""
    if not isinstance(env_vars, Mapping):
        raise AssertionError(f"{operation}: env_vars must be a mapping, got {type(env_vars).__name__}")
    if not env_vars:
        raise AssertionError(f"{operation}: profile '{profile_name}' must contain at least one environment variable.")

    for k, v in env_vars.items():
        assert_aspnet_env_key_format(k, operation=f"{operation}.key")
        if v is None:
            raise AssertionError(f"{operation}: value for key '{k}' must not be None.")


def assert_negative_scenario_profile_coverage(
    available_profiles: Mapping[str, Mapping[str, str]],
    *,
    required_profiles: tuple[str, ...] = REQUIRED_NEGATIVE_PROFILES,
    operation: str = "profile_coverage",
) -> None:
    """Assert that all required negative profiles are implemented."""
    missing = [req for req in required_profiles if req not in available_profiles]
    if missing:
        raise AssertionError(
            f"{operation}: missing required negative mock profiles: {missing}. "
            f"Available profiles: {sorted(available_profiles.keys())}"
        )


def assert_postal_scenario_override(
    env_vars: Mapping[str, str],
    barcode: str,
    expected_scenario: str,
    *,
    operation: str = "postal_override",
) -> None:
    """Assert that a specific barcode override exists for PostalApi mock."""
    expected_key = f"Integrations__PostalApi__Mock__ScenarioOverrides__{barcode}"
    actual = env_vars.get(expected_key)
    if actual != expected_scenario:
        raise AssertionError(
            f"{operation}: expected {expected_key}='{expected_scenario}', got '{actual}'"
        )


def assert_core_history_status(
    env_vars: Mapping[str, str],
    barcode: str,
    expected_status: str,
    *,
    operation: str = "core_history",
) -> None:
    """Assert that a specific history record status exists for CoreApi mock."""
    expected_key = f"Integrations__CoreApi__Mock__HistoryRecords__{barcode}__Status"
    actual = env_vars.get(expected_key)
    if actual != expected_status:
        raise AssertionError(
            f"{operation}: expected {expected_key}='{expected_status}', got '{actual}'"
        )


def assert_autodispatch_negative_deadline(
    env_vars: Mapping[str, str],
    center_code: str = "59544",
    *,
    operation: str = "autodispatch",
) -> None:
    """Assert that an invalid (negative or zero) deadline is configured in AutoDispatchPolicy."""
    key = f"Integrations__CoreApi__Mock__ConfigSnapshots__{center_code}__AutoDispatchPolicy__AllowedDeadline"
    val = env_vars.get(key)
    if not val:
        raise AssertionError(f"{operation}: missing {key} in env vars")
    is_negative = val.startswith("-")
    is_zero = val in ("00:00:00", "0")
    if not (is_negative or is_zero):
        raise AssertionError(
            f"{operation}: {key}='{val}' is not a negative or zero duration for negative testing."
        )
