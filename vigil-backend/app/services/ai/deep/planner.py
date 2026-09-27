import json
from typing import Optional

from app.core.logging_config import logger
from app.services.ai.context.schemas import ReviewContext
from app.services.ai.deep.schemas import ReviewPlan, ReviewPlanTarget
from app.services.ai.gateway import AIModelGateway, ai_gateway
from app.services.ai.prompts.review_prompt import SYSTEM_PROMPT
from app.services.ai.review.parser import StructuredReviewParser
from app.services.ai.schemas import AICompletionRequest


PLANNER_PROMPT_TRAILER = """
<instructions_trailer>
Analyze the pull request changes above. You MUST return a structured JSON plan identifying the specific files, symbols, and review focus areas that deserve deep investigation.

Return valid JSON matching this exact schema:
{
  "summary": "<High-level assessment strategy>",
  "strategy": "focused" | "comprehensive" | "security-first",
  "targets": [
    {
      "file": "<relative file path from diff>",
      "symbols": ["<function or class name if present in diff>"],
      "areas": ["security", "logic", "error_handling", "testing", "maintainability", "performance"],
      "priority": "high" | "medium" | "low",
      "reason": "<why this section warrants deep investigation>",
      "evidence": "<quoted code or diff patch header>"
    }
  ]
}

CRITICAL: Do NOT invent files or symbols that are not present in the provided PR data.
Return valid JSON only.
</instructions_trailer>
"""


class ReviewPlanner:
    """Planning engine that analyzes PR context and formulates a structured ReviewPlan."""

    def __init__(self, gateway: Optional[AIModelGateway] = None, parser: Optional[StructuredReviewParser] = None):
        self.gateway = gateway or ai_gateway
        self.parser = parser or StructuredReviewParser()

    def create_fallback_plan(self, context: ReviewContext, reason: str = "Default fallback plan") -> ReviewPlan:
        """Constructs a deterministic fallback ReviewPlan targeting all changed files in the context."""
        targets = []
        if context.changed_files:
            for f in context.changed_files:
                targets.append(
                    ReviewPlanTarget(
                        file=f.file_path,
                        symbols=[],
                        areas=["security", "logic", "error_handling", "testing"],
                        priority="high" if "security" in f.file_path.lower() or "auth" in f.file_path.lower() else "medium",
                        reason=f"Changed file {f.file_path} selected for deep review ({reason})",
                        evidence=f.diff_patch[:200] if f.diff_patch else None,
                    )
                )
        else:
            targets.append(
                ReviewPlanTarget(
                    file="unknown",
                    symbols=[],
                    areas=["security", "logic"],
                    priority="low",
                    reason="No changed files in context",
                )
            )

        return ReviewPlan(
            summary=f"Automated fallback review plan ({reason})",
            strategy="comprehensive",
            targets=targets,
        )

    async def plan(self, context: ReviewContext) -> ReviewPlan:
        """Executes the planning pass for a given ReviewContext."""
        if not context.changed_files:
            return self.create_fallback_plan(context, reason="No changed files provided")

        # Build user prompt with planner trailer
        from app.services.ai.prompts.review_prompt import ReviewPromptBuilder
        builder = ReviewPromptBuilder()
        base_user_prompt = builder.build_user_prompt(context)

        # Replace default trailer with planner trailer
        if "<instructions_trailer>" in base_user_prompt:
            base_user_prompt = base_user_prompt.split("<instructions_trailer>")[0] + PLANNER_PROMPT_TRAILER

        request = AICompletionRequest(
            prompt=base_user_prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=2048,
        )

        try:
            response = await self.gateway.complete(request)
            parsed_data, _, warnings = self.parser.parse(response.content)

            if not parsed_data or "targets" not in parsed_data:
                logger.warning(f"ReviewPlanner output lacked targets schema, using fallback plan: {warnings}")
                return self.create_fallback_plan(context, reason="Malformed planner JSON response")

            # Parse and validate targets
            raw_targets = parsed_data.get("targets", [])
            valid_files = {f.file_path for f in context.changed_files}
            plan_targets = []

            for t in raw_targets:
                target_file = t.get("file", "").strip()
                # Strict file existence verification against context
                if target_file and target_file in valid_files:
                    plan_targets.append(
                        ReviewPlanTarget(
                            file=target_file,
                            symbols=[s for s in t.get("symbols", []) if isinstance(s, str)],
                            areas=[a for a in t.get("areas", []) if isinstance(a, str)],
                            priority=t.get("priority", "medium"),
                            reason=t.get("reason", "Prioritized by planner"),
                            evidence=t.get("evidence"),
                        )
                    )

            if not plan_targets:
                return self.create_fallback_plan(context, reason="Planner produced zero valid targets matching diff")

            return ReviewPlan(
                summary=parsed_data.get("summary", "Planner constructed target plan"),
                strategy=parsed_data.get("strategy", "focused"),
                targets=plan_targets,
            )

        except Exception as exc:
            logger.error(f"ReviewPlanner execution failed: {type(exc).__name__} - {str(exc)}")
            return self.create_fallback_plan(context, reason=f"Planner execution exception: {type(exc).__name__}")
