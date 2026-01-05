# Red Flags Architecture - Problem Analysis and Solution

## Overview

This document explains the red flags detection system, the problems that were identified, and how they were solved. **READ THIS BEFORE MODIFYING ANY RED FLAGS LOGIC.**

---

## The System Architecture

There are **TWO separate systems** that handle red flags:

### System 1: Pre-LLM Analysis (`templates.py`)
**Location:** `backend/app/prompts/templates.py` → `_extract_enriched_metadata()`

**Purpose:** Extracts red flags from chunk METADATA and includes them in the LLM PROMPT so the LLM can reference them in its response.

**Flow:**
```
SmartChunkingService.chunk_cv()
    ↓ Creates chunks with metadata (job_hopping_score, avg_tenure_years, etc.)
Vector Store
    ↓ Stores all chunks with metadata
Retrieval
    ↓ Retrieves subset of chunks (e.g., 8 of 23)
_extract_enriched_metadata()
    ↓ Reads metadata from chunks, builds red_flags_section
SINGLE_CANDIDATE_TEMPLATE
    ↓ Includes red_flags_section in prompt
LLM Generation
    → LLM can reference the pre-calculated red flags in its response
```

**What it detects (using METADATA):**
- `job_hopping_score > 0.6` → High job hopping
- `job_hopping_score > 0.4` → Moderate job hopping
- `avg_tenure_years < 1.5` → Short average tenure
- `position_count > 6 && total_exp < 10` → Many positions in short time

---

### System 2: Post-LLM Analysis (`RedFlagsModule`)
**Location:** `backend/app/services/output_processor/modules/red_flags_module.py`

**Purpose:** Analyzes chunks AFTER the LLM responds and adds a structured "Red Flags Analysis" section to the output.

**Flow:**
```
LLM Generation
    ↓ LLM generates response
OutputOrchestrator.process()
    ↓ Calls RedFlagsModule.extract(chunks)
RedFlagsModule
    ↓ Analyzes chunk METADATA for flags
    ↓ Returns structured RedFlagsData
RedFlagsModule.format()
    ↓ Formats flags as markdown
Orchestrator
    → Appends "### Red Flags Analysis" section to response
```

**What it detects (using METADATA):**
- Job hopping (score-based)
- Short average tenure
- Entry-level candidates (no experience)
- Employment gaps (from gap count)

---

## THE PROBLEMS (What Went Wrong)

### Problem 1: Incorrect "Missing Experience" Detection

**The Bug:**
```python
# OLD CODE - WRONG!
def _check_missing_info(self, candidate, chunks):
    section_types = set()
    for chunk in chunks:
        section = chunk.get("metadata", {}).get("section_type", "")
        section_types.add(section)
    
    if "experience" not in section_types:
        # FLAG AS MISSING EXPERIENCE ← WRONG!
```

**Why It Was Wrong:**
- Retrieval only returns a SUBSET of chunks (e.g., 8 out of 23 total)
- A candidate may have 4 "experience" chunks in the DB, but if the query is about "red flags", those chunks might not be retrieved
- The code checked `section_types` in the RETRIEVED chunks, not ALL chunks
- Result: Candidates with experience were incorrectly flagged as "missing experience"

**The Fix:**
```python
# NEW CODE - CORRECT!
def _check_missing_info(self, candidate, chunks):
    # Get metadata from any chunk (all chunks have the same enriched metadata)
    meta = chunk.get("metadata", {})
    
    # Use metadata fields calculated from COMPLETE CV during chunking
    position_count = meta.get("position_count", 0)
    total_exp = meta.get("total_experience_years", 0)
    
    # Only flag if metadata shows no experience
    if position_count == 0 and total_exp == 0:
        # Entry-level candidate
```

**Key Insight:**
- The METADATA (job_hopping_score, position_count, total_experience_years) is calculated from the COMPLETE CV during chunking
- This metadata is stored on EVERY chunk
- Use METADATA to detect issues, NOT section_types from partial retrieval

---

### Problem 2: Thresholds Too High

**The Bug:**
- `job_hopping_score > 0.6` was required for ANY flag
- Many candidates with moderate job hopping (0.4-0.6) were not flagged
- `avg_tenure < 1.5` was not being used as a standalone flag

**The Fix:**
```python
JOB_HOPPING_THRESHOLD_HIGH = 0.6   # HIGH severity
JOB_HOPPING_THRESHOLD_MEDIUM = 0.4  # MEDIUM severity
SHORT_AVG_TENURE_THRESHOLD = 1.5    # Short tenure flag
```

---

## GOLDEN RULES FOR RED FLAGS

### Rule 1: NEVER Check section_types from Retrieved Chunks
```python
# ❌ WRONG - Don't do this!
section_types = {chunk["metadata"]["section_type"] for chunk in chunks}
if "experience" not in section_types:
    flag_missing_experience()

# ✅ CORRECT - Use metadata instead
position_count = chunks[0]["metadata"].get("position_count", 0)
if position_count == 0:
    flag_entry_level()
```

### Rule 2: ALWAYS Use Metadata Fields
The following fields are calculated from the COMPLETE CV during chunking and are reliable:
- `job_hopping_score` - Float 0-1, higher = more job changes
- `avg_tenure_years` - Average years per position
- `total_experience_years` - Total career experience
- `position_count` - Number of positions held
- `employment_gaps_count` - Number of gaps > 1 year

### Rule 3: Both Systems Must Be Consistent
If you add a new red flag type:
1. Add detection in `RedFlagsModule._check_*()` methods
2. Add formatting in `templates.py:_extract_enriched_metadata()`
3. Ensure both use the SAME thresholds

---

## Adding New Metadata Fields (Future: Languages, Hobbies, etc.)

### Step 1: Calculate in SmartChunkingService
```python
# backend/app/services/smart_chunking_service.py
def chunk_cv(self, text, cv_id, filename):
    # Calculate your new field
    languages = self._extract_languages(structured)
    hobbies = self._extract_hobbies(structured)
    
    # Add to EVERY chunk's metadata
    metadata = {
        "languages": languages,
        "hobbies": hobbies,
        # ... existing fields
    }
```

### Step 2: Use in RedFlagsModule (if needed for flags)
```python
# backend/app/services/output_processor/modules/red_flags_module.py
def _check_languages(self, candidate, metadata):
    languages = metadata.get("languages", [])
    if not languages:
        return RedFlag(
            flag_type="missing_languages",
            severity="low",
            description="No languages listed in CV"
        )
```

### Step 3: Include in LLM Prompt
```python
# backend/app/prompts/templates.py
def _extract_enriched_metadata(self, chunks):
    languages = meta.get("languages", [])
    if languages:
        stability_parts.append(f"- **Languages**: {', '.join(languages)}")
```

---

## Testing Red Flags

### Expected Behavior by Candidate Type:

| Candidate Profile | Expected Flags |
|-------------------|----------------|
| 16 years exp, 4 positions, avg 4 years | No flags (stable) |
| 4 years exp, 4 positions, avg 1 year | job_hopping (high), short_avg_tenure |
| 4 years exp, 3 positions, avg 1.3 years | job_hopping (medium) or short_avg_tenure |
| No experience listed | entry_level (low) |
| 1 gap > 1 year in history | employment_gap |

### Debug Logging

Check server logs for:
```
[RED_FLAGS] Analyzed X candidates: Y flags, Z high-risk, W clean
[ORCHESTRATOR] Formatting X red flags (using original object)
[ORCHESTRATOR] Red flags section ADDED to output
```

If you see `[ORCHESTRATOR] No red flags to format`, check:
1. Are chunks being passed to the orchestrator?
2. Does chunk metadata have the required fields?

---

## File Reference

| File | Purpose |
|------|---------|
| `smart_chunking_service.py` | Creates chunks with enriched metadata |
| `rag_service_v5.py` | Retrieval, passes chunks to orchestrator |
| `templates.py` | Pre-LLM red flags in prompt |
| `red_flags_module.py` | Post-LLM red flags analysis |
| `orchestrator.py` | Coordinates modules, builds final response |

---

## Summary

**The Problem:** RedFlagsModule was checking `section_types` in retrieved chunks, which only represent a subset of the candidate's data. This caused false positives for "missing experience".

**The Solution:** Use METADATA fields (job_hopping_score, position_count, etc.) which are calculated from the COMPLETE CV during chunking and are reliable regardless of which chunks are retrieved.

**The Rule:** NEVER trust section_types from partial retrieval. ALWAYS use metadata fields for detection logic.
