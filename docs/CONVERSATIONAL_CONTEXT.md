# Conversational Context System

> **Status: ✅ IMPLEMENTED** | Version 9.0 | January 2026

## Summary

The **conversational context** system is fully implemented and propagated through the entire pipeline:

```
Endpoint → RAG Service → Orchestrator → Structures → Modules
                    ↓
            conversation_history: List[Dict[str, str]]
```

### Current Capabilities
- ✅ `conversation_history` flows through the entire system
- ✅ All 9 Structures receive conversational context
- ✅ Pronominal references ("this candidate", "he", "she")
- ✅ Follow-up queries maintain context

### Known Limitations
- ⚠️ Context limited to last N messages (for cost control)
- ⚠️ No advanced semantic pronoun resolution (roadmap)

---

## Implementation Architecture

### 1. Database
**Status:** ✅ Already ready

The `session_messages` table already stores everything needed:
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
**Files:** 
- `backend/app/models/sessions.py` (Local)
- `backend/app/providers/cloud/sessions.py` (Cloud/Supabase)

**New method:**
```python
def get_conversation_history(
    self, 
    session_id: str, 
    limit: int = 6  # 3 turns (user + assistant)
) -> List[ChatMessage]:
    """
    Retrieves the last N messages for conversational context.
    
    Args:
        session_id: Session ID
        limit: Number of messages to retrieve (default 6 = 3 turns)
    
    Returns:
        List of messages ordered from oldest to most recent
    """
```

### 3. RAGServiceV5
**File:** `backend/app/services/rag_service_v5.py`

**Modifications:**

#### a) PipelineContextV5
Add field for history:
```python
@dataclass
class PipelineContextV5:
    question: str
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    # format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    # ...rest of fields
```

#### b) query_stream Method
Accept history parameter:
```python
async def query_stream(
    self,
    question: str,
    conversation_history: List[Dict[str, str]] | None = None,
    session_id: str | None = None,
    # ...rest of parameters
):
    ctx = PipelineContextV5(
        question=question,
        conversation_history=conversation_history or [],
        # ...
    )
```

### 4. Prompt Builder
**File:** `backend/app/prompts/templates.py`

**Generation prompt modification:**
```python
def build_generation_prompt(
    self,
    question: str,
    context: str,
    conversation_history: List[Dict[str, str]] = None,
    # ...
) -> str:
    # Build history section if it exists
    history_section = ""
    if conversation_history:
        history_section = "\n## Previous Conversation\n"
        for msg in conversation_history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            history_section += f"{role_label}: {msg['content']}\n"
        history_section += "\n"
    
    prompt = f"""
{history_section}
## Current Question
{question}

## Relevant CV Context
{context}

Generate a response based on the CVs and considering the previous conversation...
"""
```

### 5. Endpoints
**File:** `backend/app/api/routes_sessions_stream.py`

**Modification in chat_stream:**
```python
@router.post("/{session_id}/chat-stream")
async def chat_stream(
    session_id: str,
    request: ChatStreamRequest,
    mode: Mode = Query(default=settings.default_mode)
):
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    
    # NEW: Retrieve conversational history
    history = mgr.get_conversation_history(session_id, limit=6)
    
    # Convert to simple format for RAG
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in history
    ]
    
    # Save user message
    mgr.add_message(session_id, "user", request.message)
    
    # Create generator with history
    return StreamingResponse(
        event_generator(
            rag_service, 
            request.message, 
            session_id, 
            cv_ids, 
            total_cvs, 
            mgr,
            conversation_history  # NEW parameter
        ),
        media_type="text/event-stream",
        ...
    )
```

**Modification in event_generator:**
```python
async def event_generator(
    rag_service, 
    question: str, 
    session_id: str, 
    cv_ids: list, 
    total_cvs: int, 
    mgr,
    conversation_history: list = None  # NEW
):
    async for event in rag_service.query_stream(
        question=question,
        conversation_history=conversation_history,  # NEW
        session_id=session_id,
        cv_ids=cv_ids,
        total_cvs_in_session=total_cvs
    ):
        # ...
```

### 6. Frontend (Optional)
**File:** `frontend/src/components/SessionChat.jsx` (or similar)

The frontend **does not need changes** because:
- It already sends messages to the endpoint
- The endpoint handles history automatically
- The frontend only displays responses

---

## Configuration

### Number of Messages in Context

**Recommendation:** 4-6 messages (2-3 turns)

```python
# In config.py or as parameter
CONTEXT_HISTORY_LIMIT = 6  # 3 turns (user + assistant)
```

**Reasons:**
- ✅ Sufficient for immediate references
- ✅ Control of tokens sent to LLM
- ✅ Reduces API costs
- ✅ Avoids confusion with very old context

### Token Optimization

To optimize token usage:

1. **Content only, no sources:**
```python
conversation_history = [
    {"role": msg.role, "content": msg.content}
    # Don't include sources, pipeline_steps, etc.
]
```

2. **Truncate very long messages:**
```python
MAX_MESSAGE_LENGTH = 500  # characters
content = msg.content[:MAX_MESSAGE_LENGTH]
```

3. **Include only recent messages:**
```python
# Last 6 messages = 3 turns
history = mgr.get_conversation_history(session_id, limit=6)
```

---

## Complete Flow

```
1. User sends message
   ↓
2. Backend retrieves last 6 messages from session
   ↓
3. Converts to simple format [{"role": "user", "content": "..."}]
   ↓
4. Saves new user message
   ↓
5. Passes history + current question to RAG Service
   ↓
6. RAG Service includes history in generation prompt
   ↓
7. LLM generates response considering context
   ↓
8. Backend saves assistant response
   ↓
9. Frontend displays response
```

---

## Prompt Example with Context

```
## Previous Conversation
User: Who is the best candidate for Frontend?
Assistant: Juan Pérez is the best candidate for Frontend because he has 5 years of experience in React...

## Current Question
Tell me the problems with this candidate

## Relevant CV Context
[CV chunks for Juan Pérez...]

Generate a response based on the CVs and considering the previous conversation.
The user asks about "this candidate", referring to Juan Pérez mentioned earlier.
```

---

## Testing

### Test Case 1: Candidate Reference
```
User: "Who is the best for Backend?"
System: "María García..."
User: "How many years of experience does she have?"
System: ✅ "María García has 7 years of experience..."
```

### Test Case 2: Follow-up
```
User: "Compare Frontend candidates"
System: "Juan: React, Ana: Vue..."
User: "Which is better for an enterprise project?"
System: ✅ "Between Juan and Ana, Juan is better because..."
```

### Test Case 3: Limited Context
```
[8 previous messages]
User: "New question about Backend"
System: ✅ Only considers last 6 messages
```

---

## Future Improvements (Optional)

### 1. Conversation Summary
For very long conversations, summarize the history:
```python
if len(all_messages) > 20:
    summary = llm.summarize(all_messages[:-6])
    context = summary + recent_messages
```

### 2. Topic Change Detection
If user changes topic, clear context:
```python
if topic_changed(new_question, conversation_history):
    conversation_history = []
```

### 3. Message Embeddings
Search for relevant messages by semantic similarity:
```python
relevant_messages = search_similar_messages(
    question, 
    all_messages, 
    k=6
)
```

---

## Implementation Status

| Component | Status | File |
|-----------|--------|------|
| SessionManager.get_conversation_history() | ✅ Implemented | `sessions.py` |
| RAGServiceV5 conversation_history param | ✅ Implemented | `rag_service_v5.py` |
| Orchestrator conversation_history param | ✅ Implemented | `orchestrator.py` |
| All Structures with param | ✅ Implemented | `structures/*.py` |
| Endpoints with history | ✅ Implemented | `routes_sessions_stream.py` |

---

## Propagation in Structures (v6.0)

All 9 Structures now receive `conversation_history`:

```python
# Example: JobMatchStructure.assemble()
def assemble(
    self,
    llm_output: str,
    chunks: List[Dict[str, Any]],
    query: str = "",
    job_description: str = "",
    conversation_history: List[Dict[str, str]] = None  # ← IMPLEMENTED
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

## Roadmap: Future Improvements

### Phase 1: Context Resolution ✅ IMPLEMENTED
- [x] `ContextResolver` for automatic pronominal reference resolution (`context_resolver.py` - 18KB)
- [x] Detect "he", "she", "this candidate" and resolve to actual name
- [x] Top candidate references ("the best one", "#1", "el mejor")
- [x] Ordinal references ("the second one", "compare those 3")

### Phase 2: Context-Aware Structures (Pending)
- [ ] Structures adapt behavior based on history
- [ ] Comparison maintains criteria between queries
- [ ] RiskAssessment prioritizes based on previous concerns

### Phase 3: Smart Context Management (Pending)
- [ ] Intelligent selection of relevant messages
- [ ] Relevance scoring per query
