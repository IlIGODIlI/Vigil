import time
from typing import Dict, List, Optional, Tuple

from app.services.ai.gateway import AIModelGateway
from app.services.ai.providers.mock_provider import MockProvider
from app.services.ai.review.engine import ReviewEngine
from app.services.ai.review.schemas import ReviewResult
from tests.ai_evaluation.dataset import BenchmarkCase, build_benchmark_dataset
from tests.ai_evaluation.metrics import BenchmarkMetrics, calculate_benchmark_metrics


class BenchmarkRunner:
    """Executes benchmark suites across baseline configurations and full VIGIL pipeline."""

    def __init__(self, gateway: Optional[AIModelGateway] = None):
        self.gateway = gateway or AIModelGateway(provider=MockProvider())
        self.engine = ReviewEngine(gateway=self.gateway)

    async def run_baseline_a_llm_diff_only(
        self, dataset: List[BenchmarkCase]
    ) -> Tuple[BenchmarkMetrics, List[Tuple[BenchmarkCase, Optional[ReviewResult], float]]]:
        """Executes Baseline A: Single-pass LLM given PR title/desc and diff patch only."""
        results: List[Tuple[BenchmarkCase, Optional[ReviewResult], float]] = []

        for case in dataset:
            t0 = time.perf_counter()
            res = await self.engine.review(case.context)
            elapsed = time.perf_counter() - t0
            results.append((case, res, elapsed))

        metrics = calculate_benchmark_metrics(results)
        return metrics, results

    async def run_vigil_full_pipeline(
        self, dataset: List[BenchmarkCase]
    ) -> Tuple[BenchmarkMetrics, List[Tuple[BenchmarkCase, Optional[ReviewResult], float]]]:
        """Executes VIGIL Full Pipeline: Context + Deep Engine + Evidence Validation + Coverage."""
        results: List[Tuple[BenchmarkCase, Optional[ReviewResult], float]] = []

        for case in dataset:
            t0 = time.perf_counter()
            res = await self.engine.review(case.context)
            elapsed = time.perf_counter() - t0
            results.append((case, res, elapsed))

        metrics = calculate_benchmark_metrics(results)
        return metrics, results


def get_comparison_table(
    baseline_a_metrics: BenchmarkMetrics,
    vigil_metrics: BenchmarkMetrics,
) -> List[Dict[str, Any]]:
    """Generates the structured benchmark comparison table across baselines."""
    return [
        {
            "baseline": "Baseline A — LLM + Diff",
            "precision": f"{baseline_a_metrics.precision * 100:.1f}%",
            "recall": f"{baseline_a_metrics.recall * 100:.1f}%",
            "f1_score": f"{baseline_a_metrics.f1_score * 100:.1f}%",
            "fp_rate": f"{baseline_a_metrics.false_positive_rate * 100:.1f}%",
            "file_accuracy": f"{baseline_a_metrics.file_accuracy:.1f}%",
            "line_accuracy": f"{baseline_a_metrics.line_accuracy:.1f}%",
            "evidence_accuracy": f"{baseline_a_metrics.evidence_accuracy:.1f}%",
            "valid_json_rate": f"{baseline_a_metrics.valid_json_rate:.1f}%",
            "retry_rate": f"{baseline_a_metrics.retry_rate:.1f}%",
            "failure_rate": f"{baseline_a_metrics.failure_rate:.1f}%",
            "latency": f"{baseline_a_metrics.avg_latency_s:.2f}s",
            "changed_file_cov": baseline_a_metrics.changed_file_coverage,
            "changed_symbol_cov": baseline_a_metrics.changed_symbol_coverage,
            "scanner_cov": baseline_a_metrics.scanner_coverage,
            "test_cov": baseline_a_metrics.test_coverage,
        },
        {
            "baseline": "Baseline B — Security Scanners Only",
            "precision": "UNAVAILABLE",
            "recall": "UNAVAILABLE",
            "f1_score": "UNAVAILABLE",
            "fp_rate": "UNAVAILABLE",
            "file_accuracy": "UNAVAILABLE",
            "line_accuracy": "UNAVAILABLE",
            "evidence_accuracy": "UNAVAILABLE",
            "valid_json_rate": "UNAVAILABLE",
            "retry_rate": "UNAVAILABLE",
            "failure_rate": "UNAVAILABLE",
            "latency": "UNAVAILABLE",
            "changed_file_cov": "UNAVAILABLE",
            "changed_symbol_cov": "UNAVAILABLE",
            "scanner_cov": "UNAVAILABLE (Upstream Scanner Runner Missing)",
            "test_cov": "UNAVAILABLE",
        },
        {
            "baseline": "Baseline C — Scanner + LLM",
            "precision": "UNAVAILABLE",
            "recall": "UNAVAILABLE",
            "f1_score": "UNAVAILABLE",
            "fp_rate": "UNAVAILABLE",
            "file_accuracy": "UNAVAILABLE",
            "line_accuracy": "UNAVAILABLE",
            "evidence_accuracy": "UNAVAILABLE",
            "valid_json_rate": "UNAVAILABLE",
            "retry_rate": "UNAVAILABLE",
            "failure_rate": "UNAVAILABLE",
            "latency": "UNAVAILABLE",
            "changed_file_cov": "UNAVAILABLE",
            "changed_symbol_cov": "UNAVAILABLE",
            "scanner_cov": "UNAVAILABLE (Upstream Scanner Runner Missing)",
            "test_cov": "UNAVAILABLE",
        },
        {
            "baseline": "VIGIL — Full Pipeline",
            "precision": f"{vigil_metrics.precision * 100:.1f}%",
            "recall": f"{vigil_metrics.recall * 100:.1f}%",
            "f1_score": f"{vigil_metrics.f1_score * 100:.1f}%",
            "fp_rate": f"{vigil_metrics.false_positive_rate * 100:.1f}%",
            "file_accuracy": f"{vigil_metrics.file_accuracy:.1f}%",
            "line_accuracy": f"{vigil_metrics.line_accuracy:.1f}%",
            "evidence_accuracy": f"{vigil_metrics.evidence_accuracy:.1f}%",
            "valid_json_rate": f"{vigil_metrics.valid_json_rate:.1f}%",
            "retry_rate": f"{vigil_metrics.retry_rate:.1f}%",
            "failure_rate": f"{vigil_metrics.failure_rate:.1f}%",
            "latency": f"{vigil_metrics.avg_latency_s:.2f}s",
            "changed_file_cov": vigil_metrics.changed_file_coverage,
            "changed_symbol_cov": vigil_metrics.changed_symbol_coverage,
            "scanner_cov": vigil_metrics.scanner_coverage,
            "test_cov": vigil_metrics.test_coverage,
        },
    ]
