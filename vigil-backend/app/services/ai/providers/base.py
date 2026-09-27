from abc import ABC, abstractmethod
from app.services.ai.schemas import AICompletionRequest, AICompletionResponse


class BaseAIProvider(ABC):
    """Abstract interface for AI model completion providers."""

    @abstractmethod
    async def complete(self, request: AICompletionRequest) -> AICompletionResponse:
        """Asynchronously generate a completion for the given request.

        Args:
            request: The model-agnostic completion request containing prompts and generation parameters.

        Returns:
            AICompletionResponse: Normalized completion output containing text content, model name, and usage.

        Raises:
            AIGatewayError: Normalized exception hierarchy representing any provider or configuration failures.
        """
        pass
