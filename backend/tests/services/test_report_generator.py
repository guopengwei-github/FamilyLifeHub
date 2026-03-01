"""
Tests for report generator.
"""
import pytest
from datetime import date
from unittest.mock import MagicMock, AsyncMock, patch


class TestReportGenerator:
    """Test report generator."""

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.generate = AsyncMock(return_value="# 晨间报告\n\n这是测试报告内容")
        provider.model_name = "test-model"
        return provider

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_generate_morning_report(self, mock_llm_provider, mock_db):
        """Should generate morning report."""
        with patch('app.services.report_generator.aggregate_morning_report_data') as mock_agg:
            mock_agg.return_value = {
                'sleep_data': None,
                'hrv_data': None,
                'body_battery': None,
                'activity_data': None,
                'user_profile': None
            }

            from app.services.report_generator import generate_morning_report

            result = await generate_morning_report(
                db=mock_db,
                user_id=1,
                report_date=date(2026, 3, 1),
                llm_provider=mock_llm_provider
            )

            assert result is not None
            assert result['report_type'] == 'morning'
            assert 'content' in result

    @pytest.mark.asyncio
    async def test_generate_evening_report(self, mock_llm_provider, mock_db):
        """Should generate evening report."""
        with patch('app.services.report_generator.aggregate_evening_report_data') as mock_agg:
            mock_agg.return_value = {
                'heart_rate_data': None,
                'stress_data': None,
                'body_battery': None,
                'activity_data': None,
                'user_profile': None
            }

            from app.services.report_generator import generate_evening_report

            result = await generate_evening_report(
                db=mock_db,
                user_id=1,
                report_date=date(2026, 3, 1),
                llm_provider=mock_llm_provider
            )

            assert result is not None
            assert result['report_type'] == 'evening'
            assert 'content' in result

    @pytest.mark.asyncio
    async def test_generate_report_returns_model_info(self, mock_llm_provider, mock_db):
        """Should include model info in result."""
        with patch('app.services.report_generator.aggregate_morning_report_data') as mock_agg:
            mock_agg.return_value = {
                'sleep_data': None,
                'hrv_data': None,
                'body_battery': None,
                'activity_data': None,
                'user_profile': None
            }

            from app.services.report_generator import generate_morning_report

            result = await generate_morning_report(
                db=mock_db,
                user_id=1,
                report_date=date(2026, 3, 1),
                llm_provider=mock_llm_provider
            )

            assert result['llm_model'] == "test-model"
