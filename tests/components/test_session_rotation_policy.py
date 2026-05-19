"""Unit tests for SessionRotationPolicy."""
import pytest
from pipelines.components import SessionRotationPolicy


class TestSessionRotationPolicy:
    """Test SessionRotationPolicy decision logic."""

    def test_should_rotate_returns_false_below_threshold(self):
        """should_rotate() returns False when products_in_session < threshold."""
        policy = SessionRotationPolicy(threshold=3)
        assert policy.should_rotate(products_in_session=1) is False
        assert policy.should_rotate(products_in_session=2) is False

    def test_should_rotate_returns_true_at_threshold(self):
        """should_rotate() returns True when products_in_session >= threshold."""
        policy = SessionRotationPolicy(threshold=3)
        assert policy.should_rotate(products_in_session=3) is True
        assert policy.should_rotate(products_in_session=4) is True

    def test_should_rotate_with_random_threshold(self):
        """should_rotate() handles random thresholds (2-4 range)."""
        for threshold in [2, 3, 4]:
            policy = SessionRotationPolicy(threshold=threshold)
            assert policy.should_rotate(products_in_session=threshold - 1) is False
            assert policy.should_rotate(products_in_session=threshold) is True

    def test_on_rotation_returns_wait_times(self):
        """on_rotation() returns (wait_min, wait_max) tuple."""
        policy = SessionRotationPolicy(threshold=3)
        wait_min, wait_max = policy.on_rotation()
        assert isinstance(wait_min, (int, float))
        assert isinstance(wait_max, (int, float))
        assert wait_min > 0
        assert wait_max > wait_min

    def test_on_rotation_wait_range_matches_design(self):
        """on_rotation() returns 10-15s range (from arte_pipeline design)."""
        policy = SessionRotationPolicy(threshold=3)
        wait_min, wait_max = policy.on_rotation()
        # From arte_pipeline.py line 154: time.sleep(random.uniform(10, 15))
        assert wait_min == 10
        assert wait_max == 15

    def test_init_with_explicit_threshold(self):
        """SessionRotationPolicy can be initialized with explicit threshold."""
        policy = SessionRotationPolicy(threshold=2)
        assert policy.should_rotate(products_in_session=2) is True

    def test_init_with_random_threshold_in_valid_range(self):
        """SessionRotationPolicy init with random=True generates 2-4 threshold."""
        # Run multiple times to check randomness is within bounds
        thresholds = []
        for _ in range(10):
            policy = SessionRotationPolicy(random_threshold=True)
            threshold = policy._threshold
            assert 2 <= threshold <= 4
            thresholds.append(threshold)
        # Should see some variation (not all same threshold)
        assert len(set(thresholds)) > 1

    def test_default_threshold_is_random_2_to_4(self):
        """SessionRotationPolicy defaults to random threshold 2-4 when not specified."""
        policy = SessionRotationPolicy()
        threshold = policy._threshold
        assert 2 <= threshold <= 4

    def test_on_rotation_returns_custom_wait_times(self):
        """on_rotation() returns custom rotation_wait_min/max when provided."""
        policy = SessionRotationPolicy(threshold=3, rotation_wait_min=5, rotation_wait_max=8)
        assert policy.on_rotation() == (5, 8)
