# Auditoría de Módulos y Estructuras - V8

## Problema Identificado

En queries de ranking como "Rank candidates by experience", el sistema:
1. Dice "Experience (100%)" sin mencionar los años reales (31 años)
2. En tablas muestra "0 years" cuando debería ser "31 years"
3. Conclusiones dicen "60% score" sin explicar el porqué

## Causa Raíz

Los **metadatos enriquecidos** (`total_experience_years`, `job_hopping_score`, `avg_tenure_years`) existen en los chunks pero:
1. No se mostraban en el contexto enviado al LLM
2. Los módulos de Top Pick y Ranking no incluían datos numéricos concretos en sus justificaciones

---

## Correcciones Aplicadas

### 1. `templates.py` - `format_context()`
**Archivo:** `backend/app/prompts/templates.py`
**Líneas:** 1015-1053

**Cambio:** Ahora incluye metadatos enriquecidos en los headers de contexto:
```python
# Ahora el LLM verá:
- **Total Experience:** 31.0 years
- **Job Hopping Score:** 0.06 (lower is better)
- **Avg Tenure:** 12.0 years per position
- **Seniority:** Senior
- **Skills:** Python, Django, PostgreSQL...
```

### 2. `templates.py` - SYSTEM_PROMPT
**Archivo:** `backend/app/prompts/templates.py`
**Líneas:** 125-133

**Cambio:** Instrucción explícita al LLM para usar metadatos:
```
- **CRITICAL: When CV chunks include enriched metadata (Total Experience, Avg Tenure, Job Hopping Score, Skills, Seniority), you MUST use these values in your analysis and responses**
- For ranking/comparison queries: ALWAYS cite the numeric metadata values (e.g., "31 years of experience", "12 years average tenure")
```

### 3. `templates.py` - QUERY_TEMPLATE
**Archivo:** `backend/app/prompts/templates.py`
**Líneas:** 265-269

**Cambio:** Instrucción explícita para tablas de ranking:
```
**CRITICAL for ranking/experience queries:** In table cells, include ACTUAL VALUES from enriched metadata:
- For "Experience" column: Write "31 years" NOT just "100%" or "High"
- For "Tenure" column: Write "12 years avg" NOT just "Excellent"
Example row: | **[Khalid Al-Mansoori](cv:cv_eec7ef06)** | 31 years | 12 years avg tenure | ⭐⭐⭐⭐⭐ |
```

### 4. `top_pick_module.py` - `_generate_justification()`
**Archivo:** `backend/app/services/output_processor/modules/top_pick_module.py`
**Líneas:** 107-145

**Cambio:** Incluye datos numéricos concretos en la justificación:
```python
# Antes: "Experience (100%)"
# Ahora: "Key metrics: 31 years of experience, 12.0 years average tenure, strong job stability"
```

### 5. `ranking_table_module.py` - `_group_by_candidate()`
**Archivo:** `backend/app/services/output_processor/modules/ranking_table_module.py`
**Líneas:** 261-310

**Cambio:** Preserva todos los metadatos enriquecidos y toma el valor máximo cuando hay múltiples chunks del mismo candidato.

### 6. `ranking_table_module.py` - `RankedCandidate` dataclass (CRÍTICO)
**Archivo:** `backend/app/services/output_processor/modules/ranking_table_module.py`
**Líneas:** 21-35

**Problema encontrado:** El dataclass `RankedCandidate` NO incluía campos para metadatos enriquecidos. El método `to_dict()` tampoco los pasaba al `TopPickModule`.

**Cambio:**
```python
@dataclass
class RankedCandidate:
    # ... campos existentes ...
    # NUEVOS: Enriched metadata for concrete justifications
    experience_years: float = 0.0
    avg_tenure: float = 0.0
    job_hopping_score: float = 0.5
    seniority: str = ""
```

### 7. `ranking_table_module.py` - Creación de RankedCandidate
**Archivo:** `backend/app/services/output_processor/modules/ranking_table_module.py`
**Líneas:** 125-138, 222-238, 268-284

**Problema:** En los 3 lugares donde se crea `RankedCandidate`, no se pasaban los metadatos enriquecidos.

**Cambio:** Todos los constructores ahora incluyen:
```python
experience_years=cand_data.get("experience_years", 0),
avg_tenure=cand_data.get("avg_tenure", 0),
job_hopping_score=cand_data.get("job_hopping_score", 0.5),
seniority=cand_data.get("seniority", "")
```

---

## Módulos Auditados - Estado

| Módulo | Estado | Problema | Corrección |
|--------|--------|----------|------------|
| `ranking_table_module.py` | ✅ CORREGIDO | No preservaba todos los metadatos | Actualizado `_group_by_candidate()` |
| `top_pick_module.py` | ✅ CORREGIDO | Decía "Experience (100%)" sin años | Añadido `numeric_justifications` |
| `results_table_module.py` | ✅ OK | Ya incluye `{r.experience_years:.0f} years` | No requiere cambios |
| `match_score_module.py` | ✅ OK | Ya incluye strengths con años | No requiere cambios |
| `highlights_module.py` | ⚠️ REVISAR | Extrae de LLM, no de metadatos | Considerar fallback a metadatos |
| `career_module.py` | ✅ OK | Extrae correctamente fechas | No requiere cambios |
| `conclusion_module.py` | ✅ OK | Solo formatea | No requiere cambios |
| `analysis_module.py` | ✅ OK | Genera fallback con datos | No requiere cambios |
| `gap_analysis_module.py` | ✅ OK | Analiza skills correctamente | No requiere cambios |
| `risk_table_module.py` | ✅ OK | Usa metadatos de chunks | No requiere cambios |

---

## Estructuras Auditadas - Estado

| Estructura | Estado | Problema | Corrección |
|------------|--------|----------|------------|
| `ranking_structure.py` | ✅ OK | Usa módulos correctamente | No requiere cambios |
| `search_structure.py` | ✅ OK | Usa ResultsTableModule | No requiere cambios |
| `comparison_structure.py` | ⚠️ REVISAR | Usa TableModule genérico | Considerar añadir metadatos |
| `job_match_structure.py` | ✅ OK | Incluye strengths con años | No requiere cambios |
| `single_candidate_structure.py` | ✅ OK | Usa RiskTableModule | No requiere cambios |
| `summary_structure.py` | ✅ OK | Resume datos de chunks | No requiere cambios |

---

## Para Aplicar Cambios

**IMPORTANTE:** Los cambios en `templates.py` solo se aplican cuando el servidor se reinicia.

```bash
# En Windows PowerShell, en la carpeta backend:
# 1. Detener el servidor actual (Ctrl+C)
# 2. Reiniciar:
python -m uvicorn app.main:app --reload --port 8000
```

También puedes forzar el reset del orchestrator llamando:
```python
from app.services.output_processor.orchestrator import reset_orchestrator
reset_orchestrator()
```

---

## Resultado Esperado Después de Reinicio

**Query:** "Rank candidates by experience"

**Top Recommendation:**
> Khalid Al-Mansoori emerges as the top choice with 60%. **Key metrics: 31 years of experience, 12.0 years average tenure, strong job stability.**

**Tabla:**
| Candidate | Experience | Avg Tenure | Match |
|-----------|-----------|------------|-------|
| **[Khalid Al-Mansoori](cv:cv_eec7ef06)** | 31 years | 12 years avg | ⭐⭐⭐⭐⭐ |
| **[Priya Patel](cv:cv_2d404e7a)** | 9 years | 4 years avg | ⭐⭐⭐⭐ |
| **[Layla Al-Mansoor](cv:cv_4fa786c9)** | 3 years | 1.5 years avg | ⭐⭐⭐ |

**Conclusión:**
> Khalid Al-Mansoori is recommended with 31 years of experience and excellent stability (12 years average tenure). Runner-up: Priya Patel with 9 years.
