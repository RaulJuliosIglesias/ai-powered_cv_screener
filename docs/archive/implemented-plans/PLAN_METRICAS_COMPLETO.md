# IMPLEMENTATION PLAN: COMPLETE METRICS PANEL

## IDENTIFIED PROBLEMS

### 1. CONFIDENCE SCORE - INVENTED DATA
**Current problem:**
```python
# rag_service_v5.py:1643-1645
confidence = 0.8  # ❌ HARDCODED VALUE (INVENTED)
if ctx.verification_result:
    confidence = ctx.verification_result.groundedness_score
```

**Problem:**
- Default hardcoded to 0.8 when there is NO verification
- In `_build_no_results_response`: hardcoded 0.8
- Does NOT explain where the value comes from
- Does NOT document the logic

**REAL logic (when it exists):**
- If `claim_verification` is activated → uses verification `groundedness_score`
- `groundedness_score` comes from `ClaimVerificationService`
- Calculated by comparing LLM claims with context chunks
- Value between 0.0 and 1.0 based on evidence

### 2. COSTS - ONLY GENERATION, MISSING OTHER COMPONENTS
**Current problem:**
- Only captures cost of GENERATION stage
- Does NOT capture costs of:
  - Query Understanding (uses LLM)
  - Reasoning (uses LLM)
  - Claim Verification (uses LLM)
  - Multi-query (if active, uses LLM)

**Current table shows:**
```
Prompt tokens: X
Completion tokens: Y
Total: X+Y
```

**Should show:**
```
Understanding: $0.0001 (if active)
Reasoning: $0.0023 (if active)
Generation: $0.0045
Verification: $0.0008 (if active)
---
Total: $0.0077
```

---

## DETAILED IMPLEMENTATION PLAN

### PHASE 1: INVESTIGATE AND DOCUMENT CONFIDENCE SCORE

#### Task 1.1: Analyze ClaimVerificationService
- [ ] Read `claim_verification_service.py`
- [ ] Document how `groundedness_score` is calculated
- [ ] Identify influencing factors (verified/unverified/contradicted claims)
- [ ] Create clear algorithm documentation

#### Task 1.2: Remove hardcoded values
- [ ] In `_build_success_response`: DO NOT use 0.8 default
- [ ] In `_build_no_results_response`: Calculate real confidence
- [ ] If there is NO verification, use another method or indicate "N/A"

#### Task 1.3: Add confidence metadata
- [ ] Add `confidence_explanation` to `RAGResponseV5`
- [ ] Structure:
  ```python
  confidence_explanation = {
      "score": 0.85,
      "source": "claim_verification",  # or "default", "heuristic"
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
