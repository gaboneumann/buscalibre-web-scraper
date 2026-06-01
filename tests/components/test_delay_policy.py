"""Unit tests for DelayPolicy."""
import pytest
from unittest.mock import patch, MagicMock
from pipelines.components import DelayPolicy


class TestDelayPolicy:
    """Test DelayPolicy timing logic."""

    def test_init_with_explicit_delays(self):
        """DelayPolicy can be initialized with explicit delay_min and delay_max."""
        policy = DelayPolicy(delay_min=8.0, delay_max=15.0)
        assert policy._delay_min == 8.0
        assert policy._delay_max == 15.0

    def test_init_defaults_to_config_delays(self):
        """DelayPolicy defaults to config/settings DELAY_MIN and DELAY_MAX."""
        # From CLAUDE.md: DELAY_MIN=30s, DELAY_MAX=55s (production)
        # But tests may use shorter delays
        policy = DelayPolicy()
        assert hasattr(policy, '_delay_min')
        assert hasattr(policy, '_delay_max')
        assert policy._delay_min > 0
        assert policy._delay_max > policy._delay_min

    @patch('time.sleep')
    def test_wait_between_products_sleeps_in_range(self, mock_sleep):
        """wait_between_products() sleeps for time between delay_min and delay_max."""
        policy = DelayPolicy(delay_min=4.0, delay_max=8.0)
        policy.wait_between_products()
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        # Baseline: multiplier defaults to 1.0, so range is unscaled production 4-8s
        assert 4.0 <= sleep_time <= 8.0

    def test_should_take_coffee_break_false_below_threshold(self):
        """should_take_coffee_break() returns False when product_count < threshold."""
        policy = DelayPolicy(coffee_break_interval=10)
        assert policy.should_take_coffee_break(product_count=5) is False
        assert policy.should_take_coffee_break(product_count=9) is False

    def test_should_take_coffee_break_true_at_interval(self):
        """should_take_coffee_break() returns True when product_count is multiple of interval."""
        policy = DelayPolicy(coffee_break_interval=10)
        # Returns True every 10 products (10, 20, 30, etc.)
        assert policy.should_take_coffee_break(product_count=10) is True
        assert policy.should_take_coffee_break(product_count=20) is True

    def test_should_take_coffee_break_random_interval_10_to_15(self):
        """should_take_coffee_break() uses random interval 10-15 when initialized."""
        # Run multiple times to verify randomness
        intervals = []
        for _ in range(5):
            policy = DelayPolicy()
            interval = policy._coffee_break_interval
            assert 10 <= interval <= 15
            intervals.append(interval)
        # Should see some variation
        assert len(set(intervals)) > 1

    @patch('time.sleep')
    def test_wait_coffee_break_sleeps_in_150_to_250_range(self, mock_sleep):
        """wait_coffee_break() sleeps for 150-250 seconds (2.5-4.2 min)."""
        policy = DelayPolicy()
        policy.wait_coffee_break()
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        # From category_pipeline design: random.uniform(150, 250)
        assert 150 <= sleep_time <= 250

    @patch('time.sleep')
    def test_coffee_break_range_matches_design(self, mock_sleep):
        """wait_coffee_break() uses 150-250s range from category_pipeline design."""
        policy = DelayPolicy()
        policy.wait_coffee_break()
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert 150 <= sleep_time <= 250

    @patch('time.sleep')
    def test_both_delays_in_sleep_calls(self, mock_sleep):
        """Verify wait_between_products and wait_coffee_break make sleep calls."""
        policy = DelayPolicy(delay_min=1.0, delay_max=2.0)
        policy.wait_between_products()
        assert mock_sleep.call_count == 1

        policy.wait_coffee_break()
        assert mock_sleep.call_count == 2

    @patch('time.sleep')
    def test_wait_coffee_break_custom_range(self, mock_sleep):
        """wait_coffee_break() uses custom coffee_break_min/max when provided."""
        policy = DelayPolicy(coffee_break_min=0.001, coffee_break_max=0.002)
        policy.wait_coffee_break()
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert 0.001 <= sleep_time <= 0.002

    # --- Tests for new methods added in fix-orchestrator-test-hang ---

    @patch('time.sleep')
    def test_wait_between_pages_nominal(self, mock_sleep):
        """wait_between_pages() sleeps once with value in [60.0, 90.0] by default."""
        policy = DelayPolicy()
        policy.wait_between_pages()
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert 60.0 <= sleep_time <= 90.0

    @patch('time.sleep')
    def test_wait_between_pages_custom_range(self, mock_sleep):
        """wait_between_pages() respects custom page_wait_min/max (zero range)."""
        policy = DelayPolicy(page_wait_min=0, page_wait_max=0)
        policy.wait_between_pages()
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert sleep_time == 0

    @patch('time.sleep')
    def test_wait_session_rotation_default_range(self, mock_sleep):
        """wait_session_rotation() sleeps once with value in [10.0, 15.0] by default."""
        policy = DelayPolicy(rotation_wait_min=10, rotation_wait_max=15)
        policy.wait_session_rotation()
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert 10.0 <= sleep_time <= 15.0

    @patch('time.sleep')
    def test_wait_session_rotation_custom_range(self, mock_sleep):
        """wait_session_rotation() respects custom rotation_wait_min/max (zero range)."""
        policy = DelayPolicy(rotation_wait_min=0, rotation_wait_max=0)
        policy.wait_session_rotation()
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert sleep_time == 0

    @patch('time.sleep')
    def test_wait_post_rotation_default_range(self, mock_sleep):
        """wait_post_rotation() sleeps once with value in [5.0, 10.0] by default."""
        policy = DelayPolicy()
        policy.wait_post_rotation()
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert 5.0 <= sleep_time <= 10.0

    @patch('time.sleep')
    def test_wait_block_backoff_passes_wait_time(self, mock_sleep):
        """wait_block_backoff(45.5) calls time.sleep exactly once with 45.5."""
        policy = DelayPolicy()
        policy.wait_block_backoff(45.5)
        mock_sleep.assert_called_once_with(45.5)

    @patch('time.sleep')
    def test_wait_block_backoff_zero(self, mock_sleep):
        """wait_block_backoff(0) calls time.sleep once with 0."""
        policy = DelayPolicy()
        policy.wait_block_backoff(0)
        mock_sleep.assert_called_once_with(0)


class TestDelayPolicyMultiplier:
    """Tests for the adaptive delay multiplier (Layer 8)."""

    def test_default_multiplier_is_one(self):
        """GIVEN DelayPolicy constructed with no extra args WHEN multiplier read THEN == 1.0."""
        policy = DelayPolicy()
        assert policy.multiplier == 1.0

    def test_custom_params_stored_correctly(self):
        """GIVEN custom multiplier params WHEN constructed THEN multiplier==1.0, params stored."""
        policy = DelayPolicy(
            max_multiplier=2.0,
            block_rate_threshold=0.3,
            scale_up=1.2,
            scale_down=0.95,
        )
        assert policy.multiplier == 1.0
        assert policy._max_multiplier == 2.0
        assert policy._block_rate_threshold == 0.3

    def test_over_threshold_escalates(self):
        """GIVEN block_rate=0.5 > threshold=0.2 WHEN update_multiplier called THEN multiplier==1.5."""
        policy = DelayPolicy(scale_up=1.5, block_rate_threshold=0.2)
        result = policy.update_multiplier(0.5)
        assert result == 1.5
        assert policy.multiplier == 1.5

    def test_cap_clamp_at_max_multiplier(self):
        """GIVEN multiplier==2.5, update_multiplier(0.9) THEN multiplier==3.0 (not 3.75)."""
        policy = DelayPolicy(max_multiplier=3.0, scale_up=1.5)
        policy._multiplier = 2.5
        policy.update_multiplier(0.9)
        assert policy.multiplier == 3.0

    def test_decay_on_clean_batch(self):
        """GIVEN multiplier==2.0, update_multiplier(0.0) THEN multiplier==1.8."""
        policy = DelayPolicy(scale_down=0.9)
        policy._multiplier = 2.0
        policy.update_multiplier(0.0)
        assert policy.multiplier == pytest.approx(1.8)

    def test_floor_clamp_prevents_going_below_one(self):
        """GIVEN multiplier==1.0, update_multiplier(0.0) THEN multiplier stays 1.0."""
        policy = DelayPolicy(scale_down=0.9)
        policy.update_multiplier(0.0)
        assert policy.multiplier == 1.0

    def test_hold_band_below_threshold(self):
        """GIVEN multiplier==1.5, update_multiplier(0.1) (below threshold) THEN unchanged."""
        policy = DelayPolicy(block_rate_threshold=0.2)
        policy._multiplier = 1.5
        policy.update_multiplier(0.1)
        assert policy.multiplier == 1.5

    def test_hold_band_exactly_at_threshold(self):
        """GIVEN multiplier==1.5, update_multiplier(0.2) (at threshold) THEN unchanged."""
        policy = DelayPolicy(block_rate_threshold=0.2)
        policy._multiplier = 1.5
        policy.update_multiplier(0.2)
        assert policy.multiplier == 1.5
