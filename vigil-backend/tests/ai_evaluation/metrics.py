from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, ConfigDict, Field

from app.services.ai.context.normalizer import ContextNormalizer
from app.services.ai.review.schemas import ReviewFinding, ReviewResult
from tests.ai_evaluation.dataset import BenchmarkCase, GroundTruthFinding


class FindingMatchResult(BaseModel):
    """Result of matching an observed finding against ground-truth expectations."""

    model_config = ConfigDict(extra="ignore")

    is_tp: bool
    is_fp: bool
    matched_gt: Optional[GroundTruthFinding] = None
    file_matched: bool = False
    line_matched: bool = False
    evidence_matched: bool = False


class BenchmarkMetrics(BaseModel):
    """Aggregate quantitative evaluation metrics across benchmark execution."""

    model_config = ConfigDict(extra="ignore")

    total_cases: int = 0
    clean_cases: int = 0
    vuln_cases: int = 0

    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    false_positive_rate: float = 0.0

    file_accuracy: float = 0.0
    line_accuracy: float = 0.0
    evidence_accuracy: float = 0.0

    valid_json_rate: float = 1.0
    retry_rate: float = 0.0
    failure_rate: float = 0.0
    duplicate_rate: float = 0.0

    actionability: str = "UNAVAILABLE (Human Annotation Required)"
    reasoning_quality: str = "UNAVAILABLE (Human Annotation Required)"

    avg_latency_s: float = 0.0
    total_model_calls: int = 0

    changed_file_coverage: str = "100.0%"
    changed_symbol_coverage: str = "UNAVAILABLE (Upstream AST Indexer Missing)"
    scanner_coverage: str = "UNAVAILABLE (Upstream Static Scanner Missing)"
    test_coverage: str = "UNAVAILABLE (Upstream Test Suite Indexer Missing)"


def match_finding_to_ground_truth(
    finding: ReviewFinding,
    case: BenchmarkCase,
    matched_gt_set: Set[int],
) -> FindingMatchResult:
    """Evaluates whether an observed finding matches any ground-truth expectation in a test case."""
    norm_finding_file = ContextNormalizer.normalize_path(finding.file).lower()

    # Check evidence in diff
    evidence_matched = False
    diff_text = ""
    for cf in case.context.changed_files:
        if ContextNormalizer.normalize_path(cf.file_path).lower() == norm_finding_file:
            diff_text = (cf.diff_patch or "") + (cf.file_content or "")
            if finding.evidence and finding.evidence.strip() in diff_text:
                evidence_matched = True
            break

    if case.is_clean_code:
        return FindingMatchResult(
            is_tp=False,
            is_fp=True,
            file_matched=False,
            line_matched=False,
            evidence_matched=evidence_matched,
        )

    for idx, gt in enumerate(case.ground_truth_findings):
        norm_gt_file = ContextNormalizer.normalize_path(gt.file).lower()
        file_matched = norm_finding_file == norm_gt_file

        if not file_matched:
            continue

        # Line matching with +-2 line tolerance
        line_matched = True
        if finding.line is not None and gt.line_start is not None and gt.line_end is not None:
            line_matched = (gt.line_start - 2) <= finding.line <= (gt.line_end + 2)

        # Category matching
        cat_matched = (
            finding.category.value.lower() == gt.category.value.lower()
            or (finding.category.value.lower() in ("security", "authorization") and gt.category.value.lower() in ("security", "authorization"))
        )

        if file_matched and cat_matched and line_matched:
            matched_gt_set.add(idx)
            return FindingMatchResult(
                is_tp=True,
                is_fp=False,
                matched_gt=gt,
                file_matched=file_matched,
                line_matched=line_matched,
                evidence_matched=evidence_matched,
            )

    # File matched but category/line differed
    file_matched = any(ContextNormalizer.normalize_path(gt.file).lower() == norm_finding_file for gt in case.ground_truth_findings)
    return FindingMatchResult(
        is_tp=False,
        is_fp=True,
        file_matched=file_matched,
        line_matched=False,
        evidence_matched=evidence_matched,
    )


def calculate_benchmark_metrics(
    case_results: List[Tuple[BenchmarkCase, Optional[ReviewResult], float]],
) -> BenchmarkMetrics:
    """Calculates quantitative benchmark evaluation metrics from case execution records."""
    total_cases = len(case_results)
    if total_cases == 0:
        return BenchmarkMetrics()

    clean_cases = sum(1 for c, _, _ in case_results if c.is_clean_code)
    vuln_cases = total_cases - clean_cases

    tp = 0
    fp = 0
    fn = 0
    clean_fps = 0

    total_findings = 0
    file_matches = 0
    line_matches = 0
    evidence_matches = 0

    valid_json_count = 0
    total_latency = 0.0
    duplicate_count = 0

    for case, result, elapsed in case_results:
        total_latency += elapsed

        if result is None or result.status == "MALFORMED_OUTPUT":
            if case.findings_expected:
                fn += len(case.ground_truth_findings)
            continue

        valid_json_count += 1
        matched_gt_indices: Set[int] = set()

        seen_findings: Set[Tuple[str, Optional[int], str]] = set()

        for finding in result.findings:
            total_findings += 1

            # Duplicate check
            f_key = (finding.file.lower(), finding.line, finding.title.lower())
            if f_key in seen_findings:
                duplicate_count += 1
            seen_findings.add(f_key)

            match_res = match_finding_to_ground_truth(finding, case, matched_gt_indices)
            if match_res.is_tp:
                tp += 1
            else:
                fp += 1

            if match_res.file_matched:
                file_matches += 1
            if match_res.line_matched:
                line_matches += 1
            if match_res.evidence_matched:
                evidence_matches += 1

        if case.is_clean_code and len(result.findings) > 0:
            clean_fps += 1

        # Calculate False Negatives for un-matched ground truth items
        unmatched_gt = len(case.ground_truth_findings) - len(matched_gt_indices)
        fn += max(0, unmatched_gt)

    precision = (tp / (tp + fp)) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
    recall = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    fp_rate = (clean_fps / clean_cases) if clean_cases > 0 else 0.0

    file_acc = (file_matches / total_findings * 100.0) if total_findings > 0 else 100.0
    line_acc = (line_matches / total_findings * 100.0) if total_findings > 0 else 100.0
    evidence_acc = (evidence_matches / total_findings * 100.0) if total_findings > 0 else 100.0

    valid_json_rate = (valid_json_count / total_cases * 100.0) if total_cases > 0 else 100.0
    duplicate_rate = (duplicate_count / total_findings * 100.0) if total_findings > 0 else 0.0
    avg_latency = total_latency / total_cases if total_cases > 0 else 0.0

    return BenchmarkMetrics(
        total_cases=total_cases,
        clean_cases=clean_cases,
        vuln_cases=vuln_cases,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1_score=round(f1, 4),
        false_positive_rate=round(fp_rate, 4),
        file_accuracy=round(file_acc, 2),
        line_accuracy=round(line_acc, 2),
        evidence_accuracy=round(evidence_acc, 2),
        valid_json_rate=round(valid_json_rate, 2),
        retry_rate=0.0,
        failure_rate=round((total_cases - valid_json_count) / total_cases * 100.0, 2),
        duplicate_rate=round(duplicate_rate, 2),
        actionability="UNAVAILABLE (Human Annotation Required)",
        reasoning_quality="UNAVAILABLE (Human Annotation Required)",
        avg_latency_s=round(avg_latency, 2),
        total_model_calls=total_cases,
    )
