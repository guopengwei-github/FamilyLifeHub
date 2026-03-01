"""
Tests for Zhipu GLM provider implementation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestZhipuProvider:
    """Test ZhipuProvider implementation."""

    @pytest.fixture
    def mock_zhipu_client(self):
        """Create a mock ZhipuAI client."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response from GLM"
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    def test_initialization_with_api_key(self, mock_zhipu_client):
        """ZhipuProvider should initialize with API key."""
        with patch('app.services.llm.zhipu.ZhipuAI', return_value=mock_zhipu_client):
            from app.services.llm.zhipu import ZhipuProvider
            provider = ZhipuProvider(api_key="test-api-key")
            assert provider.model_name == "glm-4-flash"

    def test_custom_model_name(self, mock_zhipu_client):
        """ZhipuProvider should accept custom model name."""
        with patch('app.services.llm.zhipu.ZhipuAI', return_value=mock_zhipu_client):
            from app.services.llm.zhipu import ZhipuProvider
            provider = ZhipuProvider(api_key="test-api-key", model="glm-4")
            assert provider.model_name == "glm-4"

    @pytest.mark.asyncio
    async def test_generate_basic(self, mock_zhipu_client):
        """generate should return LLM response."""
        with patch('app.services.llm.zhipu.ZhipuAI', return_value=mock_zhipu_client):
            from app.services.llm.zhipu import ZhipuProvider
            provider = ZhipuProvider(api_key="test-api-key")
            result = await provider.generate("Hello")
            assert result == "Test response from GLM"

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, mock_zhipu_client):
        """generate should include system prompt in request."""
        with patch('app.services.llm.zhipu.ZhipuAI', return_value=mock_zhipu_client):
            from app.services.llm.zhipu import ZhipuProvider
            provider = ZhipuProvider(api_key="test-api-key")
            await provider.generate("Hello", system_prompt="You are helpful")

            # Verify the call included system prompt
            call_args = mock_zhipu_client.chat.completions.create.call_args
            messages = call_args.kwargs['messages']
            assert len(messages) == 2
            assert messages[0]['role'] == 'system'
            assert messages[0]['content'] == "You are helpful"

    @pytest.mark.asyncio
    async def test_generate_with_max_tokens(self, mock_zhipu_client):
        """generate should pass max_tokens to API."""
        with patch('app.services.llm.zhipu.ZhipuAI', return_value=mock_zhipu_client):
            from app.services.llm.zhipu import ZhipuProvider
            provider = ZhipuProvider(api_key="test-api-key")
            await provider.generate("Hello", max_tokens=500)

            call_args = mock_zhipu_client.chat.completions.create.call_args
            assert call_args.kwargs['max_tokens'] == 500

    @pytest.mark.asyncio
    async def test_generate_raises_on_api_error(self, mock_zhipu_client):
        """generate should raise LLMError on API failure."""
        mock_zhipu_client.chat.completions.create.side_effect = Exception("API Error")

        with patch('app.services.llm.zhipu.ZhipuAI', return_value=mock_zhipu_client):
            from app.services.llm.zhipu import ZhipuProvider
            from app.services.llm.base import LLMError
            provider = ZhipuProvider(api_key="test-api-key")

            with pytest.raises(LLMError):
                await provider.generate("Hello")
