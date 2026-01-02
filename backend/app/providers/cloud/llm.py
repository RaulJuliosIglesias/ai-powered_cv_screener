import time
import logging
from typing import Optional, List, Dict
import httpx
from app.providers.base import LLMProvider, LLMResult
from app.config import settings

logger = logging.getLogger(__name__)

# Available models via OpenRouter
AVAILABLE_MODELS = [
    {"id": "google/gemini-2.0-flash-exp:free", "name": "Gemini 2.0 Flash (Free)", "provider": "Google"},
    {"id": "google/gemini-pro", "name": "Gemini Pro", "provider": "Google"},
    {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "provider": "OpenAI"},
    {"id": "openai/gpt-4o", "name": "GPT-4o", "provider": "OpenAI"},
    {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "Anthropic"},
    {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku", "provider": "Anthropic"},
    {"id": "meta-llama/llama-3.1-70b-instruct", "name": "Llama 3.1 70B", "provider": "Meta"},
    {"id": "mistralai/mistral-7b-instruct", "name": "Mistral 7B", "provider": "Mistral"},
]

# Singleton for current model selection
_current_model = "google/gemini-2.0-flash-exp:free"


def get_available_models() -> List[Dict]:
    """Get list of available models."""
    return AVAILABLE_MODELS


def get_current_model() -> str:
    """Get currently selected model."""
    return _current_model


def set_current_model(model_id: str) -> bool:
    """Set the current model. Returns True if valid."""
    global _current_model
    valid_ids = [m["id"] for m in AVAILABLE_MODELS]
    if model_id in valid_ids:
        _current_model = model_id
        logger.info(f"Model changed to: {model_id}")
        return True
    return False


class OpenRouterLLMProvider(LLMProvider):
    """LLM provider using OpenRouter API."""
    
    def __init__(self, model: str = None):
        self.api_key = settings.openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = model or _current_model
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048
    ) -> LLMResult:
        import asyncio
        start = time.perf_counter()
        
        # Always use current model
        model = _current_model
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        logger.info(f"Generating with model: {model}")
        
        max_retries = 3
        retry_delay = 2
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "HTTP-Referer": "https://cv-screener.local",
                            "X-Title": "CV Screener RAG",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": model,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        }
                    )
                    
                    if response.status_code == 429:
                        wait_time = retry_delay * (attempt + 1)
                        logger.warning(f"Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    response.raise_for_status()
                    data = response.json()
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        logger.warning(f"Rate limited, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    raise
            else:
                raise Exception("Max retries exceeded for OpenRouter API")
        
        latency = (time.perf_counter() - start) * 1000
        
        usage = data.get("usage", {})
        
        return LLMResult(
            text=data["choices"][0]["message"]["content"],
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency
        )
