# Plan de Implementación: Sistema Modular de Output

## Objetivo
Crear un sistema de output completamente modular donde cada componente es independiente y no puede romper otros componentes. El sistema debe garantizar que la tabla, conclusión, razonamiento y pipeline steps funcionen siempre, independientemente de lo que el LLM genere.

---

## Arquitectura Propuesta

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG PIPELINE (Backend)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Query Understanding  →  [PipelineStep]                 │
│  2. Retrieval           →  [PipelineStep]                  │
│  3. Reasoning           →  [PipelineStep]                  │
│  4. Generation          →  [PipelineStep] + Raw LLM Output │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              OUTPUT PROCESSOR (Modular)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  OutputProcessor                                            │
│    ├─ ThinkingExtractor     → :::thinking::: block         │
│    ├─ ConclusionExtractor   → :::conclusion::: block       │
│    ├─ TableParser           → Markdown table → HTML        │
│    ├─ DirectAnswerExtractor → First paragraph              │
│    ├─ CVReferenceFormatter  → **[Name](cv:cv_xxx)**        │
│    └─ FallbackGenerator     → Si falla LLM, genera default │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  STRUCTURED OUTPUT                           │
├─────────────────────────────────────────────────────────────┤
│  {                                                          │
│    pipeline_steps: [...],      // Siempre existe           │
│    thinking: "...",            // null si no existe        │
│    direct_answer: "...",       // Extraído o generado      │
│    table_data: {               // Parseado o null          │
│      headers: [...],                                        │
│      rows: [...]                                            │
│    },                                                       │
│    conclusion: "...",          // Extraído o generado      │
│    raw_content: "..."          // Para debugging           │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                FRONTEND RENDERER (React)                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Message Component                                          │
│    ├─ PipelineStepsPanel    (pipeline_steps)              │
│    ├─ ThinkingPanel         (thinking)                     │
│    ├─ DirectAnswerSection   (direct_answer)               │
│    ├─ TableComponent        (table_data)                   │
│    └─ ConclusionPanel       (conclusion)                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Componentes a Crear

### 1. Backend: OutputProcessor (Nuevo archivo)

**Archivo:** `backend/app/services/output_processor.py`

```python
class OutputProcessor:
    """
    Procesa el output del LLM en componentes estructurados.
    Cada método es independiente y tiene fallbacks.
    """
    
    def process(self, raw_llm_output: str, chunks: list) -> StructuredOutput:
        """Método principal que orquesta todo."""
        
    def extract_thinking(self, text: str) -> str | None:
        """Extrae :::thinking::: block."""
        
    def extract_conclusion(self, text: str) -> str | None:
        """Extrae :::conclusion::: block."""
        
    def extract_direct_answer(self, text: str) -> str:
        """Extrae primer párrafo o genera uno."""
        
    def parse_table(self, text: str) -> TableData | None:
        """Parsea tabla markdown a estructura."""
        
    def format_cv_references(self, text: str) -> str:
        """Limpia y formatea referencias CV."""
        
    def generate_fallback_answer(self, chunks: list) -> str:
        """Genera respuesta si LLM falla."""
```

**Responsabilidades:**
- ✅ Extraer bloques delimitados (:::thinking:::, :::conclusion:::)
- ✅ Parsear tabla markdown a estructura de datos
- ✅ Limpiar referencias CV
- ✅ Generar fallbacks si el LLM falla
- ✅ NO depende de que el LLM siga instrucciones perfectamente

---

### 2. Backend: TableParser (Submódulo)

**Archivo:** `backend/app/services/output_processor/table_parser.py`

```python
class TableParser:
    """
    Parsea tablas markdown robustamente.
    """
    
    def parse(self, markdown_text: str) -> TableData:
        """
        Busca tabla markdown y la convierte a estructura.
        Si falla, genera tabla básica con datos de chunks.
        """
        
    def _extract_table_region(self, text: str) -> str:
        """Encuentra la región de la tabla."""
        
    def _parse_markdown_table(self, table_text: str) -> TableData:
        """Parsea pipes y celdas."""
        
    def _generate_fallback_table(self, chunks: list) -> TableData:
        """Genera tabla si no existe."""
```

---

### 3. Backend: StructuredOutput (Modelo de datos)

**Archivo:** `backend/app/models/structured_output.py`

```python
@dataclass
class TableData:
    headers: list[str]
    rows: list[list[str]]
    
@dataclass
class StructuredOutput:
    thinking: str | None
    direct_answer: str
    table_data: TableData | None
    conclusion: str | None
    raw_content: str
    cv_references: list[CVReference]
```

---

### 4. Frontend: Componentes Modulares

**Archivos a crear:**

1. `frontend/src/components/output/DirectAnswerSection.jsx`
   - Renderiza direct_answer
   - Siempre se muestra

2. `frontend/src/components/output/TableComponent.jsx`
   - Renderiza table_data como HTML
   - Botón Copy
   - Maneja null (no muestra nada)

3. `frontend/src/components/output/ThinkingPanel.jsx`
   - Ya existe, usar con nuevo formato

4. `frontend/src/components/output/ConclusionPanel.jsx`
   - Ya existe, usar con nuevo formato

5. `frontend/src/components/PipelineStepsPanel.jsx`
   - Ya creado, integrar

---

## Flujo de Datos Completo

### Backend

```python
# 1. RAG Pipeline ejecuta
result = await rag_service.query(...)

# 2. RAGServiceV5 genera raw_output
raw_output = llm.generate(prompt, context)

# 3. OutputProcessor procesa
processor = OutputProcessor()
structured = processor.process(raw_output, chunks)

# 4. Se guarda structured en ChatMessage
message = ChatMessage(
    role="assistant",
    content=raw_output,  # Para debugging
    structured_output=structured.to_dict(),
    pipeline_steps=[...],
    sources=[...]
)
```

### Frontend

```jsx
// Message.jsx recibe message con structured_output
const { structured_output, pipeline_steps } = message;

return (
  <div>
    {/* Pipeline Steps - Siempre existe */}
    <PipelineStepsPanel steps={pipeline_steps} />
    
    {/* Thinking - Opcional */}
    {structured_output?.thinking && (
      <ThinkingPanel content={structured_output.thinking} />
    )}
    
    {/* Direct Answer - Siempre existe */}
    <DirectAnswerSection content={structured_output.direct_answer} />
    
    {/* Table - Opcional pero robusto */}
    {structured_output?.table_data && (
      <TableComponent data={structured_output.table_data} />
    )}
    
    {/* Conclusion - Opcional */}
    {structured_output?.conclusion && (
      <ConclusionPanel content={structured_output.conclusion} />
    )}
  </div>
);
```

---

## Implementación por Fases

### FASE 1: Backend - OutputProcessor

**Archivos a crear:**
- `backend/app/services/output_processor/__init__.py`
- `backend/app/services/output_processor/processor.py`
- `backend/app/services/output_processor/table_parser.py`
- `backend/app/services/output_processor/extractors.py`
- `backend/app/models/structured_output.py`

**Tests:**
- Test con output perfecto del LLM
- Test con output roto (sin tabla)
- Test con output parcial (solo thinking)
- Test sin :::blocks:::

---

### FASE 2: Backend - Integración con RAG

**Modificar:**
- `backend/app/services/rag_service_v5.py`
  - Método `_build_success_response()`
  - Usar OutputProcessor en lugar de `_format_answer_with_blocks()`
  
**NO modificar:**
- `_clean_broken_cv_references()` → Mover a OutputProcessor
- Prompt actual → Solo ajustar ejemplos

---

### FASE 3: Backend - Model Updates

**Modificar:**
- `backend/app/models/sessions.py`
  - ChatMessage agregar campo `structured_output: dict`
  
**Migración de datos:**
- Mensajes viejos tendrán structured_output=null
- Frontend debe manejar ambos casos

---

### FASE 4: Frontend - Componentes Output

**Crear:**
- `frontend/src/components/output/DirectAnswerSection.jsx`
- `frontend/src/components/output/TableComponent.jsx`
- `frontend/src/components/output/index.js` (barrel export)

**Modificar:**
- `frontend/src/components/Message.jsx`
  - Detectar si tiene structured_output
  - Usar nuevos componentes si existe
  - Fallback a ReactMarkdown si no existe (mensajes viejos)

---

### FASE 5: Testing End-to-End

**Test cases:**
1. Query nuevo con output perfecto
2. Query con LLM que no sigue formato
3. Query con tabla rota
4. Query sin :::thinking:::
5. Cargar mensaje viejo (sin structured_output)
6. Verificar pipeline_steps se muestra siempre

---

## Ventajas de Esta Arquitectura

### ✅ Modularidad
- Cada componente es independiente
- Fallo en tabla NO afecta conclusión
- Fallo en LLM genera fallback

### ✅ Robustez
- OutputProcessor garantiza estructura válida
- Frontend siempre recibe datos consistentes
- No depende de que LLM sea perfecto

### ✅ Mantenibilidad
- Cambiar formato de tabla = Solo modificar TableParser
- Agregar nuevo bloque = Nuevo extractor
- Bug en output = Fácil de aislar

### ✅ Testing
- Cada componente se testea individualmente
- Mocks fáciles de crear
- Tests no se rompen entre sí

---

## Garantías del Sistema

1. **Pipeline Steps**: Siempre existen, generados por backend antes de LLM
2. **Direct Answer**: Siempre existe, extraído o generado
3. **Table**: Si LLM genera, se parsea. Si falla, null (no rompe)
4. **Thinking**: Opcional, no afecta resto si falta
5. **Conclusion**: Opcional, no afecta resto si falta

---

## Próximos Pasos

1. ✋ **APROBAR ESTE PLAN** antes de escribir código
2. Crear OutputProcessor con tests
3. Crear componentes frontend
4. Integrar en RAGServiceV5
5. Actualizar ChatMessage model
6. Testing completo
7. Deploy

---

## Notas Importantes

- **NO modificar** código existente hasta aprobar el plan
- **NO romper** funcionalidades actuales
- **Implementar** fase por fase con tests
- **Rollback** fácil si algo falla (feature flags)
