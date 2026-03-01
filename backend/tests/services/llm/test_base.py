"""
Tests for LLM provider abstract base class.
"""
import pytest
from abc import ABC
from app.services.llm.base import LLMProvider


class TestLLMProviderAbstractInterface:
    """Test that LLMProvider defines the correct abstract interface."""

    def test_is_abstract_class(self):
        """LLMProvider should be an abstract class."""
        assert issubclass(LLMProvider, ABC)

    def test_cannot_instantiate_directly(self):
        """LLMProvider should not be instantiable directly."""
        with pytest.raises(TypeError):
            LLMProvider()

    def test_generate_method_signature(self):
        """LLMProvider should define async generate method."""
        # Check that generate is an abstract method
        assert hasattr(LLMProvider, 'generate')
        assert callable(getattr(LLMProvider, 'generate'))

    def test_model_name_property_signature(self):
        """LLMProvider should define model_name property."""
        assert hasattr(LLMProvider, 'model_name')


class ConcreteLLMProvider(LLMProvider):
    """Concrete implementation for testing."""

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000
    ) -> str:
        return "test response"

    @property
    def model_name(self) -> str:
        return "test-model"


class TestConcreteLLMProvider:
    """Test that concrete implementations work correctly."""

    def test_can_instantiate_concrete(self):
        """Concrete implementations should be instantiable."""
        provider = ConcreteLLMProvider()
        assert isinstance(provider, LLMProvider)

    def test_model_name_returns_string(self):
        """model_name property should return a string."""
        provider = ConcreteLLMProvider()
        assert provider.model_name == "test-model"

    @pytest.mark.asyncio
    async def test_generate_returns_string(self):
        """generate method should return a string."""
        provider = ConcreteLLMProvider()
        result = await provider.generate("test prompt")
        assert isinstance(result, str)
        assert result == "test response"

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self):
        """generate should accept system_prompt parameter."""
        provider = ConcreteLLMProvider()
        result = await provider.generate(
            "test prompt",
            system_prompt="You are a helpful assistant"
        )
        assert result == "test response"

    @pytest.mark.asyncio
    async def test_generate_with_max_tokens(self):
        """generate should accept max_tokens parameter."""
        provider = ConcreteLLMProvider()
        result = await provider.generate("test prompt", max_tokens=1000)
        assert result == "test response"
