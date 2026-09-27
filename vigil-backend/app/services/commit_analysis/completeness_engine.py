from typing import List
from app.models.commit_analysis import CommitAnalysisOverallStatus
from app.services.commit_analysis.schemas import (
    CompletenessSignal,
    CompletenessSignalType,
    CommitAnalysisContext,
    CommitAnalysisResult,
    CommitIntent,
)


class CompletenessSignalEngine:
    """
    Combines deterministic signals and intent classification to produce
    an evidence-based, commit-type-aware analysis result.
    """

    def process(
        self,
        context: CommitAnalysisContext,
        intent: CommitIntent,
        signals: List[CompletenessSignal],
        semantic_notes: str = "",
    ) -> CommitAnalysisResult:
        # Filter signals based on commit intent
        filtered_signals = self._filter_signals_by_intent(intent, signals)

        # Build commit-type-aware analysis notes
        impl_notes = self._build_implementation_notes(context, intent, filtered_signals)
        testing_notes = self._build_testing_notes(context, intent, filtered_signals)
        error_notes = self._build_error_handling_notes(context, intent, filtered_signals)
        doc_notes = self._build_documentation_notes(context, intent, filtered_signals)
        placeholder_notes = self._build_placeholder_notes(context, intent, filtered_signals)

        # Determine overall status
        overall_status = self._determine_overall_status(context, intent, filtered_signals)

        # Build summary
        summary = (
            f"Commit Intent: {intent.value}. Overall Status: {overall_status.value}. "
            f"Analyzed {len(context.changed_files)} changed files. {semantic_notes}".strip()
        )

        return CommitAnalysisResult(
            commit_sha=context.commit_sha,
            summary=summary,
            intent=intent,
            implementation_notes=impl_notes,
            testing_notes=testing_notes,
            error_handling_notes=error_notes,
            documentation_notes=doc_notes,
            placeholder_notes=placeholder_notes,
            completeness_signals=filtered_signals,
            overall_status=overall_status,
        )

    def _filter_signals_by_intent(
        self, intent: CommitIntent, signals: List[CompletenessSignal]
    ) -> List[CompletenessSignal]:
        """
        Suppresses irrelevant signals according to the commit type.
        """
        filtered: List[CompletenessSignal] = []

        for sig in signals:
            # 1. Documentation-only commit: suppress "missing test" warnings
            if intent == CommitIntent.DOCUMENTATION and sig.type == CompletenessSignalType.MISSING_TEST_COVERAGE:
                continue

            # 2. Formatting-only commit: suppress missing tests and missing error handling
            if intent == CommitIntent.FORMATTING and sig.type in (
                CompletenessSignalType.MISSING_TEST_COVERAGE,
                CompletenessSignalType.NO_OBVIOUS_ERROR_HANDLING,
            ):
                continue

            # 3. Dependency update: suppress missing feature tests
            if intent == CommitIntent.DEPENDENCY_UPDATE and sig.type == CompletenessSignalType.MISSING_TEST_COVERAGE:
                continue

            # 4. Test-only commit: suppress missing implementation warnings
            if intent == CommitIntent.TEST and sig.type == CompletenessSignalType.MISSING_TEST_COVERAGE:
                continue

            # 5. Refactor commit: suppress missing test coverage warning if existing tests exist
            if intent == CommitIntent.REFACTOR and sig.type == CompletenessSignalType.MISSING_TEST_COVERAGE:
                continue

            filtered.append(sig)

        return filtered

    def _determine_overall_status(
        self,
        context: CommitAnalysisContext,
        intent: CommitIntent,
        signals: List[CompletenessSignal],
    ) -> CommitAnalysisOverallStatus:
        if not context.changed_files and not context.diff and not context.commit_message:
            return CommitAnalysisOverallStatus.INSUFFICIENT_EVIDENCE

        # Check for explicit issues
        has_todo = any(s.type == CompletenessSignalType.TODO_DETECTED for s in signals)
        has_placeholder = any(s.type == CompletenessSignalType.PLACEHOLDER_DETECTED for s in signals)
        has_missing_test = any(s.type == CompletenessSignalType.MISSING_TEST_COVERAGE for s in signals)
        has_missing_err = any(s.type == CompletenessSignalType.NO_OBVIOUS_ERROR_HANDLING for s in signals)

        if has_todo or has_placeholder or has_missing_test or has_missing_err:
            return CommitAnalysisOverallStatus.NEEDS_REVIEW

        # For feature/bug fix commits without any files or diff evidence:
        if intent in (CommitIntent.FEATURE, CommitIntent.BUG_FIX) and not context.changed_files:
            return CommitAnalysisOverallStatus.INSUFFICIENT_EVIDENCE

        return CommitAnalysisOverallStatus.NO_SIGNIFICANT_GAPS

    def _build_implementation_notes(
        self, context: CommitAnalysisContext, intent: CommitIntent, signals: List[CompletenessSignal]
    ) -> str:
        if intent == CommitIntent.DOCUMENTATION:
            return "No production code changes in documentation commit."
        if intent == CommitIntent.TEST:
            return "Test-only commit. Production code unchanged."
        if intent == CommitIntent.FORMATTING:
            return "Formatting changes only."
        if intent == CommitIntent.DEPENDENCY_UPDATE:
            return "Dependency configuration files updated."

        placeholders = [s.description for s in signals if s.type == CompletenessSignalType.PLACEHOLDER_DETECTED]
        if placeholders:
            return f"Potential placeholder detected: {'; '.join(placeholders)}"

        return "Implementation code modified. Looks complete based on available evidence."

    def _build_testing_notes(
        self, context: CommitAnalysisContext, intent: CommitIntent, signals: List[CompletenessSignal]
    ) -> str:
        if intent in (CommitIntent.DOCUMENTATION, CommitIntent.FORMATTING):
            return "Tests not required for this commit type."
        if intent == CommitIntent.TEST:
            return "Test suite updated."
        if intent == CommitIntent.DEPENDENCY_UPDATE:
            return "Dependency update commit. Integration tests should be verified separately."

        test_signals = [s for s in signals if s.type in (CompletenessSignalType.TEST_CHANGE_DETECTED, CompletenessSignalType.MISSING_TEST_COVERAGE, CompletenessSignalType.INSUFFICIENT_EVIDENCE)]
        if test_signals:
            return "; ".join(s.description for s in test_signals)

        return "Looks complete based on available testing evidence."

    def _build_error_handling_notes(
        self, context: CommitAnalysisContext, intent: CommitIntent, signals: List[CompletenessSignal]
    ) -> str:
        if intent in (CommitIntent.DOCUMENTATION, CommitIntent.FORMATTING, CommitIntent.TEST, CommitIntent.DEPENDENCY_UPDATE):
            return "Error handling analysis not applicable for this commit type."

        err_signals = [s.description for s in signals if s.type == CompletenessSignalType.NO_OBVIOUS_ERROR_HANDLING]
        if err_signals:
            return "; ".join(err_signals)

        return "No obvious unhandled operations detected in modified lines."

    def _build_documentation_notes(
        self, context: CommitAnalysisContext, intent: CommitIntent, signals: List[CompletenessSignal]
    ) -> str:
        doc_signals = [s.description for s in signals if s.type == CompletenessSignalType.DOCUMENTATION_CHANGE_DETECTED]
        if doc_signals:
            return "; ".join(doc_signals)

        if intent == CommitIntent.DOCUMENTATION:
            return "Documentation updated."

        return "No documentation changes detected in this commit."

    def _build_placeholder_notes(
        self, context: CommitAnalysisContext, intent: CommitIntent, signals: List[CompletenessSignal]
    ) -> str:
        placeholders = [s.description for s in signals if s.type == CompletenessSignalType.PLACEHOLDER_DETECTED]
        todos = [s.description for s in signals if s.type == CompletenessSignalType.TODO_DETECTED]

        all_findings = placeholders + todos
        if all_findings:
            return "; ".join(all_findings)

        return "No placeholders or TODO/FIXME comments detected."
