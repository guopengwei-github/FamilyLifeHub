"""
Tests for report data aggregator.
"""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock

from app.services.report_data_aggregator import (
    aggregate_morning_report_data,
    aggregate_evening_report_data
)


class TestAggregateMorningReportData:
    """Test morning report data aggregation."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock()

    def test_returns_dict_with_expected_keys(self, mock_db):
        """Should return dict with all expected keys."""
        result = aggregate_morning_report_data(
            db=mock_db,
            user_id=1,
            report_date=date(2026, 3, 1)
        )

        assert 'sleep_data' in result
        assert 'hrv_data' in result
        assert 'body_battery' in result
        assert 'sleep_metrics' in result  # NEW: sleep period metrics
        assert 'activity_data' in result
        assert 'user_profile' in result

    def test_handles_missing_user(self, mock_db):
        """Should handle missing user gracefully."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = aggregate_morning_report_data(
            db=mock_db,
            user_id=999,
            report_date=date(2026, 3, 1)
        )

        assert result['user_profile'] is None


class TestAggregateEveningReportData:
    """Test evening report data aggregation."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock()

    def test_returns_dict_with_expected_keys(self, mock_db):
        """Should return dict with all expected keys."""
        result = aggregate_evening_report_data(
            db=mock_db,
            user_id=1,
            report_date=date(2026, 3, 1)
        )

        assert 'heart_rate_data' in result
        assert 'stress_data' in result
        assert 'body_battery' in result
        assert 'activity_data' in result
        assert 'user_profile' in result
        assert 'resting_hr' in result  # NEW: resting heart rate
