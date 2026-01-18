"""
Cost tracking for OpenRouter API calls.
Based on actual OpenRouter pricing: https://openrouter.ai/docs/pricing
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict

logger = logging.getLogger(__name__)

# OpenRouter pricing per 1M tokens (as of January 2026)
# https://openrouter.ai/models
# IMPORTANT: Use native_tokens from API response for accurate billing
MODEL_PRICING = {
    # Gemini models - Based on real usage data from OpenRouter
    "google/gemini-2.0-flash-exp:free": {"input": 0.0, "output": 0.0},
    "google/gemini-2.0-flash-001": {"input": 0.26, "output": 0.26},  # Verified: $0.024/90K tokens ≈ $0.26/1M
    "google/gemini-flash-1.5": {"input": 0.075, "output": 0.30},
    "google/gemini-pro-1.5": {"input": 1.25, "output": 5.0},
    
    # DeepSeek models
    "deepseek/deepseek-chat": {"input": 0.27, "output": 1.10},
    "deepseek/deepseek-r1": {"input": 0.55, "output": 2.19},
    
    # OpenAI models
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openai/gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "openai/gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    
    # Anthropic models
    "anthropic/claude-3.5-sonnet": {"input": 3.0, "output": 15.0},
    "anthropic/claude-3-opus": {"input": 15.0, "output": 75.0},
    "anthropic/claude-3-sonnet": {"input": 3.0, "output": 15.0},
    "anthropic/claude-3-haiku": {"input": 0.25, "output": 1.25},
    
    # Meta models
    "meta-llama/llama-3.1-70b-instruct": {"input": 0.52, "output": 0.75},
    "meta-llama/llama-3.1-8b-instruct": {"input": 0.06, "output": 0.06},
    
    # Mistral models
    "mistralai/mistral-large": {"input": 3.0, "output": 9.0},
    "mistralai/mistral-medium": {"input": 2.7, "output": 8.1},
    "mistralai/mistral-small": {"input": 0.2, "output": 0.6},
    
    # Cohere models
    "cohere/command-r-plus": {"input": 2.5, "output": 10.0},
    "cohere/command-r": {"input": 0.15, "output": 0.60},
    
    # Embeddings
    "openai/text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "openai/text-embedding-3-large": {"input": 0.13, "output": 0.0},
    "nomic-ai/nomic-embed-text-v1.5": {"input": 0.02, "output": 0.0},
}

# Default pricing for unknown models (conservative estimate)
DEFAULT_PRICING = {"input": 1.0, "output": 3.0}


@dataclass
class StepCost:
    """Cost for a single pipeline step."""
    step_name: str
    model: str
    input_tokens: int
    output_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_name": self.step_name,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "input_cost_usd": round(self.input_cost_usd, 6),
            "output_cost_usd": round(self.output_cost_usd, 6),
            "total_cost_usd": round(self.total_cost_usd, 6),
        }


@dataclass
class CostSummary:
    """Summary of all costs for a query."""
    steps: list[StepCost] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    web_search_cost_usd: float = 0.0  # OpenRouter charges $0.02 per web search
    
    def add_step(self, step: StepCost) -> None:
        """Add a step cost to the summary."""
        self.steps.append(step)
        self.total_input_tokens += step.input_tokens
        self.total_output_tokens += step.output_tokens
        self.total_cost_usd += step.total_cost_usd
    
    def add_web_search_cost(self, cost: float) -> None:
        """Add web search cost (OpenRouter charges extra for this)."""
        self.web_search_cost_usd += cost
        self.total_cost_usd += cost
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "steps": [s.to_dict() for s in self.steps],
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
        }
        if self.web_search_cost_usd > 0:
            result["web_search_cost_usd"] = round(self.web_search_cost_usd, 6)
        return result


class CostTracker:
    """Tracks costs for all API calls in a pipeline."""
    
    def __init__(self):
        self.costs = CostSummary()
    
    def calculate_cost(
        self,
        step_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> StepCost:
        """Calculate cost for a single API call."""
        # Get pricing for model (case-insensitive match)
        pricing = None
        model_lower = model.lower()
        
        # Try exact match first
        if model in MODEL_PRICING:
            pricing = MODEL_PRICING[model]
        else:
            # Try case-insensitive match
            for key in MODEL_PRICING:
                if key.lower() == model_lower:
                    pricing = MODEL_PRICING[key]
                    break
        
        if not pricing:
            # Try partial match for model families
            for key in MODEL_PRICING:
                if model_lower in key.lower() or key.lower() in model_lower:
                    pricing = MODEL_PRICING[key]
                    logger.warning(f"Using approximate pricing for {model} based on {key}")
                    break
        
        if not pricing:
            logger.warning(f"No pricing found for model {model}, using default")
            pricing = DEFAULT_PRICING
        
        # Calculate costs (pricing is per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        step_cost = StepCost(
            step_name=step_name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost_usd=input_cost,
            output_cost_usd=output_cost,
            total_cost_usd=total_cost
        )
        
        self.costs.add_step(step_cost)
        
        logger.info(
            f"[COST] {step_name} using {model}: "
            f"{input_tokens} in + {output_tokens} out = ${total_cost:.6f}"
        )
        
        return step_cost
    
    def get_summary(self) -> CostSummary:
        """Get the cost summary."""
        return self.costs
    
    def get_total_cost(self) -> float:
        """Get total cost in USD."""
        return self.costs.total_cost_usd
