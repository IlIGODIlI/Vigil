from typing import Any, Dict, List, Optional, Set
from pydantic import ValidationError

from app.core.logging_config import logger
from app.services.ai.context.normalizer import ContextNormalizer
from app.services.ai.context.schemas import ReviewContext
from app.services.ai.review.schemas import (
    FindingCategory,
    FindingSeverity,
    ReviewFinding,
    ReviewResult,
    ReviewStatus,
)


class ReviewValidator:
    """Validates raw parsed review dictionaries against Pydantic schemas,

    verifies grounding against supplied review context, and eliminates hallucinations.
    """

    def __init__(self, drop_hallucinated_files: bool = True):
        self.drop_hallucinated_files = drop_hallucinated_files

    def _get_known_files(self, context: Optional[ReviewContext]) -> Set[str]:
        """Extracts normalized paths for all files present in the review context."""
        known: Set[str] = set()
        if not context:
            return known

        for cf in context.changed_files:
            norm = ContextNormalizer.normalize_path(cf.file_path)
            if norm:
                known.add(norm.lower())

        if context.repository:
            for fp in context.repository.file_paths:
                norm = ContextNormalizer.normalize_path(fp)
                if norm:
                    known.add(norm.lower())

        return known

    def _check_evidence_in_context(
        self, file_path: str, evidence: Optional[str], context: Optional[ReviewContext]
    ) -> bool:
        """Verifies if the cited evidence snippet exists in the file's diff or content."""
        if not evidence or not context:
            return True

        norm_target = ContextNormalizer.normalize_path(file_path)
        if not norm_target:
            return False

        clean_evidence = evidence.strip()
        if len(clean_evidence) < 5:
            return True  # Trivial snippet

        for cf in context.changed_files:
            if ContextNormalizer.normalize_path(cf.file_path) == norm_target:
                diff_text = cf.diff_patch or ""
                content_text = cf.file_content or ""
                if clean_evidence in diff_text or clean_evidence in content_text:
                    return True
                # Check line by line if snippet is multi-line
                for line in clean_evidence.splitlines():
                    clean_line = line.strip().lstrip("+-").strip()
                    if len(clean_line) > 10 and (clean_line in diff_text or clean_line in content_text):
                        return True
        return False

    def validate(
        self,
        raw_data: Dict[str, Any],
        context: Optional[ReviewContext],
        model: Optional[str] = None,
        parse_method: str = "direct_json",
        initial_warnings: Optional[List[str]] = None,
        raw_response: Optional[str] = None,
    ) -> ReviewResult:
        """Validates and grounds parsed review data into a verified ReviewResult."""
        warnings: List[str] = list(initial_warnings or [])
        known_files = self._get_known_files(context)

        raw_summary = raw_data.get("summary")
        if not raw_summary or not str(raw_summary).strip():
            summary = "Code review completed with no high-level summary provided."
            warnings.append("Model provided an empty summary string.")
        else:
            summary = str(raw_summary).strip()

        raw_findings = raw_data.get("findings", [])
        if not isinstance(raw_findings, list):
            warnings.append("Expected 'findings' to be a list; treating as empty list.")
            raw_findings = []

        validated_findings: List[ReviewFinding] = []
        dropped_hallucinations = 0
        grounded_count = 0

        for idx, item in enumerate(raw_findings):
            if not isinstance(item, dict):
                warnings.append(f"Finding at index {idx} was not a JSON object; omitted.")
                continue

            try:
                # Pydantic parsing with category/severity normalization
                finding = ReviewFinding.model_validate(item)

                # Normalize file path
                norm_file = ContextNormalizer.normalize_path(finding.file)
                if norm_file:
                    finding.file = norm_file

                # Hallucination check against known files
                if known_files and finding.file.lower() not in known_files:
                    if self.drop_hallucinated_files:
                        dropped_hallucinations += 1
                        warnings.append(
                            f"Dropped hallucinated finding '{finding.title}': "
                            f"file '{finding.file}' is not in review context."
                        )
                        continue
                    else:
                        finding.is_grounded = False
                        warnings.append(
                            f"Hallucination Warning: finding '{finding.title}' references "
                            f"file '{finding.file}' not present in context."
                        )

                # Evidence grounding verification
                if finding.evidence and context:
                    if not self._check_evidence_in_context(finding.file, finding.evidence, context):
                        finding.is_grounded = False
                        warnings.append(
                            f"Grounding Warning: Evidence for '{finding.title}' was not found in the diff for '{finding.file}'."
                        )

                if finding.is_grounded:
                    grounded_count += 1

                validated_findings.append(finding)

            except ValidationError as exc:
                errors = "; ".join([f"{e['loc']}: {e['msg']}" for e in exc.errors()])
                warnings.append(f"Finding at index {idx} failed schema validation and was omitted: {errors}")
                logger.warning(f"Omitted invalid finding at index {idx}: {errors}")

        # Determine status
        if parse_method in ("raw_text_fallback", "empty_fallback"):
            status = ReviewStatus.MALFORMED_OUTPUT
        elif warnings:
            status = ReviewStatus.WARNING
        else:
            status = ReviewStatus.SUCCESS

        metadata = {
            "total_raw_findings": len(raw_findings),
            "validated_findings_count": len(validated_findings),
            "dropped_hallucinations": dropped_hallucinations,
            "grounded_count": grounded_count,
            "parse_method": parse_method,
        }

        return ReviewResult(
            summary=summary,
            findings=validated_findings,
            model=model,
            status=status,
            warnings=warnings,
            validation_metadata=metadata,
            raw_response=raw_response,
        )
