# Plan de Implementación RAG v5.0 - Mejora Integral

> **Objetivo**: Transformar el sistema RAG de un pipeline básico a un sistema inteligente con razonamiento profundo, capacidades agénticas y respuestas de calidad humana.

**Fecha**: Enero 2026  
**Versión Objetivo**: 5.0.0

---

## Diagnóstico del Sistema Actual

### Problemas Identificados

| Área | Problema | Impacto |
|------|----------|---------|
| **Query Understanding** | Solo reformula queries, sin análisis profundo | Queries complejas mal interpretadas |
| **Chunking** | Regex básico por secciones | Pérdida de contexto semántico |
| **Retrieval** | Vector search simple, sin estrategias avanzadas | Chunks irrelevantes recuperados |
| **Reranking** | Scoring 0-10 superficial | No considera relaciones entre chunks |
| **Generación** | Sin razonamiento estructurado real | Respuestas genéricas, sin análisis |
| **Verificación** | Heurísticas básicas | Hallucinations no detectadas |
| **Arquitectura** | Pipeline lineal sin feedback | No aprende de errores |

### Síntomas Observados
- Respuestas genéricas que un humano superaría fácilmente
- No hay análisis comparativo real entre candidatos
- Rankings arbitrarios sin justificación profunda
- Falta de razonamiento visible en las respuestas
- El sistema no "piensa" - solo concatena información

---

## Arquitectura Propuesta v5.0

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           QUERY ENTRADA                                      │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  FASE 1: ANÁLISIS INTELIGENTE DE QUERY                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 1.1 Query Decomposition (descomponer en sub-preguntas)                  ││
│  │ 1.2 Intent Classification (clasificar intención real)                   ││
│  │ 1.3 Entity Extraction (extraer skills, roles, empresas)                 ││
│  │ 1.4 Multi-Query Generation (generar variaciones semánticas)             ││
│  │ 1.5 HyDE (generar documento hipotético ideal)                           ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  FASE 2: RETRIEVAL AVANZADO                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 2.1 Hybrid Search (vector + keyword BM25)                               ││
│  │ 2.2 Multi-Vector Retrieval (queries + HyDE + entities)                  ││
│  │ 2.3 Parent-Child Retrieval (chunk → documento completo)                 ││
│  │ 2.4 Contextual Compression (filtrar ruido)                              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  FASE 3: RERANKING PROFUNDO                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 3.1 Cross-Encoder Reranking (comparación par a par)                     ││
│  │ 3.2 Diversity Filtering (evitar redundancia)                            ││
│  │ 3.3 Relevance Explanation (por qué cada chunk es relevante)             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  FASE 4: RAZONAMIENTO AGÉNTICO                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 4.1 Chain-of-Thought Estructurado                                       ││
│  │ 4.2 Self-Ask (preguntas de seguimiento automáticas)                     ││
│  │ 4.3 Tool Use (búsquedas adicionales si falta info)                      ││
│  │ 4.4 Reflection (auto-evaluación antes de responder)                     ││
│  │ 4.5 Multi-Step Reasoning (análisis iterativo)                           ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  FASE 5: GENERACIÓN CON VERIFICACIÓN                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 5.1 Structured Output Generation                                        ││
│  │ 5.2 Claim-Level Verification                                            ││
│  │ 5.3 Confidence Calibration                                              ││
│  │ 5.4 Iterative Refinement                                                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## FASE 1: Query Understanding Avanzado

### 1.1 Query Decomposition
**Problema**: Queries complejas como "Rankea los candidatos por experiencia y dime cuáles trabajaron en FAANG" requieren múltiples análisis.

**Solución**: Descomponer en sub-tareas atómicas.

```python
# Nuevo: QueryDecomposer
class QueryDecomposer:
    async def decompose(self, query: str) -> list[SubQuery]:
        """
        Ejemplo:
        Input: "Rankea los 50 candidatos por experiencia y muestra si trabajaron en Google"
        Output: [
            SubQuery(type="ranking", criteria="experience", scope="all_candidates"),
            SubQuery(type="filter", attribute="company", values=["Google", "FAANG"]),
            SubQuery(type="aggregate", operation="count_per_group")
        ]
        """
```

### 1.2 Multi-Query Generation
**Problema**: Una sola query puede no capturar todos los chunks relevantes.

**Solución**: Generar variaciones semánticas.

```python
# Nuevo: MultiQueryGenerator
class MultiQueryGenerator:
    async def generate_variations(self, query: str) -> list[str]:
        """
        Input: "¿Quién sabe Python?"
        Output: [
            "Candidatos con experiencia en Python",
            "Desarrolladores Python",
            "Skills: Python, Django, Flask, FastAPI",
            "Programadores con conocimiento de Python"
        ]
        """
```

### 1.3 HyDE (Hypothetical Document Embeddings)
**Problema**: Embeddings de queries cortas no capturan bien la semántica.

**Solución**: Generar un "documento ideal" hipotético y buscar con ese embedding.

```python
# Nuevo: HyDEGenerator  
class HyDEGenerator:
    async def generate_hypothetical_document(self, query: str) -> str:
        """
        Input: "¿Quién tiene más experiencia en ML?"
        Output: "Juan García - Senior ML Engineer con 8 años de experiencia
                 en Machine Learning. Expertise en TensorFlow, PyTorch, 
                 modelos de deep learning, NLP y computer vision.
                 Trabajó en Google AI y Meta..."
        """
```

### 1.4 Entity Extraction
**Problema**: No se extraen entidades específicas para búsqueda precisa.

```python
# Nuevo: EntityExtractor
@dataclass
class ExtractedEntities:
    skills: list[str]           # ["Python", "React", "AWS"]
    companies: list[str]        # ["Google", "Microsoft"]
    roles: list[str]            # ["Senior Developer", "Tech Lead"]
    experience_years: int | None # 5
    education: list[str]        # ["Master's", "Computer Science"]
    locations: list[str]        # ["Madrid", "Remote"]
```

---

## FASE 2: Retrieval Avanzado

### 2.1 Hybrid Search (Vector + BM25)
**Problema**: Vector search solo no captura keywords exactos.

```python
# Nuevo: HybridRetriever
class HybridRetriever:
    async def search(self, query: str, entities: ExtractedEntities) -> list[Chunk]:
        # 1. Vector search con embedding de query
        vector_results = await self.vector_search(query)
        
        # 2. BM25 keyword search para términos exactos
        keyword_results = await self.keyword_search(entities.skills + entities.companies)
        
        # 3. Fusion con Reciprocal Rank Fusion (RRF)
        return self.rrf_fusion(vector_results, keyword_results)
```

### 2.2 Parent-Child Retrieval
**Problema**: Chunks pequeños pierden contexto.

**Solución**: Almacenar chunks pequeños pero recuperar el CV completo cuando es relevante.

```python
# Nuevo: ParentChildRetriever
class ParentChildRetriever:
    async def retrieve_with_context(self, chunks: list[Chunk]) -> list[EnrichedChunk]:
        """
        Si un chunk de "skills" es relevante, incluir también
        la sección de "experience" del mismo CV para contexto.
        """
```

### 2.3 Contextual Compression
**Problema**: Chunks contienen información irrelevante.

```python
# Nuevo: ContextualCompressor
class ContextualCompressor:
    async def compress(self, query: str, chunks: list[Chunk]) -> list[Chunk]:
        """
        Extraer SOLO las partes del chunk relevantes para la query.
        Reduce tokens y mejora precisión.
        """
```

---

## FASE 3: Reranking Profundo

### 3.1 Cross-Encoder Reranking
**Problema**: Scoring individual no considera relaciones.

```python
# Mejorado: DeepRerankingService
class DeepRerankingService:
    async def rerank(self, query: str, chunks: list[Chunk]) -> RerankResult:
        """
        Usar modelo cross-encoder que compara query+chunk juntos,
        no embeddings separados. Más preciso pero más lento.
        """
```

### 3.2 Diversity-Aware Reranking
**Problema**: Chunks redundantes de un mismo CV.

```python
# Nuevo: DiversityReranker
class DiversityReranker:
    async def rerank_with_diversity(
        self, 
        chunks: list[Chunk],
        lambda_diversity: float = 0.3
    ) -> list[Chunk]:
        """
        MMR (Maximal Marginal Relevance):
        Score = λ * relevance - (1-λ) * max_similarity_to_selected
        """
```

---

## FASE 4: Razonamiento Agéntico

### 4.1 Chain-of-Thought Estructurado
**Problema**: El LLM no "piensa" realmente.

```python
# Nuevo: StructuredCoTGenerator
COT_PROMPT = """
## ANÁLISIS PASO A PASO

### Paso 1: Comprensión
¿Qué está pidiendo exactamente el usuario?
- Tipo de consulta: {query_type}
- Criterios específicos: {criteria}
- Expectativa de formato: {expected_format}

### Paso 2: Inventario de Datos
¿Qué información tengo disponible?
- Total de candidatos: {num_candidates}
- Secciones disponibles: {sections}
- Datos faltantes: {missing_data}

### Paso 3: Análisis por Candidato
Para cada candidato relevante:
| Candidato | Criterio 1 | Criterio 2 | Evidencia | Score |
|-----------|------------|------------|-----------|-------|

### Paso 4: Síntesis
Basado en el análisis anterior...

### Paso 5: Verificación
¿Mi respuesta está fundamentada en los CVs?
- Afirmaciones verificadas: ✓
- Posibles gaps: ...
"""
```

### 4.2 Self-Ask Pattern
**Problema**: El sistema no se hace preguntas de seguimiento.

```python
# Nuevo: SelfAskAgent
class SelfAskAgent:
    async def reason(self, query: str, context: str) -> AgentResponse:
        """
        1. ¿Necesito más información para responder?
           → Si sí: generar sub-query y buscar
        2. ¿Hay ambigüedad que deba resolver?
           → Si sí: pedir clarificación O hacer suposición explícita
        3. ¿Puedo responder con confianza?
           → Si no: indicar limitaciones
        """
```

### 4.3 Tool Use (Agentic RAG)
**Problema**: Pipeline rígido, no puede hacer búsquedas adicionales.

```python
# Nuevo: AgenticRAG
class AgenticRAG:
    tools = [
        SearchCandidatesTool(),      # Buscar candidatos por criterio
        CompareCandidatesTool(),     # Comparar dos candidatos
        GetCVDetailTool(),           # Obtener CV completo
        AggregateStatsTool(),        # Estadísticas agregadas
    ]
    
    async def execute(self, query: str) -> Response:
        """
        El LLM decide qué tools usar y en qué orden.
        Permite razonamiento multi-paso real.
        """
```

### 4.4 Reflection Before Response
**Problema**: No hay auto-evaluación.

```python
# Nuevo: ReflectionStep
REFLECTION_PROMPT = """
Antes de dar tu respuesta final, responde:

1. ¿Mi respuesta contesta DIRECTAMENTE lo que preguntó el usuario?
2. ¿Cada afirmación tiene evidencia del CV correspondiente?
3. ¿Hay algún candidato que debería haber considerado pero no lo hice?
4. ¿El ranking/comparación es justo y objetivo?
5. ¿Qué nivel de confianza tengo? (alto/medio/bajo)

Si identificas problemas, CORRIGE antes de responder.
"""
```

---

## FASE 5: Generación con Verificación

### 5.1 Claim-Level Verification
**Problema**: Verificación actual es superficial.

```python
# Mejorado: ClaimVerifier
class ClaimVerifier:
    async def verify_response(self, response: str, context: list[Chunk]) -> VerificationResult:
        """
        1. Extraer cada claim de la respuesta
        2. Para cada claim, buscar evidencia en context
        3. Marcar claims como: VERIFIED, UNVERIFIED, CONTRADICTED
        4. Si hay claims no verificados, regenerar respuesta
        """
```

### 5.2 Iterative Refinement
**Problema**: Una sola pasada de generación.

```python
# Nuevo: IterativeGenerator
class IterativeGenerator:
    async def generate(self, query: str, context: list[Chunk]) -> str:
        # Paso 1: Generar draft
        draft = await self.llm.generate(query, context)
        
        # Paso 2: Auto-critique
        critique = await self.critic.evaluate(draft, context)
        
        # Paso 3: Si hay problemas, refinar
        if critique.has_issues:
            refined = await self.llm.refine(draft, critique.feedback)
            return refined
        
        return draft
```

---

## Implementación por Fases

### Fase A: Quick Wins (1-2 días)
1. **Mejorar prompts existentes** con CoT estructurado
2. **Añadir Multi-Query** al QueryUnderstandingService
3. **Mejorar formato de contexto** para incluir más metadata

### Fase B: Retrieval (3-5 días)
1. **Implementar HyDE** en EmbeddingStep
2. **Añadir keyword search** con pg_trgm o full-text search
3. **Parent-Child retrieval** con chunks jerárquicos

### Fase C: Razonamiento (5-7 días)
1. **Self-Ask pattern** en GenerationStep
2. **Reflection step** antes de respuesta final
3. **Tool use básico** para búsquedas adicionales

### Fase D: Verificación (3-4 días)
1. **Claim extraction** de respuestas
2. **Evidence matching** por claim
3. **Iterative refinement** si hay problemas

---

## Métricas de Éxito

| Métrica | Actual (estimado) | Objetivo v5.0 |
|---------|-------------------|---------------|
| Precisión de respuestas | ~60% | >90% |
| Relevancia de retrieval | ~70% | >85% |
| Detección de hallucinations | ~50% | >95% |
| Satisfacción usuario | Baja | Alta |
| Tiempo de respuesta | <5s | <8s (aceptable por calidad) |

---

## Archivos a Modificar/Crear

### Nuevos Servicios
```
backend/app/services/
├── query_decomposer.py          # NUEVO
├── multi_query_generator.py     # NUEVO
├── hyde_generator.py            # NUEVO
├── entity_extractor.py          # NUEVO
├── hybrid_retriever.py          # NUEVO
├── contextual_compressor.py     # NUEVO
├── diversity_reranker.py        # NUEVO
├── self_ask_agent.py            # NUEVO
├── reflection_service.py        # NUEVO
├── claim_verifier.py            # NUEVO
├── iterative_generator.py       # NUEVO
└── agentic_rag.py               # NUEVO
```

### Servicios a Mejorar
```
backend/app/services/
├── query_understanding_service.py  # MEJORAR
├── reranking_service.py            # MEJORAR
├── chunking_service.py             # MEJORAR
└── rag_service_v3.py → v5.py       # REFACTORIZAR
```

### Prompts a Añadir
```
backend/app/prompts/
├── templates.py                    # MEJORAR
├── cot_templates.py                # NUEVO
├── reflection_templates.py         # NUEVO
└── agentic_templates.py            # NUEVO
```

---

## Próximos Pasos Inmediatos

1. **Priorizar**: ¿Qué mejora dará más impacto inmediato?
2. **Prototipar**: Implementar Multi-Query + HyDE primero
3. **Evaluar**: Crear test set para medir mejoras
4. **Iterar**: Implementar por fases con validación continua

---

*Este plan transforma el sistema de un pipeline básico a un sistema con razonamiento profundo y capacidades agénticas.*
