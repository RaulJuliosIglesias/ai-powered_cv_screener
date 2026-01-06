# Sistema de Contexto Conversacional

> **Estado: ✅ IMPLEMENTADO** | Versión 6.0 | Enero 2026

## Resumen

El sistema de **contexto conversacional** está completamente implementado y propagado a través de todo el pipeline:

```
Endpoint → RAG Service → Orchestrator → Structures → Modules
                    ↓
            conversation_history: List[Dict[str, str]]
```

### Capacidades Actuales
- ✅ `conversation_history` fluye a través de todo el sistema
- ✅ Todas las 9 Structures reciben contexto conversacional
- ✅ Referencias pronominales ("este candidato", "él", "ella")
- ✅ Follow-up queries mantienen contexto

### Limitaciones Conocidas
- ⚠️ Contexto limitado a últimos N mensajes (por costos)
- ⚠️ No hay resolución semántica avanzada de pronombres (roadmap)

---

## Arquitectura de Implementación

### 1. Base de Datos
**Estado:** ✅ Ya está lista

La tabla `session_messages` ya guarda todo lo necesario:
```sql
CREATE TABLE session_messages (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    role TEXT CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]',
    pipeline_steps JSONB DEFAULT '[]',
    structured_output JSONB DEFAULT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. SessionManager (Backend)
**Archivos:** 
- `backend/app/models/sessions.py` (Local)
- `backend/app/providers/cloud/sessions.py` (Cloud/Supabase)

**Nuevo método:**
```python
def get_conversation_history(
    self, 
    session_id: str, 
    limit: int = 6  # 3 turnos (user + assistant)
) -> List[ChatMessage]:
    """
    Recupera los últimos N mensajes para contexto conversacional.
    
    Args:
        session_id: ID de la sesión
        limit: Número de mensajes a recuperar (por defecto 6 = 3 turnos)
    
    Returns:
        Lista de mensajes ordenados del más antiguo al más reciente
    """
```

### 3. RAGServiceV5
**Archivo:** `backend/app/services/rag_service_v5.py`

**Modificaciones:**

#### a) PipelineContextV5
Añadir campo para historial:
```python
@dataclass
class PipelineContextV5:
    question: str
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    # formato: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    # ...resto de campos
```

#### b) Método query_stream
Aceptar parámetro de historial:
```python
async def query_stream(
    self,
    question: str,
    conversation_history: List[Dict[str, str]] | None = None,
    session_id: str | None = None,
    # ...resto de parámetros
):
    ctx = PipelineContextV5(
        question=question,
        conversation_history=conversation_history or [],
        # ...
    )
```

### 4. Prompt Builder
**Archivo:** `backend/app/prompts/templates.py`

**Modificación del prompt de generación:**
```python
def build_generation_prompt(
    self,
    question: str,
    context: str,
    conversation_history: List[Dict[str, str]] = None,
    # ...
) -> str:
    # Construir sección de historial si existe
    history_section = ""
    if conversation_history:
        history_section = "\n## Conversación Previa\n"
        for msg in conversation_history:
            role_label = "Usuario" if msg["role"] == "user" else "Asistente"
            history_section += f"{role_label}: {msg['content']}\n"
        history_section += "\n"
    
    prompt = f"""
{history_section}
## Pregunta Actual
{question}

## Contexto de CVs Relevantes
{context}

Genera una respuesta basada en los CVs y considerando la conversación previa...
"""
```

### 5. Endpoints
**Archivo:** `backend/app/api/routes_sessions_stream.py`

**Modificación en chat_stream:**
```python
@router.post("/{session_id}/chat-stream")
async def chat_stream(
    session_id: str,
    request: ChatStreamRequest,
    mode: Mode = Query(default=settings.default_mode)
):
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    
    # NUEVO: Recuperar historial conversacional
    history = mgr.get_conversation_history(session_id, limit=6)
    
    # Convertir a formato simple para el RAG
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in history
    ]
    
    # Guardar mensaje del usuario
    mgr.add_message(session_id, "user", request.message)
    
    # Crear generador con historial
    return StreamingResponse(
        event_generator(
            rag_service, 
            request.message, 
            session_id, 
            cv_ids, 
            total_cvs, 
            mgr,
            conversation_history  # NUEVO parámetro
        ),
        media_type="text/event-stream",
        ...
    )
```

**Modificación en event_generator:**
```python
async def event_generator(
    rag_service, 
    question: str, 
    session_id: str, 
    cv_ids: list, 
    total_cvs: int, 
    mgr,
    conversation_history: list = None  # NUEVO
):
    async for event in rag_service.query_stream(
        question=question,
        conversation_history=conversation_history,  # NUEVO
        session_id=session_id,
        cv_ids=cv_ids,
        total_cvs_in_session=total_cvs
    ):
        # ...
```

### 6. Frontend (Opcional)
**Archivo:** `frontend/src/components/SessionChat.jsx` (o similar)

El frontend **no necesita cambios** porque:
- Ya envía mensajes al endpoint
- El endpoint maneja el historial automáticamente
- El frontend solo muestra las respuestas

---

## Configuración

### Número de Mensajes en Contexto

**Recomendación:** 4-6 mensajes (2-3 turnos)

```python
# En config.py o como parámetro
CONTEXT_HISTORY_LIMIT = 6  # 3 turnos (user + assistant)
```

**Razones:**
- ✅ Suficiente para referencias inmediatas
- ✅ Control de tokens enviados al LLM
- ✅ Reduce costos de API
- ✅ Evita confusión con contexto muy antiguo

### Optimización de Tokens

Para optimizar el uso de tokens:

1. **Solo contenido, sin fuentes:**
```python
conversation_history = [
    {"role": msg.role, "content": msg.content}
    # No incluir sources, pipeline_steps, etc.
]
```

2. **Truncar mensajes muy largos:**
```python
MAX_MESSAGE_LENGTH = 500  # caracteres
content = msg.content[:MAX_MESSAGE_LENGTH]
```

3. **Incluir solo mensajes recientes:**
```python
# Últimos 6 mensajes = 3 turnos
history = mgr.get_conversation_history(session_id, limit=6)
```

---

## Flujo Completo

```
1. Usuario envía mensaje
   ↓
2. Backend recupera últimos 6 mensajes de la sesión
   ↓
3. Convierte a formato simple [{"role": "user", "content": "..."}]
   ↓
4. Guarda nuevo mensaje de usuario
   ↓
5. Pasa historial + pregunta actual al RAG Service
   ↓
6. RAG Service incluye historial en el prompt de generación
   ↓
7. LLM genera respuesta considerando contexto
   ↓
8. Backend guarda respuesta del assistant
   ↓
9. Frontend muestra respuesta
```

---

## Ejemplo de Prompt con Contexto

```
## Conversación Previa
Usuario: ¿Cuál es el mejor candidato para Frontend?
Asistente: Juan Pérez es el mejor candidato para Frontend porque tiene 5 años de experiencia en React...

## Pregunta Actual
Dime los problemas con este candidato

## Contexto de CVs Relevantes
[CV chunks de Juan Pérez...]

Genera una respuesta basada en los CVs y considerando la conversación previa.
El usuario pregunta sobre "este candidato", refiriéndose a Juan Pérez mencionado anteriormente.
```

---

## Testing

### Caso de Prueba 1: Referencia al Candidato
```
Usuario: "¿Quién es el mejor para Backend?"
Sistema: "María García..."
Usuario: "¿Cuántos años de experiencia tiene?"
Sistema: ✅ "María García tiene 7 años de experiencia..."
```

### Caso de Prueba 2: Follow-up
```
Usuario: "Compara candidatos de Frontend"
Sistema: "Juan: React, Ana: Vue..."
Usuario: "¿Cuál es mejor para un proyecto enterprise?"
Sistema: ✅ "Entre Juan y Ana, Juan es mejor porque..."
```

### Caso de Prueba 3: Contexto Limitado
```
[8 mensajes previos]
Usuario: "Nueva pregunta sobre Backend"
Sistema: ✅ Solo considera últimos 6 mensajes
```

---

## Mejoras Futuras (Opcional)

### 1. Resumen de Conversación
Para conversaciones muy largas, resumir el historial:
```python
if len(all_messages) > 20:
    summary = llm.summarize(all_messages[:-6])
    context = summary + recent_messages
```

### 2. Detección de Cambio de Tema
Si el usuario cambia de tema, limpiar contexto:
```python
if topic_changed(new_question, conversation_history):
    conversation_history = []
```

### 3. Embeddings de Mensajes
Buscar mensajes relevantes por similitud semántica:
```python
relevant_messages = search_similar_messages(
    question, 
    all_messages, 
    k=6
)
```

---

## Estado de Implementación

| Componente | Estado | Archivo |
|------------|--------|---------|
| SessionManager.get_conversation_history() | ✅ Implementado | `sessions.py` |
| RAGServiceV5 conversation_history param | ✅ Implementado | `rag_service_v5.py` |
| Orchestrator conversation_history param | ✅ Implementado | `orchestrator.py` |
| Todas las Structures con param | ✅ Implementado | `structures/*.py` |
| Endpoints con historial | ✅ Implementado | `routes_sessions_stream.py` |

---

## Propagación en Structures (v6.0)

Todas las 9 Structures ahora reciben `conversation_history`:

```python
# Ejemplo: JobMatchStructure.assemble()
def assemble(
    self,
    llm_output: str,
    chunks: List[Dict[str, Any]],
    query: str = "",
    job_description: str = "",
    conversation_history: List[Dict[str, str]] = None  # ← IMPLEMENTADO
) -> Dict[str, Any]:
```

| Structure | conversation_history |
|-----------|---------------------|
| SingleCandidateStructure | ✅ |
| RiskAssessmentStructure | ✅ |
| ComparisonStructure | ✅ |
| SearchStructure | ✅ |
| RankingStructure | ✅ |
| JobMatchStructure | ✅ |
| TeamBuildStructure | ✅ |
| VerificationStructure | ✅ |
| SummaryStructure | ✅ |

---

## Roadmap: Mejoras Futuras

### Fase 1: Context Resolution (Pendiente)
- [ ] `ContextResolver` para resolver referencias pronominales automáticamente
- [ ] Detectar "él", "ella", "este candidato" y resolver a nombre real

### Fase 2: Context-Aware Structures (Pendiente)
- [ ] Structures adaptan comportamiento según historial
- [ ] Comparison mantiene criterios entre queries
- [ ] RiskAssessment prioriza según preocupaciones previas

### Fase 3: Smart Context Management (Pendiente)
- [ ] Selección inteligente de mensajes relevantes
- [ ] Scoring de relevancia por query
