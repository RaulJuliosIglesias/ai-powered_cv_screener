# Implementation Plan: Conversational Context Integration

## Document Purpose

Complete plan to integrate the conversational context system with the current CV Screener STRUCTURES/MODULES/ORCHESTRATOR architecture.

**Reference Documents:**
- `docs/CONVERSATIONAL_CONTEXT.md` - Original context design
- `docs/NextUpdate/ORCHESTRATION_STRUCTURES_MODULES.md` - New architecture
- `docs/NextUpdate/IMPLEMENTATION_PLAN.md` - General implementation plan

**Version:** 1.0  
**Date:** January 2026  
**Total Estimated Time:** 20-25 hours

---

# PART 1: CURRENT STATE ANALYSIS

## 1.1 Conversational Context System (Implemented)

### ✅ **Base Infrastructure - COMPLETE**

```python
# SessionManager - Local
backend/app/models/sessions.py:201-218
def get_conversation_history(session_id: str, limit: int = 6) -> List[ChatMessage]

# SessionManager - Cloud (Supabase)
backend/app/providers/cloud/sessions.py:299-336
def get_conversation_history(session_id: str, limit: int = 6) -> List[Dict]
```

**Status:** ✅ Implemented and functional
- Retrieves last N messages (default: 6 = 3 turns)
- Works in local and cloud mode
- Returns format: `[{"role": "user|assistant", "content": "..."}]`

### ✅ **Pipeline Integration - COMPLETA**

```python
# PipelineContextV5
backend/app/services/rag_service_v5.py:554
conversation_history: list[dict[str, str]] = field(default_factory=list)

# query_stream() accepts conversation_history
backend/app/services/rag_service_v5.py:899
async def query_stream(
    self,
    question: str,
    conversation_history: list[dict[str, str]] | None = None,
    ...
)
```

**Status:** ✅ Implemented
- Context flows through entire RAG pipeline
- Stored in `PipelineContextV5`

### ✅ **Endpoint Integration - COMPLETA**

```python
# routes_sessions_stream.py:111-120
history = mgr.get_conversation_history(session_id, limit=6)
conversation_history = [
    {"role": msg.role, "content": msg.content}
    for msg in history
]
```

**Status:** ✅ Implemented
- Endpoint automatically retrieves history
- Passes it to `query_stream()`

### ✅ **Prompt Builder Integration - COMPLETA**

```python
# templates.py
def build_query_prompt(..., conversation_history: list = None)
def build_single_candidate_prompt(..., conversation_history: list = None)
```

**Status:** ✅ Implemented
- Both methods accept `conversation_history`
- Format as `## CONVERSATION HISTORY` section in prompt

---

## 1.2 STRUCTURES/MODULES Architecture (New)

### ✅ **Orchestrator - PARTIALLY UPDATED**

```python
# orchestrator.py:95-103
def process(
    self,
    raw_llm_output: str,
    chunks: List[Dict[str, Any]] = None,
    query: str = "",
    query_type: str = "comparison",
    candidate_name: str = None
) -> tuple[StructuredOutput, str]:
```

**Status:** ⚠️ **Does NOT accept `conversation_history`**

### ✅ **Structures - 9 IMPLEMENTED**

```
backend/app/services/output_processor/structures/
├── single_candidate_structure.py   ✅ IMPLEMENTED
├── risk_assessment_structure.py    ✅ IMPLEMENTED  
├── comparison_structure.py         ✅ IMPLEMENTED
├── search_structure.py             ✅ IMPLEMENTED
├── ranking_structure.py            ✅ IMPLEMENTED
├── job_match_structure.py          ✅ IMPLEMENTED
├── team_build_structure.py         ✅ IMPLEMENTED
├── verification_structure.py       ✅ IMPLEMENTED
└── summary_structure.py            ✅ IMPLEMENTED
```

**Status:** ⚠️ **NONE accept `conversation_history`**

```python
# Current signature (example SingleCandidateStructure)
def assemble(
    self,
    llm_output: str,
    chunks: List[Dict],
    candidate_name: str,
    cv_id: str
) -> Dict[str, Any]:
```

---

## 1.3 Identified Problem: Context Disconnection

### 🔴 **Current Flow (INCOMPLETE)**

```
1. Endpoint retrieves conversation_history       ✅
2. RAG service receives conversation_history     ✅
3. PromptBuilder uses conversation_history       ✅
4. LLM generates response with context           ✅
5. Orchestrator processes response               ❌ WITHOUT context
6. Structure assembles output                    ❌ WITHOUT context
```

### 🔴 **Use Cases that FAIL**

#### **Case 1: Single Candidate Follow-up**
```
User: "Give me the complete profile of Juan Pérez"
→ Orchestrator → SingleCandidateStructure ✅
→ Response: [Complete profile]

User: "What red flags does he have?"
→ Orchestrator → RiskAssessmentStructure
→ ❌ Does NOT know "What red flags does he have?" refers to Juan Pérez
→ Needs to re-search candidate based only on current query
```

#### **Case 2: Pronominal References**
```
User: "Compare Juan and María"
→ ComparisonStructure ✅

User: "And for Backend these two?"
→ ❌ "these two" doesn't resolve to Juan and María
→ Structure has no context of who they are
```

#### **Case 3: Search Context**
```
User: "Find Frontend developers with React"
→ SearchStructure ✅

User: "Which one has more experience?"
→ ❌ Does NOT know it refers to previous results
→ Structure cannot filter within previous results
```

---

# PART 2: SOLUTION DESIGN

## 2.1 Target Architecture

### **Complete Flow with Integrated Context**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ENDPOINT (routes_sessions_stream.py)                    │
│    ↓ Recupera conversation_history del SessionManager      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. RAG SERVICE (rag_service_v5.py)                         │
│    ↓ Almacena en PipelineContextV5                         │
│    ↓ [NUEVO] ContextResolver resuelve referencias          │
│    ↓ Pasa contexto al PromptBuilder                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. PROMPT BUILDER (templates.py)                           │
│    ↓ Formatea conversation_history en el prompt            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. LLM GENERATION                                           │
│    ↓ Genera respuesta con contexto                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. ORCHESTRATOR (orchestrator.py)                          │
│    ↓ [NUEVO] Recibe conversation_history                   │
│    ↓ Enruta a Structure apropiada + contexto               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. STRUCTURE (single_candidate_structure.py, etc.)         │
│    ↓ [NUEVO] Recibe conversation_history                   │
│    ↓ [NUEVO] Puede adaptar comportamiento según contexto   │
│    ↓ Ensambla output context-aware                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 2.2 Componentes Nuevos a Crear

### **Componente 1: ContextResolver**

**Archivo:** `backend/app/services/context_resolver.py`

**Propósito:** Resolver referencias pronominales y entidades del contexto conversacional

```python
class ContextResolver:
    """
    Resuelve referencias en la query actual usando el contexto conversacional.
    
    Ejemplos:
    - "¿Qué red flags tiene?" + contexto con "Juan Pérez" → "¿Qué red flags tiene Juan Pérez?"
    - "estos dos candidatos" + contexto ["Juan", "María"] → "Juan Pérez y María García"
    - "el mejor" + contexto de comparación → nombre del candidato mencionado como mejor
    """
    
    def resolve_references(
        self,
        current_query: str,
        conversation_history: list[dict[str, str]]
    ) -> tuple[str, dict]:
        """
        Returns:
            tuple: (resolved_query, context_metadata)
            
        context_metadata = {
            "referenced_candidates": ["Juan Pérez", "María García"],
            "last_query_type": "comparison",
            "resolution_confidence": 0.95
        }
        """
```

### **Componente 2: SmartContextManager**

**Archivo:** `backend/app/services/smart_context_manager.py`

**Propósito:** Gestión inteligente del tamaño y relevancia del contexto

```python
class SmartContextManager:
    """
    Gestiona el contexto conversacional de forma inteligente:
    - Selección de mensajes relevantes (no siempre los últimos N)
    - Scoring de relevancia basado en la query actual
    - Optimización de tokens
    """
    
    def get_relevant_context(
        self,
        current_query: str,
        full_history: list[dict],
        max_messages: int = 6,
        max_tokens: int = 2000
    ) -> list[dict]:
        """
        Selecciona mensajes más relevantes para la query actual.
        """
```

---

# PARTE 3: PLAN DE IMPLEMENTACIÓN POR FASES

## **FASE 1: Core Integration (CRÍTICO) - 6-8 horas**

### Objetivo
Hacer que el `conversation_history` fluya desde RAG → Orchestrator → Structures

### Tareas

#### ✅ **Tarea 1.1: Actualizar Orchestrator**
**Archivo:** `backend/app/services/output_processor/orchestrator.py`

```python
# CAMBIO EN FIRMA
def process(
    self,
    raw_llm_output: str,
    chunks: List[Dict[str, Any]] = None,
    query: str = "",
    query_type: str = "comparison",
    candidate_name: str = None,
    conversation_history: list[dict[str, str]] = None  # ← NUEVO
) -> tuple[StructuredOutput, str]:
```

**Estimación:** 1 hora

---

#### ✅ **Tarea 1.2: Actualizar TODAS las Structures**

**Archivos a modificar (9 archivos):**
```
structures/single_candidate_structure.py
structures/risk_assessment_structure.py
structures/comparison_structure.py
structures/search_structure.py
structures/ranking_structure.py
structures/job_match_structure.py
structures/team_build_structure.py
structures/verification_structure.py
structures/summary_structure.py
```

**Cambio en cada estructura:**
```python
def assemble(
    self,
    llm_output: str,
    chunks: List[Dict],
    # ... otros parámetros específicos de la estructura ...
    conversation_history: list[dict[str, str]] = None  # ← NUEVO
) -> Dict[str, Any]:
    # Por ahora, solo recibir el parámetro
    # En Fase 3 se usará para lógica context-aware
```

**Estimación:** 2 horas (15-20 min por estructura)

---

#### ✅ **Tarea 1.3: Propagar desde RAG → Orchestrator**

**Archivo:** `backend/app/services/rag_service_v5.py`

**Ubicación:** Línea ~2215 (donde se llama al orchestrator)

```python
# ANTES
structured_output, formatted_answer = orchestrator.process(
    raw_llm_output=ctx.generated_response or "",
    chunks=ctx.effective_chunks,
    query=ctx.question,
    query_type=query_type,
    candidate_name=candidate_name
)

# DESPUÉS
structured_output, formatted_answer = orchestrator.process(
    raw_llm_output=ctx.generated_response or "",
    chunks=ctx.effective_chunks,
    query=ctx.question,
    query_type=query_type,
    candidate_name=candidate_name,
    conversation_history=ctx.conversation_history  # ← NUEVO
)
```

**Estimación:** 30 minutos

---

#### ✅ **Tarea 1.4: Propagar desde Orchestrator → Structures**

**Archivo:** `backend/app/services/output_processor/orchestrator.py`

**Ubicación:** Cada llamada a `structure.assemble()`

```python
# Ejemplo: SingleCandidateStructure
structure_data = self.single_candidate_structure.assemble(
    llm_output=cleaned_llm_output,
    chunks=chunks or [],
    candidate_name=candidate_name,
    cv_id=cv_id,
    conversation_history=conversation_history  # ← NUEVO
)

# Repetir para las 9 estructuras
```

**Estimación:** 2 horas

---

#### ✅ **Tarea 1.5: Testing Fase 1**

**Tests a realizar:**
1. Query simple sin contexto → debe funcionar igual que antes
2. Query con contexto → contexto debe fluir pero no afectar output aún
3. Verificar logs muestran que contexto llega a structures

**Estimación:** 1.5 horas

---

### **Entregables Fase 1**
- [ ] Orchestrator.process() acepta conversation_history
- [ ] Todas las 9 Structures aceptan conversation_history
- [ ] RAG → Orchestrator propagación implementada
- [ ] Orchestrator → Structures propagación implementada
- [ ] Tests básicos pasando
- [ ] Log traces muestran flujo completo del contexto

---

## **FASE 2: Context Resolution (ALTO IMPACTO) - 8-10 horas**

### Objetivo
Resolver referencias pronominales y entidades del contexto antes de procesamiento

### Tareas

#### ✅ **Tarea 2.1: Crear ContextResolver**

**Archivo nuevo:** `backend/app/services/context_resolver.py`

```python
class ContextResolver:
    """Resuelve referencias en queries usando contexto conversacional."""
    
    def __init__(self):
        self.entity_patterns = self._build_entity_patterns()
        self.reference_patterns = self._build_reference_patterns()
    
    def resolve_references(
        self,
        current_query: str,
        conversation_history: list[dict[str, str]]
    ) -> ResolvedQuery:
        """
        Resuelve referencias pronominales y entidades.
        
        Returns:
            ResolvedQuery con:
            - resolved_text: Query expandida
            - referenced_entities: Lista de entidades detectadas
            - confidence: Score de confianza de la resolución
            - original_text: Query original sin modificar
        """
```

**Implementación detallada:**

1. **Extracción de entidades del contexto**
   - Nombres de candidatos mencionados
   - CVs específicos referenciados
   - Criterios de búsqueda previos
   
2. **Detección de referencias en query actual**
   - Pronombres: "él", "ella", "este candidato", "estos dos"
   - Referencias implícitas: "qué red flags tiene" sin nombre
   - Referencias comparativas: "el mejor", "el más senior"

3. **Resolución y expansión**
   - Reemplazar pronombres con entidades
   - Mantener query original si no hay referencias
   - Scoring de confianza

**Estimación:** 4-5 horas

---

#### ✅ **Tarea 2.2: Integrar ContextResolver en RAG Pipeline**

**Archivo:** `backend/app/services/rag_service_v5.py`

**Ubicación:** Después de step_understand_query (línea ~1150)

```python
async def _step_resolve_context(self, ctx: PipelineContextV5):
    """
    NUEVO STEP: Resolver referencias del contexto conversacional.
    
    Debe ejecutarse DESPUÉS de query understanding pero ANTES de retrieval.
    """
    if not ctx.conversation_history:
        ctx.resolved_question = ctx.question
        return
    
    resolver = ContextResolver()
    resolved = resolver.resolve_references(
        current_query=ctx.question,
        conversation_history=ctx.conversation_history
    )
    
    ctx.resolved_question = resolved.resolved_text
    ctx.context_metadata = resolved.metadata
    
    if resolved.resolved_text != ctx.question:
        logger.info(
            f"[CONTEXT] Resolved query: '{ctx.question}' → '{resolved.resolved_text}' "
            f"(confidence: {resolved.confidence:.2f})"
        )
```

**Modificar query_stream():**
```python
# Usar resolved_question en lugar de question para el resto del pipeline
# Líneas ~1600-2000: Reemplazar ctx.question con ctx.resolved_question
```

**Estimación:** 2-3 horas

---

#### ✅ **Tarea 2.3: Añadir PipelineStage.CONTEXT_RESOLUTION**

**Archivo:** `backend/app/services/rag_service_v5.py`

```python
class PipelineStage(str, Enum):
    # ... existing stages ...
    CONTEXT_RESOLUTION = "context_resolution"  # ← NUEVO
```

**Emitir evento SSE:**
```python
yield {
    "event": "step",
    "stage": PipelineStage.CONTEXT_RESOLUTION,
    "status": "completed",
    "data": {
        "original_query": ctx.question,
        "resolved_query": ctx.resolved_question,
        "referenced_entities": ctx.context_metadata.get("entities", []),
        "confidence": ctx.context_metadata.get("confidence", 1.0)
    }
}
```

**Estimación:** 1 hora

---

#### ✅ **Tarea 2.4: Testing Fase 2**

**Tests específicos:**

1. **Test: Referencia simple**
   ```
   Contexto:
   - User: "Dame el perfil de Juan Pérez"
   - Assistant: "[Perfil completo]"
   
   Query actual: "¿Qué red flags tiene?"
   Expected: Resuelto a "¿Qué red flags tiene Juan Pérez?"
   ```

2. **Test: Referencias múltiples**
   ```
   Contexto:
   - User: "Compara Juan y María"
   - Assistant: "[Comparación]"
   
   Query actual: "¿Cuál de estos dos es mejor para Backend?"
   Expected: "¿Cuál de Juan Pérez y María García es mejor para Backend?"
   ```

3. **Test: No hay referencias**
   ```
   Query: "Busca desarrolladores Python"
   Expected: Sin cambios
   ```

4. **Test: Confianza baja**
   ```
   Query ambigua sin contexto suficiente
   Expected: confidence < 0.5, usar query original
   ```

**Estimación:** 2 horas

---

### **Entregables Fase 2**
- [ ] ContextResolver implementado y testeado
- [ ] Integrado en RAG pipeline como nuevo step
- [ ] Referencias pronominales resueltas correctamente
- [ ] SSE events muestran resolución de contexto
- [ ] Test suite con 10+ casos cubriendo escenarios comunes

---

## **FASE 3: Context-Aware Structures (ESPECIALIZACIÓN) - 5-6 horas**

### Objetivo
Las Structures usan el contexto para adaptar su comportamiento

### Tareas

#### ✅ **Tarea 3.1: RiskAssessmentStructure Context-Aware**

**Archivo:** `structures/risk_assessment_structure.py`

**Mejoras con contexto:**

```python
def assemble(
    self,
    llm_output: str,
    chunks: List[Dict],
    candidate_name: str,
    cv_id: str,
    conversation_history: list[dict] = None
) -> Dict[str, Any]:
    # NUEVO: Analizar conversación previa para entender qué preocupaciones
    # tiene el usuario sobre este candidato
    
    if conversation_history:
        concerns = self._extract_user_concerns(conversation_history)
        # Ajustar el enfoque del análisis de riesgos
        # Priorizar factores relacionados con las preocupaciones detectadas
    
    # ... resto del ensamblaje ...

def _extract_user_concerns(self, history: list[dict]) -> list[str]:
    """
    Extrae preocupaciones del usuario del contexto.
    
    Ejemplos:
    - "estabilidad" mencionada → priorizar job hopping analysis
    - "experiencia técnica" → enfocarse en skill gaps
    - "liderazgo" → enfocarse en progression pattern
    """
```

**Estimación:** 1.5 horas

---

#### ✅ **Tarea 3.2: ComparisonStructure con Memoria**

**Archivo:** `structures/comparison_structure.py`

**Mejoras con contexto:**

```python
def assemble(
    self,
    llm_output: str,
    chunks: List[Dict],
    conversation_history: list[dict] = None
) -> Dict[str, Any]:
    # NUEVO: Detectar si esta comparación es continuación de otra
    
    if conversation_history:
        previous_comparisons = self._extract_previous_comparisons(history)
        
        if previous_comparisons:
            # Mantener los mismos criterios de comparación
            # O expandir la comparación con nuevos candidatos
            criteria = previous_comparisons[-1]["criteria"]
```

**Estimación:** 1.5 horas

---

#### ✅ **Tarea 3.3: SearchStructure Context-Aware**

**Archivo:** `structures/search_structure.py`

**Mejoras con contexto:**

```python
def assemble(
    self,
    llm_output: str,
    chunks: List[Dict],
    query: str,
    conversation_history: list[dict] = None
) -> Dict[str, Any]:
    # NUEVO: Detectar si búsqueda es refinamiento de búsqueda anterior
    
    if conversation_history:
        previous_search = self._extract_last_search(history)
        
        if previous_search and self._is_refinement(query, previous_search):
            # Marcar como "Refined search from previous query"
            # Mostrar qué cambió
```

**Estimación:** 1.5 horas

---

#### ✅ **Tarea 3.4: Testing Fase 3**

**Tests de comportamiento context-aware:**

1. **RiskAssessment**: Usuario menciona "estabilidad" → análisis prioriza job hopping
2. **Comparison**: Comparación iterativa mantiene criterios
3. **Search**: Refinamiento de búsqueda detectado correctamente

**Estimación:** 1.5 horas

---

### **Entregables Fase 3**
- [ ] RiskAssessmentStructure usa contexto para priorizar análisis
- [ ] ComparisonStructure mantiene criterios entre comparaciones
- [ ] SearchStructure detecta refinamientos
- [ ] Comportamiento context-aware documentado
- [ ] Tests verifican adaptación según contexto

---

## **FASE 4: Smart Context Management (OPTIMIZACIÓN) - 4-5 horas**

### Objetivo
Optimizar qué mensajes del contexto se incluyen basándose en relevancia

### Tareas

#### ✅ **Tarea 4.1: Crear SmartContextManager**

**Archivo nuevo:** `backend/app/services/smart_context_manager.py`

```python
class SmartContextManager:
    """
    Gestiona el contexto conversacional de forma inteligente.
    
    NO siempre usa los últimos N mensajes - selecciona los más RELEVANTES.
    """
    
    def __init__(self):
        self.max_context_tokens = 2000
        self.default_message_limit = 6
    
    def get_relevant_context(
        self,
        current_query: str,
        full_history: list[dict],
        max_messages: int = None,
        max_tokens: int = None
    ) -> ContextSelection:
        """
        Selecciona mensajes más relevantes.
        
        Algoritmo:
        1. Calcular relevance score para cada mensaje
        2. Siempre incluir último mensaje (contexto inmediato)
        3. Seleccionar top N por score dentro del límite de tokens
        
        Returns:
            ContextSelection con:
            - selected_messages: Lista de mensajes seleccionados
            - relevance_scores: Score de cada mensaje
            - total_tokens: Tokens estimados
            - selection_reason: Por qué se seleccionaron estos mensajes
        """
    
    def _calculate_relevance_score(
        self,
        current_query: str,
        message: dict
    ) -> float:
        """
        Score de relevancia (0.0 - 1.0).
        
        Factores:
        - Overlap de entidades (nombres de candidatos mencionados)
        - Similitud semántica con query actual
        - Distancia temporal (recency)
        - Tipo de mensaje (user queries score más alto)
        """
```

**Estimación:** 2-3 horas

---

#### ✅ **Tarea 4.2: Integrar SmartContextManager**

**Archivo:** `backend/app/api/routes_sessions_stream.py`

```python
# ANTES (línea ~111)
history = mgr.get_conversation_history(session_id, limit=6)

# DESPUÉS
from app.services.smart_context_manager import SmartContextManager

full_history = mgr.get_conversation_history(session_id, limit=20)  # Más mensajes
context_manager = SmartContextManager()

context_selection = context_manager.get_relevant_context(
    current_query=request.message,
    full_history=full_history,
    max_messages=6,
    max_tokens=2000
)

conversation_history = context_selection.selected_messages

logger.info(
    f"[STREAM] Selected {len(conversation_history)} most relevant messages "
    f"(reason: {context_selection.selection_reason})"
)
```

**Estimación:** 1 hora

---

#### ✅ **Tarea 4.3: Testing y Métricas**

**Tests:**
1. Query sobre candidato mencionado 5 mensajes atrás → ese mensaje incluido
2. Query nueva sin relación → solo últimos 2-3 mensajes
3. Comparación larga → mensajes de comparación previa incluidos

**Métricas a añadir:**
- Promedio de mensajes seleccionados por query
- Tokens ahorrados vs. selección "dumb" (últimos N)
- Precisión de la selección (manual review)

**Estimación:** 1.5 horas

---

### **Entregables Fase 4**
- [ ] SmartContextManager implementado
- [ ] Integrado en endpoint de streaming
- [ ] Selección inteligente funcionando
- [ ] Métricas de uso de contexto implementadas
- [ ] Ahorro de tokens documentado

---

## **FASE 5: Tooling & Observability (DEBUGGING) - 3-4 horas**

### Objetivo
Herramientas para debugging y observación del sistema de contexto

### Tareas

#### ✅ **Tarea 5.1: Debug Endpoint**

**Archivo:** `backend/app/api/routes_sessions.py`

```python
@router.get("/{session_id}/context-debug")
async def debug_conversation_context(
    session_id: str,
    mode: Mode = Query(default=settings.default_mode)
):
    """
    Endpoint para visualizar el estado del contexto conversacional.
    
    Útil para:
    - Ver qué mensajes están en la ventana de contexto
    - Debugging de resolución de referencias
    - Análisis de relevancia de mensajes
    """
    mgr = get_session_manager(mode)
    full_history = mgr.get_conversation_history(session_id, limit=50)
    
    # Si hay un SmartContextManager, simular selección
    from app.services.smart_context_manager import SmartContextManager
    context_mgr = SmartContextManager()
    
    # Analizar cada mensaje
    analyzed_messages = []
    for i, msg in enumerate(full_history):
        analyzed_messages.append({
            "index": i,
            "role": msg.role if hasattr(msg, 'role') else msg.get('role'),
            "content_preview": msg.content[:100] if hasattr(msg, 'content') else msg.get('content', '')[:100],
            "timestamp": msg.timestamp if hasattr(msg, 'timestamp') else msg.get('timestamp'),
            "in_default_window": i >= len(full_history) - 6,
            "tokens_estimated": len(msg.content.split()) * 1.3 if hasattr(msg, 'content') else 0
        })
    
    return {
        "session_id": session_id,
        "total_messages": len(full_history),
        "default_context_window": 6,
        "messages": analyzed_messages,
        "context_status": {
            "has_recent_context": len(full_history) > 0,
            "context_window_full": len(full_history) >= 6,
            "total_tokens_in_window": sum(m["tokens_estimated"] for m in analyzed_messages[-6:])
        }
    }
```

**Estimación:** 1.5 horas

---

#### ✅ **Tarea 5.2: Enhanced Logging**

**Archivo:** `backend/app/utils/debug_logger.py`

```python
def log_context_resolution(
    original_query: str,
    resolved_query: str,
    referenced_entities: list[str],
    confidence: float,
    conversation_history: list[dict]
):
    """Log completo de resolución de contexto."""
    
def log_context_selection(
    current_query: str,
    full_history_count: int,
    selected_count: int,
    selection_reason: str,
    relevance_scores: dict
):
    """Log de selección inteligente de contexto."""
```

**Estimación:** 1 hora

---

#### ✅ **Tarea 5.3: Frontend Context Indicator (Opcional)**

**Archivo:** `frontend/src/components/chat/MessageInput.jsx`

Añadir indicador visual cuando hay contexto activo:

```jsx
{conversationHistory.length > 0 && (
  <div className="context-indicator">
    💬 {conversationHistory.length} messages in context
  </div>
)}
```

**Estimación:** 1 hora (opcional)

---

### **Entregables Fase 5**
- [ ] Debug endpoint funcionando
- [ ] Logging mejorado con detalles de contexto
- [ ] Documentación de endpoints de debugging
- [ ] (Opcional) Indicador visual en frontend

---

# PARTE 4: TESTING & VALIDATION

## 4.1 Test Suite Completo

### **Test Suite 1: Flujo Básico**
```python
def test_context_flows_through_pipeline():
    """Contexto fluye de endpoint → RAG → Orchestrator → Structure"""
    
def test_context_preserved_in_structures():
    """Structures reciben conversation_history intacto"""
```

### **Test Suite 2: Context Resolution**
```python
def test_pronoun_resolution():
    """'él' se resuelve a nombre del candidato"""
    
def test_multiple_entity_resolution():
    """'estos dos' se resuelve a nombres correctos"""
    
def test_no_context_fallback():
    """Sin contexto, funciona normalmente"""
```

### **Test Suite 3: Context-Aware Behavior**
```python
def test_risk_assessment_adapts_to_concerns():
    """RiskAssessment prioriza según preocupaciones previas"""
    
def test_comparison_maintains_criteria():
    """ComparisonStructure mantiene criterios entre queries"""
```

### **Test Suite 4: Smart Context**
```python
def test_relevant_message_selection():
    """SmartContextManager selecciona mensajes relevantes"""
    
def test_token_limit_respected():
    """No excede límite de tokens configurado"""
```

**Estimación Total Testing:** 4-5 horas

---

## 4.2 Casos de Uso Reales

### **Caso 1: Análisis iterativo de candidato**
```
Usuario: "Dame el perfil de Juan Pérez"
→ SingleCandidateStructure

Usuario: "¿Qué red flags tiene?"
→ RiskAssessmentStructure con context
→ ✅ Sabe que es Juan Pérez

Usuario: "¿Cómo se compara con María García?"
→ ComparisonStructure con context
→ ✅ Sabe que comparar Juan vs María
```

### **Caso 2: Búsqueda y refinamiento**
```
Usuario: "Busca desarrolladores Frontend"
→ SearchStructure

Usuario: "¿Cuál tiene más experiencia con React?"
→ SearchStructure con context
→ ✅ Sabe que filtrar dentro de resultados previos
```

### **Caso 3: Comparaciones iterativas**
```
Usuario: "Compara Juan y María para Backend"
→ ComparisonStructure con criterio "Backend"

Usuario: "¿Y para Frontend?"
→ ComparisonStructure con context
→ ✅ Mantiene candidatos, cambia criterio
```

---

# PARTE 5: MÉTRICAS Y MONITOREO

## 5.1 Métricas a Implementar

### **Context Usage Metrics**
```python
{
  "context_usage": {
    "queries_with_context": 156,
    "queries_without_context": 23,
    "avg_messages_in_context": 4.2,
    "avg_context_tokens": 847,
    "context_resolution_rate": 0.73  # % queries con referencias resueltas
  }
}
```

### **Resolution Metrics**
```python
{
  "resolution_metrics": {
    "references_detected": 89,
    "references_resolved": 81,
    "avg_confidence": 0.87,
    "low_confidence_count": 8  # confidence < 0.5
  }
}
```

### **Performance Metrics**
```python
{
  "performance": {
    "context_resolution_ms": 45,
    "context_selection_ms": 23,
    "total_overhead_ms": 68
  }
}
```

---

# PARTE 6: CRONOGRAMA Y RECURSOS

## 6.1 Estimación Total

| Fase | Tiempo | Prioridad | Dependencias |
|------|--------|-----------|--------------|
| Fase 1: Core Integration | 6-8 horas | 🔴 CRÍTICO | Ninguna |
| Fase 2: Context Resolution | 8-10 horas | 🟠 ALTO | Fase 1 |
| Fase 3: Context-Aware Structures | 5-6 horas | 🟡 MEDIO | Fase 1, 2 |
| Fase 4: Smart Context | 4-5 horas | 🟢 BAJO | Fase 1 |
| Fase 5: Tooling | 3-4 horas | 🟢 BAJO | Ninguna (paralelo) |
| Testing | 4-5 horas | 🔴 CRÍTICO | Todas |

**Total:** 30-38 horas

---

## 6.2 Cronograma Recomendado

### **Sprint 1 (1 semana):** Foundation
- Día 1-2: Fase 1 (Core Integration)
- Día 3-4: Fase 2 (Context Resolution)
- Día 5: Testing Fase 1 y 2

### **Sprint 2 (1 semana):** Enhancement
- Día 1-2: Fase 3 (Context-Aware Structures)
- Día 3: Fase 4 (Smart Context)
- Día 4-5: Fase 5 (Tooling) + Testing final

---

## 6.3 Rollout Plan

### **Stage 1: Internal Testing**
- Activar en modo local solamente
- Testing manual exhaustivo
- Recolección de métricas

### **Stage 2: Beta**
- Feature flag: `ENABLE_SMART_CONTEXT`
- Activar para 20% de queries
- Comparar con baseline (sin contexto)

### **Stage 3: Full Rollout**
- Si métricas positivas → 100%
- Monitoreo continuo
- Ajustes según feedback

---

# PARTE 7: RIESGOS Y MITIGACIÓN

## 7.1 Riesgos Identificados

### **Riesgo 1: Context Resolution Incorrecta**
**Impacto:** ALTO - Query mal resuelta → respuesta incorrecta

**Mitigación:**
- Threshold de confidence (min 0.7)
- Fallback a query original si confidence baja
- Logging exhaustivo para debugging

---

### **Riesgo 2: Token Budget Overflow**
**Impacto:** MEDIO - Contexto muy largo → costos altos / errors

**Mitigación:**
- Hard limit de tokens (2000)
- Smart context selection para optimizar
- Monitoring de token usage

---

### **Riesgo 3: Breaking Changes en Structures**
**Impacto:** ALTO - 9 estructuras a modificar

**Mitigación:**
- Cambios backward-compatible (parámetro opcional)
- Tests para cada estructura antes/después
- Rollout gradual

---

### **Riesgo 4: Performance Degradation**
**Impacto:** MEDIO - Context resolution añade latencia

**Mitigación:**
- Async processing donde posible
- Caching de entity extraction
- Target: <100ms overhead máximo

---

# PARTE 8: CRITERIOS DE ÉXITO

## 8.1 Métricas de Éxito

### **Funcionalidad**
- [ ] ✅ 100% de queries con contexto fluyen correctamente
- [ ] ✅ Referencias resueltas con >85% accuracy
- [ ] ✅ 0 breaking changes en funcionalidad existente

### **Performance**
- [ ] ✅ Overhead de contexto <100ms por query
- [ ] ✅ Uso de tokens optimizado (ahorro >30% vs baseline)

### **User Experience**
- [ ] ✅ Usuarios pueden hacer seguimiento de queries sin repetir contexto
- [ ] ✅ Respuestas mantienen coherencia conversacional
- [ ] ✅ 0 casos donde contexto cause confusión

### **Code Quality**
- [ ] ✅ 90%+ test coverage en nuevos componentes
- [ ] ✅ Logging completo para debugging
- [ ] ✅ Documentación actualizada

---

# PARTE 9: DOCUMENTACIÓN

## 9.1 Documentos a Crear/Actualizar

### **Nuevos Documentos**
1. `docs/CONTEXT_RESOLUTION_GUIDE.md` - Cómo funciona la resolución
2. `docs/SMART_CONTEXT_ALGORITHM.md` - Algoritmo de selección
3. `docs/CONTEXT_DEBUGGING.md` - Guía de debugging

### **Documentos a Actualizar**
1. `docs/CONVERSATIONAL_CONTEXT.md` - Añadir nueva arquitectura
2. `docs/ARCHITECTURE_MODULES.md` - Añadir ContextResolver
3. `README.md` - Mencionar capacidad de contexto

---

# CONCLUSIÓN

Este plan integra completamente el sistema de contexto conversacional con la arquitectura STRUCTURES/MODULES/ORCHESTRATOR, resolviendo la desconexión actual y habilitando verdaderas conversaciones iterativas context-aware.

**Próximo paso:** Comenzar con Fase 1 (Core Integration) para establecer la base.
