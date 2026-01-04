# Plan de Implementación: Confidence Scoring Avanzado

## 🔴 ANÁLISIS HONESTO: Lo que tenemos vs. Lo que necesitamos

### Estado Actual (REALIDAD)

| Técnica | ¿La tenemos? | Cómo está implementada | Calidad |
|---------|--------------|------------------------|---------|
| **Claim Extraction** | ✅ Sí | LLM via OpenRouter extrae claims del response | 🟡 Básica |
| **Claim Verification** | ✅ Parcial | LLM verifica claim vs context (NO es NLI real) | 🟡 Básica |
| **Source Relevance** | ✅ Sí | Promedio de similarity scores del vector search | 🟢 Correcta |
| **Source Coverage** | ✅ Sí | Conteo de chunks + diversidad de CVs | 🟢 Correcta |
| **Response Completeness** | ✅ Sí | Checkea componentes del structured output | 🟢 Correcta |
| **Internal Consistency** | ✅ Parcial | Heurísticas básicas (tabla↔conclusión) | 🟡 Básica |
| **LLM-as-Judge** | ❌ NO | No implementado | ❌ |
| **NLI Models** | ❌ NO | Usamos LLM genérico, no modelo NLI especializado | ❌ |
| **Self-Consistency** | ❌ NO | Solo generamos 1 respuesta | ❌ |
| **Token Probabilities** | ❌ NO | OpenRouter no expone log_probs fácilmente | ❌ |
| **Citation Verification** | ❌ NO | No generamos citas inline verificables | ❌ |
| **Answer Relevance** | ❌ NO | No medimos similitud query↔response | ❌ |
| **Confidence Calibration** | ❌ NO | No tenemos histórico de feedback | ❌ |
| **RAGAS Metrics** | ❌ NO | No usamos el framework | ❌ |

### Veredicto Brutal

**Lo que implementé antes es FUNCIONAL pero NO es nivel industria.**

- ✅ **Sí es real**: Los scores vienen de datos reales (similarity scores, claim counts, etc.)
- ❌ **NO es avanzado**: Falta LLM-as-Judge, NLI, Self-Consistency, Answer Relevance
- 🟡 **Es un 30%** de lo que hacen Sierra/Perplexity/Anthropic

---

## 📊 Gap Analysis Detallado

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NUESTRA IMPLEMENTACIÓN ACTUAL                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Query → [Guardrail] → [Retrieval] → [Generation] → [Claim Verify] →       │
│          básico        similarity    LLM             LLM básico            │
│                        scores                                               │
│                                                                             │
│  Confidence = weighted_avg(                                                 │
│      source_coverage,      ← conteo de chunks (REAL pero simplista)        │
│      source_relevance,     ← avg similarity scores (REAL ✓)                │
│      claim_verification,   ← LLM verifica claims (REAL pero NO es NLI)     │
│      response_completeness,← checkea componentes (REAL ✓)                  │
│      internal_consistency  ← heurísticas básicas (WEAK)                    │
│  )                                                                          │
│                                                                             │
│  ❌ FALTA:                                                                  │
│  • LLM-as-Judge evaluando Faithfulness/Relevance/Completeness              │
│  • NLI model para entailment real                                          │
│  • Answer Relevance (query↔response similarity)                            │
│  • Self-Consistency (múltiples samples)                                    │
│  • Token probability analysis                                              │
│  • Citation verification                                                   │
│  • Confidence calibration con feedback histórico                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                    LO QUE DEBERÍA SER (INDUSTRIA)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Query → [Pre-Retrieval Evals] → [Retrieval + Coverage Check] →            │
│          safety, intent          RAGAS context precision/recall            │
│                                                                             │
│        → [Generation + Self-Assessment] → [Post-Gen Evals] →               │
│          LLM genera + dice su confianza    LLM-as-Judge                    │
│                                            NLI Faithfulness                │
│                                            Answer Relevance                │
│                                            Citation Verify                 │
│                                                                             │
│        → [Decision Engine] → Response                                       │
│          ≥0.8: enviar                                                      │
│          ≥0.5: enviar con disclaimer                                       │
│          ≥0.3: regenerar                                                   │
│          <0.3: declinar                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Plan de Implementación por Fases

### FASE 1: LLM-as-Judge (ALTO IMPACTO, MEDIA DIFICULTAD)
**Tiempo estimado: 2-3 días**
**Cambio de arquitectura: NO**
**APIs adicionales: NO (usa OpenRouter existente)**

```python
# Nueva técnica: Un LLM evalúa la respuesta de otro LLM

# Archivo: backend/app/services/llm_judge_service.py

JUDGE_PROMPT = """You are an expert evaluator for a CV screening RAG system.

CONTEXT (retrieved CV chunks):
{context}

QUESTION: {question}

RESPONSE TO EVALUATE: {response}

Evaluate on these criteria (1-5 scale):

1. FAITHFULNESS: Is every claim supported by the CV context?
2. RELEVANCE: Does the response answer the question asked?
3. COMPLETENESS: Are all parts of the question addressed?
4. List any HALLUCINATIONS (claims not in context)

Respond in JSON:
{
  "faithfulness": <int 1-5>,
  "relevance": <int 1-5>,
  "completeness": <int 1-5>,
  "hallucinations": [<list>],
  "confidence": <float 0-1>,
  "reasoning": "<explanation>"
}"""
```

**Impacto:**
- Reemplaza nuestro claim_verification simplista
- Un solo LLM call que evalúa TODO
- Mucho más robusto que verificar claim por claim

---

### FASE 2: Answer Relevance (ALTO IMPACTO, BAJA DIFICULTAD)
**Tiempo estimado: 1 día**
**Cambio de arquitectura: NO**
**APIs adicionales: NO**

```python
# Técnica: Medir similitud semántica entre query y response

async def calculate_answer_relevance(
    query: str,
    response: str,
    embedder
) -> float:
    """
    Usa embeddings para medir si la respuesta es relevante a la pregunta.
    """
    query_embedding = await embedder.embed_text(query)
    response_embedding = await embedder.embed_text(response[:1000])  # Truncate
    
    # Cosine similarity
    similarity = cosine_similarity(query_embedding, response_embedding)
    
    return similarity  # 0.0 - 1.0
```

**Impacto:**
- Detecta respuestas que divagan o no contestan
- Reutiliza embedder existente
- Muy rápido (solo 2 embeddings)

---

### FASE 3: Self-Consistency Light (MEDIO IMPACTO, MEDIA DIFICULTAD)
**Tiempo estimado: 2 días**
**Cambio de arquitectura: MENOR (genera 2-3 responses)**
**APIs adicionales: NO**
**Costo: 2-3x más tokens**

```python
# Técnica: Generar N respuestas y medir consistencia

async def generate_with_consistency(
    prompt: str,
    llm,
    n_samples: int = 3,
    temperature: float = 0.7
) -> Tuple[str, float]:
    """
    Genera múltiples respuestas y mide consistencia.
    """
    responses = []
    for _ in range(n_samples):
        resp = await llm.generate(prompt, temperature=temperature)
        responses.append(resp.text)
    
    # Extraer "key answer" de cada respuesta
    key_answers = [extract_key_answer(r) for r in responses]
    
    # Medir consistencia
    consistency = calculate_agreement(key_answers)
    
    # Usar respuesta con temperature=0 como final
    final_response = await llm.generate(prompt, temperature=0)
    
    return final_response.text, consistency
```

**Impacto:**
- Alta consistencia = alta confianza
- Detecta cuando el modelo está "adivinando"
- Trade-off: más latencia y costo

---

### FASE 4: NLI Faithfulness (ALTO IMPACTO, ALTA DIFICULTAD)
**Tiempo estimado: 3-5 días**
**Cambio de arquitectura: SÍ (nuevo modelo)**
**APIs adicionales: SÍ - Hugging Face Inference API o modelo local**

```python
# Técnica: Modelo NLI especializado para verificar entailment

# Opción A: Hugging Face Inference API
NLI_MODEL = "microsoft/deberta-v3-large-mnli"  # O cross-encoder/nli-deberta-v3-base

async def verify_claim_nli(
    claim: str,
    context: str,
    hf_api_key: str
) -> Tuple[str, float]:
    """
    Verifica si el contexto implica (entails) el claim.
    
    Returns:
        ("entailment" | "neutral" | "contradiction", confidence)
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api-inference.huggingface.co/models/{NLI_MODEL}",
            headers={"Authorization": f"Bearer {hf_api_key}"},
            json={
                "inputs": {
                    "premise": context,
                    "hypothesis": claim
                }
            }
        )
        result = response.json()
    
    # Result: [{"label": "ENTAILMENT", "score": 0.95}, ...]
    top_label = max(result, key=lambda x: x["score"])
    return top_label["label"].lower(), top_label["score"]

# Opción B: Modelo local con transformers
from transformers import pipeline

nli_pipeline = pipeline("text-classification", model=NLI_MODEL)

def verify_claim_local(claim: str, context: str):
    result = nli_pipeline(f"{context} [SEP] {claim}")
    return result[0]["label"], result[0]["score"]
```

**Impacto:**
- Verificación de claims mucho más precisa que LLM genérico
- Modelos NLI están entrenados específicamente para esto
- Más rápido y barato que llamadas LLM

**Requisitos:**
- API key de Hugging Face (gratis para uso moderado) O
- GPU local para modelo (4GB+ VRAM)

---

### FASE 5: Citation Verification (MEDIO IMPACTO, MEDIA DIFICULTAD)
**Tiempo estimado: 2-3 días**
**Cambio de arquitectura: SÍ (cambiar prompt de generación)**
**APIs adicionales: NO**

```python
# Paso 1: Modificar prompt para que LLM genere con citas

GENERATION_PROMPT = """
Answer the question using ONLY the provided context.
IMPORTANT: Add inline citations [1], [2], etc. for every factual claim.

Context:
[1] {chunk_1}
[2] {chunk_2}
...

Question: {question}

Answer with citations:
"""

# Paso 2: Verificar cada cita

async def verify_citations(
    response: str,
    chunks: List[str]
) -> Tuple[float, List[dict]]:
    """
    Extrae citas del response y verifica cada una.
    """
    # Extraer citas: "claim [1]" → claim, source_idx
    citation_pattern = r'([^.]+)\[(\d+)\]'
    citations = re.findall(citation_pattern, response)
    
    results = []
    for claim, source_idx in citations:
        source = chunks[int(source_idx) - 1]
        
        # Verificar con NLI o LLM
        is_supported = await verify_claim_nli(claim, source)
        
        results.append({
            "claim": claim,
            "source_idx": source_idx,
            "is_valid": is_supported[0] == "entailment",
            "confidence": is_supported[1]
        })
    
    valid_count = sum(1 for r in results if r["is_valid"])
    citation_score = valid_count / len(results) if results else 0
    
    return citation_score, results
```

---

### FASE 6: Decision Engine (MEDIO IMPACTO, BAJA DIFICULTAD)
**Tiempo estimado: 1 día**
**Cambio de arquitectura: NO**
**APIs adicionales: NO**

```python
# Lógica de decisión basada en confidence

class DecisionEngine:
    THRESHOLDS = {
        "send": 0.80,
        "send_with_disclaimer": 0.50,
        "regenerate": 0.30,
        "decline": 0.0
    }
    
    def decide(
        self,
        confidence: float,
        faithfulness: float,
        has_contradictions: bool
    ) -> Tuple[str, Optional[str]]:
        """
        Decide qué hacer con la respuesta.
        
        Returns:
            (action, disclaimer_text)
        """
        # Hard failures
        if has_contradictions:
            return "regenerate", None
        
        if faithfulness < 0.5:
            return "regenerate", None
        
        # Confidence-based decision
        if confidence >= self.THRESHOLDS["send"]:
            return "send", None
        
        elif confidence >= self.THRESHOLDS["send_with_disclaimer"]:
            return "send_with_disclaimer", (
                "⚠️ Esta respuesta tiene confianza moderada. "
                "Verifica la información con los CVs originales."
            )
        
        elif confidence >= self.THRESHOLDS["regenerate"]:
            return "regenerate", None
        
        else:
            return "decline", (
                "No tengo suficiente información en los CVs para "
                "responder esta pregunta con confianza."
            )
```

---

## 📋 Resumen de Cambios Necesarios

### Cambios de Arquitectura

| Cambio | Severidad | Descripción |
|--------|-----------|-------------|
| LLM-as-Judge | 🟢 Menor | Nuevo service, no cambia flujo |
| Answer Relevance | 🟢 Menor | Reutiliza embedder existente |
| Self-Consistency | 🟡 Moderado | Genera múltiples responses |
| NLI Model | 🟡 Moderado | Nueva dependencia externa |
| Citation Verification | 🟡 Moderado | Cambia prompt de generación |
| Decision Engine | 🟢 Menor | Nueva lógica post-generación |

### Nuevas APIs/Keys Necesarias

| Servicio | ¿Necesario? | Costo | Alternativa |
|----------|-------------|-------|-------------|
| Hugging Face API | Opcional | Gratis (rate limited) | Modelo local |
| OpenRouter | Ya tenemos | Variable | - |
| Modelo NLI local | Opcional | GPU 4GB+ | HF API |

### Impacto en Stack Actual

```
STACK ACTUAL:
├── Backend: FastAPI + Python ✅ (no cambia)
├── Frontend: React + Vite ✅ (no cambia)
├── Vector DB: Supabase pgvector ✅ (no cambia)
├── LLM: OpenRouter ✅ (no cambia)
├── Embeddings: OpenRouter ✅ (no cambia)
└── NUEVO: Hugging Face API (opcional) o modelo NLI local

CAMBIOS EN CÓDIGO:
├── backend/app/services/
│   ├── confidence_calculator.py   → REESCRIBIR (integrar nuevos scores)
│   ├── llm_judge_service.py       → NUEVO
│   ├── answer_relevance_service.py → NUEVO
│   ├── nli_verifier_service.py    → NUEVO (si usamos NLI)
│   └── decision_engine.py         → NUEVO
├── backend/app/services/rag_service_v5.py → MODIFICAR (integrar fases)
└── frontend/src/components/MetricsPanel.jsx → MODIFICAR (mostrar nuevos scores)
```

---

## 🎯 Recomendación de Implementación

### Orden por ROI (Return on Investment)

| Prioridad | Técnica | Esfuerzo | Impacto | ROI |
|-----------|---------|----------|---------|-----|
| 1️⃣ | LLM-as-Judge | 2-3 días | 🔴 Alto | ⭐⭐⭐⭐⭐ |
| 2️⃣ | Answer Relevance | 1 día | 🔴 Alto | ⭐⭐⭐⭐⭐ |
| 3️⃣ | Decision Engine | 1 día | 🟡 Medio | ⭐⭐⭐⭐ |
| 4️⃣ | Citation Verification | 2-3 días | 🟡 Medio | ⭐⭐⭐ |
| 5️⃣ | Self-Consistency | 2 días | 🟡 Medio | ⭐⭐⭐ |
| 6️⃣ | NLI Faithfulness | 3-5 días | 🔴 Alto | ⭐⭐⭐ |

### MVP Recomendado (1 semana)

Implementar solo:
1. **LLM-as-Judge** - Reemplaza nuestro claim verification actual
2. **Answer Relevance** - Muy fácil, alto impacto
3. **Decision Engine** - Comportamiento inteligente

Esto nos llevaría del **30% al ~60%** de lo que hace la industria.

### Versión Completa (3-4 semanas)

Añadir:
4. **Citation Verification** - Requiere cambiar prompts
5. **Self-Consistency** - Trade-off costo/precisión
6. **NLI Model** - Requiere nueva integración

Esto nos llevaría al **~85%** de lo que hace la industria.

---

## ❓ Preguntas para Decidir

1. **¿Priorizar velocidad o precisión?**
   - Self-Consistency añade 2-3x latencia
   - NLI es más preciso pero más lento que LLM-as-Judge

2. **¿Presupuesto para APIs adicionales?**
   - Hugging Face gratis tiene rate limits
   - Modelo local requiere GPU

3. **¿Aceptamos disclaimers en respuestas?**
   - Decision Engine puede mostrar advertencias
   - ¿O preferimos solo respuestas de alta confianza?

4. **¿Queremos citas inline [1][2]?**
   - Cambia significativamente el formato de respuesta
   - Más transparente pero más verbose

---

## 📁 Archivos a Crear/Modificar

```
backend/app/services/
├── evaluation/                          # NUEVO DIRECTORIO
│   ├── __init__.py
│   ├── llm_judge.py                    # LLM-as-Judge service
│   ├── answer_relevance.py             # Query↔Response similarity
│   ├── nli_verifier.py                 # NLI-based verification (opcional)
│   ├── citation_verifier.py            # Citation checking
│   ├── self_consistency.py             # Multiple samples
│   └── decision_engine.py              # Final decision logic
├── confidence_calculator.py            # MODIFICAR - integrar nuevos scores
└── rag_service_v5.py                   # MODIFICAR - llamar a nuevos services

frontend/src/components/
└── MetricsPanel.jsx                    # MODIFICAR - mostrar breakdown detallado
```

---

## Conclusión

**¿El cambio es drástico?** 
- Arquitectura: NO, es incremental
- Stack: NO, mismo stack + 1 API opcional
- Código: SÍ, varios servicios nuevos

**¿Necesitamos nuevas APIs?**
- Mínimo: NO, todo puede hacerse con OpenRouter
- Ideal: SÍ, Hugging Face para NLI (gratis)

**¿Vale la pena?**
- LLM-as-Judge + Answer Relevance = **80% del beneficio con 20% del esfuerzo**
- NLI + Self-Consistency = **20% adicional con 80% del esfuerzo**

**Recomendación:** Implementar Fases 1-3 primero (1 semana), evaluar resultados, luego decidir si vale la pena las fases 4-6.
