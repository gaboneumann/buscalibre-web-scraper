"""Unit tests for BlockDetectionPolicy."""
import pytest
from pipelines.components import BlockDetectionPolicy


class TestBlockDetectionPolicy:
    """Test BlockDetectionPolicy consecutive failure tracking."""

    def test_init_creates_zero_consecutive_failures(self):
        """BlockDetectionPolicy starts with 0 consecutive failures."""
        policy = BlockDetectionPolicy(threshold=3)
        assert policy._consecutive_failures == 0

    def test_on_success_resets_consecutive_failures(self):
        """on_success() resets consecutive failure counter to 0."""
        policy = BlockDetectionPolicy(threshold=3)
        policy._consecutive_failures = 2
        policy.on_success()
        assert policy._consecutive_failures == 0

    def test_on_failure_increments_counter(self):
        """on_failure() increments consecutive failure counter."""
        policy = BlockDetectionPolicy(threshold=3)
        policy.on_failure()
        assert policy._consecutive_failures == 1
        policy.on_failure()
        assert policy._consecutive_failures == 2

    def test_on_failure_returns_abort_false_below_threshold(self):
        """on_failure() returns (False, wait_time) when counter < threshold."""
        policy = BlockDetectionPolicy(threshold=3)
        policy.on_failure()
        should_abort, wait_time = policy.on_failure()
        assert should_abort is False
        assert isinstance(wait_time, (int, float))
        assert wait_time > 0

    def test_on_failure_returns_abort_true_at_threshold(self):
        """on_failure() returns (True, wait_time) when counter >= threshold."""
        policy = BlockDetectionPolicy(threshold=3)
        policy.on_failure()
        policy.on_failure()
        should_abort, wait_time = policy.on_failure()
        assert should_abort is True
        assert isinstance(wait_time, (int, float))

    def test_on_failure_wait_time_range_matches_design(self):
        """on_failure() returns exponential backoff: 45s → 90s → 180s (±20% jitter)."""
        policy = BlockDetectionPolicy(threshold=3, backoff_base=45)
        # First failure: 45s * 2^0 = 45s (±20%)
        should_abort, wait_time = policy.on_failure()
        assert 36 <= wait_time <= 54  # 45 ± 20%

        # Second failure: 45s * 2^1 = 90s (±20%)
        should_abort, wait_time = policy.on_failure()
        assert 72 <= wait_time <= 108  # 90 ± 20%

    def test_threshold_3_is_default(self):
        """BlockDetectionPolicy defaults to threshold=3 (3 consecutive blocks = stop)."""
        policy = BlockDetectionPolicy()
        assert policy._threshold == 3

    def test_explicit_threshold_parameter(self):
        """BlockDetectionPolicy can be initialized with explicit threshold."""
        policy = BlockDetectionPolicy(threshold=2)
        policy.on_failure()
        should_abort, wait_time = policy.on_failure()
        assert should_abort is True

    def test_on_failure_after_successful_recovery(self):
        """After on_success(), counter resets so next failures start from 1."""
        policy = BlockDetectionPolicy(threshold=3)
        policy.on_failure()
        policy.on_failure()
        policy.on_success()  # Reset
        assert policy._consecutive_failures == 0
        should_abort, wait_time = policy.on_failure()
        assert should_abort is False

    def test_on_failure_wait_time_uses_custom_range(self):
        """on_failure() respects custom backoff_base (exponential backoff)."""
        policy = BlockDetectionPolicy(threshold=3, backoff_base=10)
        # First failure: 10s * 2^0 = 10s (±20%)
        _, wait_time = policy.on_failure()
        assert 8 <= wait_time <= 12  # 10 ± 20%
