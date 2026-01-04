# PLAN DE IMPLEMENTACIÓN: PANEL DE MÉTRICAS COMPLETO

## PROBLEMAS IDENTIFICADOS

### 1. CONFIDENCE SCORE - DATO INVENTADO
**Problema actual:**
```python
# rag_service_v5.py:1643-1645
confidence = 0.8  # ❌ VALOR HARDCODEADO (INVENTADO)
if ctx.verification_result:
    confidence = ctx.verification_result.groundedness_score
```

**Problema:**
- Default hardcoded a 0.8 cuando NO hay verificación
- En `_build_no_results_response`: hardcoded 0.8
- NO explica de dónde viene el valor
- NO documenta la lógica

**Lógica REAL (cuando existe):**
- Si `claim_verification` está activado → usa `groundedness_score` de verificación
- `groundedness_score` viene de `ClaimVerificationService`
- Se calcula comparando claims del LLM con chunks de contexto
- Valor entre 0.0 y 1.0 basado en evidencia

### 2. COSTES - SOLO GENERATION, FALTAN OTROS COMPONENTES
**Problema actual:**
- Solo captura coste de GENERATION stage
- NO captura costes de:
  - Query Understanding (usa LLM)
  - Reasoning (usa LLM)
  - Claim Verification (usa LLM)
  - Multi-query (si está activo, usa LLM)

**Tabla actual muestra:**
```
Prompt tokens: X
Completion tokens: Y
Total: X+Y
```

**Debería mostrar:**
```
Understanding: $0.0001 (si activo)
Reasoning: $0.0023 (si activo)
Generation: $0.0045
Verification: $0.0008 (si activo)
---
Total: $0.0077
```

---

## PLAN DE IMPLEMENTACIÓN DETALLADO

### FASE 1: INVESTIGAR Y DOCUMENTAR CONFIDENCE SCORE

#### Tarea 1.1: Analizar ClaimVerificationService
- [ ] Leer `claim_verification_service.py`
- [ ] Documentar cómo se calcula `groundedness_score`
- [ ] Identificar factores que influyen (verified/unverified/contradicted claims)
- [ ] Crear documentación clara del algoritmo

#### Tarea 1.2: Eliminar valores hardcoded
- [ ] En `_build_success_response`: NO usar 0.8 default
- [ ] En `_build_no_results_response`: Calcular confidence real
- [ ] Si NO hay verificación, usar otro método o indicar "N/A"

#### Tarea 1.3: Añadir metadata de confidence
- [ ] Añadir `confidence_explanation` a `RAGResponseV5`
- [ ] Estructura:
  ```python
  confidence_explanation = {
      "score": 0.85,
      "source": "claim_verification",  # o "default", "heuristic"
      "details": {
          "verified_claims": 8,
          "unverified_claims": 1,
          "contradicted_claims": 0,
          "total_claims": 9
      }
  }
  ```

---

### FASE 2: CAPTURAR COSTES DE TODOS LOS COMPONENTES RAG

#### Tarea 2.1: Identificar todos los stages que usan LLM
- [ ] Query Understanding: `_step_query_understanding` → usa LLM
- [ ] Reasoning: `_step_reasoning` → usa LLM
- [ ] Generation: `_step_generation` → usa LLM ✓ (ya captura)
- [ ] Claim Verification: `_step_claim_verification` → usa LLM

#### Tarea 2.2: Modificar cada stage para capturar coste
**Query Understanding:**
```python
# En _step_query_understanding
result = await self._query_understanding.understand(...)
openrouter_cost = result.metadata.get("openrouter_cost", 0) if result.metadata else 0

ctx.metrics.add_stage(StageMetrics(
    stage=PipelineStage.QUERY_UNDERSTANDING,
    metadata={
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "openrouter_cost": openrouter_cost
    }
))
```

**Reasoning:**
```python
# En _step_reasoning
result = await self._llm.generate(...)
openrouter_cost = result.metadata.get("openrouter_cost", 0) if result.metadata else 0

ctx.metrics.add_stage(StageMetrics(
    stage=PipelineStage.REASONING,
    metadata={
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "openrouter_cost": openrouter_cost
    }
))
```

**Claim Verification:**
```python
# En _step_claim_verification
result = await self._claim_verifier.verify_response(...)
# Capturar tokens y coste del verifier
openrouter_cost = result.metadata.get("openrouter_cost", 0) if hasattr(result, 'metadata') else 0

ctx.metrics.add_stage(StageMetrics(
    stage=PipelineStage.CLAIM_VERIFICATION,
    metadata={
        "verified": len(result.verified_claims),
        "unverified": len(result.unverified_claims),
        "contradicted": len(result.contradicted_claims),
        "openrouter_cost": openrouter_cost  # AÑADIR
    }
))
```

#### Tarea 2.3: Asegurar que servicios retornen coste
- [ ] `QueryUnderstandingService` debe retornar LLMResult con metadata
- [ ] `ClaimVerificationService` debe retornar coste en metadata
- [ ] Todos los servicios que usen LLM deben propagar `openrouter_cost`

---

### FASE 3: ACTUALIZAR FRONTEND - DESGLOSE DE COSTES POR COMPONENTE

#### Tarea 3.1: Nueva tabla de costes por stage
```jsx
// MetricsPanel.jsx
const costBreakdown = [
  {
    name: "Understanding",
    active: !!stages.query_understanding,
    cost: stages.query_understanding?.metadata?.openrouter_cost || 0,
    tokens: stages.query_understanding?.metadata?.total_tokens || 0
  },
  {
    name: "Reasoning",
    active: !!stages.reasoning,
    cost: stages.reasoning?.metadata?.openrouter_cost || 0,
    tokens: stages.reasoning?.metadata?.total_tokens || 0
  },
  {
    name: "Generation",
    active: !!stages.generation,
    cost: stages.generation?.metadata?.openrouter_cost || 0,
    tokens: stages.generation?.metadata?.total_tokens || 0
  },
  {
    name: "Verification",
    active: !!stages.claim_verification,
    cost: stages.claim_verification?.metadata?.openrouter_cost || 0,
    tokens: stages.claim_verification?.metadata?.total_tokens || 0
  }
];

const totalCost = costBreakdown.reduce((sum, item) => sum + (item.active ? item.cost : 0), 0);
const totalTokens = costBreakdown.reduce((sum, item) => sum + (item.active ? item.tokens : 0), 0);
```

#### Tarea 3.2: Rediseñar tabla de costes
```jsx
<table>
  <thead>
    <tr>
      <th>Component</th>
      <th>Status</th>
      <th>Tokens</th>
      <th>Cost</th>
    </tr>
  </thead>
  <tbody>
    {costBreakdown.map(item => (
      <tr key={item.name}>
        <td>{item.name}</td>
        <td>{item.active ? '✓' : 'OFF'}</td>
        <td>{item.active ? item.tokens.toLocaleString() : '-'}</td>
        <td>{item.active ? formatCost(item.cost) : '-'}</td>
      </tr>
    ))}
    <tr className="border-t-2 font-bold">
      <td>Total</td>
      <td></td>
      <td>{totalTokens.toLocaleString()}</td>
      <td>{formatCost(totalCost)}</td>
    </tr>
  </tbody>
</table>
```

---

### FASE 4: EXPLICAR CONFIDENCE EN EL PANEL

#### Tarea 4.1: Añadir tooltip o expandible para confidence
```jsx
<div className="flex items-center justify-between">
  <div className="flex items-center gap-2">
    <AlertTriangle size={14} className={getConfidenceColor(confidence)} />
    <span className="text-xs text-gray-400">Confidence</span>
    <InfoIcon size={10} className="text-gray-600 cursor-help" title="Click for details" />
  </div>
  <span className={`text-xs font-mono font-bold ${getConfidenceColor(confidence)}`}>
    {confidence !== undefined ? `${Math.round(confidence * 100)}%` : '-'}
  </span>
</div>

{/* Expandible explanation */}
{showConfidenceDetails && entry.confidence_explanation && (
  <div className="mt-2 p-2 bg-gray-800 rounded text-[10px]">
    <div className="text-gray-400 mb-1">Based on:</div>
    <div className="text-gray-300">
      • Source: {entry.confidence_explanation.source}
      {entry.confidence_explanation.details && (
        <>
          <br />• Verified claims: {entry.confidence_explanation.details.verified_claims}
          <br />• Unverified: {entry.confidence_explanation.details.unverified_claims}
          <br />• Contradicted: {entry.confidence_explanation.details.contradicted_claims}
        </>
      )}
    </div>
  </div>
)}
```

---

### FASE 5: CONECTAR TABLAS Y MÉTRICAS

#### Tarea 5.1: Sincronización visual
- [ ] Cuando un componente está OFF en RAG Components, su coste debe ser "-"
- [ ] Cuando un componente está ON, debe mostrar coste real
- [ ] Latency y Cost tables deben estar alineadas con RAG Components

#### Tarea 5.2: Validación de coherencia
- [ ] Si reranking está OFF → no hay latencia ni coste de reranking
- [ ] Si verification está OFF → confidence debe indicar "sin verificación"
- [ ] Total de costes = suma de componentes activos

---

## RESUMEN DE CAMBIOS

### Backend (rag_service_v5.py):
1. Eliminar `confidence = 0.8` hardcoded
2. Añadir `confidence_explanation` a RAGResponseV5
3. Capturar coste en QUERY_UNDERSTANDING stage
4. Capturar coste en REASONING stage
5. Capturar coste en CLAIM_VERIFICATION stage
6. Propagar tokens en todos los stages

### Backend (services):
7. QueryUnderstandingService debe retornar tokens/coste
8. ClaimVerificationService debe retornar tokens/coste

### Frontend (MetricsPanel.jsx):
9. Nueva tabla de costes por componente RAG
10. Explicación expandible de confidence
11. Sincronización entre tablas
12. Validación de coherencia (OFF = sin coste)

### Frontend (App.jsx):
13. Guardar `confidence_explanation` en metrics history

---

## CHECKLIST DE VALIDACIÓN

- [ ] NO hay valores hardcoded (0.8, etc.)
- [ ] TODOS los stages que usan LLM tienen coste capturado
- [ ] Tabla de costes muestra componente por componente
- [ ] Confidence tiene explicación clara
- [ ] Componentes OFF no muestran costes
- [ ] Total de costes = suma de componentes activos
- [ ] Real OpenRouter cost (no estimaciones)

---

## PRIORIDAD DE IMPLEMENTACIÓN

1. **CRÍTICO**: Eliminar confidence hardcoded
2. **CRÍTICO**: Capturar costes de todos los stages
3. **ALTO**: Tabla de costes por componente
4. **ALTO**: Explicación de confidence
5. **MEDIO**: Validación y sincronización
