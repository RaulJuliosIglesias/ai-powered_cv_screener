# 🏠 IMPLEMENTATION PLAN: LOCAL MODE

## Objective
Complete RAG system running 100% locally (except LLM which uses OpenRouter), with real embeddings, guardrails, anti-hallucination and evaluation.

---

## 📦 TECHNOLOGY STACK

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Embeddings** | `sentence-transformers` | 2.2.2+ | Real semantic embeddings |
| **Embedding Model** | `all-MiniLM-L6-v2` | - | 384 dims, fast, accurate |
| **Vector Store** | `ChromaDB` | 0.4.x | Local vector database |
| **Guardrails** | `guardrails-ai` | 0.4.x | LLM I/O validation |
| **Anti-hallucination** | Custom + `spaCy` | 3.7.x | Entity extraction |
| **LLM** | OpenRouter API | - | GPT-4o-mini / Claude |
| **Evaluation** | `ragas` | 0.1.x | Automatic RAG metrics |

---

## 🏗️ PROPOSED ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    routes_sessions.py                        ││
│  └─────────────────────────────────────────────────────────────┘│
│                                │                                 │
│                                ▼                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              GUARDRAIL SERVICE (PRE-LLM)                    ││
│  │  - Intent classifier (CV-related vs off-topic)              ││
│  │  - Input validation                                          ││
│  └─────────────────────────────────────────────────────────────┘│
│                                │                                 │
│                                ▼                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   RAG SERVICE v3                             ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       ││
│  │  │  Embedding   │  │   ChromaDB   │  │     LLM      │       ││
│  │  │ (MiniLM-L6)  │  │ Vector Store │  │ (OpenRouter) │       ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘       ││
│  └─────────────────────────────────────────────────────────────┘│
│                                │                                 │
│                                ▼                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │           ANTI-HALLUCINATION SERVICE (POST-LLM)             ││
│  │  - Verify mentioned names exist in CVs                      ││
│  │  - Verify mentioned skills are in CVs                       ││
│  │  - Confidence score                                          ││
│  └─────────────────────────────────────────────────────────────┘│
│                                │                                 │
│                                ▼                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   EVALUATION SERVICE                         ││
│  │  - Query/response logging                                   ││
│  │  - RAGAS metrics                                            ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 FILE STRUCTURE (REFACTORING)

```
backend/app/
├── providers/
│   └── local/
│       ├── embeddings.py      # REFACTOR: Forzar sentence-transformers
│       ├── vector_store.py    # REFACTOR: Usar ChromaDB real
│       └── llm.py             # OK (mantener)
├── services/
│   ├── rag_service_v2.py      # REFACTOR → rag_service_v3.py
│   ├── guardrail_service.py   # NUEVO: Pre-filtro de preguntas
│   ├── hallucination_service.py # NUEVO: Verificación post-LLM
│   └── eval_service.py        # NUEVO: Logging y métricas
├── prompts/
│   └── templates.py           # REFACTOR: Mejorar prompts
└── config.py                  # ACTUALIZAR: Nuevas configs
```

---

## 📋 IMPLEMENTATION PHASES

### PHASE 1: Real Embeddings (Day 1)
**Files to modify:** `providers/local/embeddings.py`, `requirements.txt`

#### 1.1 Install dependencies
```bash
pip install sentence-transformers==2.2.2
pip install chromadb==0.4.22
```

#### 1.2 Refactorizar embeddings.py
```python
# providers/local/embeddings.py
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

class LocalEmbeddingProvider:
    """Embeddings locales usando sentence-transformers."""
    
    MODEL_NAME = "all-MiniLM-L6-v2"
    DIMENSIONS = 384
    
    def __init__(self):
        logger.info(f"Loading embedding model: {self.MODEL_NAME}")
        self._model = SentenceTransformer(self.MODEL_NAME)
        logger.info(f"Model loaded successfully. Dimensions: {self.DIMENSIONS}")
    
    @property
    def dimensions(self) -> int:
        return self.DIMENSIONS
    
    async def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        embeddings = self._model.encode(
            texts, 
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalizar para cosine similarity
        ).tolist()
        return EmbeddingResult(embeddings=embeddings, ...)
    
    async def embed_query(self, query: str) -> EmbeddingResult:
        embedding = self._model.encode(
            query,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).tolist()
        return EmbeddingResult(embeddings=[embedding], ...)
```

#### 1.3 Verificación
```python
# Test embeddings
from app.providers.local.embeddings import LocalEmbeddingProvider
p = LocalEmbeddingProvider()
result = await p.embed_texts(["Python developer with 5 years experience"])
assert len(result.embeddings[0]) == 384
print("✅ Embeddings funcionando correctamente")
```

---

### FASE 2: ChromaDB Vector Store (Día 1-2)
**Archivos a modificar:** `providers/local/vector_store.py`

#### 2.1 Refactorizar vector_store.py
```python
# providers/local/vector_store.py
import chromadb
from chromadb.config import Settings
import logging

logger = logging.getLogger(__name__)

class ChromaVectorStore:
    """Vector store usando ChromaDB persistente."""
    
    def __init__(self, persist_dir: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="cv_embeddings",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"ChromaDB initialized. Documents: {self.collection.count()}")
    
    async def add_documents(self, documents: list, embeddings: list) -> None:
        ids = [doc["id"] for doc in documents]
        contents = [doc["content"] for doc in documents]
        metadatas = [{
            "cv_id": doc["cv_id"],
            "filename": doc["filename"],
            "chunk_index": doc["chunk_index"]
        } for doc in documents]
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas
        )
        logger.info(f"Added {len(documents)} documents. Total: {self.collection.count()}")
    
    async def search(self, embedding: list, k: int = 5, cv_ids: list = None) -> list:
        where_filter = {"cv_id": {"$in": cv_ids}} if cv_ids else None
        
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        search_results = []
        for i, doc_id in enumerate(results["ids"][0]):
            similarity = 1 - results["distances"][0][i]  # Cosine distance → similarity
            search_results.append(SearchResult(
                id=doc_id,
                cv_id=results["metadatas"][0][i]["cv_id"],
                filename=results["metadatas"][0][i]["filename"],
                content=results["documents"][0][i],
                similarity=similarity,
                metadata=results["metadatas"][0][i]
            ))
        return search_results
```

---

### FASE 3: Guardrails Pre-LLM (Día 2)
**Archivos nuevos:** `services/guardrail_service.py`

#### 3.1 Crear servicio de guardrails
```python
# services/guardrail_service.py
import re
from typing import Tuple
from app.providers.local.embeddings import LocalEmbeddingProvider

class GuardrailService:
    """Pre-filtro para detectar preguntas off-topic."""
    
    # Keywords relacionadas con CVs/reclutamiento
    CV_KEYWORDS = {
        "candidate", "cv", "resume", "experience", "skills", "education",
        "job", "hire", "qualified", "senior", "junior", "years", "developer",
        "engineer", "manager", "analyst", "candidato", "experiencia", "habilidades"
    }
    
    # Preguntas claramente off-topic
    OFF_TOPIC_PATTERNS = [
        r"receta|recipe|cocina|cook",
        r"clima|weather|temperatura",
        r"chiste|joke|funny",
        r"película|movie|film",
        r"música|music|song",
        r"deporte|sport|football|soccer",
        r"política|politic",
        r"religión|religion"
    ]
    
    def __init__(self):
        self.embedder = LocalEmbeddingProvider()
        # Embedding de referencia para preguntas de CV
        self._cv_reference_embedding = None
    
    async def is_cv_related(self, question: str) -> Tuple[bool, str]:
        """
        Verifica si la pregunta está relacionada con CVs.
        Returns: (is_related, rejection_message or None)
        """
        question_lower = question.lower()
        
        # 1. Check off-topic patterns
        for pattern in self.OFF_TOPIC_PATTERNS:
            if re.search(pattern, question_lower):
                return False, "I can only help with CV screening and candidate analysis. Please ask about the uploaded CVs."
        
        # 2. Check for CV keywords
        words = set(question_lower.split())
        if words & self.CV_KEYWORDS:
            return True, None
        
        # 3. Semantic check - compare with CV-related reference
        if self._cv_reference_embedding is None:
            ref_text = "Which candidate has the best experience for this job position?"
            result = await self.embedder.embed_query(ref_text)
            self._cv_reference_embedding = result.embeddings[0]
        
        query_result = await self.embedder.embed_query(question)
        query_embedding = query_result.embeddings[0]
        
        similarity = self._cosine_similarity(query_embedding, self._cv_reference_embedding)
        
        if similarity < 0.3:  # Threshold bajo = probablemente off-topic
            return False, "I can only help with CV screening and candidate analysis. Please ask about the uploaded CVs."
        
        return True, None
    
    def _cosine_similarity(self, a: list, b: list) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0
```

---

### FASE 4: Anti-Alucinación Post-LLM (Día 3)
**Archivos nuevos:** `services/hallucination_service.py`

#### 4.1 Crear servicio de verificación
```python
# services/hallucination_service.py
import re
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class HallucinationService:
    """Verifica que la respuesta del LLM no contenga alucinaciones."""
    
    def verify_response(
        self, 
        llm_response: str, 
        cv_chunks: List[Dict[str, Any]],
        cv_metadata: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Verifica la respuesta del LLM contra los CVs reales.
        
        Returns:
            {
                "is_valid": bool,
                "confidence_score": float,
                "warnings": list,
                "verified_claims": list,
                "unverified_claims": list
            }
        """
        # Extraer nombres mencionados en la respuesta
        mentioned_names = self._extract_names(llm_response)
        
        # Extraer CV IDs mencionados
        mentioned_cv_ids = self._extract_cv_ids(llm_response)
        
        # Nombres reales de los CVs
        real_names = set()
        real_cv_ids = set()
        for meta in cv_metadata:
            real_cv_ids.add(meta.get("cv_id", ""))
            # Extraer nombre del filename
            name = self._extract_name_from_filename(meta.get("filename", ""))
            if name:
                real_names.add(name.lower())
        
        # Verificar CV IDs
        valid_cv_ids = mentioned_cv_ids & real_cv_ids
        invalid_cv_ids = mentioned_cv_ids - real_cv_ids
        
        warnings = []
        if invalid_cv_ids:
            warnings.append(f"Invalid CV IDs mentioned: {invalid_cv_ids}")
        
        # Calcular score de confianza
        if mentioned_cv_ids:
            confidence = len(valid_cv_ids) / len(mentioned_cv_ids)
        else:
            confidence = 0.5  # Neutral si no hay IDs
        
        return {
            "is_valid": len(invalid_cv_ids) == 0,
            "confidence_score": confidence,
            "warnings": warnings,
            "verified_cv_ids": list(valid_cv_ids),
            "unverified_cv_ids": list(invalid_cv_ids)
        }
    
    def _extract_cv_ids(self, text: str) -> set:
        """Extrae CV IDs del formato [CV:cv_xxxxx]"""
        pattern = r'\[CV:(cv_[a-f0-9]+)\]'
        return set(re.findall(pattern, text))
    
    def _extract_names(self, text: str) -> set:
        """Extrae nombres propios del texto."""
        # Buscar patrones de nombre (palabras capitalizadas consecutivas)
        pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        return set(re.findall(pattern, text))
    
    def _extract_name_from_filename(self, filename: str) -> str:
        """Extrae nombre del formato: hash_Name_Surname_..."""
        parts = filename.replace('.pdf', '').split('_')
        if len(parts) >= 3:
            # Skip hash, take next 2-3 parts
            name_parts = parts[1:3]
            return ' '.join(name_parts)
        return ""
```

---

### FASE 5: Servicio de Evaluación (Día 3-4)
**Archivos nuevos:** `services/eval_service.py`

#### 5.1 Crear servicio de logging y métricas
```python
# services/eval_service.py
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class EvalService:
    """Logging y métricas para evaluar calidad del RAG."""
    
    def __init__(self, log_dir: str = "./eval_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.current_log_file = self.log_dir / f"queries_{datetime.now().strftime('%Y%m%d')}.jsonl"
    
    def log_query(
        self,
        query: str,
        response: str,
        sources: List[Dict],
        metrics: Dict[str, float],
        hallucination_check: Dict[str, Any],
        guardrail_passed: bool
    ):
        """Log una query completa para análisis posterior."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response,
            "sources": sources,
            "metrics": metrics,
            "hallucination_check": hallucination_check,
            "guardrail_passed": guardrail_passed
        }
        
        with open(self.current_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        logger.info(f"Query logged. Confidence: {hallucination_check.get('confidence_score', 'N/A')}")
    
    def get_daily_stats(self, date: str = None) -> Dict[str, Any]:
        """Obtener estadísticas del día."""
        date = date or datetime.now().strftime('%Y%m%d')
        log_file = self.log_dir / f"queries_{date}.jsonl"
        
        if not log_file.exists():
            return {"total_queries": 0}
        
        queries = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                queries.append(json.loads(line))
        
        return {
            "total_queries": len(queries),
            "avg_confidence": sum(q.get("hallucination_check", {}).get("confidence_score", 0) for q in queries) / len(queries) if queries else 0,
            "guardrail_rejections": sum(1 for q in queries if not q.get("guardrail_passed", True)),
            "avg_latency_ms": sum(q.get("metrics", {}).get("total_ms", 0) for q in queries) / len(queries) if queries else 0
        }
```

---

### FASE 6: Integración en RAG Service (Día 4)
**Archivos a modificar:** `services/rag_service_v2.py` → `services/rag_service_v3.py`

#### 6.1 Nuevo RAG Service integrado
```python
# services/rag_service_v3.py
from app.services.guardrail_service import GuardrailService
from app.services.hallucination_service import HallucinationService
from app.services.eval_service import EvalService

class RAGServiceV3:
    """RAG Service con guardrails, anti-alucinación y evaluación."""
    
    def __init__(self, mode: Mode):
        self.mode = mode
        self.embedder = ProviderFactory.get_embedding_provider(mode)
        self.vector_store = ProviderFactory.get_vector_store(mode)
        self.llm = ProviderFactory.get_llm_provider(mode)
        
        # Nuevos servicios
        self.guardrail = GuardrailService()
        self.hallucination = HallucinationService()
        self.eval = EvalService()
    
    async def query(self, question: str, cv_ids: List[str] = None, ...) -> RAGResponse:
        metrics = {}
        
        # 1. GUARDRAIL CHECK
        is_cv_related, rejection_msg = await self.guardrail.is_cv_related(question)
        if not is_cv_related:
            self.eval.log_query(question, rejection_msg, [], {}, {}, guardrail_passed=False)
            return RAGResponse(answer=rejection_msg, sources=[], ...)
        
        # 2. EMBEDDING + SEARCH (igual que antes)
        embed_result = await self.embedder.embed_query(question)
        search_results = await self.vector_store.search(...)
        
        # 3. LLM GENERATION
        llm_result = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
        
        # 4. HALLUCINATION CHECK
        cv_metadata = [{"cv_id": r.cv_id, "filename": r.filename} for r in search_results]
        hallucination_check = self.hallucination.verify_response(
            llm_result.text, 
            chunks,
            cv_metadata
        )
        
        # 5. Si hay alucinaciones, añadir warning
        answer = llm_result.text
        if hallucination_check["warnings"]:
            answer += "\n\n⚠️ *Some information could not be verified against the CVs.*"
        
        # 6. LOG para evaluación
        self.eval.log_query(
            question, answer, sources, metrics, 
            hallucination_check, guardrail_passed=True
        )
        
        return RAGResponse(answer=answer, sources=sources, ...)
```

---

## ✅ CHECKLIST DE VERIFICACIÓN

### Fase 1: Embeddings
- [ ] `pip install sentence-transformers==2.2.2`
- [ ] Refactorizar `embeddings.py`
- [ ] Test: embeddings tienen 384 dimensiones
- [ ] Test: embeddings similares para textos similares

### Fase 2: ChromaDB
- [ ] `pip install chromadb==0.4.22`
- [ ] Refactorizar `vector_store.py`
- [ ] Test: documentos se persisten en disco
- [ ] Test: búsqueda retorna resultados relevantes

### Fase 3: Guardrails
- [ ] Crear `guardrail_service.py`
- [ ] Test: "dame una receta" → rechazado
- [ ] Test: "who knows Python" → aceptado

### Fase 4: Anti-alucinación
- [ ] Crear `hallucination_service.py`
- [ ] Test: detecta CV IDs inválidos
- [ ] Test: calcula confidence score

### Fase 5: Evaluación
- [ ] Crear `eval_service.py`
- [ ] Test: queries se loguean en JSONL
- [ ] Test: stats diarios funcionan

### Fase 6: Integración
- [ ] Crear `rag_service_v3.py`
- [ ] Actualizar routes para usar v3
- [ ] Test end-to-end completo

---

## 📊 MÉTRICAS DE ÉXITO

| Métrica | Antes | Objetivo |
|---------|-------|----------|
| Embeddings reales | ❌ Hash MD5 | ✅ MiniLM-L6 |
| Búsqueda semántica | ❌ Imprecisa | ✅ Top-5 relevantes |
| Off-topic rechazado | ❌ 0% | ✅ >95% |
| Alucinaciones detectadas | ❌ 0% | ✅ >80% |
| Queries logueadas | ❌ 0% | ✅ 100% |

---

## ⏱️ ESTIMACIÓN DE TIEMPO

| Fase | Tiempo estimado |
|------|-----------------|
| Fase 1: Embeddings | 2-3 horas |
| Fase 2: ChromaDB | 2-3 horas |
| Fase 3: Guardrails | 3-4 horas |
| Fase 4: Anti-alucinación | 3-4 horas |
| Fase 5: Evaluación | 2-3 horas |
| Fase 6: Integración | 3-4 horas |
| **TOTAL** | **15-21 horas** (~2-3 días) |
