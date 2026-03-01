"""
Zhipu GLM LLM provider implementation.

Uses the zhipuai SDK to interact with Zhipu's GLM models.
"""
from zhipuai import ZhipuAI

from app.services.llm.base import LLMProvider, LLMError


class ZhipuProvider(LLMProvider):
    """
    LLM provider implementation for Zhipu GLM models.

    Uses the official zhipuai SDK for API communication.
    """

    def __init__(self, api_key: str, model: str = "glm-4-flash"):
        """
        Initialize the Zhipu provider.

        Args:
            api_key: Zhipu API key.
            model: Model name to use (default: glm-4-flash).
        """
        self._client = ZhipuAI(api_key=api_key)
        self._model = model

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self._model

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate text response using Zhipu GLM.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system prompt for context.
            max_tokens: Maximum tokens in response.

        Returns:
            Generated text response.

        Raises:
            LLMError: If the API request fails.
        """
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise LLMError(
                f"Zhipu API request failed: {str(e)}",
                original_error=e
            )
