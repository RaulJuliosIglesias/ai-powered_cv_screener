import time
from typing import Optional
import google.generativeai as genai
from app.providers.base import LLMProvider, LLMResult
from app.config import settings


class GeminiLLMProvider(LLMProvider):
    """LLM provider using Google Gemini via AI Studio."""
    
    def __init__(self, model: str):
        if not model:
            raise ValueError("model parameter is required and cannot be empty")
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(model)
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048
    ) -> LLMResult:
        start = time.perf_counter()
        
        # Combine system prompt with user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = self.model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
        )
        
        latency = (time.perf_counter() - start) * 1000
        
        # Extract token counts from response
        usage = response.usage_metadata
        
        return LLMResult(
            text=response.text,
            prompt_tokens=usage.prompt_token_count if usage else 0,
            completion_tokens=usage.candidates_token_count if usage else 0,
            latency_ms=latency
        )
