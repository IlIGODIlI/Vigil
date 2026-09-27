from typing import Optional

from app.services.ai.context.schemas import ReviewContext
from app.services.ai.gateway import AIModelGateway, ai_gateway
from app.services.ai.prompts.review_prompt import ReviewPromptBuilder
from app.services.ai.review.parser import StructuredReviewParser
from app.services.ai.review.schemas import ReviewResult
from app.services.ai.review.validator import ReviewValidator


class ReviewEngine:
    """Orchestrates structured AI code review by assembling prompts, invoking the model gateway,

    parsing untrusted model JSON outputs, and validating findings against evidence.
    """

    def __init__(
        self,
        gateway: Optional[AIModelGateway] = None,
        prompt_builder: Optional[ReviewPromptBuilder] = None,
        parser: Optional[StructuredReviewParser] = None,
        validator: Optional[ReviewValidator] = None,
    ):
        self.gateway = gateway or ai_gateway
        self.prompt_builder = prompt_builder or ReviewPromptBuilder()
        self.parser = parser or StructuredReviewParser()
        self.validator = validator or ReviewValidator()

    async def review(
        self,
        context: ReviewContext,
        model: Optional[str] = None,
        temperature: Optional[float] = 0.1,
        max_tokens: Optional[int] = 4096,
    ) -> ReviewResult:
        """Executes a structured code review for a given ReviewContext.

        Args:
            context: Validated and normalized pull request review context.
            model: Optional model override.
            temperature: Generation temperature (defaults to 0.1 for high determinism).
            max_tokens: Maximum tokens for completion output.

        Returns:
            ReviewResult: Validated code review containing grounded findings and assessment summary.
        """
        # 1. Build completion request with trust boundaries
        completion_request = self.prompt_builder.build_completion_request(
            context=context,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 2. Invoke gateway
        completion_response = await self.gateway.complete(completion_request)

        # 3. Defensively extract and parse JSON output
        parsed_data, parse_method, parse_warnings = self.parser.parse(completion_response.content)

        # 4. Ground and validate findings against context
        result = self.validator.validate(
            raw_data=parsed_data,
            context=context,
            model=completion_response.model,
            parse_method=parse_method,
            initial_warnings=parse_warnings,
            raw_response=completion_response.content,
        )

        return result


# Default singleton instance for general application use
review_engine = ReviewEngine()
