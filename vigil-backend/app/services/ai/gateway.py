from typing import Optional

from app.core.logging_config import logger
from app.services.ai.exceptions import AIGatewayError, AIResponseError
from app.services.ai.providers.base import BaseAIProvider
from app.services.ai.providers.openai_provider import OpenAICompatibleProvider
from app.services.ai.schemas import AICompletionRequest, AICompletionResponse


class AIModelGateway:
    """Central model-agnostic AI Gateway for VIGIL.

    Decouples callers from specific model providers (OpenAI, Qwen, vLLM, Hugging Face),
    standardizing prompt submission, error normalization, and response parsing.
    """

    def __init__(self, provider: Optional[BaseAIProvider] = None):
        """Initialize the gateway.

        Args:
            provider: Pluggable AI provider. If omitted, defaults to OpenAICompatibleProvider
                      configured via app.core.config.settings.
        """
        self._provider = provider

    @property
    def provider(self) -> BaseAIProvider:
        """Lazily initialize default provider to avoid side effects or configuration checks on module import."""
        if self._provider is None:
            self._provider = OpenAICompatibleProvider()
        return self._provider

    async def complete(self, request: AICompletionRequest) -> AICompletionResponse:
        """Submit a completion request to the active AI provider.

        Args:
            request: The AI completion request.

        Returns:
            AICompletionResponse: Normalized completion with generated content, model name, and usage.

        Raises:
            AIGatewayError: Normalized exception hierarchy representing any provider or configuration failures.
        """
        if not request.prompt or not request.prompt.strip():
            raise AIResponseError("Completion prompt cannot be empty or whitespace only.")

        try:
            return await self.provider.complete(request)
        except AIGatewayError:
            raise
        except Exception as exc:
            logger.error(f"Unhandled exception caught in AIModelGateway: {type(exc).__name__}")
            raise AIGatewayError(f"Unexpected error in AIModelGateway: {str(exc)}") from exc

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """High-level helper to generate a text completion and return only the generated text content."""
        request = AICompletionRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        response = await self.complete(request)
        return response.content


# Default singleton instance for general application use
ai_gateway = AIModelGateway()
