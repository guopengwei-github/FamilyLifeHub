"""
Tests for Zhipu GLM provider implementation.

Tests use Claude API compatible endpoint mocks.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestZhipuProvider:
    """Test ZhipuProvider implementation."""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock Anthropic client for Zhipu Claude-compatible API."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Test response from GLM"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response
        return mock_client

    def test_initialization_with_api_key(self, mock_anthropic_client):
        """ZhipuProvider should initialize with API key and Claude-compatible endpoint."""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client) as mock_cls:
            from app.services.llm.zhipu import ZhipuProvider
            provider = ZhipuProvider(api_key="test-api-key")

            # Verify client was created with correct base_url
            mock_cls.assert_called_once_with(
                api_key="test-api-key",
                base_url="https://open.bigmodel.cn/api/anthropic"
            )
            assert provider.model_name == "glm-4.7"

    def test_custom_model_name(self, mock_anthropic_client):
        """ZhipuProvider should accept custom model name."""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            from app.services.llm.zhipu import ZhipuProvider
            provider = ZhipuProvider(api_key="test-api-key", model="glm-5")
            assert provider.model_name == "glm-5"

    def test_custom_base_url(self, mock_anthropic_client):
        """ZhipuProvider should accept custom base_url."""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client) as mock_cls:
            from app.services.llm.zhipu import ZhipuProvider
            ZhipuProvider(api_key="test-api-key", base_url="https://custom.api.url")

            mock_cls.assert_called_once_with(
                api_key="test-api-key",
                base_url="https://custom.api.url"
            )

    @pytest.mark.asyncio
    async def test_generate_basic(self, mock_anthropic_client):
        """generate should return LLM response."""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            from app.services.llm.zhipu import ZhipuProvider
            provider = ZhipuProvider(api_key="test-api-key")
            result = await provider.generate("Hello")
            assert result == "Test response from GLM"

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, mock_anthropic_client):
        """generate should pass system prompt as separate parameter (Claude API style)."""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            from app.services.llm.zhipu import ZhipuProvider
            provider = ZhipuProvider(api_key="test-api-key")
            await provider.generate("Hello", system_prompt="You are helpful")

            # Verify the call used system parameter (Claude API style)
            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args.kwargs['system'] == "You are helpful"
            assert call_args.kwargs['messages'] == [{"role": "user", "content": "Hello"}]

    @pytest.mark.asyncio
    async def test_generate_with_max_tokens(self, mock_anthropic_client):
        """generate should pass max_tokens to API."""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            from app.services.llm.zhipu import ZhipuProvider
            provider = ZhipuProvider(api_key="test-api-key")
            await provider.generate("Hello", max_tokens=500)

            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args.kwargs['max_tokens'] == 500

    @pytest.mark.asyncio
    async def test_generate_raises_on_api_error(self, mock_anthropic_client):
        """generate should raise LLMError on API failure."""
        mock_anthropic_client.messages.create.side_effect = Exception("API Error")

        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            from app.services.llm.zhipu import ZhipuProvider
            from app.services.llm.base import LLMError
            provider = ZhipuProvider(api_key="test-api-key")

            with pytest.raises(LLMError):
                await provider.generate("Hello")
