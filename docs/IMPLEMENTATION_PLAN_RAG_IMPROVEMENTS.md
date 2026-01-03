# Plan de Implementación: Mejoras al Pipeline RAG

## 📊 Resumen Ejecutivo

Este plan detalla la implementación de **2 nuevos pasos** en el pipeline RAG, la actualización del **panel de métricas** para incluir estos pasos, y la extensión del **selector de modelos** para permitir elegir modelos para cada etapa.

---

## 🏗️ Estado Actual del Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PIPELINE RAG ACTUAL (v3)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Query → [1] Query Understanding (Gemini Flash)   ← Modelo configurable ✅  │
│            ↓                                                                │
│        [2] Guardrails (regex + query understanding)                         │
│            ↓                                                                │
│        [3] Embedding Query                                                  │
│            ↓                                                                │
│        [4] Vector Search (ChromaDB/pgVector)                                │
│            ↓                                                                │
│        [5] LLM Generation                         ← Modelo configurable ✅  │
│            ↓                                                                │
│        [6] Hallucination Check (heurísticas)      ← Solo regex/heurísticas │
│            ↓                                                                │
│        [7] Eval Logging                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Archivos Clave Actuales:
- **Backend Pipeline:** `backend/app/services/rag_service_v3.py`
- **Query Understanding:** `backend/app/services/query_understanding_service.py`
- **Hallucination (heurístico):** `backend/app/services/hallucination_service.py`
- **Frontend Settings:** `frontend/src/components/RAGPipelineSettings.jsx`
- **Frontend Metrics:** `frontend/src/components/MetricsPanel.jsx`

---

## 🎯 Pipeline Mejorado Propuesto

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PIPELINE RAG MEJORADO (v4)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Query → [1] Query Understanding        ← Modelo seleccionable             │
│            ↓                                                                │
│        [2] Guardrails                                                       │
│            ↓                                                                │
│        [3] Embedding Query                                                  │
│            ↓                                                                │
│        [4] Vector Search                                                    │
│            ↓                                                                │
│        [5] Re-ranking (NUEVO) ⭐         ← Modelo seleccionable             │
│            ↓                                                                │
│        [6] LLM Generation               ← Modelo seleccionable             │
│            ↓                                                                │
│        [7] LLM Verification (NUEVO) ⭐   ← Modelo seleccionable             │
│            ↓                                                                │
│        [8] Eval Logging                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Fases de Implementación

### FASE 1: Backend - Nuevo Servicio de Re-ranking
**Prioridad:** Alta | **Estimación:** 2-3 horas

#### 1.1 Crear `reranking_service.py`
```
backend/app/services/reranking_service.py
```

**Funcionalidad:**
- Re-ordenar resultados de búsqueda usando un modelo LLM rápido
- Puntuar relevancia de cada chunk (0-10) contra la query
- Devolver top-k chunks reordenados

**Estructura del servicio:**
```python
@dataclass
class RerankResult:
    original_results: List[SearchResult]
    reranked_results: List[SearchResult]
    latency_ms: float
    model_used: str

class RerankingService:
    def __init__(self, model: str = "google/gemini-2.0-flash-001"):
        ...
    
    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 5
    ) -> RerankResult:
        ...
```

**Modelos recomendados:**
- `google/gemini-2.0-flash-001` (barato, rápido)
- `anthropic/claude-3-haiku` (alternativa)

#### 1.2 Archivos a modificar:
| Archivo | Cambio |
|---------|--------|
| `backend/app/services/__init__.py` | Exportar RerankingService |
| `backend/app/services/rag_service_v3.py` | Integrar paso de reranking |

---

### FASE 2: Backend - Servicio de Verificación LLM
**Prioridad:** Alta | **Estimación:** 2-3 horas

#### 2.1 Crear `verification_service.py`
```
backend/app/services/verification_service.py
```

**Funcionalidad:**
- Verificar respuesta LLM contra el contexto usando un modelo de verificación
- Detectar claims no fundamentados
- Retornar score de groundedness

**Estructura del servicio:**
```python
@dataclass
class VerificationResult:
    is_grounded: bool
    confidence_score: float
    ungrounded_claims: List[str]
    verified_claims: List[str]
    latency_ms: float
    model_used: str

class LLMVerificationService:
    def __init__(self, model: str = "google/gemini-2.0-flash-001"):
        ...
    
    async def verify(
        self,
        response: str,
        context: str,
        query: str
    ) -> VerificationResult:
        """
        Prompt:
        "Verifica si TODA la información en la respuesta está respaldada
        por el contexto. Lista claims no verificables."
        """
        ...
```

#### 2.2 Archivos a modificar:
| Archivo | Cambio |
|---------|--------|
| `backend/app/services/__init__.py` | Exportar LLMVerificationService |
| `backend/app/services/rag_service_v3.py` | Integrar verificación LLM |
| `backend/app/services/hallucination_service.py` | Combinar con verificación LLM |

---

### FASE 3: Backend - Actualizar RAGServiceV3
**Prioridad:** Alta | **Estimación:** 2-3 horas

#### 3.1 Modificar `rag_service_v3.py`

**Cambios:**
1. Añadir parámetros para modelos de reranking y verificación
2. Integrar paso de reranking entre search y generation
3. Integrar paso de verificación LLM después de generation
4. Actualizar métricas con nuevos tiempos

**Nueva firma del constructor:**
```python
def __init__(
    self, 
    mode: Mode = Mode.LOCAL,
    understanding_model: Optional[str] = None,
    reranking_model: Optional[str] = None,      # NUEVO
    generation_model: Optional[str] = None,
    verification_model: Optional[str] = None     # NUEVO
):
```

**Nuevas métricas a añadir:**
```python
metrics["reranking_ms"] = ...
metrics["verification_ms"] = ...
metrics["reranking_model"] = ...
metrics["verification_model"] = ...
```

---

### FASE 4: Frontend - Actualizar RAGPipelineSettings
**Prioridad:** Alta | **Estimación:** 2-3 horas

#### 4.1 Modificar `RAGPipelineSettings.jsx`

**Cambios:**
1. Añadir 2 nuevos pasos al array `PIPELINE_STEPS`
2. Actualizar UI para mostrar 4 pasos en lugar de 2
3. Actualizar funciones de guardado/carga

**Nuevo array PIPELINE_STEPS:**
```javascript
const PIPELINE_STEPS = [
  {
    id: 'understanding',
    icon: Zap,
    color: 'amber',
    title: { es: 'Paso 1: Entendimiento de Query', en: 'Step 1: Query Understanding' },
    // ...
  },
  {
    id: 'reranking',  // NUEVO
    icon: ArrowUpDown,  // o Shuffle
    color: 'purple',
    title: { es: 'Paso 2: Re-ranking', en: 'Step 2: Re-ranking' },
    description: { 
      es: 'Reordena resultados de búsqueda por relevancia usando LLM', 
      en: 'Reorders search results by relevance using LLM' 
    },
    defaultModel: 'google/gemini-2.0-flash-001',
    recommended: { es: 'Modelo rápido para scoring', en: 'Fast model for scoring' },
    optional: true  // Puede desactivarse
  },
  {
    id: 'generation',
    icon: MessageSquare,
    color: 'blue',
    // ... (existente)
  },
  {
    id: 'verification',  // NUEVO
    icon: ShieldCheck,
    color: 'green',
    title: { es: 'Paso 4: Verificación LLM', en: 'Step 4: LLM Verification' },
    description: { 
      es: 'Verifica que la respuesta esté fundamentada en los CVs', 
      en: 'Verifies response is grounded in the CVs' 
    },
    defaultModel: 'google/gemini-2.0-flash-001',
    recommended: { es: 'Modelo preciso para verificación', en: 'Accurate model for verification' },
    optional: true
  }
];
```

**Nueva estructura de settings:**
```javascript
{
  understanding: 'google/gemini-2.0-flash-001',
  reranking: 'google/gemini-2.0-flash-001',     // NUEVO
  reranking_enabled: true,                       // NUEVO
  generation: 'google/gemini-2.0-flash-001',
  verification: 'google/gemini-2.0-flash-001',  // NUEVO
  verification_enabled: true                     // NUEVO
}
```

---

### FASE 5: Frontend - Actualizar MetricsPanel
**Prioridad:** Alta | **Estimación:** 1-2 horas

#### 5.1 Modificar `MetricsPanel.jsx`

**Cambios:**
1. Añadir métricas de Reranking y Verification
2. Mostrar modelos usados en cada paso
3. Actualizar agregados

**Nuevas métricas en QueryEntry:**
```javascript
// En la sección de Latencies
<MetricRow icon={ArrowUpDown} label="Rerank" value={formatMs(metrics.reranking_ms)} color="text-purple-400" />
<MetricRow icon={ShieldCheck} label="Verify" value={formatMs(metrics.verification_ms)} color="text-green-400" />

// Nueva sección de Modelos
<div>
  <div className="text-[10px] text-gray-500 uppercase">Models Used</div>
  <MetricRow icon={Zap} label="Understanding" value={metrics.understanding_model || '-'} />
  <MetricRow icon={ArrowUpDown} label="Reranking" value={metrics.reranking_model || '-'} />
  <MetricRow icon={MessageSquare} label="Generation" value={metrics.generation_model || '-'} />
  <MetricRow icon={ShieldCheck} label="Verification" value={metrics.verification_model || '-'} />
</div>
```

**Actualizar agregados:**
```javascript
const aggregates = {
  // ... existentes
  avgRerankingMs: ...,
  avgVerificationMs: ...,
};
```

---

### FASE 6: Backend API - Actualizar Endpoints
**Prioridad:** Media | **Estimación:** 1 hora

#### 6.1 Modificar `routes_sessions.py`

**Cambios:**
- Pasar configuración de modelos al RAGServiceV3
- Incluir nuevas métricas en respuesta

**Actualizar endpoint de chat:**
```python
@router.post("/sessions/{session_id}/chat")
async def chat_with_session(
    session_id: str,
    request: ChatRequest,
    mode: Mode = Query(default=Mode.LOCAL)
):
    # Extraer configuración de pipeline
    pipeline_config = request.pipeline_settings or {}
    
    rag_service = RAGServiceV3(
        mode=mode,
        understanding_model=pipeline_config.get('understanding'),
        reranking_model=pipeline_config.get('reranking'),
        generation_model=pipeline_config.get('generation'),
        verification_model=pipeline_config.get('verification')
    )
    
    # ...
```

---

### FASE 7: Tests
**Prioridad:** Media | **Estimación:** 2 horas

#### 7.1 Crear tests para nuevos servicios
```
backend/tests/test_reranking_service.py
backend/tests/test_verification_service.py
```

#### 7.2 Actualizar tests existentes
```
backend/tests/test_rag_service_v3.py
```

---

## 📁 Resumen de Archivos

### Archivos a CREAR:
| Archivo | Descripción |
|---------|-------------|
| `backend/app/services/reranking_service.py` | Servicio de re-ranking LLM |
| `backend/app/services/verification_service.py` | Servicio de verificación LLM |
| `backend/tests/test_reranking_service.py` | Tests de reranking |
| `backend/tests/test_verification_service.py` | Tests de verificación |

### Archivos a MODIFICAR:
| Archivo | Cambios |
|---------|---------|
| `backend/app/services/rag_service_v3.py` | Integrar nuevos pasos |
| `backend/app/services/__init__.py` | Exportar nuevos servicios |
| `backend/app/api/routes_sessions.py` | Pasar config de modelos |
| `frontend/src/components/RAGPipelineSettings.jsx` | Añadir 2 nuevos pasos |
| `frontend/src/components/MetricsPanel.jsx` | Mostrar nuevas métricas |
| `frontend/src/services/api.js` | Actualizar payload si necesario |

---

## ⏱️ Estimación Total

| Fase | Tiempo |
|------|--------|
| Fase 1: Reranking Service | 2-3h |
| Fase 2: Verification Service | 2-3h |
| Fase 3: Update RAGServiceV3 | 2-3h |
| Fase 4: Update RAGPipelineSettings | 2-3h |
| Fase 5: Update MetricsPanel | 1-2h |
| Fase 6: Update API | 1h |
| Fase 7: Tests | 2h |
| **TOTAL** | **12-17 horas** |

---

## 🚀 Orden de Implementación Recomendado

1. **Backend primero:** Crear servicios de reranking y verification
2. **Integrar en RAG:** Actualizar rag_service_v3.py
3. **Frontend Settings:** Actualizar RAGPipelineSettings
4. **Frontend Metrics:** Actualizar MetricsPanel
5. **Tests:** Validar todo funciona

---

## 💡 Consideraciones Adicionales

### Toggle para Pasos Opcionales
Los pasos de **Reranking** y **Verification** deben poder **desactivarse** para:
- Reducir latencia cuando no se necesitan
- Reducir costos de API
- Debugging

### Modelos Recomendados por Paso
| Paso | Modelo Recomendado | Alternativa |
|------|-------------------|-------------|
| Understanding | gemini-2.0-flash-001 | claude-3-haiku |
| Reranking | gemini-2.0-flash-001 | - |
| Generation | gemini-2.0-flash-001 | gpt-4o-mini |
| Verification | gemini-2.0-flash-001 | claude-3-haiku |

### Costos Estimados por Query
| Paso | Costo Aprox. |
|------|--------------|
| Understanding | ~$0.0001 |
| Reranking | ~$0.0003 |
| Generation | ~$0.001 |
| Verification | ~$0.0002 |
| **TOTAL** | ~$0.0016/query |

---

## ✅ Checklist de Implementación

- [ ] Crear `reranking_service.py`
- [ ] Crear `verification_service.py`
- [ ] Actualizar `rag_service_v3.py`
- [ ] Actualizar `RAGPipelineSettings.jsx`
- [ ] Actualizar `MetricsPanel.jsx`
- [ ] Actualizar `routes_sessions.py`
- [ ] Crear tests
- [ ] Probar flujo completo
- [ ] Documentar cambios en ARCHITECTURE.md
