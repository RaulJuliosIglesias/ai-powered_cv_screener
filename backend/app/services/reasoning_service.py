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

from app.config import settings, timeouts
from app.utils.text_utils import smart_truncate

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

What specific criteria is the user asking for? Break down the requirements clearly.

If no explicit criteria given, state default criteria: seniority, skills breadth, years of experience, etc.

**Inventory**

List ALL candidates found with their CV IDs:
- **[Luca Müller](cv:cv_fe6338e6)**
- **[Layla Hassan](cv:cv_71736e47)**
- **[Mei-Ling Chen](cv:cv_ffc6d564)**

Note which ones seem most relevant based on job titles or qualifications.

**Detailed Analysis**

For EACH relevant candidate:

**[Candidate Name](cv:cv_xxx)**:
- Key skills matching the query
- Years of experience in relevant areas
- Notable achievements or projects
- Strengths and potential weaknesses

Compare candidates directly. Explain differences clearly.

**Final Decision**

Provide clear ranking with explicit rationale.

Explain WHY **[Candidate A](cv:cv_xxx)** is better than **[Candidate B](cv:cv_yyy)**.

Base decision on the detailed analysis above.
:::

**Direct Answer**
[1-2 sentences. Candidate names MUST use this EXACT format: **[Full Name](cv:cv_xxx)** — Nothing else.]

**Analysis**

| Candidate | Key Skills | Experience | Score |
|-----------|------------|------------|-------|
| **[Full Name](cv:cv_xxx)** | skill1, skill2, skill3 | X years in area | 
| **[Full Name](cv:cv_xxx)** | skill4, skill5 | Y years in area | 

:::conclusion
[Final recommendation. Use ONLY format: **[Full Name](cv:cv_xxx)** for each candidate.]
:::

---

## CRITICAL FORMATTING RULES (MANDATORY - NO EXCEPTIONS)

1. **:::thinking block** - MANDATORY with detailed reasoning
2. **TABLE** - Valid markdown with pipes | aligned properly
3. **CANDIDATE NAME FORMAT** - THIS IS THE **ONLY** ACCEPTABLE FORMAT:

   
   CORRECT FORMAT (USE EXACTLY THIS):
   ```
   **[Patrik Hübner](cv:cv_dd668ac0)**
   **[Luca Müller](cv:cv_fe6338e6)**
   **[Layla Hassan](cv:cv_71736e47)**
   ```
   
   WRONG FORMATS (NEVER USE THESE):
   ```
   **[ Luca Müller](cv:cv_fe6338e6)**        SPACE after **
   ** Layla Hassan** cv_71736e47            SPACE after ** + standalone cv_xxx
   **Luca Müller** cv_fe6338e6              Missing link, standalone cv_xxx
   **Luca** [cv_fe6338e6](cv_fe6338e6)      Incomplete name + wrong link
   [Luca Müller](cv_fe6338e6)               Missing cv: prefix
   ```

4. **NO SPACES AFTER OPENING `**`** - The bracket `[` must come IMMEDIATELY after `**`
5. **EVERY candidate mention** in Thinking, Inventory, Analysis, Direct Answer, Table, AND Conclusion MUST use: `**[Full Name](cv:cv_xxx)**`
6. **NEVER write cv_xxx alone** - It MUST ALWAYS be inside the link: `(cv:cv_xxx)`
7. **NEVER duplicate references** - Write `**[Name](cv:cv_xxx)**` ONCE per mention

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
    
    def __init__(
        self,
        model: str,
        reflection_enabled: bool = True
    ):
        if not model:
            raise ValueError("model parameter is required and cannot be empty")
        self.model = model
        self.reflection_enabled = reflection_enabled
        self.api_key = settings.openrouter_api_key or ""
        logger.info(f"ReasoningService initialized with model: {self.model}")
    
    async def reason(
        self,
        question: str,
        context: str,
        total_cvs: int = 0
    ) -> 'LLMResult':
        """
        Apply structured reasoning to question with context.
        
        Returns:
            LLMResult with reasoning trace and final answer including OpenRouter metadata
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
        truncated_context = smart_truncate(
            context,
            max_chars=15000,
            preserve="both"
        )
        prompt = SELF_ASK_PROMPT.format(
            question=question,
            context=truncated_context,
            total_cvs=total_cvs
        )
        from app.providers.base import get_openrouter_url
        
        async with httpx.AsyncClient(timeout=timeouts.HTTP_LONG) as client:
            response = await client.post(
                get_openrouter_url("chat/completions"),
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
        
        # Extract OpenRouter usage metadata
        usage_metadata = {}
        if "usage" in data:
            usage = data["usage"]
            if isinstance(usage, dict):
                usage_metadata["prompt_tokens"] = usage.get("prompt_tokens", 0)
                usage_metadata["completion_tokens"] = usage.get("completion_tokens", 0)
                usage_metadata["total_tokens"] = usage.get("total_tokens", 0)
                usage_metadata["openrouter_cost"] = usage.get("total_cost", 0.0)
                logger.info(f"[REASONING] OpenRouter usage: {usage_metadata}")
            else:
                usage_metadata["openrouter_cost"] = float(usage) if usage else 0.0
        
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
                # Extract content after pattern
                idx = content.find(marker)
                end_idx = len(content)
                
                # Find next step
                for next_pattern, _ in answer_markers:
                    if next_pattern != marker:
                        next_idx = content.find(next_pattern, idx + len(marker))
                        if next_idx > 0:
                            end_idx = min(end_idx, next_idx)
                
                content = content[idx:end_idx].strip()
                if content:
                    thinking = content
                    answer = content
        
        # If no clear split, use the full content as thinking
        if not answer:
            answer = content
        
        logger.debug(f"Reasoning produced {len(thinking)} chars of thinking")
        return thinking, answer, usage_metadata
    
    async def _reflect_and_refine(
        self,
        question: str,
        draft: str,
        context: str
    ) -> str:
        """Reflect on draft and refine if needed."""
        truncated_context = smart_truncate(
            context,
            max_chars=10000,
            preserve="end"
        )
        prompt = REFLECTION_PROMPT.format(
            question=question,
            draft=draft,
            context=truncated_context
        )
        from app.providers.base import get_openrouter_url
        
        async with httpx.AsyncClient(timeout=timeouts.HTTP_LONG) as client:
            response = await client.post(
                get_openrouter_url("chat/completions"),
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
    model: str,
    reflection_enabled: bool = True
) -> ReasoningService:
    """Get singleton instance."""
    global _reasoning_service
    if _reasoning_service is None or _reasoning_service.model != model:
        _reasoning_service = ReasoningService(
            model=model,
            reflection_enabled=reflection_enabled
        )
    return _reasoning_service
