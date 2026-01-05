# CV Screener - Arquitectura Actual y Plan de Mejoras

## 🏗️ ESTADO ACTUAL DEL SISTEMA

### Modos de Operación
El sistema tiene **2 modos**: `local` y `cloud` (Supabase)

---

## 📍 MODO LOCAL (`mode=local`)

### Componentes Actuales:

| Componente | Archivo | Estado | Descripción |
|------------|---------|--------|-------------|
| **Embeddings** | `providers/local/embeddings.py` | ⚠️ BÁSICO | Intenta ONNX → SentenceTransformers → **Hash fallback** |
| **Vector Store** | `providers/local/vector_store.py` | ⚠️ BÁSICO | JSON en disco + cosine similarity manual |
| **LLM** | `providers/local/llm.py` | ✅ OK | Usa OpenRouter API |

### Problemas del Modo Local:
1. **Embeddings Hash**: Si ONNX/SentenceTransformers no están instalados, usa hash MD5 (muy impreciso)
2. **Sin guardrails reales**: Solo prompt engineering, el LLM puede ignorarlo
3. **Sin evals**: No hay forma de medir calidad de respuestas
4. **Sin detección de alucinaciones**: El LLM puede inventar datos

---

## ☁️ MODO CLOUD - SUPABASE (`mode=cloud`)

### Componentes Actuales:

| Componente | Archivo | Estado | Descripción |
|------------|---------|--------|-------------|
| **Embeddings** | `providers/cloud/embeddings.py` | ✅ OK | OpenRouter `nomic-embed-text-v1.5` (768 dims) |
| **Vector Store** | `providers/cloud/vector_store.py` | ⚠️ INCOMPLETO | Supabase pgvector |
| **LLM** | `providers/cloud/llm.py` | ✅ OK | OpenRouter API |

### Problemas del Modo Cloud:
1. **Tablas Supabase vacías**: `cvs` y `cv_embeddings` no se populan correctamente
2. **Función RPC faltante**: `match_cv_embeddings` puede no existir
3. **Sin guardrails reales**: Mismo problema que local
4. **Sin evals ni métricas**: No se mide nada

---

## ❌ LO QUE FALTA (AMBOS MODOS)

### 1. EMBEDDINGS REALES
```
LOCAL:
- [ ] Instalar sentence-transformers correctamente
- [ ] Usar modelo: all-MiniLM-L6-v2 (384 dims)
- [ ] Verificar que NO usa hash fallback

CLOUD:
- [ ] Verificar que OpenRouter embeddings funcionan
- [ ] Logging para confirmar embeddings generados
```

### 2. GUARDRAILS (Prevención de off-topic)
```
- [ ] Pre-filtro ANTES del LLM para detectar preguntas off-topic
- [ ] Clasificador simple (keywords o embedding similarity)
- [ ] Rechazar preguntas sobre recetas, clima, etc.
```

### 3. ANTI-ALUCINACIÓN
```
- [ ] Verificación post-LLM: ¿Los nombres mencionados existen en los CVs?
- [ ] Verificación: ¿Las skills mencionadas están en los CVs?
- [ ] Score de confianza basado en similarity de chunks
```

### 4. EVALS (Evaluación de Calidad)
```
- [ ] Logging de todas las queries y respuestas
- [ ] Métricas: relevancia, precisión, recall
- [ ] Dataset de prueba con preguntas/respuestas esperadas
- [ ] Dashboard de métricas
```

### 5. SUPABASE SETUP CORRECTO
```sql
-- Tabla cvs
CREATE TABLE cvs (
  id TEXT PRIMARY KEY,
  filename TEXT NOT NULL,
  chunk_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla cv_embeddings con pgvector
CREATE TABLE cv_embeddings (
  id SERIAL PRIMARY KEY,
  cv_id TEXT REFERENCES cvs(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  embedding VECTOR(768),  -- Para nomic-embed
  metadata JSONB DEFAULT '{}',
  UNIQUE(cv_id, chunk_index)
);

-- Índice para búsqueda rápida
CREATE INDEX ON cv_embeddings USING ivfflat (embedding vector_cosine_ops);

-- Función RPC para búsqueda
CREATE OR REPLACE FUNCTION match_cv_embeddings(
  query_embedding VECTOR(768),
  match_count INT DEFAULT 5,
  match_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
  id INTEGER,
  cv_id TEXT,
  filename TEXT,
  content TEXT,
  similarity FLOAT,
  metadata JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    cv_embeddings.id,
    cv_embeddings.cv_id,
    cv_embeddings.filename,
    cv_embeddings.content,
    1 - (cv_embeddings.embedding <=> query_embedding) AS similarity,
    cv_embeddings.metadata
  FROM cv_embeddings
  WHERE 1 - (cv_embeddings.embedding <=> query_embedding) > match_threshold
  ORDER BY cv_embeddings.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
```

---

## 🎯 PLAN DE MEJORAS PROPUESTO

### Fase 1: Embeddings Reales (LOCAL)
1. Verificar instalación de sentence-transformers
2. Forzar uso de modelo real, no hash fallback
3. Añadir logging para confirmar qué modelo se usa

### Fase 2: Supabase Funcionando (CLOUD)
1. Ejecutar SQL de setup en Supabase
2. Verificar que embeddings se insertan
3. Probar búsqueda RPC

### Fase 3: Guardrails Pre-LLM
1. Crear clasificador de intención (CV-related vs off-topic)
2. Rechazar preguntas off-topic ANTES de llamar al LLM
3. Ahorrar tokens y tiempo

### Fase 4: Anti-Alucinación Post-LLM
1. Extraer nombres y skills de la respuesta del LLM
2. Verificar contra los CVs reales
3. Marcar o corregir información no verificable

### Fase 5: Evals y Métricas
1. Logging estructurado de queries
2. Dataset de evaluación
3. Métricas automáticas

---

## 📊 FLUJO ACTUAL vs FLUJO IDEAL

### ACTUAL (v5.1.1):
```
Pregunta → [GUARDRAIL] → Embedding → Vector Search → [Reranking] → LLM
                                                                    ↓
                                                        [Chain-of-Thought Reasoning]
                                                                    ↓
                                                        [Claim Verification]
                                                                    ↓
                                                    [Output Orchestrator]
                                                    ┌───────────────────────┐
                                                    │ Core Modules (5):     │
                                                    │ - Thinking            │
                                                    │ - DirectAnswer        │
                                                    │ - Analysis            │
                                                    │ - Table               │
                                                    │ - Conclusion          │
                                                    ├───────────────────────┤
                                                    │ Enhanced Modules (3): │ ← NEW v5.1.1
                                                    │ - GapAnalysis         │
                                                    │ - RedFlags            │
                                                    │ - Timeline            │
                                                    └───────────────────────┘
                                                                    ↓
                                                          Respuesta Estructurada
```

### METADATA ENRIQUECIDA (v5.1.1)

Durante la indexación de CVs, se extrae automáticamente:

| Campo | Descripción |
|-------|-------------|
| `total_experience_years` | Años totales de experiencia |
| `seniority_level` | junior/mid/senior/lead/executive |
| `current_role` | Puesto actual |
| `current_company` | Empresa actual |
| `has_faang_experience` | Experiencia en Big Tech |
| `job_hopping_score` | Índice de rotación (0-1) |
| `avg_tenure_years` | Promedio de permanencia |
| `employment_gaps` | Gaps de empleo detectados |

### NUEVOS TIPOS DE PREGUNTAS (v5.1.1)

**Gap Analysis:**
- "¿Qué candidatos tienen todas las skills: Maya, Houdini y Python?"
- "¿Cuál es el candidato con mejor cobertura para mis requisitos?"

**Red Flags:**
- "¿Hay candidatos con job hopping?"
- "¿Cuáles son los candidatos más estables?"
- "Dame los candidatos sin red flags"

**Timeline:**
- "¿Quién tiene la mejor progresión de carrera?"
- "Compara las trayectorias de los 3 mejores candidatos"
