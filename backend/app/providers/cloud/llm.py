import time
import logging
from typing import Optional, List, Dict
import httpx
from app.providers.base import LLMProvider, LLMResult
from app.config import settings

logger = logging.getLogger(__name__)

# Cache for models fetched from OpenRouter
_cached_models: List[Dict] = []
_current_model = "openai/gpt-4o-mini"  # Safe default


async def fetch_openrouter_models() -> List[Dict]:
    """Fetch all available models from OpenRouter API."""
    global _cached_models
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"}
            )
            response.raise_for_status()
            data = response.json()
            
            models = []
            for m in data.get("data", []):
                pricing = m.get("pricing", {})
                prompt_price = float(pricing.get("prompt", 0)) * 1000000  # per 1M tokens
                completion_price = float(pricing.get("completion", 0)) * 1000000
                
                # Extract architecture info
                arch = m.get("architecture", {})
                
                # Check for reasoning/thinking capability from description or name
                model_id = m["id"].lower()
                model_name = m.get("name", "").lower()
                description = m.get("description", "").lower()
                
                is_reasoning = any(kw in model_id or kw in model_name or kw in description 
                    for kw in ["reasoning", "thinking", "o1", "o3", "deepseek-r1", "qwq", "think"])
                
                is_free = prompt_price == 0 and completion_price == 0
                
                models.append({
                    "id": m["id"],
                    "name": m.get("name", m["id"]),
                    "description": m.get("description", ""),
                    "context_length": m.get("context_length", 0),
                    "pricing": {
                        "prompt": f"${prompt_price:.2f}/1M",
                        "completion": f"${completion_price:.2f}/1M"
                    },
                    "pricing_raw": {"prompt": prompt_price, "completion": completion_price},
                    "created": m.get("created"),  # Unix timestamp
                    "architecture": {
                        "tokenizer": arch.get("tokenizer", ""),
                        "modality": arch.get("modality", "text"),
                        "instruct_type": arch.get("instruct_type", "")
                    },
                    "top_provider": m.get("top_provider", {}),
                    "is_reasoning": is_reasoning,
                    "is_free": is_free
                })
            
            # Sort by name by default
            models.sort(key=lambda x: x["name"].lower())
            _cached_models = models
            logger.info(f"Fetched {len(models)} models from OpenRouter")
            return models
    except Exception as e:
        logger.error(f"Failed to fetch OpenRouter models: {e}")
        return _cached_models if _cached_models else []


def get_available_models() -> List[Dict]:
    """Get cached models (use fetch_openrouter_models for fresh data)."""
    return _cached_models


def get_current_model() -> str:
    """Get currently selected model."""
    return _current_model


def set_current_model(model_id: str) -> bool:
    """Set the current model."""
    global _current_model
    _current_model = model_id
    logger.info(f"Model changed to: {model_id}")
    return True


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
        
        # Use instance model if set, otherwise use global current model
        model = self.model or _current_model
        
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
                    logger.error(f"OpenRouter error {e.response.status_code}: {e.response.text}")
                    if e.response.status_code == 429 and attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        logger.warning(f"Rate limited, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    if e.response.status_code == 400:
                        # Bad request - likely invalid model, try fallback
                        error_detail = e.response.text
                        raise Exception(f"OpenRouter API error: {error_detail}")
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
