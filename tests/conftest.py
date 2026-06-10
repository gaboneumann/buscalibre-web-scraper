"""Shared pytest fixtures for the whole test suite."""
import pytest


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Neutralize real ``time.sleep`` across the suite.

    Production anti-detection pauses (``DelayPolicy`` waits, block-detection
    backoff, and ``HTTPClient._initialize_session`` home->category pauses) leak
    into tests that mock the browser but not the clock. They are real seconds —
    one block-backoff test alone slept ~315s — which pushed the suite to ~8 min
    with zero added coverage.

    No test asserts on real elapsed wall-time; the few that inspect sleep
    arguments apply their own ``@patch('time.sleep')``, which shadows this
    fixture for their duration and restores to this no-op afterwards.
    """
    monkeypatch.setattr("time.sleep", lambda *args, **kwargs: None)
