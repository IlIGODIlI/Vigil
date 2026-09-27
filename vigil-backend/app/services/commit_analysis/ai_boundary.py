from abc import ABC, abstractmethod
import logging
from typing import Optional

from app.services.commit_analysis.schemas import CommitAnalysisContext

logger = logging.getLogger(__name__)


class CommitSemanticAnalyzerInterface(ABC):
    """
    Abstract interface for semantic commit analysis (Member 3 boundary).
    Analyzes whether implementation changes match the stated intent of the commit message.
    """

    @abstractmethod
    async def analyze_semantic_consistency(
        self, context: CommitAnalysisContext
    ) -> Optional[str]:
        """
        Returns a human-readable observation string regarding semantic consistency,
        or None if semantic analysis is unavailable or unneeded.
        """
        pass


class StubCommitSemanticAnalyzer(CommitSemanticAnalyzerInterface):
    """
    Default stub/fallback analyzer when Member 3's AI gateway is unavailable.
    Ensures deterministic analysis works 100% without AI model providers.
    """

    async def analyze_semantic_consistency(
        self, context: CommitAnalysisContext
    ) -> Optional[str]:
        return "Semantic AI analysis unavailable; deterministic analysis completed."


class SafeAISemanticAnalyzerWrapper(CommitSemanticAnalyzerInterface):
    """
    Wrapper around an optional AI provider. Catches any AI failures, timeouts,
    or malformed results without interrupting the deterministic analysis pipeline.
    """

    def __init__(self, inner: Optional[CommitSemanticAnalyzerInterface] = None):
        self._inner = inner or StubCommitSemanticAnalyzer()

    async def analyze_semantic_consistency(
        self, context: CommitAnalysisContext
    ) -> Optional[str]:
        try:
            return await self._inner.analyze_semantic_consistency(context)
        except Exception as exc:
            logger.warning(
                "Semantic AI analysis failed for commit %s: %s",
                context.commit_sha,
                str(exc),
                exc_info=True,
            )
            # Crucial: AI failure must NOT be treated as "No issues found".
            return "Semantic AI analysis was unavailable or failed; relying on deterministic evidence."
