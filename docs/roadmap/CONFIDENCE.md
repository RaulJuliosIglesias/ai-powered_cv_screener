# Implementation Plan: Advanced Confidence Scoring

## 🔴 HONEST ANALYSIS: What We Have vs. What We Need

### Current State (REALITY)

| Technique | Do We Have It? | How It's Implemented | Quality |
|-----------|----------------|----------------------|---------|
| **Claim Extraction** | ✅ Yes | LLM via OpenRouter extracts claims from response | 🟡 Basic |
| **Claim Verification** | ✅ Partial | LLM verifies claim vs context (NOT real NLI) | 🟡 Basic |
| **Source Relevance** | ✅ Yes | Average similarity scores from vector search | 🟢 Correct |
| **Source Coverage** | ✅ Yes | Chunk count + CV diversity | 🟢 Correct |
| **Response Completeness** | ✅ Yes | Checks structured output components | 🟢 Correct |
| **Internal Consistency** | ✅ Partial | Basic heuristics (table↔conclusion) | 🟡 Basic |
| **LLM-as-Judge** | ❌ NO | Not implemented | ❌ |
| **NLI Models** | ❌ NO | We use generic LLM, not specialized NLI model | ❌ |
| **Self-Consistency** | ❌ NO | We only generate 1 response | ❌ |
| **Token Probabilities** | ❌ NO | OpenRouter doesn't easily expose log_probs | ❌ |
| **Citation Verification** | ❌ NO | We don't generate verifiable inline citations | ❌ |
| **Answer Relevance** | ❌ NO | We don't measure query↔response similarity | ❌ |
| **Confidence Calibration** | ❌ NO | We don't have historical feedback | ❌ |
| **RAGAS Metrics** | ❌ NO | We don't use the framework | ❌ |

### Brutal Verdict

**What I implemented before is FUNCTIONAL but NOT industry-level.**

- ✅ **It is real**: Scores come from real data (similarity scores, claim counts, etc.)
- ❌ **NOT advanced**: Missing LLM-as-Judge, NLI, Self-Consistency, Answer Relevance
- 🟡 **It's about 30%** of what Sierra/Perplexity/Anthropic do

---

## 📊 Detailed Gap Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    OUR CURRENT IMPLEMENTATION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Query → [Guardrail] → [Retrieval] → [Generation] → [Claim Verify] →       │
│          basic         similarity    LLM             basic LLM             │
│                        scores                                               │
│                                                                             │
│  Confidence = weighted_avg(                                                 │
│      source_coverage,      ← chunk count (REAL but simplistic)             │
│      source_relevance,     ← avg similarity scores (REAL ✓)                │
│      claim_verification,   ← LLM verifies claims (REAL but NOT NLI)        │
│      response_completeness,← checks components (REAL ✓)                    │
│      internal_consistency  ← basic heuristics (WEAK)                       │
│  )                                                                          │
│                                                                             │
│  ❌ MISSING:                                                                │
│  • LLM-as-Judge evaluating Faithfulness/Relevance/Completeness             │
│  • NLI model for real entailment                                           │
│  • Answer Relevance (query↔response similarity)                            │
│  • Self-Consistency (multiple samples)                                     │
│  • Token probability analysis                                              │
│  • Citation verification                                                   │
│  • Confidence calibration with historical feedback                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                    WHAT IT SHOULD BE (INDUSTRY)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Query → [Pre-Retrieval Evals] → [Retrieval + Coverage Check] →            │
│          safety, intent          RAGAS context precision/recall            │
│                                                                             │
│        → [Generation + Self-Assessment] → [Post-Gen Evals] →               │
│          LLM generates + states confidence  LLM-as-Judge                   │
│                                             NLI Faithfulness               │
│                                             Answer Relevance               │
│                                             Citation Verify                │
│                                                                             │
│        → [Decision Engine] → Response                                       │
│          ≥0.8: send                                                        │
│          ≥0.5: send with disclaimer                                        │
│          ≥0.3: regenerate                                                  │
│          <0.3: decline                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Phased Implementation Plan

### PHASE 1: LLM-as-Judge (HIGH IMPACT, MEDIUM DIFFICULTY)
**Estimated time: 2-3 days**
**Architecture change: NO**
**Additional APIs: NO (uses existing OpenRouter)**

```python
# New technique: One LLM evaluates another LLM's response

# File: backend/app/services/llm_judge_service.py

JUDGE_PROMPT = """You are an expert evaluator for a CV screening RAG system.

CONTEXT (retrieved CV chunks):
{context}

QUESTION: {question}

RESPONSE TO EVALUATE: {response}

Evaluate on these criteria (1-5 scale):

1. FAITHFULNESS: Is every claim supported by the CV context?
2. RELEVANCE: Does the response answer the question asked?
3. COMPLETENESS: Are all parts of the question addressed?
4. List any HALLUCINATIONS (claims not in context)

Respond in JSON:
{
  "faithfulness": <int 1-5>,
  "relevance": <int 1-5>,
  "completeness": <int 1-5>,
  "hallucinations": [<list>],
  "confidence": <float 0-1>,
  "reasoning": "<explanation>"
}"""
```

**Impact:**
- Replaces our simplistic claim_verification
- A single LLM call that evaluates EVERYTHING
- Much more robust than verifying claim by claim

---

### PHASE 2: Answer Relevance (HIGH IMPACT, LOW DIFFICULTY)
**Estimated time: 1 day**
**Architecture change: NO**
**Additional APIs: NO**

```python
# Technique: Measure semantic similarity between query and response

async def calculate_answer_relevance(
    query: str,
    response: str,
    embedder
) -> float:
    """
    Uses embeddings to measure if the response is relevant to the question.
    """
    query_embedding = await embedder.embed_text(query)
    response_embedding = await embedder.embed_text(response[:1000])  # Truncate
    
    # Cosine similarity
    similarity = cosine_similarity(query_embedding, response_embedding)
    
    return similarity  # 0.0 - 1.0
```

**Impact:**
- Detects responses that ramble or don't answer
- Reuses existing embedder
- Very fast (only 2 embeddings)

---

### PHASE 3: Self-Consistency Light (MEDIUM IMPACT, MEDIUM DIFFICULTY)
**Estimated time: 2 days**
**Architecture change: MINOR (generates 2-3 responses)**
**Additional APIs: NO**
**Cost: 2-3x more tokens**

```python
# Technique: Generate N responses and measure consistency

async def generate_with_consistency(
    prompt: str,
    llm,
    n_samples: int = 3,
    temperature: float = 0.7
) -> Tuple[str, float]:
    """
    Generates multiple responses and measures consistency.
    """
    responses = []
    for _ in range(n_samples):
        resp = await llm.generate(prompt, temperature=temperature)
        responses.append(resp.text)
    
    # Extract "key answer" from each response
    key_answers = [extract_key_answer(r) for r in responses]
    
    # Measure consistency
    consistency = calculate_agreement(key_answers)
    
    # Use response with temperature=0 as final
    final_response = await llm.generate(prompt, temperature=0)
    
    return final_response.text, consistency
```

**Impact:**
- High consistency = high confidence
- Detects when the model is "guessing"
- Trade-off: more latency and cost

---

### PHASE 4: NLI Faithfulness (HIGH IMPACT, HIGH DIFFICULTY)
**Estimated time: 3-5 days**
**Architecture change: YES (new model)**
**Additional APIs: YES - Hugging Face Inference API or local model**

```python
# Technique: Specialized NLI model to verify entailment

# Option A: Hugging Face Inference API
NLI_MODEL = "microsoft/deberta-v3-large-mnli"  # Or cross-encoder/nli-deberta-v3-base

async def verify_claim_nli(
    claim: str,
    context: str,
    hf_api_key: str
) -> Tuple[str, float]:
    """
    Verifies if the context entails the claim.
    
    Returns:
        ("entailment" | "neutral" | "contradiction", confidence)
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api-inference.huggingface.co/models/{NLI_MODEL}",
            headers={"Authorization": f"Bearer {hf_api_key}"},
            json={
                "inputs": {
                    "premise": context,
                    "hypothesis": claim
                }
            }
        )
        result = response.json()
    
    # Result: [{"label": "ENTAILMENT", "score": 0.95}, ...]
    top_label = max(result, key=lambda x: x["score"])
    return top_label["label"].lower(), top_label["score"]

# Option B: Local model with transformers
from transformers import pipeline

nli_pipeline = pipeline("text-classification", model=NLI_MODEL)

def verify_claim_local(claim: str, context: str):
    result = nli_pipeline(f"{context} [SEP] {claim}")
    return result[0]["label"], result[0]["score"]
```

**Impact:**
- Much more precise claim verification than generic LLM
- NLI models are specifically trained for this
- Faster and cheaper than LLM calls

**Requirements:**
- Hugging Face API key (free for moderate usage) OR
- Local GPU for model (4GB+ VRAM)

---

### PHASE 5: Citation Verification (MEDIUM IMPACT, MEDIUM DIFFICULTY)
**Estimated time: 2-3 days**
**Architecture change: YES (change generation prompt)**
**Additional APIs: NO**

```python
# Step 1: Modify prompt so LLM generates with citations

GENERATION_PROMPT = """
Answer the question using ONLY the provided context.
IMPORTANT: Add inline citations [1], [2], etc. for every factual claim.

Context:
[1] {chunk_1}
[2] {chunk_2}
...

Question: {question}

Answer with citations:
"""

# Step 2: Verify each citation

async def verify_citations(
    response: str,
    chunks: List[str]
) -> Tuple[float, List[dict]]:
    """
    Extracts citations from response and verifies each one.
    """
    # Extract citations: "claim [1]" → claim, source_idx
    citation_pattern = r'([^.]+)\[(\d+)\]'
    citations = re.findall(citation_pattern, response)
    
    results = []
    for claim, source_idx in citations:
        source = chunks[int(source_idx) - 1]
        
        # Verify with NLI or LLM
        is_supported = await verify_claim_nli(claim, source)
        
        results.append({
            "claim": claim,
            "source_idx": source_idx,
            "is_valid": is_supported[0] == "entailment",
            "confidence": is_supported[1]
        })
    
    valid_count = sum(1 for r in results if r["is_valid"])
    citation_score = valid_count / len(results) if results else 0
    
    return citation_score, results
```

---

### PHASE 6: Decision Engine (MEDIUM IMPACT, LOW DIFFICULTY)
**Estimated time: 1 day**
**Architecture change: NO**
**Additional APIs: NO**

```python
# Confidence-based decision logic

class DecisionEngine:
    THRESHOLDS = {
        "send": 0.80,
        "send_with_disclaimer": 0.50,
        "regenerate": 0.30,
        "decline": 0.0
    }
    
    def decide(
        self,
        confidence: float,
        faithfulness: float,
        has_contradictions: bool
    ) -> Tuple[str, Optional[str]]:
        """
        Decides what to do with the response.
        
        Returns:
            (action, disclaimer_text)
        """
        # Hard failures
        if has_contradictions:
            return "regenerate", None
        
        if faithfulness < 0.5:
            return "regenerate", None
        
        # Confidence-based decision
        if confidence >= self.THRESHOLDS["send"]:
            return "send", None
        
        elif confidence >= self.THRESHOLDS["send_with_disclaimer"]:
            return "send_with_disclaimer", (
                "⚠️ This response has moderate confidence. "
                "Verify the information with the original CVs."
            )
        
        elif confidence >= self.THRESHOLDS["regenerate"]:
            return "regenerate", None
        
        else:
            return "decline", (
                "I don't have enough information in the CVs to "
                "answer this question with confidence."
            )
```

---

## 📋 Summary of Required Changes

### Architecture Changes

| Change | Severity | Description |
|--------|----------|-------------|
| LLM-as-Judge | 🟢 Minor | New service, doesn't change flow |
| Answer Relevance | 🟢 Minor | Reuses existing embedder |
| Self-Consistency | 🟡 Moderate | Generates multiple responses |
| NLI Model | 🟡 Moderate | New external dependency |
| Citation Verification | 🟡 Moderate | Changes generation prompt |
| Decision Engine | 🟢 Minor | New post-generation logic |

### New APIs/Keys Required

| Service | Required? | Cost | Alternative |
|---------|-----------|------|-------------|
| Hugging Face API | Optional | Free (rate limited) | Local model |
| OpenRouter | Already have | Variable | - |
| Local NLI Model | Optional | GPU 4GB+ | HF API |

### Impact on Current Stack

```
CURRENT STACK:
├── Backend: FastAPI + Python ✅ (unchanged)
├── Frontend: React + Vite ✅ (unchanged)
├── Vector DB: Supabase pgvector ✅ (unchanged)
├── LLM: OpenRouter ✅ (unchanged)
├── Embeddings: OpenRouter ✅ (unchanged)
└── NEW: Hugging Face API (optional) or local NLI model

CODE CHANGES:
├── backend/app/services/
│   ├── confidence_calculator.py   → REWRITE (integrate new scores)
│   ├── llm_judge_service.py       → NEW
│   ├── answer_relevance_service.py → NEW
│   ├── nli_verifier_service.py    → NEW (if using NLI)
│   └── decision_engine.py         → NEW
├── backend/app/services/rag_service_v5.py → MODIFY (integrate phases)
└── frontend/src/components/MetricsPanel.jsx → MODIFY (show new scores)
```

---

## 🎯 Implementation Recommendation

### Order by ROI (Return on Investment)

| Priority | Technique | Effort | Impact | ROI |
|----------|-----------|--------|--------|-----|
| 1️⃣ | LLM-as-Judge | 2-3 days | 🔴 High | ⭐⭐⭐⭐⭐ |
| 2️⃣ | Answer Relevance | 1 day | 🔴 High | ⭐⭐⭐⭐⭐ |
| 3️⃣ | Decision Engine | 1 day | 🟡 Medium | ⭐⭐⭐⭐ |
| 4️⃣ | Citation Verification | 2-3 days | 🟡 Medium | ⭐⭐⭐ |
| 5️⃣ | Self-Consistency | 2 days | 🟡 Medium | ⭐⭐⭐ |
| 6️⃣ | NLI Faithfulness | 3-5 days | 🔴 High | ⭐⭐⭐ |

### Recommended MVP (1 week)

Implement only:
1. **LLM-as-Judge** - Replaces our current claim verification
2. **Answer Relevance** - Very easy, high impact
3. **Decision Engine** - Intelligent behavior

This would take us from **30% to ~60%** of what industry does.

### Complete Version (3-4 weeks)

Add:
4. **Citation Verification** - Requires changing prompts
5. **Self-Consistency** - Cost/precision trade-off
6. **NLI Model** - Requires new integration

This would take us to **~85%** of what industry does.

---

## ❓ Questions to Decide

1. **Prioritize speed or precision?**
   - Self-Consistency adds 2-3x latency
   - NLI is more precise but slower than LLM-as-Judge

2. **Budget for additional APIs?**
   - Free Hugging Face has rate limits
   - Local model requires GPU

3. **Do we accept disclaimers in responses?**
   - Decision Engine can show warnings
   - Or do we prefer only high-confidence responses?

4. **Do we want inline citations [1][2]?**
   - Significantly changes response format
   - More transparent but more verbose

---

## 📁 Files to Create/Modify

```
backend/app/services/
├── evaluation/                          # NEW DIRECTORY
│   ├── __init__.py
│   ├── llm_judge.py                    # LLM-as-Judge service
│   ├── answer_relevance.py             # Query↔Response similarity
│   ├── nli_verifier.py                 # NLI-based verification (optional)
│   ├── citation_verifier.py            # Citation checking
│   ├── self_consistency.py             # Multiple samples
│   └── decision_engine.py              # Final decision logic
├── confidence_calculator.py            # MODIFY - integrate new scores
└── rag_service_v5.py                   # MODIFY - call new services

frontend/src/components/
└── MetricsPanel.jsx                    # MODIFY - show detailed breakdown
```

---

## Conclusion

**Is the change drastic?** 
- Architecture: NO, it's incremental
- Stack: NO, same stack + 1 optional API
- Code: YES, several new services

**Do we need new APIs?**
- Minimum: NO, everything can be done with OpenRouter
- Ideal: YES, Hugging Face for NLI (free)

**Is it worth it?**
- LLM-as-Judge + Answer Relevance = **80% of the benefit with 20% of the effort**
- NLI + Self-Consistency = **20% additional with 80% of the effort**

**Recommendation:** Implement Phases 1-3 first (1 week), evaluate results, then decide if phases 4-6 are worth it.
