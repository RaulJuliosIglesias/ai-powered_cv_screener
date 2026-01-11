# AI-Powered CV Screener - Análisis Completo para Presentación

> **Versión:** 7.0
> **Última actualización:** Enero 2026
> **Tipo de documento:** Análisis técnico para presentación

---

## 1. VISIÓN GENERAL DEL PROYECTO

### 1.1 ¿Qué es?

Un **sistema inteligente de análisis de CVs** que utiliza tecnología RAG (Retrieval-Augmented Generation) para permitir a reclutadores hacer preguntas en lenguaje natural sobre candidatos y recibir respuestas estructuradas, verificadas y con citas a los documentos fuente.

### 1.2 El Problema que Resuelve

| Problema Tradicional | Nuestra Solución |
|---------------------|------------------|
| Revisar 100+ CVs manualmente | Preguntas naturales: "¿Quién tiene más experiencia en Python?" |
| Comparar candidatos en Excel | "Compara a Juan vs María para el puesto de backend" |
| Perder información importante | Cada respuesta cita el documento fuente |
| Subjetividad en evaluaciones | Análisis estructurado con métricas objetivas |
| No detectar red flags | Análisis automático de riesgos, gaps, job hopping |

### 1.3 Principio Fundamental

**Zero Hallucinations** - Cada respuesta es trazable a documentos fuente con output visual estructurado.

```
📄 Upload CVs  →  🔍 Ask Questions  →  ✅ Get Structured Answers

"Rank all candidates by experience and show red flags"

✨ Response:
   🏆 Top Pick: Juan García - 8 years, no red flags
   📊 Risk Assessment Table with 5-factor analysis
   📎 Sources: Juan_Garcia.pdf (95%), Maria_Lopez.pdf (89%)
```

---

## 2. ARQUITECTURA DEL SISTEMA

### 2.1 Diagrama de Alto Nivel

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React 18 + Shadcn UI)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ Sessions │ │   Chat   │ │ Pipeline │ │ Sources  │ │ Metrics  │          │
│  │  Panel   │ │ Window   │ │ Progress │ │ Badges   │ │  Panel   │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │              STRUCTURED OUTPUT RENDERER                       │          │
│  │  SingleCandidateProfile | RankingTable | RiskAssessment | ... │          │
│  └──────────────────────────────────────────────────────────────┘          │
└────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼ HTTP/SSE
┌────────────────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI + Python)                          │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      RAG PIPELINE v7.0 (11 Stages)                   │  │
│  │  Query → Understand → MultiQuery → Guardrail → Embed → Search →      │  │
│  │  CrossEncoder → Generate → NLI Verify → RAGAS → ORCHESTRATOR         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                     │                                      │
│  ┌──────────────────────────────────┴───────────────────────────────────┐  │
│  │                      OUTPUT ORCHESTRATOR                              │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  STRUCTURES (9): SingleCandidate | RiskAssessment | Comparison  │ │  │
│  │  │  Search | Ranking | JobMatch | TeamBuild | Verify | Summary     │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  MODULES (29+): Thinking | DirectAnswer | Analysis | RiskTable  │ │  │
│  │  │  MatchScore | Timeline | GapAnalysis | RedFlags | Skills | ...  │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌─────────────────────────┐       ┌─────────────────────────┐             │
│  │      LOCAL MODE         │       │      CLOUD MODE         │             │
│  │  • JSON persistence     │  OR   │  • Supabase pgvector    │             │
│  │  • sentence-transformers│       │  • nomic-embed-v1.5     │             │
│  │  • 384-dim vectors      │       │  • 768-dim vectors      │             │
│  └─────────────────────────┘       └─────────────────────────┘             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Estructura de Directorios

```
ai-powered-cv-screener/
├── backend/                          # Python FastAPI
│   ├── app/
│   │   ├── api/                     # Endpoints REST
│   │   │   ├── routes_sessions.py   # CRUD sesiones
│   │   │   ├── routes_sessions_stream.py  # Server-Sent Events
│   │   │   └── export_routes.py     # Export PDF/DOCX
│   │   ├── services/                # Lógica de negocio
│   │   │   ├── rag_service_v5.py   # Pipeline RAG (2900+ líneas)
│   │   │   ├── query_understanding_service.py  # 65+ patrones
│   │   │   ├── output_processor/    # Orquestador
│   │   │   │   ├── orchestrator.py  # Router inteligente
│   │   │   │   ├── structures/      # 9 estructuras
│   │   │   │   └── modules/         # 29+ módulos
│   │   │   └── v7_integration.py    # HuggingFace services
│   │   ├── providers/               # Factory pattern
│   │   │   ├── local/               # Embeddings locales
│   │   │   └── cloud/               # Supabase + OpenRouter
│   │   └── models/                  # Pydantic schemas
│   ├── data/                        # Persistencia (modo local)
│   │   ├── sessions.json            # Sesiones
│   │   └── vectors.json             # Embeddings
│   └── requirements.txt
├── frontend/                        # React + TypeScript
│   ├── src/
│   │   ├── components/              # Componentes UI
│   │   │   ├── output/              # Renderers estructurados
│   │   │   └── modals/              # Settings, About
│   │   ├── contexts/                # State management
│   │   ├── hooks/                   # Custom hooks
│   │   └── services/api.ts          # Cliente HTTP
│   └── package.json
├── docs/                            # Documentación
│   ├── evaluation/                  # Criterios evaluación
│   └── roadmap/                     # Plan de desarrollo
└── scripts/                         # Setup utilities
    └── setup_supabase_complete.sql  # Schema cloud
```

---

## 3. FLUJO COMPLETO DE EXPERIENCIA DEL USUARIO

### 3.1 PASO 1: El Usuario Sube un Documento (CV)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLUJO DE UPLOAD DE CV                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  USUARIO                                                                    │
│     │                                                                       │
│     │  1. Drag & Drop PDF(s)                                               │
│     ▼                                                                       │
│  ┌─────────────────┐                                                       │
│  │   FRONTEND      │  React detecta archivos, valida (PDF, <10MB)          │
│  │  EmptySession   │                                                       │
│  │   Dropzone      │                                                       │
│  └────────┬────────┘                                                       │
│           │                                                                 │
│           │  2. POST /api/sessions/{id}/cvs                                │
│           │     Content-Type: multipart/form-data                          │
│           ▼                                                                 │
│  ┌─────────────────┐                                                       │
│  │    BACKEND      │                                                       │
│  │  routes_sessions│  Recibe archivos, genera job_id                       │
│  │       .py       │  Inicia tarea en background                           │
│  └────────┬────────┘                                                       │
│           │                                                                 │
│           │  3. Background Processing                                       │
│           ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    PDF PROCESSING PIPELINE                           │   │
│  │                                                                      │   │
│  │  ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐      │   │
│  │  │    PDF    │──▶│   TEXT    │──▶│  CHUNKING │──▶│ EMBEDDING │      │   │
│  │  │ EXTRACTION│   │  PARSING  │   │  SERVICE  │   │  SERVICE  │      │   │
│  │  │ pdfplumber│   │  sections │   │ ~1000 tok │   │ 384/768 d │      │   │
│  │  └───────────┘   └───────────┘   └───────────┘   └───────────┘      │   │
│  │                                                                      │   │
│  │                          │                                           │   │
│  │                          ▼                                           │   │
│  │                 ┌─────────────────┐                                  │   │
│  │                 │   ENRICHED      │  Auto-extracted metadata:        │   │
│  │                 │   METADATA      │  • total_experience_years        │   │
│  │                 │   EXTRACTION    │  • seniority_level               │   │
│  │                 │                 │  • skills[], companies[]         │   │
│  │                 │                 │  • job_hopping_score             │   │
│  │                 │                 │  • employment_gaps               │   │
│  │                 │                 │  • has_faang_experience          │   │
│  │                 └─────────────────┘                                  │   │
│  │                          │                                           │   │
│  │                          ▼                                           │   │
│  │                 ┌─────────────────┐                                  │   │
│  │                 │  VECTOR STORE   │  LOCAL: JSON (vectors.json)      │   │
│  │                 │    INDEXING     │  CLOUD: Supabase pgvector        │   │
│  │                 └─────────────────┘                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│           │                                                                 │
│           │  4. Progress updates via polling                               │
│           ▼                                                                 │
│  ┌─────────────────┐                                                       │
│  │   FRONTEND      │  BackgroundUploadWidget muestra progreso              │
│  │  Muestra toast  │  "Processing CV 1/5... Extracting text..."           │
│  │  con progreso   │  "Generating embeddings... Done!"                     │
│  └─────────────────┘                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Archivos involucrados:**
- `frontend/src/components/EmptySessionDropzone.jsx` - UI de drag & drop
- `frontend/src/contexts/BackgroundTaskContext.jsx` - Manejo de tareas en background
- `backend/app/api/routes_sessions.py` - Endpoint upload
- `backend/app/services/pdf_service.py` - Extracción de texto y metadata
- `backend/app/services/chunking_service.py` - Segmentación inteligente
- `backend/app/services/embedding_service.py` - Generación de embeddings
- `backend/app/providers/local/vector_store.py` - Almacenamiento vectorial

### 3.2 PASO 2: El Usuario Hace una Pregunta

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLUJO DE QUERY (PREGUNTA)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  USUARIO                                                                    │
│     │                                                                       │
│     │  "¿Quién tiene más experiencia en Python y React?"                   │
│     ▼                                                                       │
│  ┌─────────────────┐                                                       │
│  │   FRONTEND      │  ChatInputField captura query                         │
│  │  ChatInputField │  Envía con modelo seleccionado + settings             │
│  └────────┬────────┘                                                       │
│           │                                                                 │
│           │  POST /api/sessions/{id}/chat                                  │
│           │  { query, model, rag_settings }                                │
│           ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     RAG PIPELINE v7.0 (11 STAGES)                    │   │
│  │                                                                      │   │
│  │  STAGE 1: QUERY UNDERSTANDING (~150ms)                               │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │  • Clasificación de tipo: ranking/search/comparison/...      │     │   │
│  │  │  • Resolución de pronombres: "ella" → "María López"          │     │   │
│  │  │  • Extracción de requisitos: [Python, React, 5+ años]        │     │   │
│  │  │  • 65+ patrones de detección                                 │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                        │   │
│  │                              ▼                                        │   │
│  │  STAGE 2: MULTI-QUERY EXPANSION (~100ms)                             │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │  Query original → Variaciones para mejor recall              │     │   │
│  │  │  + HyDE: Genera documento hipotético de respuesta           │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                        │   │
│  │                              ▼                                        │   │
│  │  STAGE 3: GUARDRAILS (~50ms)                                         │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │  • Zero-shot classification (HuggingFace)                    │     │   │
│  │  │  • Rechaza: "receta de pasta", ataques, off-topic           │     │   │
│  │  │  • Detecta: CV-related, candidate queries, analysis requests │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                        │   │
│  │                              ▼                                        │   │
│  │  STAGE 4: EMBEDDING (~45ms)                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │  LOCAL: sentence-transformers all-MiniLM-L6-v2 (384 dims)    │     │   │
│  │  │  CLOUD: nomic-embed-text-v1.5 (768 dims)                     │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                        │   │
│  │                              ▼                                        │   │
│  │  STAGE 5: VECTOR SEARCH + HYBRID (~120ms)                            │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │  • Búsqueda vectorial (semántica)                            │     │   │
│  │  │  • BM25 (léxica) - para términos exactos                    │     │   │
│  │  │  • Reciprocal Rank Fusion (RRF) - combina ambos             │     │   │
│  │  │  • Filtra por session_id (solo CVs de la sesión)            │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                        │   │
│  │                              ▼                                        │   │
│  │  STAGE 6: CROSS-ENCODER RERANKING (~200ms)                           │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │  HuggingFace BAAI/bge-reranker-base                          │     │   │
│  │  │  Re-ordena por relevancia real query-documento              │     │   │
│  │  │  100x más rápido que reranking con LLM                       │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                        │   │
│  │                              ▼                                        │   │
│  │  STAGE 7: REASONING (~500ms)                                         │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │  Chain-of-Thought estructurado                               │     │   │
│  │  │  Self-Ask pattern para queries complejos                    │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                        │   │
│  │                              ▼                                        │   │
│  │  STAGE 8: LLM GENERATION (~2000ms)                                   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │  OpenRouter API → GPT-4o / Claude 3.5 / Llama 3.1 / etc.    │     │   │
│  │  │  Prompt template optimizado por tipo de query               │     │   │
│  │  │  Incluye contexto de conversación anterior                  │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                        │   │
│  │                              ▼                                        │   │
│  │  STAGE 9: NLI VERIFICATION (~150ms)                                  │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │  HuggingFace facebook/bart-large-mnli                        │     │   │
│  │  │  Natural Language Inference: ¿La respuesta está soportada?  │     │   │
│  │  │  Clasificación: entailment / neutral / contradiction        │     │   │
│  │  │  Detecta alucinaciones antes de enviar al usuario           │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                        │   │
│  │                              ▼                                        │   │
│  │  STAGE 10: RAGAS EVALUATION (~100ms)                                 │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │  Métricas automáticas de calidad:                            │     │   │
│  │  │  • Faithfulness (fidelidad al contexto)                     │     │   │
│  │  │  • Answer Relevancy (relevancia de respuesta)               │     │   │
│  │  │  • Context Precision (precisión del contexto)               │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                        │   │
│  │                              ▼                                        │   │
│  │  STAGE 11: OUTPUT ORCHESTRATION (~50ms)                              │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │  Router inteligente: query_type → Structure → Modules        │     │   │
│  │  │  Genera structured_output JSON para renderizado              │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│           │                                                                 │
│           │  Response JSON                                                  │
│           ▼                                                                 │
│  ┌─────────────────┐                                                       │
│  │   FRONTEND      │  StructuredOutputRenderer                             │
│  │  Renderiza:     │  Muestra tablas, cards, gráficos según estructura     │
│  │  - RankingTable │  PipelineProgressPanel muestra progreso en tiempo real│
│  │  - SourceBadges │  SourceBadge permite click → ver PDF original         │
│  │  - TopPickCard  │                                                       │
│  └─────────────────┘                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Output Orchestrator: Routing Inteligente

El sistema detecta el tipo de pregunta y genera una respuesta estructurada específica:

| Tipo de Query | Estructura | Ejemplo | Output Visual |
|---------------|------------|---------|---------------|
| `search` | SearchStructure | "¿Quién sabe Python?" | Tabla de resultados con scores |
| `single_candidate` | SingleCandidateStructure | "Perfil completo de Juan" | Card con highlights, carrera, skills |
| `ranking` | RankingStructure | "Top 5 para backend" | Tabla ranking + Top Pick card |
| `comparison` | ComparisonStructure | "Compara Juan vs María" | Tabla comparativa lado a lado |
| `red_flags` | RiskAssessmentStructure | "Red flags de este candidato" | Tabla 5 factores de riesgo |
| `job_match` | JobMatchStructure | "¿Quién encaja mejor para Senior React?" | Match scores + coverage |
| `team_build` | TeamBuildStructure | "Arma un equipo de 3 devs" | Team composition + synergy |
| `verification` | VerificationStructure | "¿Juan tiene certificación AWS?" | Claim + Evidence + Verdict |
| `summary` | SummaryStructure | "Overview de todos los candidatos" | Pool summary + distribuciones |

---

## 4. JUSTIFICACIÓN DEL STACK TECNOLÓGICO

### 4.1 ¿Por qué este Backend? (Python + FastAPI)

#### **Python: El Lenguaje del AI/ML**

| Razón | Explicación |
|-------|-------------|
| **Ecosistema AI/ML** | sentence-transformers, HuggingFace, LangChain, RAGAS - todas las librerías de AI están en Python |
| **Async nativo** | asyncio permite manejar múltiples requests de embeddings/LLM concurrentemente |
| **Madurez** | Librerías estables para PDF (pdfplumber), HTTP (httpx), data validation (Pydantic) |
| **Comunidad RAG** | La mayoría de ejemplos, tutoriales y herramientas RAG son en Python |

#### **FastAPI: El Framework Moderno**

| Característica | Beneficio |
|----------------|-----------|
| **Async/Await nativo** | Pipeline RAG con múltiples llamadas async a APIs externas |
| **Pydantic integrado** | Validación automática de requests/responses, schemas tipados |
| **OpenAPI automático** | Swagger UI en `/docs` sin código adicional |
| **Performance** | Comparable a Node.js/Go, mucho más rápido que Flask/Django |
| **Type hints** | Autocompletado, detección de errores en IDE |
| **SSE Support** | Server-Sent Events para streaming de respuestas |

```python
# Ejemplo: Endpoint con validación automática
@router.post("/sessions/{session_id}/chat")
async def chat(
    session_id: str,
    request: ChatRequest,  # Pydantic valida automáticamente
    mode: Mode = Query(Mode.LOCAL)
) -> ChatResponse:  # Response tipada
    ...
```

#### **¿Por qué NO Node.js/Go/Rust?**

| Alternativa | Por qué no |
|-------------|------------|
| **Node.js** | Ecosistema AI/ML inmaduro, sentence-transformers no existe |
| **Go** | Sin librerías de embeddings locales, AI ecosystem muy limitado |
| **Rust** | Curva de aprendizaje alta, ecosistema AI emergente pero no maduro |
| **Java/Spring** | Overhead alto, ecosistema AI limitado comparado con Python |

---

### 4.2 ¿Por qué este Frontend? (React + TypeScript + Tailwind)

#### **React 18: El Estándar de la Industria**

| Razón | Explicación |
|-------|-------------|
| **Componentes reutilizables** | 29+ componentes para diferentes tipos de output |
| **State management flexible** | Context API para pipeline state, hooks custom |
| **Ecosistema maduro** | React-markdown, Radix UI, miles de componentes |
| **Developer experience** | Hot reload, React DevTools, amplia documentación |
| **Concurrent features** | React 18 con Suspense para mejor UX durante carga |

#### **TypeScript: Seguridad de Tipos**

```typescript
// Tipos estrictos para respuestas estructuradas
interface StructuredOutput {
  structure_type: 'ranking' | 'search' | 'comparison' | ...;
  direct_answer: string;
  results_table?: TableData;
  risk_assessment?: RiskData;
}
```

| Beneficio | Impacto |
|-----------|---------|
| **Autocompletado** | IDE sugiere propiedades de structured_output |
| **Refactoring seguro** | Cambiar un tipo actualiza todos los usos |
| **Documentación viva** | Los tipos son la documentación |
| **Errores en compile-time** | No en runtime |

#### **Tailwind CSS: Utility-First**

| Ventaja | Ejemplo |
|---------|---------|
| **Sin CSS separado** | `className="bg-blue-500 hover:bg-blue-600 p-4 rounded-lg"` |
| **Responsive built-in** | `md:flex-row lg:grid-cols-3` |
| **Dark mode trivial** | `dark:bg-gray-800 dark:text-white` |
| **Bundle pequeño** | PurgeCSS elimina clases no usadas |
| **Consistencia** | Design system built-in (spacing, colors) |

#### **Shadcn UI + Radix: Componentes Accesibles**

```jsx
// Componentes accesibles out-of-the-box
<Dialog>
  <DialogTrigger asChild>
    <Button variant="outline">Open Settings</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>RAG Pipeline Settings</DialogTitle>
    </DialogHeader>
    ...
  </DialogContent>
</Dialog>
```

| Razón | Beneficio |
|-------|-----------|
| **Accesibilidad (a11y)** | ARIA attributes, keyboard navigation automáticos |
| **Headless** | Estilos completamente customizables |
| **Copy-paste** | No es dependencia, es código propio |
| **Composable** | Primitivos que se combinan |

#### **¿Por qué NO Vue/Angular/Svelte?**

| Alternativa | Por qué no |
|-------------|------------|
| **Vue** | Ecosistema de componentes UI menos maduro |
| **Angular** | Overhead alto para aplicación de esta complejidad |
| **Svelte** | Ecosistema emergente, menos componentes disponibles |
| **Vanilla JS** | Imposible mantener 29+ componentes estructurados sin framework |

---

### 4.3 ¿Por qué esta Base de Datos? (Dual Mode)

#### **Modo LOCAL: JSON + Cosine Similarity**

```json
// data/vectors.json - Simple pero efectivo para desarrollo
{
  "embeddings": [
    {
      "chunk_id": "uuid",
      "cv_id": "uuid",
      "embedding": [0.123, -0.456, ...],  // 384 dims
      "content": "text chunk",
      "metadata": { "section": "experience", "candidate_name": "Juan" }
    }
  ]
}
```

| Ventaja | Uso |
|---------|-----|
| **Zero setup** | No necesita instalar nada |
| **Debuggeable** | Puedes abrir el archivo y ver los datos |
| **Portable** | Copia el archivo y tienes todo |
| **Gratis** | $0 en infraestructura |

**Ideal para:** Desarrollo, demos, testing, proyectos pequeños (<100 CVs)

#### **Modo CLOUD: Supabase + pgvector**

```sql
-- cv_embeddings table con búsqueda vectorial
CREATE TABLE cv_embeddings (
    id BIGSERIAL PRIMARY KEY,
    cv_id TEXT REFERENCES cvs(id),
    content TEXT,
    embedding vector(768),  -- nomic-embed dimensions
    metadata JSONB
);

-- Índice IVFFlat para búsqueda rápida
CREATE INDEX cv_embeddings_embedding_idx
ON cv_embeddings USING ivfflat (embedding vector_cosine_ops);

-- RPC function para búsqueda semántica
CREATE FUNCTION match_cv_embeddings(
    query_embedding vector(768),
    match_count INT DEFAULT 5
) RETURNS TABLE (...);
```

| Ventaja | Explicación |
|---------|-------------|
| **pgvector** | Extensión nativa de PostgreSQL para vectores |
| **SQL queries** | Combina búsqueda vectorial con filtros SQL |
| **Escalable** | Millones de vectores con índices IVFFlat/HNSW |
| **Supabase** | PostgreSQL managed + Auth + Storage incluido |
| **Row Level Security** | Seguridad a nivel de fila para multi-tenant |

**Ideal para:** Producción, múltiples usuarios, >100 CVs

#### **¿Por qué NO otras bases de datos?**

| Alternativa | Por qué no |
|-------------|------------|
| **Pinecone** | Vendor lock-in, costoso a escala |
| **Weaviate** | Complejidad adicional, self-hosted |
| **ChromaDB** | Inestable en v0.4, problemas de persistencia |
| **MongoDB Atlas** | Vector search menos maduro que pgvector |
| **Qdrant** | Otro servicio a mantener, pgvector es suficiente |

#### **El Patrón Factory: Switching Sin Cambios de Código**

```python
# providers/factory.py - Abstracción elegante
class ProviderFactory:
    @classmethod
    def get_vector_store(cls, mode: Mode) -> VectorStoreProvider:
        if mode == Mode.CLOUD:
            return SupabaseVectorStore()   # pgvector
        else:
            return SimpleVectorStore()      # JSON file

    @classmethod
    def get_embedding_provider(cls, mode: Mode) -> EmbeddingProvider:
        if mode == Mode.CLOUD:
            return OpenRouterEmbeddingProvider()  # 768 dims
        else:
            return LocalEmbeddingProvider()       # 384 dims
```

**Beneficio:** Cambias `?mode=cloud` en la URL y todo funciona con Supabase.

---

### 4.4 ¿Por qué estos Servicios de AI?

#### **OpenRouter: Gateway Universal de LLMs**

```python
# Un API key, 100+ modelos
MODELS = [
    "openai/gpt-4o",
    "anthropic/claude-3.5-sonnet",
    "meta-llama/llama-3.1-70b-instruct",
    "google/gemini-pro",
    "mistralai/mistral-large"
]
```

| Ventaja | Impacto |
|---------|---------|
| **Un API, todos los modelos** | No necesitas cuentas en OpenAI, Anthropic, Google... |
| **Fallback automático** | Si GPT-4 falla, usa Llama |
| **Modelos gratis** | Varios modelos con tier gratis para query understanding |
| **Precios unificados** | Facturación única |
| **Rate limiting compartido** | Mejor que rate limits individuales |

#### **HuggingFace: ML Gratuito (v7)**

```python
# Servicios gratuitos sin API key
v7_services = {
    "nli": "facebook/bart-large-mnli",           # Verificación
    "reranker": "BAAI/bge-reranker-base",        # Reranking
    "zero_shot": "facebook/bart-large-mnli"      # Guardrails
}
```

| Servicio | Uso | Costo |
|----------|-----|-------|
| **NLI Verification** | Detectar alucinaciones | $0 |
| **Cross-Encoder Reranking** | Reordenar resultados | $0 |
| **Zero-Shot Classification** | Guardrails/validación | $0 |

#### **sentence-transformers: Embeddings Locales**

```python
# Modelo local, sin llamadas a API
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
embedding = model.encode("Python developer with 5 years experience")
# → [0.123, -0.456, ...] (384 dims)
```

| Ventaja | Beneficio |
|---------|-----------|
| **100% offline** | Funciona sin internet |
| **Costo $0** | Sin límites de uso |
| **Baja latencia** | ~5ms por embedding |
| **Privacidad** | CVs nunca salen de tu máquina |

---

## 5. DECISIONES DE ARQUITECTURA DESTACADAS

### 5.1 Sistema Anti-Alucinaciones (3 Capas)

```
┌─────────────────────────────────────────────────────────────────┐
│                  ANTI-HALLUCINATION SYSTEM                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CAPA 1: PRE-GENERACIÓN (Guardrails)                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Zero-Shot Classification (HuggingFace)                     │ │
│  │  • Rechaza queries off-topic                                │ │
│  │  • Detecta ataques de prompt injection                      │ │
│  │  • Valida que sea CV-related                                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  CAPA 2: DURANTE GENERACIÓN (Grounding)                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Prompt template con instrucciones estrictas               │ │
│  │  • "Only use information from the provided CV chunks"       │ │
│  │  • "If information is not in the context, say so"          │ │
│  │  • Context window limitado a chunks relevantes             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  CAPA 3: POST-GENERACIÓN (Verificación NLI)                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Natural Language Inference (bart-large-mnli)               │ │
│  │  • Extrae claims de la respuesta                           │ │
│  │  • Verifica cada claim contra el contexto                  │ │
│  │  • entailment / neutral / contradiction                     │ │
│  │  • Si contradiction > threshold → regenerar                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Búsqueda Híbrida (BM25 + Vector + RRF)

```
┌─────────────────────────────────────────────────────────────────┐
│                     HYBRID SEARCH SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Query: "Find developers with React and TypeScript experience"  │
│                              │                                   │
│          ┌───────────────────┴───────────────────┐              │
│          ▼                                       ▼              │
│  ┌─────────────────┐                 ┌─────────────────┐        │
│  │  BM25 SEARCH    │                 │  VECTOR SEARCH  │        │
│  │  (Lexical)      │                 │  (Semantic)     │        │
│  │                 │                 │                 │        │
│  │  Busca:         │                 │  Entiende:      │        │
│  │  "React"        │                 │  "frontend dev" │        │
│  │  "TypeScript"   │                 │  ≈ "React dev"  │        │
│  │  exactamente    │                 │  ≈ "UI engineer"│        │
│  │                 │                 │                 │        │
│  │  Rank: [3,7,1]  │                 │  Rank: [1,5,3]  │        │
│  └────────┬────────┘                 └────────┬────────┘        │
│           │                                   │                  │
│           └─────────────┬─────────────────────┘                  │
│                         ▼                                        │
│           ┌─────────────────────────┐                           │
│           │  RECIPROCAL RANK FUSION │                           │
│           │  (RRF with k=60)        │                           │
│           │                         │                           │
│           │  score = Σ 1/(k + rank) │                           │
│           │                         │                           │
│           │  Combina lo mejor de    │                           │
│           │  ambos mundos           │                           │
│           └────────────┬────────────┘                           │
│                        ▼                                         │
│           Final Ranking: [1, 3, 5, 7, ...]                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**¿Por qué híbrido?**
- **BM25** encuentra términos exactos (nombres de tecnologías, certificaciones)
- **Vector** entiende sinónimos y contexto
- **RRF** combina rankings sin necesidad de normalizar scores

### 5.3 Output Orchestrator Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR PATTERN                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Query Understanding detecta: query_type = "ranking"            │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  ORCHESTRATOR (orchestrator.py)                              ││
│  │                                                              ││
│  │  ROUTING TABLE:                                              ││
│  │  "ranking"    → RankingStructure                             ││
│  │  "search"     → SearchStructure                              ││
│  │  "comparison" → ComparisonStructure                          ││
│  │  "red_flags"  → RiskAssessmentStructure                      ││
│  │  ...                                                         ││
│  └──────────────────────────┬──────────────────────────────────┘│
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  RANKING STRUCTURE                                           ││
│  │                                                              ││
│  │  Compone estos MODULES:                                      ││
│  │  1. ThinkingModule      → Razonamiento visible               ││
│  │  2. DirectAnswerModule  → Respuesta directa                  ││
│  │  3. RankingTableModule  → Tabla con ranking                  ││
│  │  4. RankingCriteriaModule → Criterios usados                 ││
│  │  5. TopPickModule       → Card del mejor candidato           ││
│  │  6. ConclusionModule    → Conclusión final                   ││
│  └──────────────────────────┬──────────────────────────────────┘│
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  structured_output JSON                                      ││
│  │  {                                                           ││
│  │    "structure_type": "ranking",                              ││
│  │    "thinking": "Analyzing 5 candidates for backend...",      ││
│  │    "direct_answer": "Top candidate is Juan García",          ││
│  │    "ranking_table": { "headers": [...], "rows": [...] },     ││
│  │    "top_pick": { "name": "Juan García", "score": 95 },       ││
│  │    "conclusion": "Juan is the strongest candidate..."        ││
│  │  }                                                           ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Beneficios del patrón:**
- **Modular:** Agregar nueva estructura = crear una clase
- **Reutilizable:** ThinkingModule usado en 9 estructuras
- **Testeable:** Cada módulo se puede testear independientemente
- **Extensible:** Nuevos módulos sin modificar existentes

---

## 6. MÉTRICAS Y RENDIMIENTO

### 6.1 Tiempos Típicos del Pipeline

| Stage | Tiempo | % del Total |
|-------|--------|-------------|
| Query Understanding | 150ms | 5% |
| Multi-Query | 100ms | 3% |
| Guardrails | 50ms | 2% |
| Embedding | 45ms | 2% |
| Vector Search | 120ms | 4% |
| Cross-Encoder Reranking | 200ms | 7% |
| LLM Generation | 2000ms | 66% |
| NLI Verification | 150ms | 5% |
| RAGAS Evaluation | 100ms | 3% |
| Orchestration | 50ms | 2% |
| **TOTAL** | **~3000ms** | **100%** |

### 6.2 Costos por Operación

| Operación | Modelo | Costo Aproximado |
|-----------|--------|------------------|
| Query Understanding | Modelos gratis OpenRouter | ~$0.00001/query |
| Embeddings (Cloud) | nomic-embed-v1.5 | ~$0.02/1M tokens |
| Embeddings (Local) | sentence-transformers | $0 |
| LLM Generation | GPT-4o/Claude 3.5 | ~$0.01/query |
| HuggingFace Services | NLI + Reranker | $0 (gratis) |
| RAGAS Evaluation | Métricas | ~$0.002/query |

**Uso típico (30 CVs, 50 queries):** ~$0.10-0.20
**Modo LOCAL completo:** $0 (solo OpenRouter para generación)

---

## 7. RESUMEN EJECUTIVO

### 7.1 Lo que hace único a este proyecto

| Característica | Descripción |
|----------------|-------------|
| **Dual-Mode Architecture** | Mismo código, LOCAL (desarrollo) o CLOUD (producción) |
| **11-Stage RAG Pipeline** | Más completo que implementaciones típicas |
| **3-Layer Anti-Hallucination** | Guardrails + Grounding + NLI Verification |
| **9 Structured Outputs** | No solo texto, UI estructurada por tipo de query |
| **29+ Reusable Modules** | Arquitectura de componentes como en frontend |
| **Free HuggingFace Integration** | NLI, Reranking, Guardrails sin costo |
| **Conversational Context** | Resolución de pronombres, follow-ups naturales |
| **Real-time Pipeline Visibility** | Usuario ve cada paso del procesamiento |

### 7.2 Stack Final Justificado

| Capa | Tecnología | Razón Principal |
|------|------------|-----------------|
| **Frontend** | React 18 + TypeScript | Componentes estructurados, type safety, ecosistema |
| **UI** | Tailwind + Shadcn | Desarrollo rápido, accesibilidad, dark mode |
| **Backend** | FastAPI + Python | Ecosistema AI/ML, async, validación automática |
| **DB Local** | JSON files | Zero setup, debuggeable, portable |
| **DB Cloud** | Supabase + pgvector | PostgreSQL managed, vector search nativo |
| **Embeddings Local** | sentence-transformers | Offline, gratis, baja latencia |
| **Embeddings Cloud** | nomic-embed-v1.5 | Alta calidad, 768 dims |
| **LLM** | OpenRouter | 100+ modelos, fallback, un API |
| **ML Services** | HuggingFace | NLI, reranking, guardrails gratis |

### 7.3 Para la Presentación - Puntos Clave

1. **Problema real:** Reclutadores pierden horas revisando CVs manualmente
2. **Solución elegante:** Preguntas naturales con respuestas estructuradas
3. **Tecnología de punta:** RAG, embeddings, LLMs, NLI verification
4. **Zero hallucinations:** 3 capas de verificación
5. **Dual mode:** Desarrollo local gratis, producción cloud escalable
6. **Arquitectura modular:** 9 estructuras, 29+ módulos reutilizables
7. **Costo eficiente:** ~$0.10-0.20 para 50 queries, gratis en local
8. **Production-ready:** 2900+ líneas de pipeline, tests, documentación

---

*Documento generado para presentación técnica del proyecto AI-Powered CV Screener v7.0*
