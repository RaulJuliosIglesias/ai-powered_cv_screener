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
from app.providers.cloud.llm import calculate_openrouter_cost

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


SELF_ASK_PROMPT = """You are an expert CV analyst and talent acquisition specialist with deep expertise in evaluating candidates. Your task is to provide a comprehensive, well-reasoned analysis based ONLY on the provided CV data.

USER QUESTION: {question}

CV DATA:
{context}

TOTAL CANDIDATES IN DATABASE: {total_cvs}

---

## YOUR TASK

You must think deeply and thoroughly before answering. Your reasoning process should be extensive, covering every angle of the question. Do NOT rush to conclusions.

## OUTPUT FORMAT (MANDATORY)

:::thinking

### STEP 1: DEEP QUERY UNDERSTANDING

Before analyzing any candidate, I need to fully understand what is being asked:

**Primary Intent Analysis:**
- What is the user's main objective? (hiring, comparison, skill search, etc.)
- What type of role or profile are they looking for?
- Are there any implicit requirements beyond what's explicitly stated?

**Explicit Requirements Extraction:**
- List every specific criterion mentioned in the query
- For each criterion, define what "good" vs "excellent" looks like
- Note any must-have vs nice-to-have distinctions

**Implicit Requirements Inference:**
- Based on the role/query type, what skills are typically expected?
- What experience level seems appropriate?
- Are there industry-specific considerations?

**Evaluation Framework Definition:**
- How should I weight different criteria?
- What scoring approach makes sense for this query?
- What would disqualify a candidate vs just lower their ranking?

---

### STEP 2: COMPREHENSIVE CANDIDATE INVENTORY

Now I will systematically catalog ALL candidates found in the provided data:

**Complete Candidate List:**
For each candidate in the CV data, record:
- Full name and CV ID
- Current/most recent job title
- Primary domain/industry
- Years of total experience (if determinable)
- First impression relevance to query (High/Medium/Low/None)

**Initial Relevance Triage:**
- Which candidates appear highly relevant at first glance? Why?
- Which candidates are potentially relevant but need deeper analysis?
- Which candidates appear clearly not relevant? Why exclude them?

**Data Quality Assessment:**
- Is the CV data complete for each candidate?
- Are there gaps that might affect my evaluation?
- What information is missing that would be helpful?

---

### STEP 3: DEEP INDIVIDUAL CANDIDATE ANALYSIS

For EACH relevant candidate, I will conduct a thorough analysis:

**[Candidate Name](cv:cv_xxx):**

*Professional Background Deep Dive:*
- Career trajectory and progression pattern
- Industry experience and domain expertise
- Company types worked at (startup, enterprise, agency, etc.)
- Role evolution (IC to lead, specialist to generalist, etc.)

*Technical/Skill Assessment:*
- Core competencies directly matching query requirements
- Adjacent skills that add value
- Technology stack depth and breadth
- Certifications or formal qualifications

*Experience Quality Analysis:*
- Not just years, but quality and relevance of experience
- Specific projects or achievements that demonstrate capability
- Scale of work (team size, project scope, budget, etc.)
- Measurable outcomes or impact where stated

*Strengths Identification:*
- What makes this candidate stand out?
- Unique value propositions
- Competitive advantages over other candidates

*Potential Concerns or Gaps:*
- What's missing from their profile?
- Any red flags or areas of weakness?
- Experience gaps relative to the requirements

*Fit Score Justification:*
- How well do they match each explicit requirement? (score 1-10)
- How well do they match implicit requirements?
- Overall fit assessment with detailed reasoning

[Repeat this entire analysis block for EACH relevant candidate]

---

### STEP 4: COMPARATIVE ANALYSIS

Now I will directly compare candidates against each other:

**Head-to-Head Comparisons:**

*[Candidate A](cv:cv_xxx) vs [Candidate B](cv:cv_yyy):*
- Where does A outperform B?
- Where does B outperform A?
- For the specific query requirements, who has the edge and why?
- If they're close, what's the tiebreaker?

[Repeat for each meaningful candidate pair]

**Dimensional Comparison Matrix:**
- Compare all candidates on each key dimension
- Identify clear winners on each dimension
- Note where candidates are roughly equivalent

**Trade-off Analysis:**
- What trade-offs exist between top candidates?
- Is there a "safe choice" vs "high upside" candidate?
- How should different user priorities affect the ranking?

---

### STEP 5: SELF-VERIFICATION & BIAS CHECK

Before finalizing, I need to verify my reasoning:

**Evidence Verification:**
- For each claim I'm making, can I point to specific CV data?
- Am I making any assumptions not supported by the data?
- Have I misread or misinterpreted any information?

**Bias Check:**
- Am I favoring candidates for irrelevant reasons?
- Have I given fair consideration to all relevant candidates?
- Am I being consistent in how I evaluate similar qualifications?

**Alternative Perspective:**
- If someone disagreed with my ranking, what would their argument be?
- Is there a reasonable case for a different top candidate?
- What additional information would change my assessment?

**Confidence Calibration:**
- How confident am I in my top recommendation?
- Where is there genuine uncertainty?
- What caveats should I include?

---

### STEP 6: FINAL SYNTHESIS & RANKING

**Definitive Ranking:**
1. **[Top Candidate](cv:cv_xxx)** - Primary recommendation
   - Key differentiators that put them first
   - Strongest matching qualifications
   - Why they edge out #2

2. **[Second Candidate](cv:cv_yyy)** - Strong alternative
   - What they do well
   - Why they're not #1
   - When they might be the better choice

[Continue for all relevant candidates]

**Recommendation Confidence:**
- High/Medium/Low confidence in ranking
- Key factors that could change the ranking

**Key Insights:**
- Most important takeaways from this analysis
- Patterns or observations worth noting
:::

---

## FINAL RESPONSE

**Direct Answer**
[2-3 clear sentences answering the user's question directly. Every candidate name MUST use format: **[Full Name](cv:cv_xxx)**]

**Analysis Summary**

| Candidate | Key Qualifications | Relevant Experience | Fit Score |
|-----------|-------------------|---------------------|----------|
| **[Full Name](cv:cv_xxx)** | Top 3 relevant skills | X years in Y | 9/10 |
| **[Full Name](cv:cv_yyy)** | Top 3 relevant skills | X years in Y | 8/10 |

**Key Differentiators**
[Brief explanation of what separates the top candidates]

:::conclusion
[Final recommendation with clear rationale. Use ONLY format: **[Full Name](cv:cv_xxx)** for each candidate mentioned.]
:::

---

## CRITICAL FORMATTING RULES (MANDATORY)

1. **:::thinking block** - MUST be extensive with ALL 6 steps fully developed
2. **Candidate name format** - ONLY acceptable format: **[Full Name](cv:cv_xxx)**
3. **Never write cv_xxx alone** - Always inside link: (cv:cv_xxx)
4. **No spaces after `**`** - Bracket must immediately follow: **[Name]
5. **Table format** - Valid markdown with aligned pipes

CORRECT: **[Patrik Hübner](cv:cv_dd668ac0)**
WRONG: **Patrik Hübner** cv_dd668ac0
WRONG: [Patrik Hübner](cv_dd668ac0)
WRONG: ** [Patrik Hübner](cv:cv_dd668ac0)**

Now provide your complete analysis:"""


REFLECTION_PROMPT = """You are a senior talent acquisition expert reviewing an analysis for accuracy, completeness, and quality.

ORIGINAL QUESTION: {question}

DRAFT RESPONSE TO REVIEW:
{draft}

AVAILABLE CV DATA:
{context}

---

## COMPREHENSIVE REVIEW CHECKLIST

**Accuracy Review:**
1. Is every factual claim directly supported by the CV data provided?
2. Are candidate names, job titles, and companies accurately stated?
3. Are years of experience calculated correctly?
4. Have any skills or qualifications been misattributed?

**Completeness Review:**
5. Does the response fully address the user's question?
6. Are all relevant candidates mentioned and analyzed?
7. Were any strong candidates overlooked or dismissed too quickly?
8. Is the reasoning thorough enough to justify the conclusions?

**Logic & Fairness Review:**
9. Is the ranking/comparison logic consistent and fair?
10. Are similar qualifications evaluated consistently across candidates?
11. Are the evaluation criteria appropriate for the question asked?
12. Is the confidence level appropriate given the available data?

**Quality Review:**
13. Is the response clear and well-structured?
14. Are the key differentiators clearly articulated?
15. Would the user understand WHY this recommendation was made?
16. Is the thinking process thorough and insightful?

---

## YOUR TASK

Based on your review:

**If you find significant issues:**
Provide a CORRECTED RESPONSE that fixes all identified problems.
Start with "CORRECTED RESPONSE:" followed by the improved analysis.

**If the response is accurate and complete:**
Respond with "RESPONSE VERIFIED: The analysis is accurate and complete."
Then restate the key conclusion.

**Always ensure:**
- Candidate format: **[Full Name](cv:cv_xxx)** 
- No unsupported claims
- Clear, justified rankings

Your review:"""


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
            max_chars=25000,
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
                    "temperature": 0.3,
                    "max_tokens": 6000
                }
            )
            response.raise_for_status()
            data = response.json()
        
        content = data["choices"][0]["message"]["content"].strip()
        
        # Extract OpenRouter usage metadata and calculate cost
        usage_metadata = {}
        if "usage" in data:
            usage = data["usage"]
            if isinstance(usage, dict):
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                usage_metadata["prompt_tokens"] = prompt_tokens
                usage_metadata["completion_tokens"] = completion_tokens
                usage_metadata["total_tokens"] = prompt_tokens + completion_tokens
                # Calculate cost from tokens and model pricing
                usage_metadata["openrouter_cost"] = calculate_openrouter_cost(
                    self.model, prompt_tokens, completion_tokens
                )
                logger.info(f"[REASONING] OpenRouter usage: {usage_metadata}")
        
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
        
        # Look for step markers - updated for 6-step deep reasoning process
        step_patterns = [
            ("### STEP 1: DEEP QUERY UNDERSTANDING", "query_understanding"),
            ("### STEP 2: COMPREHENSIVE CANDIDATE INVENTORY", "inventory"),
            ("### STEP 3: DEEP INDIVIDUAL CANDIDATE ANALYSIS", "deep_analysis"),
            ("### STEP 4: COMPARATIVE ANALYSIS", "comparison"),
            ("### STEP 5: SELF-VERIFICATION & BIAS CHECK", "verification"),
            ("### STEP 6: FINAL SYNTHESIS & RANKING", "synthesis"),
            # Fallback patterns for shorter markers
            ("STEP 1:", "query_understanding"),
            ("STEP 2:", "inventory"),
            ("STEP 3:", "deep_analysis"),
            ("STEP 4:", "comparison"),
            ("STEP 5:", "verification"),
            ("STEP 6:", "synthesis"),
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
                        content=content[:2000]  # Increased limit for richer content
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
