"""
Tests for scheduler module.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestSchedulerFunctions:
    """Test scheduler functions."""

    @pytest.fixture(autouse=True)
    def reset_scheduler(self):
        """Reset scheduler before each test."""
        import app.tasks.scheduler as scheduler_module
        scheduler_module.scheduler = None
        yield
        scheduler_module.scheduler = None

    def test_start_scheduler_creates_jobs(self):
        """Start scheduler should create morning and evening jobs."""
        with patch('app.tasks.scheduler.AsyncIOScheduler') as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler

            from app.tasks.scheduler import start_scheduler

            start_scheduler()

            # Should add two jobs
            assert mock_scheduler.add_job.call_count == 2
            mock_scheduler.start.assert_called_once()

    def test_stop_scheduler(self):
        """Stop scheduler should shutdown."""
        with patch('app.tasks.scheduler.AsyncIOScheduler') as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler

            from app.tasks.scheduler import start_scheduler, stop_scheduler

            start_scheduler()
            stop_scheduler()

            mock_scheduler.shutdown.assert_called_once()

    def test_get_llm_provider(self):
        """Get LLM provider should return ZhipuProvider."""
        with patch('app.tasks.scheduler.settings') as mock_settings:
            mock_settings.ZHIPU_API_KEY = "test-key"
            mock_settings.ZHIPU_MODEL = "test-model"

            from app.tasks.scheduler import get_llm_provider

            provider = get_llm_provider()

            assert provider is not None
            assert provider.model_name == "test-model"
