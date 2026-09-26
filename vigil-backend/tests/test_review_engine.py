import json
import pytest

from app.services.ai.context.builder import ReviewContextBuilder
from app.services.ai.gateway import AIModelGateway
from app.services.ai.providers.mock_provider import MockProvider
from app.services.ai.review.engine import ReviewEngine
from app.services.ai.review.parser import StructuredReviewParser
from app.services.ai.review.schemas import (
    FindingCategory,
    FindingSeverity,
    ReviewFinding,
    ReviewResult,
    ReviewStatus,
)
from app.services.ai.review.validator import ReviewValidator


# 1. PARSER TESTS
def test_parser_direct_json():
    parser = StructuredReviewParser()
    raw = json.dumps({
        "summary": "Clean refactoring of auth middleware.",
        "findings": [
            {
                "category": "Security",
                "severity": "high",
                "title": "Unverified JWT decode",
                "file": "app/auth.py",
                "line": 42,
                "problem": "Token decoded without secret key verification",
                "why": "Allows forged signatures to bypass auth",
                "evidence": "jwt.decode(token, verify=False)",
                "suggestion": "jwt.decode(token, key=SECRET, algorithms=['HS256'])",
                "source": "AI",
            }
        ],
    })

    data, method, warnings = parser.parse(raw)
    assert method == "direct_json"
    assert data["summary"] == "Clean refactoring of auth middleware."
    assert len(data["findings"]) == 1
    assert data["findings"][0]["title"] == "Unverified JWT decode"
    assert len(warnings) == 0


def test_parser_markdown_fence():
    parser = StructuredReviewParser()
    raw = (
        "Here is the review result:\n"
        "```json\n"
        "{\n"
        '  "summary": "Markdown fenced review.",\n'
        '  "findings": []\n'
        "}\n"
        "```\n"
        "Let me know if you need more details!"
    )

    data, method, warnings = parser.parse(raw)
    assert "markdown_fence" in method
    assert data["summary"] == "Markdown fenced review."
    assert data["findings"] == []


def test_parser_trailing_comma_cleanup():
    parser = StructuredReviewParser()
    raw = (
        "```json\n"
        "{\n"
        '  "summary": "Fixed trailing comma.",\n'
        '  "findings": [\n'
        "    {\n"
        '      "category": "Logic",\n'
        '      "severity": "low",\n'
        '      "title": "Minor style issue",\n'
        '      "file": "main.py",\n'
        '      "problem": "Unused import",\n'
        '      "why": "Clutters namespace",\n'
        "    },\n"
        "  ],\n"
        "}\n"
        "```"
    )

    data, method, warnings = parser.parse(raw)
    assert "cleaned" in method or method == "markdown_fence"
    assert data["summary"] == "Fixed trailing comma."
    assert len(data["findings"]) == 1


def test_parser_outer_braces_in_chat():
    parser = StructuredReviewParser()
    raw = (
        "I analyzed your pull request. Below is my JSON assessment:\n"
        '{"summary": "No major risks detected.", "findings": []}\n'
        "Overall score: 9/10."
    )

    data, method, warnings = parser.parse(raw)
    assert method == "outer_braces"
    assert data["summary"] == "No major risks detected."


def test_parser_plain_text_fallback():
    parser = StructuredReviewParser()
    raw = (
        "This code looks great! I checked all lines and found no vulnerabilities.\n"
        "Approved."
    )

    data, method, warnings = parser.parse(raw)
    assert method == "raw_text_fallback"
    assert "This code looks great!" in data["summary"]
    assert data["findings"] == []
    assert len(warnings) > 0


def test_parser_empty_text():
    parser = StructuredReviewParser()
    data, method, warnings = parser.parse("   ")
    assert method == "empty_fallback"
    assert data["findings"] == []


# 2. VALIDATOR & GROUNDING TESTS
def test_validator_normalizes_category_and_severity():
    validator = ReviewValidator()
    raw_data = {
        "summary": "Test summary",
        "findings": [
            {
                "category": "SECURITY",
                "severity": "CRITICAL",
                "title": "SQL Injection",
                "file": "app/db.py",
                "line": 12,
                "problem": "Direct user input interpolation",
                "why": "Allows database exfiltration",
                "evidence": "SELECT * FROM users",
                "suggestion": "Use parameterized queries",
            }
        ],
    }

    context = (
        ReviewContextBuilder()
        .add_changed_file(file_path="app/db.py", diff_patch="+SELECT * FROM users WHERE id = %s")
        .build()
    )

    result = validator.validate(raw_data, context=context)
    assert len(result.findings) == 1
    f = result.findings[0]
    assert f.category == FindingCategory.SECURITY
    assert f.severity == FindingSeverity.CRITICAL
    assert f.file == "app/db.py"
    assert f.is_grounded is True


def test_validator_drops_hallucinated_files():
    validator = ReviewValidator(drop_hallucinated_files=True)
    raw_data = {
        "summary": "Hallucination test",
        "findings": [
            {
                "category": "Security",
                "severity": "high",
                "title": "Ghost issue",
                "file": "nonexistent/ghost_file.py",
                "problem": "Imaginary bug",
                "why": "Imaginary risk",
            },
            {
                "category": "Logic",
                "severity": "medium",
                "title": "Real issue",
                "file": "app/real.py",
                "problem": "Real bug",
                "why": "Real risk",
            },
        ],
    }

    context = (
        ReviewContextBuilder()
        .add_changed_file(file_path="app/real.py", diff_patch="+x = 1")
        .build()
    )

    result = validator.validate(raw_data, context=context)
    # The nonexistent file finding should be dropped
    assert len(result.findings) == 1
    assert result.findings[0].file == "app/real.py"
    assert any("Dropped hallucinated finding" in w for w in result.warnings)
    assert result.validation_metadata["dropped_hallucinations"] == 1


def test_validator_handles_invalid_finding_gracefully():
    validator = ReviewValidator()
    raw_data = {
        "summary": "Validation error test",
        "findings": [
            # Missing required field 'problem'
            {
                "category": "Security",
                "severity": "high",
                "title": "Incomplete finding",
                "file": "app/main.py",
            },
            # Valid finding
            {
                "category": "Testing",
                "severity": "low",
                "title": "Missing test case",
                "file": "app/main.py",
                "problem": "No unit test added for new endpoint",
                "why": "Reduces test coverage",
            },
        ],
    }

    context = (
        ReviewContextBuilder()
        .add_changed_file(file_path="app/main.py", diff_patch="+@app.get('/new')")
        .build()
    )

    result = validator.validate(raw_data, context=context)
    # Only the valid finding is kept
    assert len(result.findings) == 1
    assert result.findings[0].title == "Missing test case"
    assert any("failed schema validation and was omitted" in w for w in result.warnings)


# 3. END-TO-END REVIEW ENGINE ORCHESTRATION TESTS
@pytest.mark.asyncio
async def test_review_engine_successful_run():
    review_json = json.dumps({
        "summary": "Pull request adds robust user authentication with token validation.",
        "findings": [
            {
                "category": "Security",
                "severity": "high",
                "title": "Hardcoded JWT secret",
                "file": "app/auth.py",
                "line": 15,
                "problem": "Secret key is hardcoded directly in source code",
                "why": "Exposes signing key to repository readers",
                "evidence": "SECRET = 'supersecretkey123'",
                "suggestion": "Read from settings.SECRET_KEY instead",
                "source": "AI",
            }
        ],
    })

    mock_provider = MockProvider(default_response=review_json)
    gateway = AIModelGateway(provider=mock_provider)
    engine = ReviewEngine(gateway=gateway)

    context = (
        ReviewContextBuilder()
        .set_pull_request(title="Add auth middleware", pr_number=12)
        .add_changed_file(
            file_path="app/auth.py",
            diff_patch="@@ -10,3 +10,6 @@\n+SECRET = 'supersecretkey123'\n+def verify(): pass",
            change_type="modified",
        )
        .build()
    )

    result = await engine.review(context)

    assert isinstance(result, ReviewResult)
    assert result.status == ReviewStatus.SUCCESS
    assert "adds robust user authentication" in result.summary
    assert len(result.findings) == 1
    assert result.findings[0].title == "Hardcoded JWT secret"
    assert result.findings[0].category == FindingCategory.SECURITY
    assert result.findings[0].severity == FindingSeverity.HIGH
    assert result.findings[0].is_grounded is True
    assert mock_provider.call_count == 1


@pytest.mark.asyncio
async def test_review_engine_markdown_wrapped_response():
    markdown_response = (
        "Here is the code review analysis:\n\n"
        "```json\n"
        "{\n"
        '  "summary": "Performance optimization in database queries.",\n'
        '  "findings": [\n'
        "    {\n"
        '      "category": "Performance",\n'
        '      "severity": "medium",\n'
        '      "title": "N+1 query problem",\n'
        '      "file": "app/services.py",\n'
        '      "line": 20,\n'
        '      "problem": "Query executed inside a loop",\n'
        '      "why": "Causes quadratic latency under load",\n'
        '      "evidence": "for user in users: db.get(user.id)",\n'
        '      "suggestion": "Batch query using IN clause"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "```\n"
    )

    mock_provider = MockProvider(default_response=markdown_response)
    gateway = AIModelGateway(provider=mock_provider)
    engine = ReviewEngine(gateway=gateway)

    context = (
        ReviewContextBuilder()
        .add_changed_file(
            file_path="app/services.py",
            diff_patch="+for user in users: db.get(user.id)",
        )
        .build()
    )

    result = await engine.review(context)

    assert result.status == ReviewStatus.SUCCESS
    assert len(result.findings) == 1
    assert result.findings[0].category == FindingCategory.PERFORMANCE
    assert result.findings[0].file == "app/services.py"


@pytest.mark.asyncio
async def test_review_engine_malformed_plain_text_fallback():
    mock_provider = MockProvider(
        default_response="LGTM! I reviewed the PR manually and everything looks safe to merge."
    )
    gateway = AIModelGateway(provider=mock_provider)
    engine = ReviewEngine(gateway=gateway)

    context = (
        ReviewContextBuilder()
        .add_changed_file(file_path="main.py", diff_patch="+print('ok')")
        .build()
    )

    result = await engine.review(context)

    assert result.status == ReviewStatus.MALFORMED_OUTPUT
    assert "LGTM!" in result.summary
    assert len(result.findings) == 0
    assert any("did not contain valid structured JSON" in w for w in result.warnings)
