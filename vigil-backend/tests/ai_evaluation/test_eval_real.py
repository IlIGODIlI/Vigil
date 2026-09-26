import pytest

from app.core.config import settings
from app.services.ai.gateway import ai_gateway
from app.services.ai.review.engine import ReviewEngine
from tests.ai_evaluation.fixtures import get_all_fixtures, get_fixture_a_security
from tests.ai_evaluation.harness import ReviewEvaluator

# Check if real API key is available
has_api_key = bool(settings.AI_API_KEY and settings.AI_API_KEY.strip())


def test_provider_configuration_safety():
    """Verifies that provider configuration can be inspected safely without exposing secrets."""
    config_metadata = {
        "api_key_configured": has_api_key,
        "model": settings.AI_MODEL,
        "base_url": settings.AI_BASE_URL or "Default (OpenAI public endpoint)",
        "timeout": settings.AI_TIMEOUT_SECONDS,
        "max_retries": settings.AI_MAX_RETRIES,
    }

    # Verify key properties exist
    assert config_metadata["model"] == "Qwen/Qwen3-8B"
    assert config_metadata["timeout"] == 60.0
    assert config_metadata["max_retries"] == 3

    # Assert that no secrets are contained in the metadata dictionary
    for k, v in config_metadata.items():
        assert "sk-" not in str(v)
        assert "bearer" not in str(v).lower()


@pytest.mark.real_ai
@pytest.mark.skipif(not has_api_key, reason="AI_API_KEY is not configured. Skipping live model evaluation.")
@pytest.mark.asyncio
async def test_real_qwen_provider_smoke():
    """Live smoke test sending Fixture A (SQL injection) to the configured real model endpoint."""
    engine = ReviewEngine(gateway=ai_gateway)
    evaluator = ReviewEvaluator(engine=engine)
    fixture = get_fixture_a_security()

    res = await evaluator.evaluate_fixture(fixture)

    print("\n" + "=" * 60)
    print("LIVE QWEN SMOKE TEST EVALUATION RESULT:")
    print(f"Model: {res.model}")
    print(f"Elapsed Time: {res.elapsed_time}s")
    print(f"Parsed Successfully: {res.parsed_successfully}")
    print(f"Validated Successfully: {res.validated_successfully}")
    print(f"Findings Count: {res.findings_count} (Grounded: {res.grounded_findings}, Dropped: {res.dropped_findings})")
    print(f"Review Summary: {res.review_summary}")
    if res.review and res.review.findings:
        for i, f in enumerate(res.review.findings, 1):
            print(f"\n[Finding #{i}]")
            print(f"  Category: {f.category.value}")
            print(f"  Severity: {f.severity.value}")
            print(f"  Title: {f.title}")
            print(f"  File: {f.file}:{f.line}")
            print(f"  Description: {f.description}")
            if f.evidence:
                print(f"  Evidence: {f.evidence}")
            if f.suggested_fix:
                print(f"  Suggested Fix: {f.suggested_fix}")
    print("=" * 60 + "\n")

    assert res.error is None
    assert res.parsed_successfully is True
    assert res.validated_successfully is True
    assert res.model != "unknown"


@pytest.mark.real_ai
@pytest.mark.skipif(not has_api_key, reason="AI_API_KEY is not configured. Skipping live model evaluation.")
@pytest.mark.asyncio
async def test_real_qwen_evaluation_all_fixtures():
    """Live execution of all 6 fixtures against the configured real model endpoint."""
    engine = ReviewEngine(gateway=ai_gateway)
    evaluator = ReviewEvaluator(engine=engine)

    results = await evaluator.run_all(get_all_fixtures())
    assert len(results) == 6

    # Verify all responses parsed without crashing
    for r in results:
        assert r.parsed_successfully is True, f"Failed parsing on {r.case_name}: {r.warnings}"
