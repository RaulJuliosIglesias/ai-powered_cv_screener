# Query Type Detection System (V7)

## Overview

The Query Detection System automatically identifies the type of query to route it to the appropriate output structure. Version 7 includes **65+ regex patterns** for comprehensive detection.

**File:** `backend/app/prompts/templates.py`  
**Functions:** `detect_single_candidate_query()`, `is_multi_candidate_query()`

---

## Query Types

| Query Type | Template/Structure | Example |
|------------|-------------------|---------|
| `single_candidate` | SingleCandidateStructure | "Tell me about Carmen Rodriguez" |
| `comparison` | ComparisonStructure | "Compare Juan vs María" |
| `ranking` | RankingStructure | "Rank top 5 candidates" |
| `red_flags` | RiskAssessmentStructure | "What are the red flags?" |
| `job_match` | JobMatchStructure | "Who fits a senior developer role?" |
| `team_build` | TeamBuildStructure | "Build a team of 3" |
| `verification` | VerificationStructure | "Did Juan work at Google?" |
| `summary` | SummaryStructure | "Give me an overview of all candidates" |
| `search` | SearchStructure | "Who has Python experience?" |

---

## Single Candidate Patterns (35+)

### Basic Analysis Patterns
```regex
\b(?:analiza|analyze|examina|examine)\s+(?:completamente|fully|en detalle|in detail)?\s*(?:a\s+)?(?:este|this|el)\s+(?:candidato|candidate)\b
\b(?:este|this)\s+(?:candidato|candidate)\b
\b(?:el|the)\s+(?:candidato|candidate)\s+(?:anterior|previous|seleccionado|selected)\b
\b(?:profile|perfil)\s+(?:completo|complete|full)\b
\b(?:dame|give me)\s+(?:todo|everything)\s+(?:sobre|about)\s+(?:él|ella|him|her|this)\b
```

### Ranking References
```regex
#\d+\s*(?:candidato?|candidate)?                     # #1, #2, #3
\b(?:the|el|la)?\s*(?:top|best|first|number one|número uno|primero?|mejor|winner|ganador)\s+(?:candidato?|candidate)?\b
\b(?:second|third|fourth|fifth|last|runner-up|segundo|tercero|cuarto|quinto|último|subcampeón)\s+(?:candidato?|candidate)?\b
\b(?:the\s+)?(?:second|third|fourth|fifth|last)\s+(?:best|worst|mejor|peor)\s+(?:candidato?|candidate)?\b
```

### Selection References
```regex
\b(?:the|el|la)?\s*(?:chosen|selected|picked|recommended|preferred|shortlisted|elegido|seleccionado|escogido|recomendado|preferido|preseleccionado)\s+(?:one|candidato?|candidate)?\b
\b(?:give me|dame)\s+(?:more\s+details|details|info)\s+(?:about|on)\s+(?:the\s+)?(?:chosen|selected|recommended|elegido|seleccionado|recomendado)\b
```

### Superlatives
```regex
\b(?:the|el|la)?\s*(?:strongest|weakest|most|least|más|menos)\s+(?:qualified|experienced|suitable|talented|skilled|prepared|capable|fuerte|débil|cualificado|experimentado|apto|talentoso|capacitado)\s+(?:candidato?|candidate)?\b
\b(?:the\s+)?(?:highest|lowest|mayor|menor)\s+(?:scoring|ranked|performing|puntuado|rankeado)\s+(?:candidato?|candidate)?\b
```

### Leader/Loser References
```regex
\b(?:the|el|la)?\s*(?:leader|líder|front-runner|leading|winning|perdedor|loser|trailing)\s+(?:candidato?|candidate)?\b
\b(?:who\s+)?(?:is\s+)?(?:leading|winning|trailing|ahead|behind)\b
```

### Contextual/Demonstrative References
```regex
\b(?:that|those|ese|esos|aquel|aquellos)\s+(?:one|candidato?|candidate|perfil|profile)\b
\b(?:tell\s+me|dime)\s+(?:more|details|about)\s+(?:that|ese|aquel)\s+(?:one|candidato|candidate)\b
```

### Winner/Ganador Patterns
```regex
\b(?:the|el|la)?\s*(?:comparison\s+)?(?:winner|ganador)\b
\b(?:more|more\s+details|details)\s+(?:about|on)\s+(?:the\s+)?(?:winner|ganador)\b
\b(?:tell\s+me|dime)\s+(?:more|details)\s+(?:about)\s+(?:the\s+)?(?:winner|ganador)\b
```

### Previous/Conversational References
```regex
\b(?:the|el|la)?\s*(?:mentioned|previous|earlier|above|mencionado|previo|anterior|arriba)\s+(?:one|candidato?|candidate)?\b
\b(?:tell\s+me|dame)\s+(?:more\s+details|about)\s+(?:the\s+)?(?:mentioned|mencionado|previous|previo)\b
```

### Ordinal Comparatives
```regex
\b(?:the|el|la)?\s*(?:next|following|subsequent|siguiente|próximo)\s+(?:candidato?|candidate)?\b
\b(?:the|el|la)?\s*(?:other|another|otro|otro\s+más)\s+(?:candidato?|candidate)?\b
```

### Personal References
```regex
\b(?:my|tu|su)\s+(?:favorite|preferido|preferred|choice|elección)\s+(?:candidato?|candidate)?\b
\b(?:the\s+)?(?:preferred|preferido)\s+(?:candidato?|candidate)?\b
```

### Anaphoric References
```regex
\b(?:tell\s+me|dame)\s+(?:more|about)\s+(?:him|her|them|él|ella|ellos)\b
\b(?:the\s+)?(?:same|mismo)\s+(?:candidato?|candidate)?\b
```

---

## Multi-Candidate Patterns (30+)

### Basic Comparison
```regex
\ball\b.*\bcandidates?\b
\beveryone\b
\btodos\b.*\bcandidatos?\b
\bcompare\b
\brank\b
\btop\s+\d+\b
\bbest\b.*\bcandidates?\b
\bmejores?\b
\bvs\b
\bversus\b
```

### Differential Questions
```regex
\b(?:difference|differences|diferencia|diferencias)\s+(?:between|among|entre)\b
\b(?:distinguish|distinguir|contrast|contrastar)\s+(?:between|among|entre)\b
\b(?:gap|brecha|discrepancy)\s+(?:between|among|entre)\b
\b(?:what\s+)?(?:how\s+)?(?:are|son)\s+(?:they|ellos)\s+(?:different|diferentes)\b
```

### Sorting/Ordering
```regex
\b(?:sort|ordenar|arrange|organizar|prioritize|priorizar)\b.*\b(?:candidates?|candidatos?)\b
\b(?:sort|ordenar)\s+(?:by|por|according to|según)\b
\b(?:order|orden)\s+(?:them|los)\s+(?:by|por)\b
\b(?:rank|rankear|clasificar)\s+(?:all|todos)\s+(?:the|los)\s+(?:candidates|candidatos)\b
```

### Quantity Indicators
```regex
\b(?:several|various|multiple|múltiples|some|algunos|few|pocos)\s+(?:candidates?|candidatos?)\b
\b(?:a\s+)?(?:few|pocos)\s+(?:of|de)\s+(?:the|los)\s+(?:candidates|candidatos)\b
\b(?:some|algunos)\s+(?:of|de)\s+(?:these|estos)\s+(?:candidates|candidatos)\b
```

### Group/Pool References
```regex
\b(?:pool|grupo|batch|lote|set|conjunto|cohort|cohorte)\s+(?:of|de)?\s*(?:candidates|candidatos)?\b
\b(?:the\s+)?(?:entire|complete|completo)\s+(?:pool|grupo|set|conjunto)\b
\b(?:all\s+)?(?:candidates|candidatos)\s+(?:in\s+)?(?:the\s+)?(?:pool|grupo)\b
```

### Selection from Many
```regex
\b(?:choose|elegir|select|seleccionar|pick|escoger|shortlist|preseleccionar)\s+(?:from|de|entre)\b
\b(?:who\s+)?(?:should\s+)?(?:we|yo)\s+(?:choose|elegir|select|seleccionar)\b
\b(?:help\s+)?(?:me\s+)?(?:choose|elegir|decide)\b
\b(?:narrow\s+down|reducir|filter|filtrar)\s+(?:the|los)\s+(?:candidates|candidatos)\b
```

### Decision-Making
```regex
\b(?:which\s+)?(?:one|uno)\s+(?:is\s+)?(?:better|mejor|best|mejor)\b
\b(?:who\s+)?(?:wins|gana|comes\s+out\s+on\s+top)\b
\b(?:make\s+)?(?:a\s+)?(?:decision|decisión|choice|elección)\b
\b(?:help\s+)?(?:me\s+)?(?:decide|decidir)\b
```

### Exclusion Patterns
```regex
\b(?:except|excepto|without|sin|excluding|excluyendo|but\s+not|menos)\b.*\b(?:candidates?|candidatos?)\b
\b(?:all|todos)\s+(?:except|excepto|menos)\b
\b(?:not|no|neither|ninguno|none)\s+(?:of|de)\s+(?:these|estos)\s+(?:candidates|candidatos)\b
```

### Comparative Analysis
```regex
\b(?:compare|comparar)\s+(?:and\s+)?(?:contrast|contrastar)\b
\b(?:pros\s+and\s+cons|ventajas\s+y\s+desventajas)\s+(?:of|de)\b
\b(?:strengths\s+and\s+weaknesses|fortalezas\s+y\s+debilidades)\b
\b(?:advantages\s+and\s+disadvantages|ventajas\s+y\s+desventajas)\b
```

### Multiple Specific References
```regex
\b(?:both|ambos)\s+(?:candidates|candidatos)\b
\b(?:either|cualquiera)\s+(?:of|de)\s+(?:the|los)\s+(?:two|dos)\b
\b(?:among|entre)\s+(?:the|los)\s+(?:candidates|candidatos)\b
\b(?:across|a\s+través\s+de)\s+(?:all|todos)\s+(?:candidates|candidatos)\b
```

---

## Detection Flow

```
User Query
    │
    ▼
is_multi_candidate_query() ──Yes──► comparison/ranking
    │
    No
    │
    ▼
detect_single_candidate_query()
    │
    ├── Method 1: Explicit name in query ──► single_candidate
    │
    ├── Method 2: Only 1 candidate in chunks ──► single_candidate
    │
    ├── Method 3: Single intent patterns ──► single_candidate
    │
    └── Default ──► search/comparison
```

---

## Testing Query Detection

```python
# Test single candidate detection
from app.prompts.templates import detect_single_candidate_query

result = detect_single_candidate_query(
    question="Give me more details about the comparison winner",
    chunks=[{"metadata": {"candidate_name": "Juan García", "cv_id": "cv_123"}}]
)
print(result.is_single_candidate)  # True
print(result.detection_method)      # "single_intent_pattern_top_chunk"
```

---

## Adding New Patterns

To add a new detection pattern:

1. **Identify the query type** (single vs multi)
2. **Add pattern to appropriate list** in `templates.py`
3. **Test with sample queries**
4. **Update this documentation**

```python
# Example: Adding "champion" pattern
single_candidate_intent_patterns = [
    ...
    r"\b(?:the\s+)?(?:champion|campeón)\s+(?:candidato?|candidate)?\b",
]
```

---

## Pattern Statistics

| Category | V6 Count | V7 Count | Increase |
|----------|----------|----------|----------|
| Single Candidate | 12 | 35+ | +192% |
| Multi-Candidate | 15 | 30+ | +100% |
| **Total** | **27** | **65+** | **+141%** |
