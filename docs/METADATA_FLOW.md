# 📊 Metadata Flow Documentation

> **CRITICAL**: Read this before adding new metadata fields or modules.
>
> Last Updated: January 2026

---

## 🔄 Complete Metadata Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    CV UPLOAD & INDEXING                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. routes_sessions.py:process_cvs_for_session()               │
│     ↓                                                           │
│  2. SmartChunkingService.chunk_cv()  ← ENTRY POINT FOR METADATA │
│     ↓ Creates chunks with enriched metadata dict                │
│  3. rag_service_v5.py:index_documents()                        │
│     ↓                                                           │
│  4. vector_store.add_documents()                                │
│     ↓ Stores in JSON vector store                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    QUERY & RETRIEVAL                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  5. routes_sessions_stream.py:event_generator()                │
│     ↓                                                           │
│  6. rag_service_v5.py:query_stream()                           │
│     ↓                                                           │
│  7. _step_fusion_retrieval()                                   │
│     ↓ vector_store.search() returns SearchResult               │
│     ↓ PRESERVES ALL METADATA (see CRITICAL comment in code)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    LLM PROMPT BUILDING                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  8. templates.py:build_single_candidate_prompt()               │
│     ↓                                                           │
│  9. _extract_enriched_metadata()  ← EXTRACTION POINT           │
│     ↓ Formats metadata for LLM consumption                     │
│  10. LLM receives enriched context with pre-calculated metrics │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## ➕ How to Add a New Metadata Field

### Step 1: Calculate in SmartChunkingService

Edit `backend/app/services/smart_chunking_service.py`:

```python
def chunk_cv(self, text, cv_id, filename):
    # ... existing code ...
    
    # Add your calculation here:
    my_new_metric = self._calculate_my_metric(structured.positions)
    
    # Then add to EACH chunk's metadata dict:
    chunks.append({
        "metadata": {
            # ... existing fields ...
            "my_new_metric": my_new_metric,  # ← ADD HERE
        }
    })
```

### Step 2: Extract in templates.py

Edit `backend/app/prompts/templates.py`:

```python
def _extract_enriched_metadata(self, chunks):
    # ... existing code ...
    
    # Extract your field:
    my_new_metric = meta.get("my_new_metric")
    
    # Format for LLM:
    if my_new_metric:
        stability_parts.append(f"- **My Metric**: {my_new_metric}")
```

### Step 3: Test

1. Delete vector store data: `rm -rf backend/data/vectors.json`
2. Restart server
3. Upload a CV
4. Check logs for: `[ENRICHED_METADATA] First chunk metadata keys: [..., 'my_new_metric', ...]`

---

## 📋 Current Metadata Fields

| Field | Type | Description | Used By |
|-------|------|-------------|---------|
| `job_hopping_score` | float (0-1) | Career stability, higher = less stable | RedFlagsModule, templates.py |
| `avg_tenure_years` | float | Average years per position | RedFlagsModule, templates.py |
| `total_experience_years` | float | Total career experience | templates.py, TimelineModule |
| `position_count` | int | Number of positions held | templates.py |
| `employment_gaps_count` | int | Gaps > 1 year between jobs | RedFlagsModule |
| `current_role` | str | Current job title | templates.py |
| `current_company` | str | Current employer | templates.py |
| `section_type` | str | CV section type | General routing |
| `candidate_name` | str | Candidate's name | All modules |

---

## ⚠️ Critical Code Locations

### DO NOT MODIFY (unless you understand the flow):

1. **`rag_service_v5.py:1612-1650`** - Metadata preservation
   - Contains CRITICAL comment about preserving ALL metadata
   - If you rebuild metadata dict here, you'll lose enriched fields

2. **`vector_store.py:add_documents()`** - Stores `doc.get("metadata", {})`
   - Stores complete metadata dict as-is

3. **`vector_store.py:search()`** - Returns `metadata=doc.get("metadata", {})`
   - Returns complete metadata in SearchResult

---

## 🗑️ Obsolete Files (DO NOT USE)

These files exist but are NOT used in the current pipeline:

| File | Status | Replacement |
|------|--------|-------------|
| `routes.py` | ❌ Not registered in main.py | Use `routes_sessions.py` |
| `chunking_service.py` | ⚠️ Legacy | Use `smart_chunking_service.py` |
| `pdf_service.py` | ⚠️ Only CVChunk class used | Use `smart_chunking_service.py` for chunking |

### Active Routers (registered in main.py):
- ✅ `routes_v2.py`
- ✅ `routes_sessions.py`
- ✅ `routes_sessions_stream.py`

---

## 🔧 Troubleshooting

### Problem: Metadata shows `None` in logs

```
[ENRICHED_METADATA] First chunk metadata values: job_hopping_score=None
```

**Causes:**
1. CVs were indexed before metadata fields were added
2. Metadata is being truncated somewhere in the pipeline

**Solutions:**
1. Delete vector store data and re-upload CVs
2. Check `rag_service_v5.py:_step_fusion_retrieval()` preserves ALL metadata

### Problem: New field not appearing

1. Verify field is added in `SmartChunkingService.chunk_cv()` to ALL chunk types
2. Verify field is extracted in `templates.py:_extract_enriched_metadata()`
3. Check logs for the field name in metadata keys list

---

## 📚 Related Documentation

- `STRUCTURED_OUTPUT.md` - Output modules (RedFlagsModule, GapAnalysisModule, etc.)
- `RAG_WORKFLOW.md` - Complete RAG pipeline overview
- `ARCHITECTURE.md` - System architecture
