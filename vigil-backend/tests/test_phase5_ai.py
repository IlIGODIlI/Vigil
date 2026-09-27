import pytest
import uuid
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.analysis import AnalysisStatus
from app.services.ai.schema import AIAnalysisResultSchema
from app.services.ai.service import AIAnalysisService
from app.services.ai.provider import GroqProvider


@pytest.fixture
def mock_groq_provider():
    provider = GroqProvider(api_key="test_key", model="test_model")
    provider.analyze_commit = AsyncMock()
    return provider


def test_prompt_builder():
    from app.services.ai.prompt import AnalysisPromptBuilder
    from app.integrations.repolens.schema import RepositoryContext

    ctx = RepositoryContext(repository="test/repo", commit_sha="123", generated_at="now", files={})
    commit_data = {"sha": "123", "message": "Test"}

    prompt = AnalysisPromptBuilder.build(ctx, commit_data)
    assert "UNTRUSTED REPOSITORY DATA BEGIN" in prompt
    assert "test/repo" in prompt
    assert "123" in prompt


@pytest.mark.asyncio
async def test_groq_provider_success():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "summary": "Looks good",
                    "overall_assessment": "Clean",
                    "findings": []
                })
            }
        }]
    }

    mock_client_instance = MagicMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        provider = GroqProvider(api_key="test_key")
        result = await provider.analyze_commit("test prompt")
        assert result.summary == "Looks good"
        assert len(result.findings) == 0


@pytest.mark.asyncio
async def test_groq_provider_malformed_json():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": "Not JSON at all"
            }
        }]
    }

    mock_client_instance = MagicMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        provider = GroqProvider(api_key="test_key")
        with pytest.raises(Exception):
            await provider.analyze_commit("test prompt")


@pytest.mark.asyncio
async def test_groq_provider_missing_key():
    provider = GroqProvider(api_key="")
    with pytest.raises(ValueError):
        await provider.analyze_commit("test prompt")
