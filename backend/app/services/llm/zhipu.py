"""
Zhipu GLM LLM provider implementation.

Uses Claude API compatible endpoint to leverage Coding Plan subscription.
"""
import logging
import anthropic

from app.services.llm.base import LLMProvider, LLMError

logger = logging.getLogger(__name__)


class ZhipuProvider(LLMProvider):
    """
    LLM provider implementation for Zhipu GLM models.

    Uses Claude API compatible endpoint for Coding Plan subscription support.
    """

    def __init__(self, api_key: str, model: str = "glm-4.7", base_url: str = "https://open.bigmodel.cn/api/anthropic"):
        """
        Initialize the Zhipu provider.

        Args:
            api_key: Zhipu API key.
            model: Model name to use (default: glm-4.7).
            base_url: API base URL for Claude-compatible endpoint.
        """
        self._client = anthropic.Anthropic(
            api_key=api_key,
            base_url=base_url
        )
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
        Generate text response using Zhipu GLM via Claude compatible API.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system prompt for context.
            max_tokens: Maximum tokens in response.

        Returns:
            Generated text response.

        Raises:
            LLMError: If the API request fails.
        """
        messages = [{"role": "user", "content": prompt}]

        try:
            logger.info(f"Zhipu API call: model={self._model}, max_tokens={max_tokens}, prompt_len={len(prompt)}")

            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages
            )

            # Log response details
            content_text = response.content[0].text
            logger.info(f"Zhipu API response: content_len={len(content_text)} chars, "
                       f"stop_reason={response.stop_reason}, "
                       f"input_tokens={getattr(response.usage, 'input_tokens', 'N/A')}, "
                       f"output_tokens={getattr(response.usage, 'output_tokens', 'N/A')}")

            if response.stop_reason == "max_tokens":
                logger.warning(f"Response truncated due to max_tokens limit ({max_tokens})")

            return content_text
        except Exception as e:
            raise LLMError(
                f"Zhipu API request failed: {str(e)}",
                original_error=e
            )
