"""
Abstract base class for LLM providers.

Defines the interface that all LLM implementations must follow,
enabling easy switching between different providers (Zhipu, OpenAI, etc.).
"""
from abc import ABC, abstractmethod


class LLMError(Exception):
    """Exception raised when LLM request fails."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM implementations must inherit from this class and implement
    the abstract methods and properties.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate text response from the LLM.

        Args:
            prompt: The user prompt to send to the LLM.
            system_prompt: Optional system prompt to set the context.
            max_tokens: Maximum number of tokens in the response.

        Returns:
            The generated text response.

        Raises:
            LLMError: If the LLM request fails.
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Get the name of the model being used.

        Returns:
            The model name string (e.g., "glm-4-flash", "gpt-4").
        """
        pass
