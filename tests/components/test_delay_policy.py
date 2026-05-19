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
        policy = DelayPolicy(delay_min=8.0, delay_max=15.0)
        policy.wait_between_products()
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert 8.0 <= sleep_time <= 15.0

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
        # From arte_pipeline.py line 197: random.uniform(150, 250)
        assert 150 <= sleep_time <= 250

    @patch('time.sleep')
    def test_coffee_break_range_matches_design(self, mock_sleep):
        """wait_coffee_break() uses 150-250s range from arte_pipeline design."""
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
