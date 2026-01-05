# CV Screener RAG v6 - Implementation Plan

## Your Current Pipeline vs. Industry Best Practices

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        TU PIPELINE ACTUAL (v5)                             │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  1. Understanding ──► 2. Multi-Query ──► 3. Safety ──► 4. Embeddings       │
│       [LLM]              [LLM]           [REGEX]        [OpenRouter]       │
│                                            ⚠️                              │
│                                                                            │
│  ──► 5. Searching ──► 6. Re-ranking ──► 7. Analyzing ──► 8. Generating     │
│       [pgvector]        [LLM]             [LLM]           [LLM]            │
│                          ⚠️                                                │
│                                                                            │
│  ──► 9. Verifying ──► 10. Refining                                         │
│       [LLM+Regex]        [LLM]                                             │
│          ⚠️                                                                │
│                                                                            │
│  ⚠️ = Puntos débiles (hardcoded o ineficiente)                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Services & Models Map (ALL FREE or Very Cheap)

### Complete Provider Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PROVIDERS POR COMPONENTE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     OPENROUTER (Ya tienes)                          │    │
│  │  ────────────────────────────────────────────────────────────────   │    │
│  │  ✓ LLM Principal: google/gemini-2.0-flash-exp:free         FREE    │    │
│  │  ✓ LLM Judge: openai/gpt-4o-mini                      $0.15/1M    │    │
│  │  ✓ Embeddings: nomic-ai/nomic-embed-text-v1.5        $0.02/1M    │    │
│  │                                                                     │    │
│  │  Usar para: Query Understanding, Multi-Query, Reasoning,           │    │
│  │             Generation, LLM-as-Judge                                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                   HUGGINGFACE INFERENCE API (FREE)                  │    │
│  │  ────────────────────────────────────────────────────────────────   │    │
│  │  ✓ NLI Model: microsoft/deberta-v3-base-mnli              FREE    │    │
│  │  ✓ Cross-Encoder Reranker: BAAI/bge-reranker-base        FREE    │    │
│  │  ✓ NER (nombres): dslim/bert-base-NER                     FREE    │    │
│  │  ✓ Guardrails NLI: MoritzLaurer/deberta-v3-base-zeroshot  FREE    │    │
│  │                                                                     │    │
│  │  Rate limit: 30,000 requests/hour (más que suficiente)             │    │
│  │                                                                     │    │
│  │  Usar para: Verification (NLI), Reranking, Safety Check,           │    │
│  │             Entity extraction                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      LOCAL (sentence-transformers)                  │    │
│  │  ────────────────────────────────────────────────────────────────   │    │
│  │  ✓ Similarity: all-MiniLM-L6-v2                           FREE    │    │
│  │  ✓ Reranker: cross-encoder/ms-marco-MiniLM-L-6-v2        FREE    │    │
│  │                                                                     │    │
│  │  Usar para: Fallback si HuggingFace API no disponible              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         RAGAS (Local Library)                       │    │
│  │  ────────────────────────────────────────────────────────────────   │    │
│  │  ✓ pip install ragas                                      FREE    │    │
│  │                                                                     │    │
│  │  Usar para: Evals automáticos (faithfulness, relevance, etc.)      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      LANGSMITH (Optional)                           │    │
│  │  ────────────────────────────────────────────────────────────────   │    │
│  │  ✓ Free tier: 5,000 traces/month                          FREE    │    │
│  │                                                                     │    │
│  │  Usar para: Tracing, debugging, observability                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Pipeline Step-by-Step: What to Use Where

### Step 1: Query Understanding

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: QUERY UNDERSTANDING                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ACTUAL: ✅ LLM (OpenRouter) - MANTENER                                      │
│                                                                              │
│  ¿Cambiar a modelo específico? NO                                           │
│  Razón: LLM es necesario para entender intención y reformular               │
│                                                                              │
│  Provider: OpenRouter                                                        │
│  Model: google/gemini-2.0-flash-exp:free                                    │
│  Cost: FREE                                                                  │
│                                                                              │
│  ¿LangChain? OPCIONAL - LangChain tiene PromptTemplate que puede ayudar     │
│  ¿LangGraph? NO necesario aquí                                              │
│                                                                              │
│  ACCIÓN: Mantener como está                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step 2: Multi-Query + HyDE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: MULTI-QUERY + HyDE                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ACTUAL: ✅ LLM (OpenRouter) - MANTENER                                      │
│                                                                              │
│  ¿Cambiar a modelo específico? NO                                           │
│  Razón: Necesitas LLM para generar variaciones y documentos hipotéticos     │
│                                                                              │
│  Provider: OpenRouter                                                        │
│  Model: google/gemini-2.0-flash-exp:free                                    │
│  Cost: FREE                                                                  │
│                                                                              │
│  ¿LangChain? SÍ - MultiQueryRetriever está implementado                     │
│  ¿LangGraph? NO necesario aquí                                              │
│                                                                              │
│  ACCIÓN: Considerar usar LangChain MultiQueryRetriever para simplificar     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step 3: Safety Check (Guardrails) ⚠️ MEJORAR

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: SAFETY CHECK (GUARDRAILS)                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ACTUAL: ⚠️ Regex + Keywords hardcodeados - MEJORAR                         │
│                                                                              │
│  PROBLEMA:                                                                   │
│  - CV_KEYWORDS hardcodeados (~100 palabras)                                  │
│  - OFF_TOPIC_PATTERNS con regex frágiles                                     │
│  - No escala, muchos falsos positivos/negativos                              │
│                                                                              │
│  SOLUCIÓN: Zero-Shot Classification (HuggingFace FREE)                       │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  MODELO RECOMENDADO                                                   │  │
│  │                                                                       │  │
│  │  Provider: HuggingFace Inference API                                  │  │
│  │  Model: MoritzLaurer/deberta-v3-base-zeroshot-v2.0                   │  │
│  │  Task: Zero-shot classification                                       │  │
│  │  Cost: FREE                                                           │  │
│  │                                                                       │  │
│  │  Input: "What's the weather today?"                                   │  │
│  │  Labels: ["CV-related question", "off-topic question"]                │  │
│  │  Output: {"CV-related": 0.12, "off-topic": 0.88} → REJECT             │  │
│  │                                                                       │  │
│  │  Input: "Who has Python experience?"                                  │  │
│  │  Labels: ["CV-related question", "off-topic question"]                │  │
│  │  Output: {"CV-related": 0.95, "off-topic": 0.05} → ACCEPT             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ALTERNATIVE: Guardrails AI library con LLM                                  │
│  - pip install guardrails-ai                                                 │
│  - Define validators en YAML                                                 │
│  - Más flexible pero más lento                                               │
│                                                                              │
│  ¿LangChain? NO necesario                                                    │
│  ¿LangGraph? NO necesario                                                    │
│                                                                              │
│  ACCIÓN: Añadir Zero-Shot classifier + mantener regex como fallback         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step 4: Embeddings

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: EMBEDDINGS                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ACTUAL: ✅ OpenRouter (nomic-embed) - MANTENER                              │
│                                                                              │
│  Provider: OpenRouter                                                        │
│  Model: nomic-ai/nomic-embed-text-v1.5                                      │
│  Dimensions: 768                                                             │
│  Cost: $0.02/1M tokens (muy barato)                                         │
│                                                                              │
│  ALTERNATIVA GRATIS (si quieres):                                           │
│  Provider: HuggingFace Inference API                                         │
│  Model: BAAI/bge-base-en-v1.5                                               │
│  Cost: FREE                                                                  │
│                                                                              │
│  ¿LangChain? SÍ - LangChain tiene HuggingFaceEmbeddings wrapper             │
│  ¿LangGraph? NO necesario                                                    │
│                                                                              │
│  ACCIÓN: Mantener OpenRouter o migrar a HuggingFace gratis                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step 5: Searching CVs

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: SEARCHING CVs                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ACTUAL: ✅ Supabase pgvector + Fusion - MANTENER                            │
│                                                                              │
│  Provider: Supabase                                                          │
│  Technology: pgvector (PostgreSQL)                                           │
│  Cost: FREE tier                                                             │
│                                                                              │
│  Tu implementación con RRF-like fusion es buena.                            │
│                                                                              │
│  ¿LangChain? SÍ - SupabaseVectorStore disponible                            │
│  ¿LangGraph? NO necesario                                                    │
│                                                                              │
│  ACCIÓN: Mantener como está                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step 6: Re-ranking ⚠️ MEJORAR

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: RE-RANKING                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ACTUAL: ⚠️ LLM scoring - CARO y LENTO                                       │
│                                                                              │
│  PROBLEMA:                                                                   │
│  - Cada documento requiere una llamada LLM                                   │
│  - Lento (~500ms por documento)                                              │
│  - Costoso si usas modelo de pago                                            │
│                                                                              │
│  SOLUCIÓN: Cross-Encoder (HuggingFace FREE)                                  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  MODELO RECOMENDADO                                                   │  │
│  │                                                                       │  │
│  │  Provider: HuggingFace Inference API                                  │  │
│  │  Model: BAAI/bge-reranker-base                                       │  │
│  │  Task: Text classification (relevance scoring)                        │  │
│  │  Cost: FREE                                                           │  │
│  │  Speed: ~50ms para 10 documentos (vs 5000ms con LLM)                 │  │
│  │                                                                       │  │
│  │  ALTERNATIVAS:                                                        │  │
│  │  - BAAI/bge-reranker-v2-m3 (mejor, más grande)                       │  │
│  │  - cross-encoder/ms-marco-MiniLM-L-6-v2 (más rápido)                 │  │
│  │  - mixedbread-ai/mxbai-rerank-base-v1 (muy bueno)                    │  │
│  │                                                                       │  │
│  │  Input: [query, document] pairs                                       │  │
│  │  Output: relevance score (0-1)                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ¿LangChain? SÍ - CohereRerank o custom reranker                            │
│  ¿LangGraph? NO necesario                                                    │
│                                                                              │
│  ACCIÓN: Reemplazar LLM reranking con Cross-Encoder                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step 7: Analyzing (Reasoning)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 7: ANALYZING (REASONING)                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ACTUAL: ✅ LLM Chain-of-Thought - MANTENER                                  │
│                                                                              │
│  Provider: OpenRouter                                                        │
│  Model: google/gemini-2.0-flash-exp:free                                    │
│  Cost: FREE                                                                  │
│                                                                              │
│  Chain-of-Thought requiere LLM, no hay modelo específico mejor.             │
│                                                                              │
│  ¿LangChain? OPCIONAL - Tiene prompts de CoT                                │
│  ¿LangGraph? CONSIDERAR - Si quieres reasoning con múltiples pasos          │
│                                                                              │
│  ACCIÓN: Mantener, considerar LangGraph para flujos complejos               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step 8: Generating

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 8: GENERATING                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ACTUAL: ✅ LLM (OpenRouter) - MANTENER                                      │
│                                                                              │
│  Provider: OpenRouter                                                        │
│  Model: google/gemini-2.0-flash-exp:free                                    │
│  Cost: FREE                                                                  │
│                                                                              │
│  ¿LangChain? SÍ - ChatOpenAI compatible con OpenRouter                      │
│  ¿LangGraph? CONSIDERAR - Para generación con branching/retry               │
│                                                                              │
│  ACCIÓN: Mantener, integrar LangChain para estandarizar                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step 9: Verifying ⚠️ MEJORAR

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 9: VERIFYING (Claim Verification)                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ACTUAL: ⚠️ LLM + Regex heurísticas - MEJORAR                               │
│                                                                              │
│  PROBLEMA:                                                                   │
│  - ClaimVerifierService usa LLM (funciona pero costoso)                      │
│  - HallucinationService usa regex patterns (frágil)                          │
│  - No hay NLI real para verificar entailment                                 │
│                                                                              │
│  SOLUCIÓN: NLI Model (HuggingFace FREE)                                      │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  MODELO RECOMENDADO                                                   │  │
│  │                                                                       │  │
│  │  Provider: HuggingFace Inference API                                  │  │
│  │  Model: microsoft/deberta-v3-base-mnli                               │  │
│  │  Task: Natural Language Inference                                     │  │
│  │  Cost: FREE                                                           │  │
│  │                                                                       │  │
│  │  Cómo funciona:                                                       │  │
│  │  ────────────────────────────────────────────────────────────────    │  │
│  │  Premise (contexto): "María García, Python 5 años, DataCorp"         │  │
│  │  Hypothesis (claim): "María tiene 5 años de experiencia en Python"   │  │
│  │                                                                       │  │
│  │  Output:                                                              │  │
│  │  - ENTAILMENT: 0.94  ← Claim is SUPPORTED ✓                          │  │
│  │  - NEUTRAL: 0.04                                                      │  │
│  │  - CONTRADICTION: 0.02                                                │  │
│  │                                                                       │  │
│  │  ────────────────────────────────────────────────────────────────    │  │
│  │  Premise: "María García, Python 5 años, DataCorp"                    │  │
│  │  Hypothesis: "María trabajó en Google"                               │  │
│  │                                                                       │  │
│  │  Output:                                                              │  │
│  │  - ENTAILMENT: 0.05                                                   │  │
│  │  - NEUTRAL: 0.15                                                      │  │
│  │  - CONTRADICTION: 0.80  ← Claim is UNSUPPORTED/HALLUCINATION ✗       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ESTRATEGIA COMBINADA:                                                       │
│  1. Extraer claims con LLM (ya lo haces)                                     │
│  2. Verificar cada claim con NLI (AÑADIR)                                    │
│  3. LLM Judge como segunda opinión para casos dudosos                        │
│                                                                              │
│  ¿LangChain? NO necesario                                                    │
│  ¿LangGraph? CONSIDERAR - Para flujo de verificación con retry              │
│                                                                              │
│  ACCIÓN: Añadir NLI verification antes/después de LLM verification          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step 10: Refining

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 10: REFINING                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ACTUAL: ✅ LLM refinamiento iterativo - MANTENER                            │
│                                                                              │
│  Provider: OpenRouter                                                        │
│  Model: google/gemini-2.0-flash-exp:free                                    │
│  Cost: FREE                                                                  │
│                                                                              │
│  ¿LangChain? OPCIONAL                                                        │
│  ¿LangGraph? SÍ - Ideal para loops de refinamiento con condiciones          │
│                                                                              │
│  ACCIÓN: Considerar LangGraph para manejar el loop de refinamiento          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Dónde Usar LangChain vs LangGraph

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     LANGCHAIN vs LANGGRAPH                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         LANGCHAIN                                    │    │
│  │  ────────────────────────────────────────────────────────────────   │    │
│  │  Qué es: Biblioteca de COMPONENTES para LLM apps                    │    │
│  │                                                                      │    │
│  │  Usar para:                                                          │    │
│  │  ✓ Wrappers de LLM (ChatOpenAI compatible con OpenRouter)           │    │
│  │  ✓ Embeddings (HuggingFaceEmbeddings, OpenAIEmbeddings)             │    │
│  │  ✓ Vector stores (SupabaseVectorStore)                              │    │
│  │  ✓ Prompt templates                                                  │    │
│  │  ✓ Output parsers (JSON, structured output)                         │    │
│  │  ✓ Document loaders (PDF)                                            │    │
│  │  ✓ Text splitters (chunking)                                         │    │
│  │                                                                      │    │
│  │  NO usar para:                                                       │    │
│  │  ✗ Orquestación compleja                                            │    │
│  │  ✗ Flujos con estados                                                │    │
│  │  ✗ Branching condicional                                            │    │
│  │  ✗ Human-in-the-loop                                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         LANGGRAPH                                    │    │
│  │  ────────────────────────────────────────────────────────────────   │    │
│  │  Qué es: Framework de ORQUESTACIÓN con estados y grafos             │    │
│  │                                                                      │    │
│  │  Usar para:                                                          │    │
│  │  ✓ Pipeline RAG completo como grafo de estados                      │    │
│  │  ✓ Flujos con branching (if confidence < 0.5 → retry)               │    │
│  │  ✓ Loops de refinamiento con condiciones de salida                  │    │
│  │  ✓ Human-in-the-loop (pedir confirmación)                           │    │
│  │  ✓ Checkpointing (guardar estado)                                   │    │
│  │  ✓ Streaming de pasos intermedios                                   │    │
│  │                                                                      │    │
│  │  NO usar para:                                                       │    │
│  │  ✗ Pipelines simples lineales                                       │    │
│  │  ✗ Si tu código actual funciona bien                                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Recomendación para tu proyecto:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MI RECOMENDACIÓN                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. NO migres todo a LangChain/LangGraph ahora                               │
│     - Tu código Python custom funciona                                       │
│     - Migrar todo es trabajo sin valor inmediato                            │
│                                                                              │
│  2. USA LangChain SOLO para:                                                 │
│     - LLM wrapper (estandariza tu OpenRouter client)                        │
│     - Embeddings wrapper (si migras a HuggingFace)                          │
│     - SupabaseVectorStore (simplifica tu código)                            │
│                                                                              │
│  3. CONSIDERA LangGraph para:                                                │
│     - El loop de refinamiento (step 10)                                      │
│     - Si quieres añadir human-in-the-loop                                   │
│     - Si necesitas checkpointing para queries largos                        │
│                                                                              │
│  4. PRIORIZA modelos específicos sobre refactoring:                          │
│     - Añadir NLI (HuggingFace) tiene más impacto que LangGraph              │
│     - Añadir Cross-Encoder tiene más impacto que LangChain                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Arquitectura Propuesta v6

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RAG PIPELINE v6 (Proposed)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  1. QUERY UNDERSTANDING                                              │    │
│  │     Provider: OpenRouter (Gemini FREE)                               │    │
│  │     Change: None                                                     │    │
│  └───────────────────────────────────┬─────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  2. MULTI-QUERY + HyDE                                               │    │
│  │     Provider: OpenRouter (Gemini FREE)                               │    │
│  │     Change: None                                                     │    │
│  └───────────────────────────────────┬─────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  3. SAFETY CHECK                                                     │    │
│  │     Provider: HuggingFace Inference API (FREE)                       │    │
│  │     Model: MoritzLaurer/deberta-v3-base-zeroshot-v2.0 ← NEW         │    │
│  │     Fallback: Tu regex actual                                        │    │
│  │     Change: ADD zero-shot classifier                                 │    │
│  └───────────────────────────────────┬─────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  4. EMBEDDINGS                                                       │    │
│  │     Provider: OpenRouter OR HuggingFace (both work)                  │    │
│  │     Model: nomic-embed OR bge-base-en                               │    │
│  │     Change: Optional - can switch to free HF                         │    │
│  └───────────────────────────────────┬─────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  5. SEARCHING                                                        │    │
│  │     Provider: Supabase pgvector                                      │    │
│  │     Change: None                                                     │    │
│  └───────────────────────────────────┬─────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  6. RE-RANKING                                                       │    │
│  │     Provider: HuggingFace Inference API (FREE)                       │    │
│  │     Model: BAAI/bge-reranker-base ← NEW (replaces LLM)              │    │
│  │     Change: REPLACE LLM scoring with cross-encoder                   │    │
│  └───────────────────────────────────┬─────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  7. REASONING                                                        │    │
│  │     Provider: OpenRouter (Gemini FREE)                               │    │
│  │     Change: None                                                     │    │
│  └───────────────────────────────────┬─────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  8. GENERATING                                                       │    │
│  │     Provider: OpenRouter (Gemini FREE)                               │    │
│  │     Change: None                                                     │    │
│  └───────────────────────────────────┬─────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  9. VERIFYING                                                        │    │
│  │     Provider: HuggingFace Inference API (FREE)                       │    │
│  │     Model: microsoft/deberta-v3-base-mnli ← NEW (adds NLI)          │    │
│  │     + Keep existing LLM claim verification                           │    │
│  │     Change: ADD NLI verification layer                               │    │
│  └───────────────────────────────────┬─────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  10. REFINING                                                        │    │
│  │     Provider: OpenRouter (Gemini FREE)                               │    │
│  │     Optional: LangGraph for loop control                             │    │
│  │     Change: None (or add LangGraph)                                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## New Services to Add

### Service 1: HuggingFace Inference Client

```python
# backend/app/providers/huggingface_client.py

import httpx
from app.config import settings

class HuggingFaceClient:
    """Client for HuggingFace Inference API."""
    
    BASE_URL = "https://api-inference.huggingface.co/models"
    
    def __init__(self):
        self.api_key = settings.huggingface_api_key
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
    
    async def zero_shot_classification(
        self,
        text: str,
        labels: list[str],
        model: str = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"
    ) -> dict:
        """Classify text into labels."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/{model}",
                headers=self.headers,
                json={
                    "inputs": text,
                    "parameters": {"candidate_labels": labels}
                }
            )
            return response.json()
    
    async def nli_inference(
        self,
        premise: str,
        hypothesis: str,
        model: str = "microsoft/deberta-v3-base-mnli"
    ) -> dict:
        """Natural Language Inference."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/{model}",
                headers=self.headers,
                json={"inputs": f"{premise} [SEP] {hypothesis}"}
            )
            result = response.json()
            # Parse NLI output
            return {
                "entailment": self._get_score(result, "ENTAILMENT"),
                "neutral": self._get_score(result, "NEUTRAL"),
                "contradiction": self._get_score(result, "CONTRADICTION")
            }
    
    async def rerank(
        self,
        query: str,
        documents: list[str],
        model: str = "BAAI/bge-reranker-base"
    ) -> list[dict]:
        """Rerank documents by relevance."""
        pairs = [[query, doc] for doc in documents]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/{model}",
                headers=self.headers,
                json={"inputs": pairs}
            )
            scores = response.json()
        
        # Sort by score descending
        results = [
            {"document": doc, "score": score}
            for doc, score in zip(documents, scores)
        ]
        return sorted(results, key=lambda x: x["score"], reverse=True)
    
    def _get_score(self, result: list, label: str) -> float:
        for item in result:
            if item.get("label", "").upper() == label:
                return item.get("score", 0.0)
        return 0.0
```

### Service 2: Enhanced Guardrail Service

```python
# backend/app/services/guardrail_service_v2.py

from app.providers.huggingface_client import HuggingFaceClient

class GuardrailServiceV2:
    """Enhanced guardrails with zero-shot classification."""
    
    def __init__(self):
        self.hf_client = HuggingFaceClient()
        # Keep existing regex as fallback
        self.legacy_guardrails = GuardrailService()  # Your existing service
    
    async def check_query(self, query: str) -> dict:
        """Check if query is CV-related."""
        
        # Primary: Zero-shot classification
        try:
            result = await self.hf_client.zero_shot_classification(
                text=query,
                labels=[
                    "question about job candidates or CVs",
                    "question about resumes or work experience",
                    "off-topic question not related to hiring"
                ]
            )
            
            cv_score = (
                result.get("scores", [0, 0, 0])[0] +
                result.get("scores", [0, 0, 0])[1]
            ) / 2
            
            return {
                "is_allowed": cv_score > 0.5,
                "confidence": cv_score,
                "method": "zero-shot-classifier",
                "details": result
            }
            
        except Exception as e:
            # Fallback: Use existing regex-based guardrails
            legacy_result = self.legacy_guardrails.check(query)
            return {
                "is_allowed": legacy_result["passed"],
                "confidence": 0.5,  # Unknown confidence
                "method": "regex-fallback",
                "error": str(e)
            }
```

### Service 3: NLI Verification Service

```python
# backend/app/services/nli_verification_service.py

from app.providers.huggingface_client import HuggingFaceClient

class NLIVerificationService:
    """Verify claims using Natural Language Inference."""
    
    def __init__(self):
        self.hf_client = HuggingFaceClient()
    
    async def verify_claim(
        self,
        claim: str,
        context_chunks: list[str]
    ) -> dict:
        """
        Verify if a claim is supported by context.
        
        Returns:
            {
                "status": "supported" | "unsupported" | "contradicted",
                "confidence": float,
                "supporting_chunks": list[int]
            }
        """
        best_entailment = 0.0
        best_contradiction = 0.0
        supporting_chunks = []
        
        for i, chunk in enumerate(context_chunks):
            result = await self.hf_client.nli_inference(
                premise=chunk,
                hypothesis=claim
            )
            
            if result["entailment"] > 0.7:
                supporting_chunks.append(i)
                best_entailment = max(best_entailment, result["entailment"])
            
            best_contradiction = max(best_contradiction, result["contradiction"])
        
        # Determine status
        if best_entailment > 0.7:
            status = "supported"
            confidence = best_entailment
        elif best_contradiction > 0.7:
            status = "contradicted"
            confidence = best_contradiction
        else:
            status = "unsupported"
            confidence = 1 - max(best_entailment, best_contradiction)
        
        return {
            "claim": claim,
            "status": status,
            "confidence": confidence,
            "supporting_chunks": supporting_chunks
        }
    
    async def compute_faithfulness(
        self,
        claims: list[str],
        context_chunks: list[str]
    ) -> float:
        """Compute overall faithfulness score."""
        if not claims:
            return 1.0
        
        supported = 0
        for claim in claims:
            result = await self.verify_claim(claim, context_chunks)
            if result["status"] == "supported":
                supported += 1
            elif result["status"] == "contradicted":
                supported -= 0.5  # Penalty for contradictions
        
        return max(0, supported / len(claims))
```

### Service 4: Cross-Encoder Reranking Service

```python
# backend/app/services/reranking_service_v2.py

from app.providers.huggingface_client import HuggingFaceClient

class CrossEncoderRerankingService:
    """Fast reranking using cross-encoder models."""
    
    def __init__(self):
        self.hf_client = HuggingFaceClient()
        # Fallback to LLM reranking if HF fails
        self.llm_reranker = RerankingService()  # Your existing service
    
    async def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 5
    ) -> list[dict]:
        """Rerank documents using cross-encoder."""
        
        if not documents:
            return []
        
        try:
            # Extract text from documents
            texts = [doc.get("content", "") for doc in documents]
            
            # Get cross-encoder scores
            ranked = await self.hf_client.rerank(
                query=query,
                documents=texts,
                model="BAAI/bge-reranker-base"
            )
            
            # Map back to original documents with scores
            result = []
            for item in ranked[:top_k]:
                idx = texts.index(item["document"])
                doc = documents[idx].copy()
                doc["rerank_score"] = item["score"]
                result.append(doc)
            
            return result
            
        except Exception as e:
            # Fallback to LLM reranking
            return await self.llm_reranker.rerank(query, documents, top_k)
```

---

## Environment Variables to Add

```bash
# .env additions

# HuggingFace Inference API (FREE)
HUGGINGFACE_API_KEY=hf_...

# Get from: https://huggingface.co/settings/tokens
# Create token with "Read" access

# Model configuration
HF_NLI_MODEL=microsoft/deberta-v3-base-mnli
HF_RERANKER_MODEL=BAAI/bge-reranker-base
HF_ZEROSHOT_MODEL=MoritzLaurer/deberta-v3-base-zeroshot-v2.0

# Feature flags (enable gradually)
USE_HF_GUARDRAILS=true
USE_HF_RERANKER=true
USE_HF_NLI=true
```

---

## Dependencies to Add

```txt
# requirements.txt additions

# HuggingFace (for API client)
huggingface-hub>=0.20.0

# RAGAS for evals
ragas>=0.1.0
datasets>=2.16.0

# LangChain (optional, for standardization)
langchain>=0.1.0
langchain-community>=0.0.10

# LangGraph (optional, for orchestration)
langgraph>=0.0.20

# LangSmith (optional, for observability)
langsmith>=0.0.83
```

---

## Implementation Priority

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      IMPLEMENTATION PRIORITY                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PHASE 1: Quick Wins (2-3 hours) - HIGH IMPACT                               │
│  ─────────────────────────────────────────────────────────────────────────   │
│  □ Add HuggingFace API client                                                │
│  □ Implement Cross-Encoder reranking (replaces slow LLM reranking)          │
│  □ Add NLI verification service                                              │
│                                                                              │
│  PHASE 2: Guardrails Upgrade (1-2 hours)                                     │
│  ─────────────────────────────────────────────────────────────────────────   │
│  □ Add Zero-Shot classifier for guardrails                                   │
│  □ Keep regex as fallback                                                    │
│                                                                              │
│  PHASE 3: Integration (2-3 hours)                                            │
│  ─────────────────────────────────────────────────────────────────────────   │
│  □ Integrate NLI into verification step                                      │
│  □ Integrate Cross-Encoder into reranking step                               │
│  □ Update confidence calculation with new signals                            │
│                                                                              │
│  PHASE 4: Evals (1-2 hours)                                                  │
│  ─────────────────────────────────────────────────────────────────────────   │
│  □ Add RAGAS evaluation                                                      │
│  □ Create eval dataset from existing queries                                 │
│                                                                              │
│  PHASE 5: Optional - LangGraph (3-4 hours)                                   │
│  ─────────────────────────────────────────────────────────────────────────   │
│  □ Refactor pipeline to LangGraph (only if needed)                           │
│  □ Add checkpointing                                                         │
│  □ Add human-in-the-loop for low confidence                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Cost Summary (Monthly)

| Component | Provider | Cost |
|-----------|----------|------|
| LLM (Gemini) | OpenRouter | FREE |
| Embeddings | OpenRouter | ~$0.50 |
| Zero-Shot Guardrails | HuggingFace | FREE |
| Cross-Encoder Reranking | HuggingFace | FREE |
| NLI Verification | HuggingFace | FREE |
| LLM Judge (backup) | OpenRouter | ~$1-2 |
| **TOTAL** | | **~$2-3/month** |

---

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/providers/huggingface_client.py` | HuggingFace API client |
| `backend/app/services/guardrail_service_v2.py` | Zero-shot guardrails |
| `backend/app/services/nli_verification_service.py` | NLI claim verification |
| `backend/app/services/reranking_service_v2.py` | Cross-encoder reranking |

## Files to Update

| File | Changes |
|------|---------|
| `backend/app/services/rag_service_v5.py` → v6 | Integrate new services |
| `backend/app/services/hallucination_service.py` | Add NLI verification |
| `backend/app/services/confidence_calculator.py` | Add NLI signals |
| `backend/app/config.py` | Add HuggingFace settings |
| `backend/requirements.txt` | Add dependencies |

---

## Success Criteria

- [ ] Cross-Encoder reranking is 10x faster than LLM reranking
- [ ] NLI verification catches hallucinations that regex missed
- [ ] Zero-shot guardrails have fewer false positives than regex
- [ ] Overall pipeline latency stays under 5 seconds
- [ ] No increase in API costs (all new services are FREE)