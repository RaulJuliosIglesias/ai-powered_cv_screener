# V10 Complete Pipeline Fix - Plan de Implementación

## 📋 Resumen Ejecutivo

Este documento detalla el plan completo para corregir **TODOS** los problemas del pipeline de CV Screener, desde la extracción de datos del PDF hasta la generación de respuestas estructuradas.

**Estado de Implementación (2026-01-11):**
1. ✅ Extracción incorrecta de datos del CV → **FASE 1 COMPLETADA**
2. ✅ Embeddings no capturan información estructurada → **FASE 2 COMPLETADA**
3. ✅ Retrieval no encuentra chunks relevantes → **FASE 3 COMPLETADA**
4. ✅ LLM no recibe metadata enriquecida → **FASE 4 COMPLETADA**
5. ✅ Respuestas con tablas vacías y análisis incompletos → **FASE 5 COMPLETADA**
6. ✅ Output modules no parsean correctamente → **FASE 6 COMPLETADA**
7. ✅ Supabase schema + SupabaseVectorStore → **FASE 7 COMPLETADA**
8. ⏳ Testing E2E con 23 CVs → **PENDIENTE**

**Objetivo V10:** Supabase como fuente principal de datos

---

## 🎉 IMPLEMENTACIÓN COMPLETADA

### Archivos Modificados:

| Archivo | Cambios |
|---------|---------|
| `pdf_service.py` | +4 dataclasses (EducationEntry, LanguageEntry, CertificationEntry, SkillWithLevel), +4 métodos extracción |
| `smart_chunking_service.py` | +13 boolean flags en metadata, enriched summary content builder |
| `rag_service_v5.py` | +`_detect_metadata_filters()` para queries tipo "who speaks French" |
| `templates.py` | +`_extract_fase1_metadata()` para LLM context enriquecido |
| `table_module.py` | Fallback mejorado con metadata enriquecida FASE 1 |
| `supabase/migrations/002_fase1_enhanced_schema.sql` | Schema completo con pgvector + hybrid search |
| `supabase_vector_store.py` | **NUEVO** - Service completo para Supabase |

### Nuevos Campos Extraídos (FASE 1):

```python
# Educación
education_entries, education_field, graduation_year, has_mba, has_phd

# Idiomas  
languages, primary_language, speaks_english, speaks_french, speaks_spanish, speaks_german

# Certificaciones
certifications, has_aws_cert, has_azure_cert, has_gcp_cert, has_pmp, has_cbap, has_scrum

# Skills con niveles
skills_with_levels  # List[SkillWithLevel] con level 1-10
```

### Funciones Supabase Nuevas:

- `hybrid_search_cv_chunks()` - Búsqueda vector + BM25 con filtros metadata
- `search_by_metadata()` - Búsqueda directa por metadata (speaks_french, has_aws_cert, etc.)
- `upsert_cv_metadata()` - Inserción/actualización de metadata estructurada

---

## 🔄 FLUJO ACTUAL DEL PIPELINE

```
PDF Upload → PDFService/SmartChunking → Embeddings → Vector Store → Retrieval → LLM → Output Modules → Frontend
```

### Puntos de Fallo Identificados:

| Etapa | Problema | Impacto |
|-------|----------|---------|
| PDF Parsing | Títulos extraídos como descripciones | Metadata incorrecta |
| PDF Parsing | Años de experiencia mal calculados | Rankings erróneos |
| PDF Parsing | Skills ratings (10/10) confundidos con empresas | Datos basura |
| Embeddings | Solo texto, no metadata estructurada | Búsqueda semántica pobre |
| Retrieval | Chunks sin contexto enriquecido | LLM sin información |
| LLM Prompt | Metadata no formateada para análisis | Respuestas genéricas |
| LLM Output | Markdown mal parseado | Tablas vacías |
| Output Modules | No extraen datos de chunks | "No candidates match" |

---

## 📦 FASE 1: CV PARSING ROBUSTO

### 1.1 Mejorar `pdf_service.py`

**Estado actual:** ✅ PARCIALMENTE COMPLETADO

```python
# Fixes ya implementados:
- _extract_company_from_block(): Detecta formato "YEAR | Company"
- _validate_company_name(): Rechaza ratings (10/10)
- _extract_job_title_from_block(): Busca título ANTES de fecha
- _validate_job_title(): Rechaza descripciones (verbos pasados)
- _calculate_total_experience_from_span(): Calcula desde año más antiguo
```

**Pendiente:**

```python
# 1.1.1 Extraer TODOS los campos del CV
class EnrichedCVData:
    # Básicos (ya existe)
    candidate_name: str
    total_experience_years: float
    current_role: str
    current_company: str
    
    # Experiencia detallada (MEJORAR)
    experiences: List[ExperienceEntry]  # Con títulos/empresas correctos
    
    # Educación (AÑADIR)
    education: List[EducationEntry]
    highest_degree: str
    graduation_year: int
    institutions: List[str]
    
    # Skills estructurados (MEJORAR)
    technical_skills: List[str]
    soft_skills: List[str]
    skill_levels: Dict[str, int]  # "Python": 9
    
    # Idiomas (AÑADIR)
    languages: List[LanguageEntry]
    primary_language: str
    
    # Certificaciones (MEJORAR)
    certifications: List[CertificationEntry]
    
    # Contacto (ya existe parcialmente)
    email: str
    phone: str
    location: str
    linkedin: str
    github: str
    portfolio: str
    
    # Red Flags calculados (ya existe)
    job_hopping_score: float
    avg_tenure_years: float
    employment_gaps: List[Tuple[int, int]]
```

### 1.2 Archivo: `backend/app/services/pdf_service.py`

**Cambios requeridos:**

```python
# 1.2.1 Mejorar extracción de skills con niveles
def extract_skills_with_levels(self, text: str) -> Dict[str, int]:
    """
    Extrae skills y sus niveles del formato "Python 9/10" o "Python ⭐⭐⭐⭐"
    
    Returns:
        {"Python": 9, "SQL": 10, "Tableau": 8}
    """
    pass

# 1.2.2 Extraer educación estructurada
def extract_education(self, text: str) -> List[EducationEntry]:
    """
    Extrae grados, instituciones, años de graduación.
    
    Patterns:
    - "Master of Business Administration\nSeoul National University\n2019"
    - "Bachelor of Science in Economics, Korea University, 2012"
    """
    pass

# 1.2.3 Extraer certificaciones con fechas
def extract_certifications(self, text: str) -> List[CertificationEntry]:
    """
    Extrae certificaciones y cuándo se obtuvieron.
    
    Pattern: "2022\nCertified Business Analysis Professional (CBAP)\nIIBA"
    """
    pass

# 1.2.4 Extraer idiomas con niveles
def extract_languages(self, text: str) -> List[LanguageEntry]:
    """
    Extrae idiomas y niveles CEFR.
    
    Pattern: "English C2 (Native)", "French B1 (Intermediate)"
    """
    pass
```

### 1.3 Archivo: `backend/app/services/smart_chunking_service.py`

**Cambios requeridos:**

```python
# 1.3.1 Añadir más metadata a cada chunk
def chunk_cv(self, text: str, cv_id: str, filename: str) -> List[Dict]:
    # ... existing code ...
    
    # NUEVO: Metadata extendida para CADA chunk
    extended_metadata = {
        # Existente
        "candidate_name": str,
        "total_experience_years": float,
        "job_hopping_score": float,
        "avg_tenure_years": float,
        "position_count": int,
        "employment_gaps_count": int,
        
        # NUEVO: Skills como string searchable
        "skills_searchable": "Python,SQL,Tableau,AWS",
        
        # NUEVO: Idiomas
        "languages_searchable": "English,French,Korean",
        "speaks_french": True,  # Para queries directos
        "speaks_english": True,
        
        # NUEVO: Educación
        "education_level": "masters",  # phd, masters, bachelors
        "has_mba": True,
        
        # NUEVO: Certificaciones
        "has_aws_cert": True,
        "has_cbap": True,
        "certifications_searchable": "AWS,CBAP,PMP",
        
        # NUEVO: Industria/Sector
        "industries": "finance,consulting,tech",
        
        # NUEVO: Seniority searchable
        "is_senior": True,
        "is_lead": False,
        "is_director": True,
    }
```

---

## 📦 FASE 2: EMBEDDINGS ENRIQUECIDOS

### 2.1 Problema Actual

Los embeddings actuales solo capturan el **texto** del chunk, no la metadata estructurada.

```python
# ACTUAL (insuficiente)
embedding = embed(chunk.content)  # Solo texto

# IDEAL
embedding = embed(chunk.content + structured_context)
```

### 2.2 Archivo: `backend/app/services/vector_store.py`

**Cambios requeridos:**

```python
def add_chunks(self, chunks: List[CVChunk], embeddings: List[List[float]]) -> int:
    # NUEVO: Crear texto enriquecido para embedding
    enriched_texts = []
    for chunk in chunks:
        # Combinar contenido con metadata estructurada
        enriched = self._build_enriched_text(chunk)
        enriched_texts.append(enriched)
    
    # Generar embeddings del texto enriquecido
    enriched_embeddings = await self._embedder.embed_texts(enriched_texts)
    
def _build_enriched_text(self, chunk: CVChunk) -> str:
    """
    Construye texto enriquecido para mejor búsqueda semántica.
    
    Example output:
    "CANDIDATE: Amir Hassan
     EXPERIENCE: 31 years, Lead/Director level
     CURRENT: Lead Editorial & Visual Stylist at Select Luxury Brands
     SKILLS: Editorial Styling, Visual Merchandising, Wardrobe Management
     LANGUAGES: English (Native), Arabic (Professional), French (Intermediate)
     EDUCATION: Diploma Fashion Styling, Ryerson University
     CERTIFICATIONS: Advanced Color Theory, Luxury Brand Management
     
     --- CONTENT ---
     [original chunk content]"
    """
    parts = []
    meta = chunk.metadata or {}
    
    # Header estructurado (siempre incluir)
    parts.append(f"CANDIDATE: {meta.get('candidate_name', 'Unknown')}")
    parts.append(f"EXPERIENCE: {meta.get('total_experience_years', 0):.0f} years")
    
    if meta.get('current_role'):
        parts.append(f"CURRENT ROLE: {meta.get('current_role')}")
    if meta.get('current_company'):
        parts.append(f"COMPANY: {meta.get('current_company')}")
    
    # Skills
    if meta.get('skills'):
        parts.append(f"SKILLS: {meta.get('skills')}")
    
    # Languages (crítico para queries como "who speaks French")
    if meta.get('languages'):
        parts.append(f"LANGUAGES: {meta.get('languages')}")
    
    # Certifications (crítico para "has AWS certification")
    if meta.get('certifications'):
        parts.append(f"CERTIFICATIONS: {meta.get('certifications')}")
    
    parts.append("\n--- CONTENT ---\n")
    parts.append(chunk.content)
    
    return "\n".join(parts)
```

### 2.3 Supabase Vector Store

**Archivo nuevo:** `backend/app/services/supabase_vector_store.py`

```python
class SupabaseVectorStore:
    """
    Vector store usando Supabase pgvector.
    
    Será la fuente PRINCIPAL en V10.
    """
    
    async def add_documents(
        self,
        chunks: List[Dict],
        embeddings: List[List[float]]
    ) -> int:
        """
        Inserta chunks en Supabase con embeddings.
        
        Tabla: cv_chunks
        Columns:
        - id: uuid
        - cv_id: text
        - content: text
        - embedding: vector(1536)
        - metadata: jsonb
        - created_at: timestamp
        """
        pass
    
    async def hybrid_search(
        self,
        query_embedding: List[float],
        query_text: str,  # Para BM25
        k: int = 10,
        filters: Dict = None
    ) -> List[SearchResult]:
        """
        Búsqueda híbrida: vector + BM25 full-text.
        
        Supabase permite:
        - pgvector para similarity
        - to_tsvector/plainto_tsquery para text search
        - Combinar con RRF
        """
        pass
```

---

## 📦 FASE 3: RETRIEVAL MEJORADO

### 3.1 Problema Actual

La búsqueda no encuentra chunks relevantes porque:
1. Embeddings no capturan metadata
2. No hay filtrado por metadata estructurada
3. Queries como "who speaks French" no matchean

### 3.2 Archivo: `backend/app/services/rag_service_v5.py`

**Cambios en `_step_fusion_retrieval`:**

```python
async def _step_fusion_retrieval(self, ctx: PipelineContextV5) -> None:
    # NUEVO: Detectar tipo de query para estrategia de retrieval
    query_strategy = self._determine_retrieval_strategy(ctx)
    
    if query_strategy == "metadata_filter":
        # Queries como "who speaks French", "has AWS cert"
        chunks = await self._metadata_filtered_search(ctx)
    elif query_strategy == "skill_match":
        # Queries como "Python developers"
        chunks = await self._skill_based_search(ctx)
    elif query_strategy == "experience_range":
        # Queries como "5+ years experience"
        chunks = await self._experience_filtered_search(ctx)
    else:
        # Default: semantic search with RRF
        chunks = await self._semantic_rrf_search(ctx)

def _determine_retrieval_strategy(self, ctx: PipelineContextV5) -> str:
    """
    Analiza la query para determinar mejor estrategia.
    """
    query = ctx.question.lower()
    
    # Language queries
    if any(lang in query for lang in ['speaks', 'french', 'spanish', 'language']):
        return "metadata_filter"
    
    # Certification queries
    if any(cert in query for cert in ['aws', 'certification', 'certified', 'cbap']):
        return "metadata_filter"
    
    # Skill queries
    if any(skill in query for skill in ['python', 'sql', 'developer', 'programming']):
        return "skill_match"
    
    # Experience queries
    if re.search(r'\d+\+?\s*years?', query):
        return "experience_range"
    
    return "semantic"

async def _metadata_filtered_search(self, ctx: PipelineContextV5) -> List[Dict]:
    """
    Búsqueda por metadata específica.
    
    Para: "who speaks French", "has AWS certification"
    """
    # Extraer filtros de la query
    filters = self._extract_metadata_filters(ctx.question)
    
    # Buscar en vector store con filtros
    results = await self._vector_store.search(
        embedding=ctx.query_embeddings.get(ctx.question),
        k=ctx.k,
        filter_metadata=filters  # {"speaks_french": True}
    )
    
    return results
```

---

## 📦 FASE 4: LLM INPUT MEJORADO

### 4.1 Problema Actual

El LLM no recibe la metadata estructurada en un formato útil.

### 4.2 Archivo: `backend/app/prompts/templates.py`

**Cambios requeridos:**

```python
def _format_cv_context(self, chunks: List[Dict]) -> str:
    """
    Formatea chunks con TODA la metadata estructurada para el LLM.
    """
    context_parts = []
    
    # Agrupar chunks por candidato
    candidates = self._group_by_candidate(chunks)
    
    for cv_id, candidate_chunks in candidates.items():
        # Obtener metadata del primer chunk (summary)
        meta = candidate_chunks[0].get("metadata", {})
        
        # Header estructurado
        header = f"""
═══════════════════════════════════════════════════════
CANDIDATE: {meta.get('candidate_name', 'Unknown')}
CV ID: {cv_id}
═══════════════════════════════════════════════════════

📊 QUICK STATS:
  • Total Experience: {meta.get('total_experience_years', 0):.0f} years
  • Seniority: {meta.get('seniority_level', 'unknown').upper()}
  • Positions Held: {meta.get('position_count', 0)}
  • Avg Tenure: {meta.get('avg_tenure_years', 0):.1f} years
  • Job Stability Score: {self._format_stability(meta.get('job_hopping_score', 0))}
  • Employment Gaps: {meta.get('employment_gaps_count', 0)}

💼 CURRENT POSITION:
  • Role: {meta.get('current_role', 'Not specified')}
  • Company: {meta.get('current_company', 'Not specified')}

🛠️ SKILLS:
  {self._format_skills(meta.get('skills', ''))}

🌐 LANGUAGES:
  {self._format_languages(meta.get('languages', ''))}

🎓 EDUCATION:
  • Level: {meta.get('education_level', 'Not specified').upper()}
  • Institution: {meta.get('education_institution', 'Not specified')}
  • Field: {meta.get('education_field', 'Not specified')}

📜 CERTIFICATIONS:
  {self._format_certifications(meta.get('certifications', ''))}

───────────────────────────────────────────────────────
CV CONTENT:
───────────────────────────────────────────────────────
"""
        context_parts.append(header)
        
        # Añadir contenido de cada chunk
        for chunk in candidate_chunks:
            context_parts.append(chunk.get("content", ""))
        
        context_parts.append("\n")
    
    return "\n".join(context_parts)
```

---

## 📦 FASE 5: LLM OUTPUT PARSING

### 5.1 Problema Actual

El LLM genera markdown que no se parsea correctamente, resultando en:
- Tablas vacías
- Secciones de análisis incompletas
- "No candidates match" cuando sí hay matches

### 5.2 Archivo: `backend/app/services/output_processor/orchestrator.py`

**Cambios requeridos:**

```python
def process(self, raw_llm_output: str, ...) -> tuple[StructuredOutput, str]:
    """
    CRÍTICO: Mejorar parsing del output del LLM.
    """
    
    # 1. Limpiar output
    cleaned = self._pre_clean_llm_output(raw_llm_output)
    
    # 2. NUEVO: Extraer tablas markdown de forma robusta
    tables = self._extract_markdown_tables(cleaned)
    
    # 3. NUEVO: Si no hay tablas en el output, generar desde chunks
    if not tables and chunks:
        tables = self._generate_tables_from_chunks(chunks, query_type)
    
    # 4. NUEVO: Extraer análisis y conclusión
    analysis = self._extract_analysis_section(cleaned)
    conclusion = self._extract_conclusion_section(cleaned)
    
    # 5. Construir output estructurado
    return self._build_structured_output(...)

def _extract_markdown_tables(self, text: str) -> List[Dict]:
    """
    Extrae tablas markdown robustamente.
    
    Handles:
    - | Header1 | Header2 |
    - |---------|---------|
    - | Value1  | Value2  |
    
    Returns:
    [
        {
            "headers": ["Header1", "Header2"],
            "rows": [["Value1", "Value2"], ...]
        }
    ]
    """
    tables = []
    lines = text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Detectar inicio de tabla (línea con |)
        if line.startswith('|') and line.endswith('|'):
            table = self._parse_table_block(lines, i)
            if table:
                tables.append(table)
                i += len(table.get('_raw_lines', []))
                continue
        
        i += 1
    
    return tables

def _generate_tables_from_chunks(
    self, 
    chunks: List[Dict], 
    query_type: str
) -> List[Dict]:
    """
    FALLBACK: Genera tablas desde metadata de chunks cuando el LLM no lo hace.
    
    Esto soluciona el problema de tablas vacías.
    """
    if query_type == "comparison":
        return self._generate_comparison_table(chunks)
    elif query_type == "ranking":
        return self._generate_ranking_table(chunks)
    elif query_type == "search":
        return self._generate_search_results_table(chunks)
    
    return []

def _generate_comparison_table(self, chunks: List[Dict]) -> List[Dict]:
    """
    Genera tabla de comparación desde metadata de chunks.
    """
    # Agrupar por candidato
    candidates = {}
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        cv_id = meta.get("cv_id")
        if cv_id not in candidates:
            candidates[cv_id] = {
                "name": meta.get("candidate_name", "Unknown"),
                "skills": meta.get("skills", ""),
                "experience": meta.get("total_experience_years", 0),
                "current_role": meta.get("current_role", ""),
                "score": chunk.get("score", 0)
            }
    
    # Construir tabla
    headers = ["Candidate", "Relevant Skills/Experience", "Why They Match", "Score"]
    rows = []
    
    for cv_id, data in candidates.items():
        rows.append([
            data["name"],
            f"{data['current_role']}, {data['skills'][:50]}...",
            f"{data['experience']:.0f} years experience",
            f"{data['score']*100:.0f}%"
        ])
    
    return [{"headers": headers, "rows": rows}]
```

---

## 📦 FASE 6: OUTPUT MODULES

### 6.1 Problema Actual

Los módulos de output no extraen datos correctamente, especialmente:
- `comparison_structure.py`: Tabla vacía
- `search_structure.py`: "No candidates match"
- `job_match_structure.py`: Match scores incorrectos

### 6.2 Archivos a modificar:

```
backend/app/services/output_processor/structures/
├── comparison_structure.py
├── search_structure.py
├── ranking_structure.py
├── job_match_structure.py
└── verification_structure.py
```

### 6.3 Ejemplo: `comparison_structure.py`

```python
class ComparisonStructure:
    def assemble(
        self,
        llm_output: str,
        chunks: List[Dict],
        conversation_history: List[Dict]
    ) -> Dict:
        """
        Ensambla estructura de comparación.
        
        CRÍTICO: Si el LLM no generó tabla, crear desde chunks.
        """
        # 1. Intentar extraer tabla del LLM
        table_data = self._extract_comparison_table(llm_output)
        
        # 2. FALLBACK: Generar desde chunks si tabla vacía
        if not table_data or not table_data.get("rows"):
            logger.warning("[COMPARISON] Table empty from LLM, generating from chunks")
            table_data = self._generate_from_chunks(chunks)
        
        # 3. Extraer análisis
        analysis = self._extract_analysis(llm_output)
        
        # 4. FALLBACK: Generar análisis si vacío
        if not analysis:
            analysis = self._generate_analysis_from_chunks(chunks)
        
        return {
            "structure_type": "comparison",
            "table_data": table_data,
            "analysis": analysis,
            "conclusion": self._extract_conclusion(llm_output),
            # NUEVO: Siempre incluir datos raw de chunks
            "raw_candidate_data": self._extract_candidate_data(chunks)
        }
    
    def _generate_from_chunks(self, chunks: List[Dict]) -> Dict:
        """
        Genera tabla de comparación desde metadata de chunks.
        """
        candidates = self._group_chunks_by_candidate(chunks)
        
        rows = []
        for cv_id, candidate_data in candidates.items():
            meta = candidate_data["metadata"]
            rows.append({
                "candidate": meta.get("candidate_name", "Unknown"),
                "cv_id": cv_id,
                "skills": meta.get("skills", "").split(",")[:5],
                "experience": f"{meta.get('total_experience_years', 0):.0f} years",
                "current_role": meta.get("current_role", ""),
                "match_reason": self._infer_match_reason(candidate_data),
                "score": candidate_data.get("score", 0)
            })
        
        return {
            "headers": ["Candidate", "Relevant Skills/Experience", "Why They Match", "Score"],
            "rows": rows
        }
```

---

## 📦 FASE 7: SUPABASE INTEGRATION

### 7.1 Migración a Supabase

**Nuevo archivo:** `backend/app/services/supabase_service.py`

```python
class SupabaseService:
    """
    Servicio principal de Supabase para V10.
    """
    
    def __init__(self):
        self.client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
    
    # ====== CV STORAGE ======
    
    async def store_cv(self, cv_data: Dict) -> str:
        """Almacena CV completo en Supabase."""
        pass
    
    async def store_chunks(self, chunks: List[Dict], embeddings: List[List[float]]) -> int:
        """Almacena chunks con embeddings en pgvector."""
        pass
    
    # ====== SEARCH ======
    
    async def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        filters: Dict = None,
        k: int = 10
    ) -> List[Dict]:
        """
        Búsqueda híbrida: vector + full-text.
        
        Usa función RPC de Supabase:
        - match_cv_chunks(query_embedding, match_threshold, match_count)
        - Combina con ts_query para full-text
        """
        pass
    
    # ====== METADATA QUERIES ======
    
    async def get_candidates_by_skill(self, skill: str) -> List[Dict]:
        """Obtiene candidatos que tienen un skill específico."""
        pass
    
    async def get_candidates_by_language(self, language: str) -> List[Dict]:
        """Obtiene candidatos que hablan un idioma."""
        pass
    
    async def get_candidates_by_certification(self, cert: str) -> List[Dict]:
        """Obtiene candidatos con una certificación."""
        pass
    
    async def get_candidates_by_experience_range(
        self, 
        min_years: int, 
        max_years: int = None
    ) -> List[Dict]:
        """Obtiene candidatos por rango de experiencia."""
        pass
```

### 7.2 Schema de Supabase

```sql
-- Tabla principal de CVs
CREATE TABLE cvs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cv_id TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    candidate_name TEXT,
    raw_text TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Metadata estructurada
CREATE TABLE cv_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cv_id TEXT REFERENCES cvs(cv_id),
    total_experience_years FLOAT,
    current_role TEXT,
    current_company TEXT,
    seniority_level TEXT,
    job_hopping_score FLOAT,
    avg_tenure_years FLOAT,
    employment_gaps_count INT,
    location TEXT,
    UNIQUE(cv_id)
);

-- Skills
CREATE TABLE cv_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cv_id TEXT REFERENCES cvs(cv_id),
    skill_name TEXT NOT NULL,
    skill_level INT,  -- 1-10
    is_technical BOOLEAN DEFAULT TRUE
);
CREATE INDEX idx_cv_skills_name ON cv_skills(skill_name);

-- Languages
CREATE TABLE cv_languages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cv_id TEXT REFERENCES cvs(cv_id),
    language TEXT NOT NULL,
    level TEXT,  -- A1, A2, B1, B2, C1, C2
    is_native BOOLEAN DEFAULT FALSE
);
CREATE INDEX idx_cv_languages ON cv_languages(language);

-- Certifications
CREATE TABLE cv_certifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cv_id TEXT REFERENCES cvs(cv_id),
    certification_name TEXT NOT NULL,
    issuer TEXT,
    year_obtained INT
);
CREATE INDEX idx_cv_certs ON cv_certifications(certification_name);

-- Education
CREATE TABLE cv_education (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cv_id TEXT REFERENCES cvs(cv_id),
    degree TEXT,
    field TEXT,
    institution TEXT,
    graduation_year INT
);

-- Experience entries
CREATE TABLE cv_experiences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cv_id TEXT REFERENCES cvs(cv_id),
    job_title TEXT,
    company TEXT,
    start_year INT,
    end_year INT,
    is_current BOOLEAN DEFAULT FALSE,
    duration_years FLOAT,
    description TEXT,
    position_order INT
);

-- Chunks con embeddings (pgvector)
CREATE TABLE cv_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cv_id TEXT REFERENCES cvs(cv_id),
    chunk_index INT,
    section_type TEXT,
    content TEXT,
    embedding vector(1536),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para búsqueda
CREATE INDEX idx_chunks_embedding ON cv_chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX idx_chunks_cv_id ON cv_chunks(cv_id);
CREATE INDEX idx_chunks_section ON cv_chunks(section_type);

-- Full-text search
ALTER TABLE cv_chunks ADD COLUMN content_tsv tsvector
GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
CREATE INDEX idx_chunks_fts ON cv_chunks USING GIN(content_tsv);

-- Función de búsqueda híbrida
CREATE OR REPLACE FUNCTION hybrid_search_cv_chunks(
    query_embedding vector(1536),
    query_text text,
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 10,
    session_cv_ids text[] DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    cv_id text,
    content text,
    metadata jsonb,
    similarity float,
    text_rank float,
    combined_score float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.cv_id,
        c.content,
        c.metadata,
        1 - (c.embedding <=> query_embedding) as similarity,
        ts_rank(c.content_tsv, plainto_tsquery('english', query_text)) as text_rank,
        -- RRF combination
        (0.7 * (1 - (c.embedding <=> query_embedding))) + 
        (0.3 * ts_rank(c.content_tsv, plainto_tsquery('english', query_text))) as combined_score
    FROM cv_chunks c
    WHERE 
        (session_cv_ids IS NULL OR c.cv_id = ANY(session_cv_ids))
        AND 1 - (c.embedding <=> query_embedding) > match_threshold
    ORDER BY combined_score DESC
    LIMIT match_count;
END;
$$;
```

---

## 📋 ORDEN DE IMPLEMENTACIÓN

### Sprint 1 (Semana 1-2): CV Parsing Robusto
1. ✅ Fix job title extraction
2. ✅ Fix company extraction  
3. ✅ Fix total experience calculation
4. [ ] Add education extraction
5. [ ] Add language extraction with levels
6. [ ] Add certification extraction with dates
7. [ ] Add skill levels extraction (9/10 format)

### Sprint 2 (Semana 2-3): Embeddings Enriquecidos
1. [ ] Implement enriched text builder
2. [ ] Update vector store to use enriched text
3. [ ] Add metadata-based filtering
4. [ ] Test semantic search with new embeddings

### Sprint 3 (Semana 3-4): Retrieval Mejorado
1. [ ] Implement query strategy detection
2. [ ] Add metadata filtered search
3. [ ] Add skill-based search
4. [ ] Add experience range filtering
5. [ ] Improve RRF fusion

### Sprint 4 (Semana 4-5): LLM Pipeline
1. [ ] Improve prompt templates with full metadata
2. [ ] Fix output parsing for tables
3. [ ] Add fallback table generation from chunks
4. [ ] Fix analysis/conclusion extraction

### Sprint 5 (Semana 5-6): Output Modules
1. [ ] Fix comparison_structure.py
2. [ ] Fix search_structure.py
3. [ ] Fix job_match_structure.py
4. [ ] Fix verification_structure.py
5. [ ] Add raw data fallbacks

### Sprint 6 (Semana 6-7): Supabase Integration
1. [ ] Create Supabase schema
2. [ ] Implement SupabaseVectorStore
3. [ ] Implement hybrid search function
4. [ ] Migrate local store to Supabase
5. [ ] Add metadata query endpoints

### Sprint 7 (Semana 7-8): Testing & Polish
1. [ ] End-to-end testing with 23 CVs
2. [ ] Performance optimization
3. [ ] Error handling
4. [ ] Documentation

---

## ✅ CHECKLIST FINAL

- [ ] CVs extraen TODOS los campos correctamente
- [ ] Embeddings incluyen metadata estructurada
- [ ] Retrieval encuentra chunks relevantes para cualquier query
- [ ] LLM recibe contexto completo y formateado
- [ ] Tablas siempre tienen datos (nunca vacías)
- [ ] Análisis siempre tiene contenido
- [ ] "No candidates match" solo cuando realmente no hay matches
- [ ] Supabase como fuente principal funcionando
- [ ] Búsqueda híbrida (vector + text) funcionando
- [ ] Queries de metadata funcionando ("speaks French", "has AWS")

---

*Documento creado: 2026-01-11*
*Versión: V10 Planning*
