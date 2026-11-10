"""Pace deliberately failed authentication attempts in one pytest process.

The deployed Edge allows five unsuccessful requests per minute. Keep the QA
suite below that ceiling, including failures from separate config sync/device lifecycle tests.
This cannot account for traffic from other machines or concurrent test runs.
"""

from collections import deque
from threading import Lock
import time
from typing import Callable, TypeVar


_T = TypeVar("_T")
_WINDOW_SECONDS = 60.0
_MAX_TEST_ATTEMPTS = 4  # Leave one of the five backend slots unused.
_SAFETY_SECONDS = 1.0
_attempts: deque[float] = deque()
_lock = Lock()


def pace_expected_auth_failure(
    action: Callable[[], _T],
    *,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> _T:
    """Reserve one slot before a negative login/Auth, even if it raises."""
    with _lock:
        now = clock()
        while _attempts and now - _attempts[0] >= _WINDOW_SECONDS:
            _attempts.popleft()
        if len(_attempts) >= _MAX_TEST_ATTEMPTS:
            wait = _attempts[0] + _WINDOW_SECONDS + _SAFETY_SECONDS - now
            if wait > 0:
                print(f"[auth-pacing] Waiting {wait:.1f}s before the next negative authentication", flush=True)
                sleep(wait)
            now = clock()
            while _attempts and now - _attempts[0] >= _WINDOW_SECONDS:
                _attempts.popleft()
        _attempts.append(now)
    return action()
