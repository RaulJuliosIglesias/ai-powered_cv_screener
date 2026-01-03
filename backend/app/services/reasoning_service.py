"""
Reasoning Service for RAG v5.

Implements structured Chain-of-Thought reasoning and Self-Ask patterns
for more intelligent response generation.
"""
import logging
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ReasoningStep:
    """A single step in the reasoning chain."""
    step_type: str  # "analysis", "sub_question", "evidence", "synthesis"
    content: str
    confidence: float = 1.0
    sources: List[str] = field(default_factory=list)


@dataclass
class ReasoningResult:
    """Result of reasoning process."""
    steps: List[ReasoningStep]
    final_answer: str
    needs_more_info: bool = False
    follow_up_queries: List[str] = field(default_factory=list)
    confidence: float = 0.8
    thinking_trace: str = ""


SELF_ASK_PROMPT = """You are an expert CV analyst. Answer based ONLY on provided CV data.

USER QUESTION: {question}

CV DATA:
{context}

TOTAL CANDIDATES: {total_cvs}

---

## OUTPUT FORMAT (MANDATORY)

:::thinking
**Understanding Query**
[What is being asked? What criteria to use?]

**Inventory**
[How many candidates found? Which ones are most relevant?]

**Analysis**
[Compare candidates on key dimensions]

**Decision**
[Final ranking and rationale]
:::

**Direct Answer**
[1-2 sentences. Use format: **[Name](cv:cv_xxx)**]

**Analysis**

| Candidate | Key Skills | Experience | Score |
|-----------|------------|------------|-------|
| **[Name](cv:cv_xxx)** | skill1, skill2 | X years | ⭐⭐⭐⭐ |
| **[Name](cv:cv_xxx)** | skill3, skill4 | Y years | ⭐⭐⭐ |

:::conclusion
[Clear recommendation with names as **[Name](cv:cv_xxx)**]
:::

---

## CRITICAL RULES

1. **ALWAYS include :::thinking block** - This shows your reasoning process
2. **TABLE must be valid markdown** - One row per candidate, pipes aligned
3. **CANDIDATE FORMAT**: `**[Full Name](cv:cv_xxx)**` - NO spaces after **
4. **NO standalone cv_xxx** anywhere except inside (cv:cv_xxx)
5. **IF NO CRITERIA**: State in thinking: "No criteria given. Using: seniority, skills, experience"

Answer now:"""


REFLECTION_PROMPT = """Review your draft response for accuracy and completeness.

ORIGINAL QUESTION: {question}

YOUR DRAFT RESPONSE:
{draft}

AVAILABLE CONTEXT:
{context}

CHECKLIST:
1. Does the response directly answer what was asked?
2. Is every claim supported by specific CV data?
3. Are there candidates I should have mentioned but didn't?
4. Is the ranking/comparison fair and justified?
5. Are there any unsupported assumptions?

If you find issues, provide a CORRECTED response.
If the response is good, return it unchanged.

REFLECTION:"""


class ReasoningService:
    """
    Service for structured reasoning and self-reflection.
    
    Implements:
    - Chain-of-Thought: Explicit step-by-step reasoning
    - Self-Ask: Generate and answer sub-questions
    - Reflection: Self-critique before final answer
    """
    
    DEFAULT_MODEL = "google/gemini-2.0-flash-001"
    
    def __init__(
        self,
        model: Optional[str] = None,
        reflection_enabled: bool = True
    ):
        self.model = model or self.DEFAULT_MODEL
        self.reflection_enabled = reflection_enabled
        self.api_key = settings.openrouter_api_key or ""
        logger.info(f"ReasoningService initialized with model: {self.model}")
    
    async def reason(
        self,
        question: str,
        context: str,
        total_cvs: int = 0
    ) -> ReasoningResult:
        """
        Apply structured reasoning to generate a well-thought answer.
        
        Args:
            question: User's question
            context: Formatted context from retrieved chunks
            total_cvs: Total CVs in session for context
            
        Returns:
            ReasoningResult with steps, answer, and metadata
        """
        if not self.api_key:
            logger.warning("No API key for reasoning")
            return ReasoningResult(
                steps=[],
                final_answer="",
                thinking_trace=""
            )
        
        try:
            # Step 1: Self-Ask structured reasoning
            thinking, draft_answer = await self._self_ask_reason(
                question, context, total_cvs
            )
            
            # Step 2: Reflection (if enabled)
            final_answer = draft_answer
            if self.reflection_enabled and draft_answer:
                final_answer = await self._reflect_and_refine(
                    question, draft_answer, context
                )
            
            # Parse reasoning steps
            steps = self._parse_thinking(thinking)
            
            return ReasoningResult(
                steps=steps,
                final_answer=final_answer,
                confidence=0.85 if steps else 0.7,
                thinking_trace=thinking
            )
            
        except Exception as e:
            logger.error(f"Reasoning failed: {e}")
            return ReasoningResult(
                steps=[],
                final_answer="",
                thinking_trace=""
            )
    
    async def _self_ask_reason(
        self,
        question: str,
        context: str,
        total_cvs: int
    ) -> tuple[str, str]:
        """Execute self-ask reasoning process."""
        prompt = SELF_ASK_PROMPT.format(
            question=question,
            context=context[:15000],  # Limit context size
            total_cvs=total_cvs
        )
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 3000
                }
            )
            response.raise_for_status()
            data = response.json()
        
        content = data["choices"][0]["message"]["content"].strip()
        
        # Split thinking from final answer
        thinking = content
        answer = ""
        
        # Look for final answer markers
        answer_markers = [
            "## FINAL ANSWER",
            "## Final Answer",
            "**FINAL ANSWER**",
            "ANSWER:",
            "---\n\n"
        ]
        
        for marker in answer_markers:
            if marker in content:
                parts = content.split(marker, 1)
                thinking = parts[0]
                answer = parts[1].strip() if len(parts) > 1 else ""
                break
        
        # If no clear split, use the full content as thinking
        if not answer:
            answer = content
        
        logger.debug(f"Reasoning produced {len(thinking)} chars of thinking")
        return thinking, answer
    
    async def _reflect_and_refine(
        self,
        question: str,
        draft: str,
        context: str
    ) -> str:
        """Reflect on draft and refine if needed."""
        prompt = REFLECTION_PROMPT.format(
            question=question,
            draft=draft,
            context=context[:10000]
        )
        
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 2000
                }
            )
            response.raise_for_status()
            data = response.json()
        
        refined = data["choices"][0]["message"]["content"].strip()
        
        # Check if reflection indicates changes
        if "unchanged" in refined.lower()[:100] or "response is good" in refined.lower()[:100]:
            return draft
        
        # Extract corrected response if present
        correction_markers = ["CORRECTED RESPONSE:", "CORRECTED:", "REFINED:"]
        for marker in correction_markers:
            if marker in refined:
                return refined.split(marker, 1)[1].strip()
        
        # If substantial difference, use refined
        if len(refined) > len(draft) * 0.5:
            return refined
        
        return draft
    
    def _parse_thinking(self, thinking: str) -> List[ReasoningStep]:
        """Parse thinking trace into structured steps."""
        steps = []
        
        # Look for step markers
        step_patterns = [
            ("## Step 1", "analysis"),
            ("## Step 2", "inventory"),
            ("## Step 3", "analysis"),
            ("## Step 4", "verification"),
            ("## Step 5", "synthesis"),
            ("UNDERSTAND", "analysis"),
            ("INVENTORY", "inventory"),
            ("ANALYZE", "analysis"),
            ("SELF-CHECK", "verification"),
            ("SYNTHESIZE", "synthesis")
        ]
        
        for pattern, step_type in step_patterns:
            if pattern in thinking:
                # Extract content after pattern
                idx = thinking.find(pattern)
                end_idx = len(thinking)
                
                # Find next step
                for next_pattern, _ in step_patterns:
                    if next_pattern != pattern:
                        next_idx = thinking.find(next_pattern, idx + len(pattern))
                        if next_idx > 0:
                            end_idx = min(end_idx, next_idx)
                
                content = thinking[idx:end_idx].strip()
                if content:
                    steps.append(ReasoningStep(
                        step_type=step_type,
                        content=content[:500]  # Limit size
                    ))
        
        return steps


# Singleton
_reasoning_service: Optional[ReasoningService] = None


def get_reasoning_service(
    model: Optional[str] = None,
    reflection_enabled: bool = True
) -> ReasoningService:
    """Get singleton instance."""
    global _reasoning_service
    if _reasoning_service is None:
        _reasoning_service = ReasoningService(
            model=model,
            reflection_enabled=reflection_enabled
        )
    return _reasoning_service
