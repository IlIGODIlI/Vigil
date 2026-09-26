import httpx
from typing import Optional
from app.core.config import settings
from app.services.ai.schema import AIAnalysisResultSchema

class LLMProvider:
    async def analyze_commit(self, prompt: str) -> AIAnalysisResultSchema:
        raise NotImplementedError

class GroqProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "LLM_API_KEY", None)
        self.model = model or getattr(settings, "LLM_MODEL", "llama3-8b-8192")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    async def analyze_commit(self, prompt: str) -> AIAnalysisResultSchema:
        if not self.api_key:
            raise ValueError("LLM API key is not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a senior security and software engineer analyzing a commit. You always reply with valid JSON matching the requested schema. Do not include markdown blocks, just the JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            return AIAnalysisResultSchema.model_validate_json(content)

def get_llm_provider() -> LLMProvider:
    provider_name = getattr(settings, "LLM_PROVIDER", "groq").lower()
    if provider_name == "groq":
        return GroqProvider()
    else:
        # Fallback/default to groq for now
        return GroqProvider()
