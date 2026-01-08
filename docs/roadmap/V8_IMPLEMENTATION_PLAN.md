# RAG v8 Implementation Plan

> **Status**: 📋 PLANNED
> 
> **Date**: January 2026
> 
> **Prerequisites**: RAG v7 (Cross-Encoder, NLI, Zero-Shot Guardrails, RAGAS) ✅ Completed

---

## Executive Summary

RAG v8 focuses on **advanced orchestration** and **production-ready features**:
- LangGraph for stateful conversation flows
- Semantic caching for faster responses
- A/B testing framework for model comparison
- Production observability with LangSmith

---

## Implementation Phases

### Phase 1: LangGraph Integration (HIGH PRIORITY)
**Estimated Time**: 2-3 days

Replace sequential pipeline with stateful graph for:
- **Conditional branching**: Different paths for simple vs complex queries
- **Parallel execution**: Run reranking + reasoning simultaneously
- **State persistence**: Resume conversations across sessions
- **Human-in-the-loop**: Allow user intervention for low-confidence answers

```
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Pipeline v8                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Query] ──► [Understanding] ──► [Router] ──┬──► [Simple Path]  │
│                                             │                   │
│                                             └──► [Complex Path] │
│                                                      │          │
│                                    ┌─────────────────┘          │
│                                    ▼                            │
│                            [Parallel Execution]                 │
│                           /         |         \                 │
│                    [Retrieval] [Reranking] [Context Analysis]   │
│                           \         |         /                 │
│                            └───────►[Merge]──────►[Generate]    │
│                                                       │         │
│                                              [Verify + Refine]  │
│                                                       │         │
│                                                  [Response]     │
└─────────────────────────────────────────────────────────────────┘
```

**Files to Create**:
- `backend/app/services/langgraph_pipeline.py`
- `backend/app/services/graph_nodes.py`
- `backend/app/services/graph_state.py`

**Benefits**:
- 30-40% faster for complex queries (parallel execution)
- Better error recovery (retry individual nodes)
- Clearer debugging (visual graph representation)

---

### Phase 2: Semantic Caching (MEDIUM PRIORITY)
**Estimated Time**: 1-2 days

Cache responses based on semantic similarity, not exact match:

| Feature | Description |
|---------|-------------|
| **Embedding Cache** | Cache query embeddings (avoid re-computation) |
| **Response Cache** | Cache full responses for similar queries |
| **Similarity Threshold** | 0.95 cosine similarity = cache hit |
| **TTL** | 24 hours for CV-related data |

```python
# Example usage
cache_result = await semantic_cache.get(
    query="Who has Python experience?",
    threshold=0.95
)
if cache_result.hit:
    return cache_result.response  # Instant response!
```

**Files to Create**:
- `backend/app/services/semantic_cache.py`
- `backend/app/providers/cache_provider.py`

**Benefits**:
- 90%+ faster for repeated/similar queries
- Reduced API costs
- Better user experience

---

### Phase 3: A/B Testing Framework (MEDIUM PRIORITY)
**Estimated Time**: 1-2 days

Compare model performance systematically:

| Dimension | Options |
|-----------|---------|
| **Models** | Gemini vs GPT-4o-mini vs Claude |
| **Reranking** | Cross-encoder vs LLM |
| **Verification** | NLI vs LLM |
| **Prompts** | Template A vs B |

**Automatic Metrics Collection**:
- Latency (p50, p90, p99)
- Token usage
- Cost per query
- User satisfaction (thumbs up/down)
- RAGAS scores

**Files to Create**:
- `backend/app/services/ab_testing.py`
- `backend/app/api/ab_routes.py`
- `frontend/src/components/ABTestingDashboard.jsx`

---

### Phase 4: Production Observability (LOW PRIORITY)
**Estimated Time**: 1 day

Integrate LangSmith for production monitoring:

| Feature | Value |
|---------|-------|
| **Tracing** | Full trace of every pipeline step |
| **Debugging** | Replay failed queries |
| **Alerts** | Notify on high error rates |
| **Cost Tracking** | Per-query cost breakdown |

**Files to Modify**:
- `backend/app/config.py` - Add LangSmith API key
- `backend/app/services/rag_service_v5.py` - Add tracing decorators

---

## Priority Matrix

| Phase | Priority | Effort | Impact | Dependencies |
|-------|----------|--------|--------|--------------|
| LangGraph | 🔴 HIGH | 2-3 days | High | None |
| Semantic Caching | 🟡 MEDIUM | 1-2 days | High | None |
| A/B Testing | 🟡 MEDIUM | 1-2 days | Medium | LangGraph (optional) |
| Observability | 🟢 LOW | 1 day | Medium | None |

---

## Recommended Order

### Week 1: Foundation
1. **Day 1-2**: LangGraph basic setup (state, nodes, simple graph)
2. **Day 3**: LangGraph parallel execution + conditional routing

### Week 2: Optimization
3. **Day 4-5**: Semantic caching implementation
4. **Day 6**: A/B testing framework

### Week 3: Production
5. **Day 7**: LangSmith integration
6. **Day 8**: Dashboard for metrics visualization

---

## Alternative Quick Wins (If Time-Constrained)

If you don't have time for full LangGraph implementation, consider these quick improvements:

### 1. Query Complexity Router (2 hours)
```python
def route_query(query_understanding) -> str:
    if query_understanding.complexity == "simple":
        return "fast_path"  # Skip reasoning, direct generation
    return "full_path"  # Full pipeline
```

### 2. Response Streaming Optimization (2 hours)
- Stream generation tokens directly to frontend
- Show "Analyzing..." → "Generating..." → actual response

### 3. Smart Fallback Chain (1 hour)
```python
FALLBACK_MODELS = [
    "google/gemini-2.0-flash-lite-001",
    "openai/gpt-4o-mini",
    "anthropic/claude-3-haiku"
]
# Auto-failover on rate limits or errors
```

### 4. Query Deduplication (1 hour)
- Detect if user is asking the same question
- Return cached response with "I already answered this" note

---

## Cost Estimate

| Feature | Monthly Cost |
|---------|-------------|
| LangGraph | $0 (local) |
| Semantic Cache | $0 (Redis/local) |
| A/B Testing | $0 (local metrics) |
| LangSmith | $0 (free tier: 5K traces/month) |
| **Total** | **~$0** |

---

## Success Metrics

| Metric | Current (v7) | Target (v8) |
|--------|-------------|-------------|
| Avg Query Latency | ~8-12s | ~4-6s |
| Cache Hit Rate | 0% | 30-50% |
| Error Rate | ~5% | <1% |
| Complex Query Success | ~85% | >95% |

---

## Next Steps

1. ¿Quieres empezar con **LangGraph** (más impacto pero más complejo)?
2. ¿O prefieres **Semantic Caching** (más rápido de implementar)?
3. ¿O los **Quick Wins** primero (mejoras inmediatas sin arquitectura nueva)?

