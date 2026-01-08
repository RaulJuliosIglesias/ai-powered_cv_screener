# HuggingFace Integration Guide (V7)

## Overview

Version 7.0 introduces **free** HuggingFace Inference API integration for enhanced verification, reranking, and evaluation capabilities.

---

## 🔑 Setup

### 1. Get Your API Key (FREE)

1. Go to https://huggingface.co/settings/tokens
2. Click "New token"
3. Name it (e.g., "cv-screener")
4. Select "Read" access (sufficient for inference)
5. Copy the token (starts with `hf_`)

### 2. Configure Environment

```bash
# backend/.env
HUGGINGFACE_API_KEY=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Verify Installation

```bash
cd backend
python -c "from app.providers.huggingface_client import HuggingFaceClient; print('OK')"
```

---

## 🔬 Services

### 1. NLI Verification Service

**Purpose:** Verify that generated claims are supported by the source documents.

**Model:** `facebook/bart-large-mnli`

**How it works:**
```
Claim: "Juan has 5 years of Python experience"
Context: "Juan García - Software Engineer with 5 years of Python..."
         ↓
NLI Model
         ↓
Result: "entailment" (supported) | "contradiction" | "neutral"
```

**File:** `backend/app/services/nli_verification_service.py`

**Usage:**
```python
from app.services.nli_verification_service import NLIVerificationService

service = NLIVerificationService()
result = await service.verify_claims(
    claims=["Juan has Python experience"],
    context="Juan García CV: Python developer with 5 years..."
)
print(result.faithfulness_score)  # 0.95
```

**Configuration:**
| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `true` | Enable/disable NLI verification |
| `threshold` | `0.5` | Minimum confidence for "supported" |
| `max_claims` | `10` | Maximum claims to verify per response |

---

### 2. Cross-Encoder Reranking Service

**Purpose:** Semantically rerank search results for better precision.

**Model:** `BAAI/bge-reranker-base`

**How it works:**
```
Query: "Python experience"
Results: [Chunk1, Chunk2, Chunk3, ...]
         ↓
Cross-Encoder scores each (query, chunk) pair
         ↓
Reranked: [Chunk3, Chunk1, Chunk2, ...] (by semantic relevance)
```

**File:** `backend/app/services/reranking_service_v2.py`

**Usage:**
```python
from app.services.reranking_service_v2 import RerankingServiceV2

service = RerankingServiceV2()
reranked = await service.rerank(
    query="Python developer",
    chunks=[chunk1, chunk2, chunk3]
)
```

**Configuration:**
| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `true` | Enable/disable cross-encoder reranking |
| `top_k` | `10` | Number of results to rerank |
| `model` | `BAAI/bge-reranker-base` | Cross-encoder model |

---

### 3. RAGAS Evaluation Service

**Purpose:** Automatically evaluate response quality with standardized metrics.

**Metrics:**
| Metric | Description | Range |
|--------|-------------|-------|
| **Faithfulness** | Is the answer grounded in context? | 0-100% |
| **Answer Relevancy** | Does the answer address the query? | 0-100% |
| **Context Relevancy** | Are retrieved chunks relevant? | 0-100% |
| **Overall Score** | Weighted combination | 0-100% |

**File:** `backend/app/services/ragas_evaluation_service.py`

**Usage:**
```python
from app.services.ragas_evaluation_service import RAGASEvaluationService

service = RAGASEvaluationService()
result = await service.evaluate(
    query="Who has Python experience?",
    answer="Juan García has 5 years of Python experience.",
    contexts=["Juan García CV: Python developer..."]
)
print(result.overall_score)  # 0.85
```

---

### 4. Zero-Shot Guardrails

**Purpose:** Detect off-topic queries without training data.

**Model:** `facebook/bart-large-mnli`

**How it works:**
```
Query: "What's a good recipe for pasta?"
Labels: ["CV screening", "job search", "off-topic"]
         ↓
Zero-Shot Classification
         ↓
Result: "off-topic" (0.92 confidence)
```

**File:** `backend/app/services/guardrail_service_v2.py`

---

## 📊 API Rate Limits

HuggingFace Free Tier:
- **Rate:** ~30 requests/minute
- **Concurrency:** 1 request at a time
- **Queue:** Requests are queued automatically

For higher limits, consider HuggingFace Pro ($9/month).

---

## 🔧 Troubleshooting

### "Model is loading"

HuggingFace models may need to "warm up" on first request:

```python
# Error: "Model facebook/bart-large-mnli is currently loading"
# Solution: Wait 20-30 seconds and retry
```

The client automatically retries with exponential backoff.

### "Rate limit exceeded"

```python
# Error: "Rate limit exceeded"
# Solution: Wait 1 minute or upgrade to Pro
```

### "Invalid API key"

```bash
# Verify your key
curl -H "Authorization: Bearer hf_xxxxx" \
  https://api-inference.huggingface.co/models/facebook/bart-large-mnli
```

---

## 🎛️ Frontend Settings

Users can enable/disable HuggingFace services in **RAG Pipeline Settings**:

| Step | Model | Optional |
|------|-------|----------|
| Step 5: NLI Verification | `facebook/bart-large-mnli` | ✅ |
| Step 6: RAGAS Evaluation | `auto` | ✅ |
| Step 7: Cross-Encoder Reranking | `BAAI/bge-reranker-base` | ✅ |

---

## 📈 Performance Impact

| Service | Latency | Cost |
|---------|---------|------|
| NLI Verification | +500-1000ms | FREE |
| Cross-Encoder Reranking | +300-500ms | FREE |
| RAGAS Evaluation | +1000-2000ms | FREE |

**Total additional latency:** ~2-3.5s per query (when all enabled)

**Recommendation:** Enable for quality-critical use cases, disable for speed-critical.

---

## 🔗 Related Documentation

- [CHANGELOG_V7.md](./CHANGELOG_V7.md) - Full changelog
- [RAG_WORKFLOW.md](./RAG_WORKFLOW.md) - Pipeline architecture
- [QUERY_DETECTION.md](./QUERY_DETECTION.md) - Query patterns
