# Plan de Implementación: Structured Output Visual

## Objetivo
Implementar un sistema de salida estructurada que renderice cada componente de forma visual, modular y consistente, tal como se muestra en el diseño de referencia.

---

## Diseño de Referencia

### Componentes Visuales (en orden)

```
┌─────────────────────────────────────────────────────────────┐
│ ⚙️ Thinking Process                                    [▼]  │  ← Colapsable, fondo púrpura
├─────────────────────────────────────────────────────────────┤
│ (Contenido del razonamiento interno - monospace)            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 📄 Direct Answer                                            │  ← Borde amarillo/dorado
├─────────────────────────────────────────────────────────────┤
│ Respuesta directa en 2-3 oraciones...                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 📊 Analysis                                                 │  ← Borde cyan/azul
├─────────────────────────────────────────────────────────────┤
│ Análisis detallado explicando el razonamiento...            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 📋 Candidate Comparison Table                               │  ← Tabla con scores coloreados
├──────────┬────────────┬───────────────┬────────────────────┤
│ Candidate│ Experience │ Specialization│ Match Score        │
├──────────┼────────────┼───────────────┼────────────────────┤
│ María    │ 5 years    │ Django        │ [95%] ← Verde      │
│ Carlos   │ 3 years    │ Data Science  │ [82%] ← Amarillo   │
│ Ana      │ 2 years    │ ML            │ [75%] ← Gris       │
└──────────┴────────────┴───────────────┴────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ✓ Conclusion                                                │  ← Borde verde/cyan
├─────────────────────────────────────────────────────────────┤
│ **Recomendación:** María García es el mejor candidato...    │
└─────────────────────────────────────────────────────────────┘
```

### Colores de Match Score
- **Verde** (#10B981): Score ≥ 90%
- **Amarillo** (#F59E0B): Score 70-89%
- **Gris** (#6B7280): Score < 70%

---

## Arquitectura

### 1. Backend: Modelo de Datos

```python
# app/models/structured_output.py

@dataclass
class TableRow:
    candidate_name: str
    cv_id: str
    columns: Dict[str, str]  # {"Experience": "5 years", "Specialization": "Django"}
    match_score: int  # 0-100

@dataclass
class TableData:
    title: str  # "Candidate Comparison Table"
    headers: List[str]  # ["Candidate", "Experience", "Specialization", "Match Score"]
    rows: List[TableRow]

@dataclass
class StructuredOutput:
    thinking: str           # Razonamiento interno (colapsable)
    direct_answer: str      # Respuesta directa (2-3 oraciones)
    analysis: str           # Análisis detallado
    table: TableData        # Tabla de candidatos con scores
    conclusion: str         # Conclusión/recomendación
    
    # Metadata
    processing_time_ms: int
    components_extracted: List[str]
```

### 2. Backend: Módulos de Extracción

```
backend/app/services/output_processor/
├── orchestrator.py          # Coordina todo el proceso
├── processor.py             # Extrae componentes usando módulos
└── modules/
    ├── __init__.py
    ├── thinking_module.py   # Extrae :::thinking ... :::
    ├── direct_answer_module.py  # Extrae respuesta directa
    ├── analysis_module.py   # Extrae análisis
    ├── table_module.py      # Extrae tabla con scores
    └── conclusion_module.py # Extrae :::conclusion ... :::
```

#### Flujo de Procesamiento

```
LLM Output
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│ ORCHESTRATOR.process(raw_llm_output, chunks)             │
│                                                          │
│  1. _pre_clean_llm_output()  ← Limpia código blocks      │
│  2. processor.process()       ← Extrae con módulos       │
│  3. _assemble_parts()         ← Ensambla componentes     │
│  4. _post_clean_output()      ← Limpieza final           │
│                                                          │
│  Return: (StructuredOutput, formatted_string)            │
└──────────────────────────────────────────────────────────┘
    │
    ▼
Frontend recibe StructuredOutput como JSON
```

### 3. Frontend: Componentes React

```
frontend/src/components/structured-output/
├── StructuredOutputRenderer.jsx  # Componente principal
├── ThinkingSection.jsx           # Sección colapsable
├── DirectAnswerSection.jsx       # Con borde amarillo
├── AnalysisSection.jsx           # Con borde cyan
├── CandidateTable.jsx            # Tabla con Match Scores
├── ConclusionSection.jsx         # Con borde verde
└── MatchScoreBadge.jsx           # Badge coloreado para scores
```

---

## Plan de Implementación Detallado

### FASE 1: Backend - Modelo de Datos (30 min)

**Archivo:** `backend/app/models/structured_output.py`

1. Actualizar `TableData` para incluir `match_score` por fila
2. Añadir campo `title` a `TableData`
3. Crear `TableRow` dataclass con estructura clara
4. Asegurar que todos los campos son serializables a JSON

```python
@dataclass
class TableRow:
    candidate_name: str
    cv_id: str
    columns: Dict[str, str]
    match_score: int  # 0-100
    
@dataclass  
class TableData:
    title: str = "Candidate Comparison Table"
    headers: List[str] = field(default_factory=list)
    rows: List[TableRow] = field(default_factory=list)
```

### FASE 2: Backend - Módulo de Tabla (45 min)

**Archivo:** `backend/app/services/output_processor/modules/table_module.py`

1. Extraer Match Score de cada fila (buscar %, ⭐, números)
2. Normalizar score a 0-100
3. Estructurar cada fila como `TableRow`
4. El `format()` devuelve JSON estructurado, NO markdown

```python
def extract(self, llm_output: str, chunks: List[dict]) -> TableData:
    # 1. Parsear tabla markdown
    # 2. Extraer match_score de última columna
    # 3. Crear TableRow por cada fila
    # 4. Retornar TableData estructurada

def _extract_match_score(self, cell: str) -> int:
    # "95%" → 95
    # "⭐⭐⭐⭐⭐" → 100
    # "⭐⭐⭐" → 60
```

### FASE 3: Backend - Orchestrator (30 min)

**Archivo:** `backend/app/services/output_processor/orchestrator.py`

1. Modificar `process()` para retornar `StructuredOutput` completo
2. NO convertir a string markdown
3. Retornar objeto JSON serializable para el frontend

```python
def process(self, raw_llm_output: str, chunks: List) -> StructuredOutput:
    cleaned = self._pre_clean_llm_output(raw_llm_output)
    
    # Extraer cada componente
    thinking = self.thinking_module.extract(cleaned)
    direct_answer = self.direct_answer_module.extract(cleaned)
    analysis = self.analysis_module.extract(cleaned, direct_answer, None)
    table = self.table_module.extract(cleaned, chunks)
    conclusion = self.conclusion_module.extract(cleaned)
    
    return StructuredOutput(
        thinking=thinking,
        direct_answer=direct_answer,
        analysis=analysis,
        table=table,
        conclusion=conclusion
    )
```

### FASE 4: Backend - API Response (20 min)

**Archivo:** `backend/app/api/routes.py`

1. Modificar endpoint `/chat` para incluir `structured_output` en respuesta
2. Serializar `StructuredOutput` a JSON
3. El campo `answer` puede seguir siendo string para compatibilidad

```python
return {
    "answer": formatted_answer,  # String para compatibilidad
    "structured_output": {
        "thinking": structured.thinking,
        "direct_answer": structured.direct_answer,
        "analysis": structured.analysis,
        "table": {
            "title": structured.table.title,
            "headers": structured.table.headers,
            "rows": [
                {
                    "candidate_name": row.candidate_name,
                    "cv_id": row.cv_id,
                    "columns": row.columns,
                    "match_score": row.match_score
                }
                for row in structured.table.rows
            ]
        },
        "conclusion": structured.conclusion
    }
}
```

### FASE 5: Frontend - Componente Principal (60 min)

**Archivo:** `frontend/src/components/structured-output/StructuredOutputRenderer.jsx`

```jsx
const StructuredOutputRenderer = ({ data }) => {
  if (!data) return null;
  
  return (
    <div className="space-y-4">
      {/* 1. Thinking Process - Colapsable */}
      {data.thinking && (
        <ThinkingSection content={data.thinking} />
      )}
      
      {/* 2. Direct Answer - Borde amarillo */}
      {data.direct_answer && (
        <DirectAnswerSection content={data.direct_answer} />
      )}
      
      {/* 3. Analysis - Borde cyan */}
      {data.analysis && (
        <AnalysisSection content={data.analysis} />
      )}
      
      {/* 4. Table - Con Match Scores coloreados */}
      {data.table && data.table.rows?.length > 0 && (
        <CandidateTable data={data.table} />
      )}
      
      {/* 5. Conclusion - Borde verde */}
      {data.conclusion && (
        <ConclusionSection content={data.conclusion} />
      )}
    </div>
  );
};
```

### FASE 6: Frontend - Secciones Individuales (45 min)

#### ThinkingSection.jsx
```jsx
const ThinkingSection = ({ content }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  return (
    <div className="bg-purple-900/30 rounded-xl border border-purple-700/50">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4"
      >
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-purple-400" />
          <span className="font-semibold text-purple-300">Thinking Process</span>
        </div>
        <ChevronDown className={`transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      {isOpen && (
        <div className="px-4 pb-4 font-mono text-sm text-gray-300 whitespace-pre-wrap">
          {content}
        </div>
      )}
    </div>
  );
};
```

#### DirectAnswerSection.jsx
```jsx
const DirectAnswerSection = ({ content }) => (
  <div className="bg-slate-800/50 rounded-xl border-l-4 border-amber-500 p-4">
    <div className="flex items-center gap-2 mb-2">
      <FileText className="w-5 h-5 text-amber-400" />
      <span className="font-semibold text-amber-400">Direct Answer</span>
    </div>
    <div className="text-gray-200">{content}</div>
  </div>
);
```

#### AnalysisSection.jsx
```jsx
const AnalysisSection = ({ content }) => (
  <div className="bg-slate-800/50 rounded-xl border-l-4 border-cyan-500 p-4">
    <div className="flex items-center gap-2 mb-2">
      <BarChart3 className="w-5 h-5 text-cyan-400" />
      <span className="font-semibold text-cyan-400">Analysis</span>
    </div>
    <div className="text-gray-200">{content}</div>
  </div>
);
```

#### ConclusionSection.jsx
```jsx
const ConclusionSection = ({ content }) => (
  <div className="bg-emerald-900/20 rounded-xl border border-emerald-700/50 p-4">
    <div className="flex items-center gap-2 mb-2">
      <CheckCircle className="w-5 h-5 text-emerald-400" />
      <span className="font-semibold text-emerald-400">Conclusion</span>
    </div>
    <div className="text-gray-200">{content}</div>
  </div>
);
```

### FASE 7: Frontend - Tabla con Match Scores (45 min)

**Archivo:** `frontend/src/components/structured-output/CandidateTable.jsx`

```jsx
const getScoreColor = (score) => {
  if (score >= 90) return 'bg-emerald-500 text-white';
  if (score >= 70) return 'bg-amber-500 text-white';
  return 'bg-gray-500 text-white';
};

const CandidateTable = ({ data }) => (
  <div className="bg-slate-800/50 rounded-xl p-4">
    <div className="flex items-center gap-2 mb-4">
      <Table className="w-5 h-5 text-slate-400" />
      <span className="font-semibold text-slate-300">{data.title}</span>
    </div>
    
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-600">
            {data.headers.map((header, i) => (
              <th key={i} className="text-left p-2 text-slate-400 font-medium">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row, i) => (
            <tr key={i} className="border-b border-slate-700/50">
              <td className="p-2 text-slate-200">{row.candidate_name}</td>
              {Object.values(row.columns).map((val, j) => (
                <td key={j} className="p-2 text-slate-300">{val}</td>
              ))}
              <td className="p-2">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getScoreColor(row.match_score)}`}>
                  {row.match_score}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);
```

---

## Integración en App.jsx

### Modificar renderizado de mensajes del asistente

```jsx
// En lugar de renderizar msg.content como string:
{msg.role === 'assistant' && msg.structured_output ? (
  <StructuredOutputRenderer data={msg.structured_output} />
) : (
  <div className="prose">{msg.content}</div>
)}
```

---

## Checklist de Implementación

### Backend
- [ ] Actualizar `StructuredOutput` model con `TableRow`
- [ ] Modificar `table_module.py` para extraer `match_score`
- [ ] Actualizar `orchestrator.py` para retornar JSON estructurado
- [ ] Modificar API response para incluir `structured_output`

### Frontend
- [ ] Crear carpeta `components/structured-output/`
- [ ] Implementar `StructuredOutputRenderer.jsx`
- [ ] Implementar `ThinkingSection.jsx`
- [ ] Implementar `DirectAnswerSection.jsx`
- [ ] Implementar `AnalysisSection.jsx`
- [ ] Implementar `CandidateTable.jsx`
- [ ] Implementar `ConclusionSection.jsx`
- [ ] Integrar en `App.jsx`

### Testing
- [ ] Probar con query "Who has Python experience?"
- [ ] Verificar colores de Match Score
- [ ] Verificar colapsable de Thinking Process
- [ ] Verificar que todas las secciones aparecen

---

## Tiempo Estimado Total: ~4-5 horas

| Fase | Tarea | Tiempo |
|------|-------|--------|
| 1 | Modelo de datos | 30 min |
| 2 | Módulo de tabla | 45 min |
| 3 | Orchestrator | 30 min |
| 4 | API Response | 20 min |
| 5 | Componente principal | 60 min |
| 6 | Secciones individuales | 45 min |
| 7 | Tabla con scores | 45 min |
| 8 | Integración y testing | 30 min |

---

## Notas Importantes

1. **El frontend debe recibir JSON estructurado**, no markdown
2. **Match Score debe ser numérico** (0-100) para poder colorear
3. **Thinking siempre colapsado por defecto**
4. **El orden de secciones es fijo**: Thinking → Direct Answer → Analysis → Table → Conclusion
5. **Todas las secciones son opcionales** excepto Direct Answer
