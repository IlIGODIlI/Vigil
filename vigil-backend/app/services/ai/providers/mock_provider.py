from typing import List, Optional

from app.services.ai.exceptions import (
    AIAuthenticationError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)
from app.services.ai.providers.base import BaseAIProvider
from app.services.ai.schemas import AICompletionRequest, AICompletionResponse, AIUsageInfo


class MockProvider(BaseAIProvider):
    """Deterministic, zero-network mock provider for testing AI Gateway workflows."""

    def __init__(
        self,
        default_response: str = "Mock AI completion response.",
        default_model: str = "mock-model",
        responses: Optional[List[str]] = None,
        simulate_timeout: bool = False,
        simulate_rate_limit: bool = False,
        simulate_auth_error: bool = False,
        simulate_provider_error: bool = False,
        simulate_empty_response: bool = False,
    ):
        self.default_response = default_response
        self.default_model = default_model
        self.responses = list(responses) if responses is not None else None
        self.simulate_timeout = simulate_timeout
        self.simulate_rate_limit = simulate_rate_limit
        self.simulate_auth_error = simulate_auth_error
        self.simulate_provider_error = simulate_provider_error
        self.simulate_empty_response = simulate_empty_response
        self.call_count: int = 0
        self.last_request: Optional[AICompletionRequest] = None

    async def complete(self, request: AICompletionRequest) -> AICompletionResponse:
        self.call_count += 1
        self.last_request = request

        if self.simulate_timeout:
            raise AITimeoutError("Simulated request timeout in MockProvider")

        if self.simulate_rate_limit:
            raise AIRateLimitError("Simulated rate limit exceeded in MockProvider")

        if self.simulate_auth_error:
            raise AIAuthenticationError("Simulated authentication error in MockProvider")

        if self.simulate_provider_error:
            raise AIProviderError("Simulated provider failure in MockProvider")

        if self.simulate_empty_response:
            return AICompletionResponse(
                content="",
                model=request.model or self.default_model,
                usage=AIUsageInfo(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                finish_reason="stop",
            )

        if self.responses:
            content = self.responses.pop(0)
        else:
            content = self.default_response

        return AICompletionResponse(
            content=content,
            model=request.model or self.default_model,
            usage=AIUsageInfo(
                prompt_tokens=len(request.prompt.split()),
                completion_tokens=len(content.split()),
                total_tokens=len(request.prompt.split()) + len(content.split()),
            ),
            finish_reason="stop",
        )
