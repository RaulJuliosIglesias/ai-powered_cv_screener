import time
import logging
from typing import Optional, List, Dict
import httpx
from app.providers.base import LLMProvider, LLMResult
from app.config import settings

logger = logging.getLogger(__name__)

# Cache for models fetched from OpenRouter
_cached_models: List[Dict] = []


async def fetch_openrouter_models() -> List[Dict]:
    """Fetch all available models from OpenRouter API."""
    global _cached_models
    try:
        from app.providers.base import get_openrouter_url
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                get_openrouter_url("models"),
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


def calculate_openrouter_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate cost for an OpenRouter model based on token counts.
    
    This is a shared utility function that can be used by any service
    that makes OpenRouter API calls.
    """
    for m in _cached_models:
        if m["id"] == model:
            pricing = m.get("pricing_raw", {})
            # pricing_raw is per 1M tokens
            prompt_cost = (prompt_tokens / 1_000_000) * pricing.get("prompt", 0)
            completion_cost = (completion_tokens / 1_000_000) * pricing.get("completion", 0)
            return prompt_cost + completion_cost
    return 0.0


class OpenRouterLLMProvider(LLMProvider):
    """LLM provider using OpenRouter API."""
    
    def __init__(self, model: str):
        if not model:
            raise ValueError("model parameter is required and cannot be empty")
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = model
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048
    ):
        """Generate response with streaming tokens.
        
        Yields:
            dict with either:
                - {"token": "..."} for each token
                - {"done": True, "text": "...", "usage": {...}} when complete
        """
        import asyncio
        start = time.perf_counter()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        logger.info(f"[LLM STREAM] Starting stream with model: {self.model}")
        
        full_response = ""
        prompt_tokens = 0
        completion_tokens = 0
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": settings.http_referer,
                    "X-Title": settings.app_title,
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            import json
                            data = json.loads(data_str)
                            
                            # Extract token from delta
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    full_response += content
                                    yield {"token": content}
                            
                            # Extract usage if present (some providers send at end)
                            usage = data.get("usage")
                            if usage:
                                prompt_tokens = usage.get("prompt_tokens", 0)
                                completion_tokens = usage.get("completion_tokens", 0)
                        except json.JSONDecodeError:
                            continue
        
        latency = (time.perf_counter() - start) * 1000
        
        # Estimate tokens if not provided
        if not completion_tokens:
            completion_tokens = len(full_response.split()) * 1.3  # rough estimate
        
        total_cost = self._calculate_cost(int(prompt_tokens), int(completion_tokens))
        
        logger.info(f"[LLM STREAM] Completed: {prompt_tokens}+{completion_tokens} tokens, cost=${total_cost:.6f}, latency={latency:.0f}ms")
        
        yield {
            "done": True,
            "text": full_response,
            "usage": {
                "prompt_tokens": int(prompt_tokens),
                "completion_tokens": int(completion_tokens),
                "total_tokens": int(prompt_tokens + completion_tokens)
            },
            "latency_ms": latency,
            "openrouter_cost": total_cost
        }
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048
    ) -> LLMResult:
        import asyncio
        start = time.perf_counter()
        
        model = self.model
        
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
                            "HTTP-Referer": settings.http_referer,
                            "X-Title": settings.app_title,
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
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        # Calculate cost from tokens and model pricing
        # OpenRouter doesn't return cost directly in chat/completions response
        total_cost = self._calculate_cost(prompt_tokens, completion_tokens)
        
        logger.info(f"[LLM] {self.model}: {prompt_tokens}+{completion_tokens} tokens, cost=${total_cost:.6f}")
        
        return LLMResult(
            text=data["choices"][0]["message"]["content"],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency,
            metadata={"openrouter_cost": total_cost}
        )
    
    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost based on model pricing and token counts."""
        # Try to get pricing from cached models
        for m in _cached_models:
            if m["id"] == self.model:
                pricing = m.get("pricing_raw", {})
                # pricing_raw is per 1M tokens
                prompt_cost = (prompt_tokens / 1_000_000) * pricing.get("prompt", 0)
                completion_cost = (completion_tokens / 1_000_000) * pricing.get("completion", 0)
                return prompt_cost + completion_cost
        
        # Fallback: if model not in cache, return 0 (will be updated when models are fetched)
        return 0.0
