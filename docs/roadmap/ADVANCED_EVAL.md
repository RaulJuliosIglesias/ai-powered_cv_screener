# Advanced Evaluation System - Implementation Plan

## Document Purpose

This document provides implementation instructions for a production-grade evaluation and confidence scoring system for the CV Screener RAG application. The system follows patterns used by Sierra AI, Perplexity, and enterprise RAG systems.

---

## APIs and Services Required

### What OpenRouter CANNOT Do (Need Additional Services)

| Capability | OpenRouter | Additional Service Needed |
|------------|------------|---------------------------|
| LLM Generation | ✅ Yes | - |
| Embeddings | ✅ Yes (nomic-embed) | - |
| Token Log Probabilities | ❌ No | OpenAI API directly |
| NLI Models | ❌ No | HuggingFace Inference API or Local |
| Streaming with logprobs | ❌ No | OpenAI / Anthropic direct |
| Fine-tuned eval models | ❌ No | HuggingFace / Replicate |

### Required API Keys

```bash
# REQUIRED - Already have
OPENROUTER_API_KEY=sk-or-...          # LLM + Embeddings

# REQUIRED - Need to add
OPENAI_API_KEY=sk-...                  # For logprobs + calibrated confidence
                                       # Cost: ~$0.01 per eval

# OPTIONAL - For advanced NLI
HUGGINGFACE_API_KEY=hf_...            # For DeBERTa NLI model
                                       # Free tier: 30k requests/month

# OPTIONAL - For observability
LANGSMITH_API_KEY=ls_...              # LangChain tracing (free tier)
```

### Cost Estimation (per 1000 queries)

| Component | Service | Cost |
|-----------|---------|------|
| Main LLM (generation) | OpenRouter Gemini | $0.00 (free) |
| Query Understanding | OpenRouter Gemini | $0.00 (free) |
| LLM-as-Judge | OpenRouter GPT-4o-mini | ~$0.15 |
| Logprobs Analysis | OpenAI GPT-4o-mini | ~$0.10 |
| NLI Verification | HuggingFace (free tier) | $0.00 |
| **Total** | | **~$0.25 per 1000 queries** |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ADVANCED EVAL SYSTEM ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  EXISTING SERVICES (Keep)              NEW EVAL SERVICES (Add)               │
│  ─────────────────────────             ──────────────────────────            │
│  ✓ query_understanding_service         + confidence_calibration_service      │
│  ✓ guardrail_service                   + llm_judge_service                   │
│  ✓ hallucination_service (basic)       + nli_verification_service            │
│  ✓ eval_service (logging)              + citation_verification_service       │
│  ✓ rag_service_v3                      + self_consistency_service            │
│                                        + token_analysis_service              │
│                                        + eval_aggregator_service             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## New File Structure

```
backend/app/
├── services/
│   ├── eval/                              # NEW DIRECTORY
│   │   ├── __init__.py
│   │   ├── base.py                        # Base classes and types
│   │   ├── llm_judge_service.py           # LLM-as-Judge evaluation
│   │   ├── nli_service.py                 # NLI-based faithfulness
│   │   ├── citation_service.py            # Citation verification
│   │   ├── consistency_service.py         # Self-consistency checking
│   │   ├── token_analysis_service.py      # Logprobs confidence
│   │   ├── calibration_service.py         # Confidence calibration
│   │   └── aggregator_service.py          # Combines all scores
│   │
│   ├── rag_service_v3.py                  # UPDATE: integrate eval system
│   ├── hallucination_service.py           # UPDATE: enhance with NLI
│   └── eval_service.py                    # UPDATE: richer logging
│
├── models/
│   └── eval_schemas.py                    # NEW: Eval data models
│
└── prompts/
    └── eval_prompts.py                    # NEW: Judge prompts
```

---

## Phase 1: Core Eval Types and Base Classes

### Task 1.1: Create Eval Schemas

**Location:** Create `backend/app/models/eval_schemas.py`

**Requirements:**

Define dataclasses/Pydantic models for:

```
EvalMetrics:
    - faithfulness_score: float (0-1)
    - relevance_score: float (0-1)
    - completeness_score: float (0-1)
    - hallucination_risk: float (0-1)
    - citation_validity: float (0-1)
    - self_consistency: float (0-1)
    - token_confidence: float (0-1)
    - final_confidence: float (0-1)
    - should_send: bool
    - requires_disclaimer: bool
    - issues: List[str]
    - eval_latency_ms: float

ClaimExtraction:
    - claim_id: str
    - claim_text: str
    - source_sentence: str
    - supporting_chunk_ids: List[str]
    - verification_status: "supported" | "partial" | "unsupported" | "contradicted"
    - confidence: float

JudgeVerdict:
    - faithfulness: int (1-5)
    - relevance: int (1-5)
    - completeness: int (1-5)
    - hallucinations: List[str]
    - reasoning: str
    - confidence: float

CitationCheck:
    - citation_id: str
    - claim: str
    - source_text: str
    - is_valid: bool
    - match_type: "exact" | "paraphrase" | "partial" | "invalid"
    - confidence: float

ConsistencyResult:
    - samples: List[str]
    - extracted_answers: List[str]
    - agreement_score: float
    - majority_answer: str
    - variance_indicator: str

TokenAnalysis:
    - mean_logprob: float
    - min_logprob: float
    - entropy: float
    - low_confidence_tokens: List[str]
    - estimated_confidence: float
```

### Task 1.2: Create Base Eval Service

**Location:** Create `backend/app/services/eval/base.py`

**Requirements:**

Define abstract base class `BaseEvalService`:
- Abstract method: `evaluate(context, question, response) -> EvalResult`
- Shared utility: `extract_claims(text) -> List[str]`
- Shared utility: `compute_semantic_similarity(text1, text2) -> float`
- Timing decorator for latency tracking
- Error handling wrapper

Define `EvalConfig` dataclass:
- enable_llm_judge: bool (default True)
- enable_nli: bool (default True)
- enable_citation_check: bool (default True)
- enable_self_consistency: bool (default False, expensive)
- enable_token_analysis: bool (default False, requires OpenAI)
- confidence_threshold_high: float (default 0.8)
- confidence_threshold_low: float (default 0.3)
- max_eval_latency_ms: int (default 2000)

---

## Phase 2: LLM-as-Judge Service

### Task 2.1: Create Judge Prompts

**Location:** Create `backend/app/prompts/eval_prompts.py`

**Requirements:**

Define comprehensive judge prompts:

```
LLM_JUDGE_SYSTEM_PROMPT:
    Role: Expert RAG evaluator
    Task: Evaluate response quality on multiple dimensions
    Output: Structured JSON with scores and reasoning

LLM_JUDGE_USER_TEMPLATE:
    Inputs: {context}, {question}, {response}
    
    Evaluation criteria:
    1. FAITHFULNESS (1-5): Is every claim supported by context?
       - 5: Every statement directly supported
       - 4: All major claims supported, minor details assumed
       - 3: Most supported, some unsupported but plausible
       - 2: Multiple unsupported claims
       - 1: Major claims contradict or aren't in context
    
    2. RELEVANCE (1-5): Does response answer the question?
       - 5: Directly and completely answers
       - 4: Answers main question, minor tangents
       - 3: Partially answers, some irrelevant content
       - 2: Barely addresses the question
       - 1: Does not answer the question
    
    3. COMPLETENESS (1-5): Are all parts of question addressed?
       - 5: All aspects covered thoroughly
       - 4: Main points covered well
       - 3: Core answered, some gaps
       - 2: Significant gaps
       - 1: Critical information missing
    
    4. HALLUCINATIONS: List specific claims NOT in context
    
    5. CONFIDENCE (0.0-1.0): Overall confidence this is good response
    
    Output format: JSON with reasoning

CLAIM_EXTRACTION_PROMPT:
    Task: Extract individual factual claims from response
    Output: List of atomic claims that can be verified
    Example: "María has 5 years Python experience at Google as Senior Engineer"
    Claims: ["María has 5 years Python experience", "María worked at Google", "María was Senior Engineer"]

RELEVANCE_REVERSE_PROMPT:
    Task: Generate questions that this response would answer
    Purpose: Compare generated questions with original to measure relevance
```

### Task 2.2: Implement LLM Judge Service

**Location:** Create `backend/app/services/eval/llm_judge_service.py`

**Requirements:**

Class `LLMJudgeService`:

1. Initialize with:
   - OpenRouter client (for fast/cheap models)
   - Judge model: "openai/gpt-4o-mini" (good balance cost/quality)
   - Fallback model: "google/gemini-2.0-flash-exp:free"
   - Timeout: 10 seconds
   - Max retries: 2

2. Method `evaluate(context: str, question: str, response: str) -> JudgeVerdict`:
   - Format prompt with inputs
   - Call judge LLM with JSON mode
   - Parse response into JudgeVerdict
   - Handle parsing errors gracefully (return neutral scores)
   - Track latency

3. Method `extract_claims(response: str) -> List[str]`:
   - Use claim extraction prompt
   - Split response into atomic verifiable claims
   - Filter out opinions/hedging statements
   - Return list of factual claims

4. Method `batch_evaluate(items: List[tuple]) -> List[JudgeVerdict]`:
   - Process multiple evaluations concurrently
   - Use asyncio.gather with semaphore (max 5 concurrent)
   - For offline batch evaluation

5. Error handling:
   - On timeout: return neutral verdict (scores = 3, confidence = 0.5)
   - On parse error: retry once with simpler prompt
   - On API error: use fallback model

---

## Phase 3: NLI Verification Service

### Task 3.1: Implement NLI Service

**Location:** Create `backend/app/services/eval/nli_service.py`

**Requirements:**

Class `NLIVerificationService`:

1. Initialize with:
   - HuggingFace Inference API client
   - Model: "microsoft/deberta-v3-base-mnli" (free, accurate)
   - Alternative: "facebook/bart-large-mnli"
   - Local fallback: sentence-transformers for similarity-based approximation
   - Cache for repeated premise-hypothesis pairs

2. Method `verify_claim(claim: str, context_chunks: List[str]) -> ClaimVerification`:
   ```
   For each chunk:
       result = nli_model(premise=chunk, hypothesis=claim)
       # Returns: {"entailment": 0.9, "neutral": 0.08, "contradiction": 0.02}
   
   Aggregate results:
       - If any chunk ENTAILS claim (>0.7): claim is SUPPORTED
       - If any chunk CONTRADICTS claim (>0.7): claim is CONTRADICTED
       - If all chunks NEUTRAL: claim is UNSUPPORTED
   
   Return ClaimVerification with supporting chunk IDs
   ```

3. Method `compute_faithfulness(claims: List[str], context_chunks: List[str]) -> float`:
   ```
   verified_claims = [verify_claim(c, context_chunks) for c in claims]
   
   supported = count where status == "supported"
   partial = count where status == "partial" 
   contradicted = count where status == "contradicted"
   
   faithfulness = (supported + 0.5*partial) / total_claims
   
   Return faithfulness score (0-1)
   ```

4. Method `get_hallucinated_claims(claims: List[str], context: List[str]) -> List[str]`:
   - Return claims with status "unsupported" or "contradicted"
   - Include confidence score for each

5. Fallback when HuggingFace unavailable:
   - Use semantic similarity (cosine) between claim and chunks
   - Threshold > 0.7: supported
   - Threshold > 0.5: partial
   - Threshold < 0.5: unsupported
   - Less accurate but always available

6. Caching strategy:
   - Cache NLI results by hash(premise + hypothesis)
   - TTL: 1 hour
   - Reduces API calls significantly

---

## Phase 4: Citation Verification Service

### Task 4.1: Implement Citation Service

**Location:** Create `backend/app/services/eval/citation_service.py`

**Requirements:**

Class `CitationVerificationService`:

1. Method `extract_citations(response: str) -> List[Citation]`:
   ```
   Parse response for citation patterns:
   - [1], [2], [3] style
   - [📄 filename.pdf] style  
   - **[Name](cv:cv_id)** style (current format)
   - (Source: filename) style
   
   For each citation found:
       - citation_id
       - position in response (char index)
       - claimed source (filename or cv_id)
       - surrounding context (sentence containing citation)
   ```

2. Method `verify_citation(citation: Citation, sources: List[Chunk]) -> CitationCheck`:
   ```
   1. Find the claim being cited (text before citation marker)
   2. Find the referenced source in chunks
   3. If source not found: INVALID (source doesn't exist)
   4. If source found:
      - Extract relevant text from source
      - Use NLI or semantic similarity to verify claim matches source
      - EXACT: claim is verbatim or very close
      - PARAPHRASE: claim accurately represents source
      - PARTIAL: claim partially supported
      - INVALID: claim not supported by cited source
   ```

3. Method `compute_citation_score(response: str, sources: List[Chunk]) -> float`:
   ```
   citations = extract_citations(response)
   
   if no citations:
       return 0.5  # Neutral - can't evaluate
   
   verified = [verify_citation(c, sources) for c in citations]
   
   valid_count = count where is_valid == True
   partial_count = count where match_type == "partial"
   
   score = (valid_count + 0.5*partial_count) / total_citations
   return score
   ```

4. Method `get_uncited_claims(response: str, claims: List[str]) -> List[str]`:
   - Find claims in response that have no citation
   - Important for identifying potential hallucinations
   - Return list of uncited factual claims

---

## Phase 5: Self-Consistency Service

### Task 5.1: Implement Consistency Service

**Location:** Create `backend/app/services/eval/consistency_service.py`

**Requirements:**

Class `SelfConsistencyService`:

1. Initialize with:
   - LLM client (OpenRouter)
   - Number of samples: 3-5 (configurable)
   - Temperature for sampling: 0.7-0.9
   - Answer extraction prompt

2. Method `generate_samples(question: str, context: str, n: int = 3) -> List[str]`:
   ```
   Generate n responses with temperature > 0:
   
   samples = []
   for i in range(n):
       response = llm.generate(
           prompt=format_prompt(question, context),
           temperature=0.7 + (i * 0.1),  # Vary temperature
           max_tokens=500
       )
       samples.append(response)
   
   return samples
   ```

3. Method `extract_key_answer(response: str, question: str) -> str`:
   ```
   Use LLM to extract the "key answer" from response:
   
   Prompt: "Given this question: {question}
            And this response: {response}
            Extract ONLY the key factual answer in 1-2 sentences.
            If it's a name, just the name.
            If it's a number, just the number.
            If it's a list, just the items."
   
   This normalizes responses for comparison.
   ```

4. Method `compute_consistency(samples: List[str], question: str) -> ConsistencyResult`:
   ```
   1. Extract key answer from each sample
   2. Cluster similar answers (semantic similarity > 0.85)
   3. Find majority cluster
   4. Compute agreement score:
      agreement = size_of_majority_cluster / total_samples
   
   5. Determine variance:
      if agreement >= 0.8: "low" (consistent)
      elif agreement >= 0.5: "medium" (some disagreement)
      else: "high" (significant disagreement)
   
   Return ConsistencyResult
   ```

5. Cost optimization:
   - Only run for complex/ambiguous queries
   - Detect complexity: multi-part questions, comparison requests, subjective queries
   - Skip for simple factual lookups

6. Integration note:
   - This is EXPENSIVE (3-5x LLM calls per query)
   - Default: DISABLED
   - Enable for: high-stakes queries, user-requested verification, batch evaluation

---

## Phase 6: Token Analysis Service

### Task 6.1: Implement Token Analysis

**Location:** Create `backend/app/services/eval/token_analysis_service.py`

**Requirements:**

Class `TokenAnalysisService`:

1. Initialize with:
   - OpenAI client (NOT OpenRouter - need logprobs)
   - Model: "gpt-4o-mini" (supports logprobs)
   - Note: This requires direct OpenAI API

2. Method `generate_with_logprobs(prompt: str, system: str) -> TokenAnalysisResult`:
   ```
   response = openai.chat.completions.create(
       model="gpt-4o-mini",
       messages=[
           {"role": "system", "content": system},
           {"role": "user", "content": prompt}
       ],
       logprobs=True,
       top_logprobs=5,
       max_tokens=1000
   )
   
   Extract from response:
   - tokens: List of generated tokens
   - logprobs: Log probability for each token
   - top_logprobs: Top 5 alternatives per position
   ```

3. Method `analyze_confidence(logprobs: List[float]) -> TokenAnalysis`:
   ```
   # Mean log probability (higher = more confident)
   mean_logprob = mean(logprobs)
   
   # Minimum log probability (identifies uncertain spots)
   min_logprob = min(logprobs)
   
   # Entropy (uncertainty measure)
   # High entropy = model uncertain between options
   entropy = compute_entropy(top_logprobs)
   
   # Find low-confidence tokens (potential hallucination points)
   low_conf_tokens = [
       (token, prob) for token, prob in zip(tokens, logprobs)
       if prob < -2.0  # Threshold for "uncertain"
   ]
   
   # Convert to confidence score (0-1)
   # logprob of 0 = 100% confident
   # logprob of -5 = ~0.7% confident
   estimated_confidence = exp(mean_logprob)
   
   return TokenAnalysis(...)
   ```

4. Method `identify_uncertain_claims(response: str, token_analysis: TokenAnalysis) -> List[str]`:
   ```
   Map low-confidence tokens back to claims:
   
   For each low_confidence_token:
       Find the sentence containing this token
       If sentence contains factual claim:
           Flag as "uncertain claim"
   
   Return list of uncertain claims for additional verification
   ```

5. Integration note:
   - Requires OpenAI API (additional cost)
   - Very useful for calibration
   - Can be used to trigger additional verification for uncertain responses
   - Default: DISABLED (opt-in for premium evaluation)

---

## Phase 7: Confidence Calibration Service

### Task 7.1: Implement Calibration Service

**Location:** Create `backend/app/services/eval/calibration_service.py`

**Requirements:**

Class `ConfidenceCalibrationService`:

1. Initialize with:
   - Path to calibration data file (JSON)
   - Minimum samples for calibration: 100
   - Recalibration interval: daily

2. Data structure for calibration history:
   ```
   CalibrationDataPoint:
       - query_id: str
       - predicted_confidence: float (what model said)
       - actual_correctness: float (from user feedback)
       - timestamp: datetime
       - query_type: str (factual, comparison, etc.)
   ```

3. Method `record_prediction(query_id: str, predicted_conf: float, metadata: dict)`:
   - Store prediction for later calibration
   - Called when response is generated

4. Method `record_feedback(query_id: str, actual_correctness: float)`:
   - Store actual correctness from:
     - User thumbs up/down (1.0 or 0.0)
     - User correction (0.0)
     - Follow-up question (0.5 - indicates incomplete)
     - No feedback after 24h (assume 0.7 - neutral)
   - Triggers recalibration if enough new data

5. Method `calibrate() -> CalibrationFunction`:
   ```
   Load all data points with feedback
   
   Use isotonic regression:
       - X: predicted_confidence values
       - Y: actual_correctness values
       - Fit isotonic regressor (monotonic)
   
   This creates a mapping:
       raw_confidence -> calibrated_confidence
   
   Common finding: Models say 0.9 but are correct only 0.6 of the time
   After calibration: 0.9 -> 0.6
   ```

6. Method `calibrate_confidence(raw_confidence: float) -> float`:
   ```
   If not enough calibration data:
       # Apply conservative discount
       return raw_confidence * 0.7
   
   If calibration model exists:
       return calibration_model.predict(raw_confidence)
   ```

7. Method `get_calibration_stats() -> dict`:
   - Return calibration curve
   - Expected calibration error (ECE)
   - Sample count per confidence bin
   - For monitoring dashboard

---

## Phase 8: Eval Aggregator Service

### Task 8.1: Implement Aggregator

**Location:** Create `backend/app/services/eval/aggregator_service.py`

**Requirements:**

Class `EvalAggregatorService`:

1. Initialize with:
   - All eval services (injected)
   - EvalConfig (which evals to run)
   - Weights for final score

2. Method `evaluate(context: List[str], question: str, response: str, sources: List[dict]) -> EvalMetrics`:
   ```
   metrics = EvalMetrics()
   start_time = now()
   
   # Run enabled evaluations concurrently
   tasks = []
   
   if config.enable_llm_judge:
       tasks.append(llm_judge.evaluate(context, question, response))
   
   if config.enable_nli:
       claims = llm_judge.extract_claims(response)
       tasks.append(nli_service.compute_faithfulness(claims, context))
   
   if config.enable_citation_check:
       tasks.append(citation_service.compute_citation_score(response, sources))
   
   if config.enable_self_consistency:
       tasks.append(consistency_service.compute_consistency(...))
   
   if config.enable_token_analysis:
       tasks.append(token_service.analyze_confidence(...))
   
   # Wait for all with timeout
   results = await asyncio.wait_for(
       asyncio.gather(*tasks, return_exceptions=True),
       timeout=config.max_eval_latency_ms / 1000
   )
   
   # Aggregate results into metrics
   # ... populate metrics from results
   
   return metrics
   ```

3. Method `compute_final_confidence(metrics: EvalMetrics) -> float`:
   ```
   # Weighted average of available scores
   weights = {
       "faithfulness": 0.30,
       "relevance": 0.20,
       "hallucination_risk": 0.20,  # Inverted
       "citation_validity": 0.15,
       "self_consistency": 0.10,
       "token_confidence": 0.05
   }
   
   available_scores = []
   available_weights = []
   
   for metric, weight in weights.items():
       score = getattr(metrics, f"{metric}_score", None)
       if score is not None:
           if metric == "hallucination_risk":
               score = 1 - score  # Invert (high risk = low confidence)
           available_scores.append(score)
           available_weights.append(weight)
   
   # Normalize weights
   total_weight = sum(available_weights)
   normalized_weights = [w/total_weight for w in available_weights]
   
   # Weighted average
   raw_confidence = sum(s*w for s,w in zip(available_scores, normalized_weights))
   
   # Apply calibration
   calibrated = calibration_service.calibrate_confidence(raw_confidence)
   
   # Apply penalties
   if metrics.faithfulness_score < 0.5:
       calibrated *= 0.5  # Heavy penalty
   
   if metrics.hallucination_risk > 0.7:
       calibrated *= 0.3  # Severe penalty
   
   return min(calibrated, 0.99)
   ```

4. Method `make_decision(metrics: EvalMetrics) -> dict`:
   ```
   confidence = metrics.final_confidence
   
   decision = {
       "action": None,
       "disclaimer": None,
       "issues": metrics.issues
   }
   
   if confidence >= config.confidence_threshold_high:  # 0.8
       decision["action"] = "SEND"
       decision["disclaimer"] = None
   
   elif confidence >= 0.5:
       decision["action"] = "SEND_WITH_DISCLAIMER"
       decision["disclaimer"] = "I'm not entirely certain about this answer. Please verify the information."
   
   elif confidence >= config.confidence_threshold_low:  # 0.3
       decision["action"] = "REGENERATE"
       decision["disclaimer"] = None
   
   else:
       decision["action"] = "DECLINE"
       decision["disclaimer"] = "I don't have enough reliable information to answer this question accurately."
   
   return decision
   ```

5. Method `run_fast_eval(context, question, response) -> EvalMetrics`:
   - Subset of evals for real-time (< 500ms)
   - Only: basic faithfulness check, entity verification
   - Used in production for every request

6. Method `run_full_eval(context, question, response) -> EvalMetrics`:
   - All enabled evals
   - Used async after response sent
   - Used for batch evaluation

---

## Phase 9: Integration with RAG Service

### Task 9.1: Update RAG Service V3

**Location:** Update `backend/app/services/rag_service_v3.py`

**Requirements:**

Add evaluation integration:

```
1. Import EvalAggregatorService

2. In __init__:
   - Initialize eval_aggregator with config
   - Load eval config from settings

3. In query() method, after generating response:
   
   # Fast eval (real-time)
   fast_metrics = await eval_aggregator.run_fast_eval(
       context=retrieved_chunks,
       question=reformulated_query,
       response=generated_response
   )
   
   # Make decision
   decision = eval_aggregator.make_decision(fast_metrics)
   
   if decision["action"] == "DECLINE":
       return {
           "response": decision["disclaimer"],
           "sources": [],
           "confidence": fast_metrics.final_confidence,
           "declined": True
       }
   
   if decision["action"] == "REGENERATE":
       # Try once more with different parameters
       generated_response = await self.regenerate_with_adjustments(...)
       fast_metrics = await eval_aggregator.run_fast_eval(...)
       decision = eval_aggregator.make_decision(fast_metrics)
   
   # Build response
   final_response = generated_response
   if decision["disclaimer"]:
       final_response = f"{generated_response}\n\n⚠️ {decision['disclaimer']}"
   
   # Schedule async full eval (non-blocking)
   asyncio.create_task(self.run_async_eval(
       query_id=query_id,
       context=retrieved_chunks,
       question=original_question,
       response=generated_response
   ))
   
   return {
       "response": final_response,
       "sources": sources,
       "confidence": fast_metrics.final_confidence,
       "metrics": fast_metrics.to_dict()
   }

4. Add method run_async_eval():
   - Run full evaluation in background
   - Store results in eval database
   - Don't block response to user
```

### Task 9.2: Update Existing Hallucination Service

**Location:** Update `backend/app/services/hallucination_service.py`

**Requirements:**

Enhance existing service with NLI:

```
1. Import NLIVerificationService

2. In verify() method:
   
   # Existing: Entity verification (keep)
   entity_issues = self.verify_entities(response, context)
   
   # NEW: Add NLI verification
   if nli_enabled:
       claims = self.extract_claims(response)
       nli_results = await nli_service.compute_faithfulness(claims, context)
       hallucinated = await nli_service.get_hallucinated_claims(claims, context)
   else:
       # Fallback to existing similarity-based check
       nli_results = self.similarity_based_check(response, context)
       hallucinated = []
   
   # Combine results
   return {
       "entity_issues": entity_issues,
       "hallucinated_claims": hallucinated,
       "faithfulness_score": nli_results,
       "confidence": self.compute_confidence(entity_issues, nli_results)
   }
```

### Task 9.3: Update API Response Schema

**Location:** Update `backend/app/models/schemas.py`

**Requirements:**

Add evaluation fields to ChatResponse:

```
ChatResponse:
    response: str
    sources: List[Source]
    conversation_id: str
    metrics: ResponseMetrics
    evaluation: EvaluationSummary  # NEW

EvaluationSummary:  # NEW
    confidence_score: float
    confidence_level: "high" | "medium" | "low"
    faithfulness_score: float
    has_disclaimer: bool
    issues: List[str]
    eval_version: str
```

---

## Phase 10: Frontend Integration

### Task 10.1: Display Confidence in UI

**Location:** Update frontend components

**Requirements:**

1. Update Message component to show confidence:
   ```
   If confidence >= 0.8:
       Show green confidence indicator
       No additional UI
   
   If confidence >= 0.5:
       Show yellow confidence indicator
       Show disclaimer if present
   
   If confidence < 0.5:
       Show red confidence indicator
       Prominent disclaimer
   ```

2. Add ConfidenceIndicator component:
   - Small badge showing confidence level
   - Tooltip with detailed metrics on hover
   - Color coded: green/yellow/red

3. Update MetricsBar to show eval metrics:
   - Faithfulness score
   - Confidence score
   - Eval latency

---

## Phase 11: Observability and Logging

### Task 11.1: Enhanced Eval Logging

**Location:** Update `backend/app/services/eval_service.py`

**Requirements:**

Extend logging to capture all eval data:

```
EvalLogEntry:
    # Existing fields
    query_id: str
    timestamp: datetime
    question: str
    response: str
    latency_ms: float
    
    # NEW eval fields
    eval_config: dict
    eval_metrics: EvalMetrics
    decision: dict
    claims_extracted: List[str]
    hallucinated_claims: List[str]
    citation_checks: List[CitationCheck]
    async_eval_scheduled: bool
    
    # For calibration
    predicted_confidence: float
    user_feedback: Optional[float]  # Added later via feedback endpoint
```

### Task 11.2: Create Eval Dashboard Endpoint

**Location:** Add to `backend/app/api/routes.py`

**Requirements:**

New endpoint: GET /api/eval/stats

Response:
```
{
    "period": "last_24h",
    "total_queries": 150,
    "average_confidence": 0.72,
    "confidence_distribution": {
        "high": 45,
        "medium": 80,
        "low": 25
    },
    "average_faithfulness": 0.78,
    "hallucination_rate": 0.12,
    "declined_queries": 5,
    "regenerated_queries": 18,
    "average_eval_latency_ms": 450,
    "calibration_status": {
        "samples": 500,
        "last_calibrated": "2025-01-04T10:00:00Z",
        "ece_score": 0.08
    }
}
```

---

## Configuration

### Environment Variables

```bash
# .env additions

# ============================================
# EVAL SYSTEM CONFIGURATION
# ============================================

# Feature flags
EVAL_ENABLE_LLM_JUDGE=true
EVAL_ENABLE_NLI=true
EVAL_ENABLE_CITATION_CHECK=true
EVAL_ENABLE_SELF_CONSISTENCY=false    # Expensive, opt-in
EVAL_ENABLE_TOKEN_ANALYSIS=false      # Requires OpenAI

# Thresholds
EVAL_CONFIDENCE_HIGH=0.8
EVAL_CONFIDENCE_LOW=0.3
EVAL_MAX_LATENCY_MS=2000

# API Keys for eval services
OPENAI_API_KEY=sk-...                 # Required for token analysis
HUGGINGFACE_API_KEY=hf_...            # Required for NLI

# Judge model
EVAL_JUDGE_MODEL=openai/gpt-4o-mini

# Calibration
EVAL_CALIBRATION_FILE=./data/calibration.json
EVAL_MIN_CALIBRATION_SAMPLES=100
```

---

## Dependencies

### Add to requirements.txt

```
# Eval system dependencies
scikit-learn>=1.3.0          # For isotonic regression (calibration)
numpy>=1.24.0                # Numerical operations
openai>=1.10.0               # For logprobs analysis (direct API)
huggingface-hub>=0.20.0      # For NLI models

# Optional: Local NLI (if HuggingFace API unavailable)
transformers>=4.36.0         # For local DeBERTa
torch>=2.1.0                 # PyTorch backend
```

---

## Execution Order

```
Phase 1: Core Types (Task 1.1, 1.2)
    └─→ Foundation for all services

Phase 2: LLM Judge (Task 2.1, 2.2)
    └─→ Primary evaluation method

Phase 3: NLI Service (Task 3.1)
    └─→ Faithfulness verification

Phase 4: Citation Service (Task 4.1)
    └─→ Source attribution checking

Phase 5: Consistency Service (Task 5.1)
    └─→ Optional, expensive

Phase 6: Token Analysis (Task 6.1)
    └─→ Optional, requires OpenAI

Phase 7: Calibration Service (Task 7.1)
    └─→ Long-term improvement

Phase 8: Aggregator (Task 8.1)
    └─→ Combines all scores

Phase 9: RAG Integration (Task 9.1, 9.2, 9.3)
    └─→ Connect to main pipeline

Phase 10: Frontend (Task 10.1)
    └─→ User-facing confidence display

Phase 11: Observability (Task 11.1, 11.2)
    └─→ Monitoring and debugging
```

---

## Success Criteria

- [ ] LLM-as-Judge evaluates every response
- [ ] NLI verification detects unsupported claims
- [ ] Citations are verified against sources
- [ ] Confidence score reflects actual reliability
- [ ] Low-confidence responses show disclaimer
- [ ] Very low confidence triggers decline
- [ ] All evals complete in < 2 seconds (real-time path)
- [ ] Full evals run async for monitoring
- [ ] Dashboard shows eval statistics
- [ ] Calibration improves over time with feedback

---

## What This Demonstrates to Employer

1. **Deep RAG knowledge** - Multi-stage evaluation pipeline
2. **AI safety awareness** - Hallucination detection, guardrails
3. **Production mindset** - Latency budgets, async processing
4. **ML engineering** - NLI models, confidence calibration
5. **System design** - Modular, configurable, observable
6. **Industry awareness** - RAGAS metrics, LLM-as-judge patterns