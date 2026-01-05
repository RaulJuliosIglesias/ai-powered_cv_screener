# Plan de Implementación V2: Output Estructurado

## Problemas Identificados

### 1. Referencias CV Rotas (CRÍTICO)
```
ACTUAL:    **Aisha Nkosi Staff** cv_a3a1761e [cv_a3a1761e](cv_a3a1761e)
ESPERADO:  **[Aisha Nkosi](cv:cv_a3a1761e)**
```
- El post-procesador actual NO está limpiando estos patrones
- También aparece en medio del texto: `**Staff** cv_a3a1761e [cv_a3a1761e](cv_a3a1761e)`
- Palabras como "Solutions", "Staff" están siendo tratadas como referencias

### 2. Indicador de Análisis es MOCKUP
```
ACTUAL:    Pasos estáticos que nunca avanzan (siempre en "Understanding query...")
ESPERADO:  Pasos que avanzan en tiempo real según el pipeline
```
- El indicador actual es decorativo, no refleja el estado real
- Necesita conexión con el backend para mostrar progreso real

### 3. Output en Code Block
```
ACTUAL:    Bloque de código con markdown raw
ESPERADO:  Tabla HTML renderizada + lista formateada
```
- El LLM está generando markdown pero se muestra en code block
- Debería renderizarse como HTML

### 4. Razonamiento Pobre
```
ACTUAL:    "I need to evaluate each candidate's qualifications against the requirements for the role"
PROBLEMA:  La query NO especifica ningún rol ni criterios
ESPERADO:  "No se especificaron criterios. Evaluaré por: experiencia total, diversidad de skills, nivel de seniority"
```

### 5. Arquitectura de Componentes
```
┌─────────────────────────────────────────────────────────────┐
│ MENSAJE DE RESPUESTA                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 📊 PASOS DE ANÁLISIS (Desplegable - guardado)        │ │
│  │    ✓ Entendiendo consulta (0.2s)                     │ │
│  │    ✓ Buscando en 70 CVs (1.3s)                       │ │
│  │    ✓ Encontrados 15 relevantes                       │ │
│  │    ✓ Analizando candidatos (2.1s)                    │ │
│  │    ✓ Generando respuesta (1.5s)                      │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 🧠 RAZONAMIENTO INTERNO (Desplegable)                │ │
│  │    - Qué se pregunta: Top 3 de 70 candidatos         │ │
│  │    - Criterios: No especificados → usar defaults     │ │
│  │    - CVs relevantes: 15 encontrados                  │ │
│  │    - Confianza: Alta                                 │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 📝 RESPUESTA DIRECTA                                 │ │
│  │    Los top 3 candidatos son: [Name](cv:id)...        │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 📊 TABLA DE ANÁLISIS (Copiable)                      │ │
│  │    | Candidato | Skills | Experiencia | Score |      │ │
│  │    |-----------|--------|-------------|-------|      │ │
│  │    | [Name]()  | ...    | ...         | ⭐⭐⭐  |      │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ ✅ CONCLUSIÓN                                         │ │
│  │    Recomiendo entrevistar a [Name](cv:id)...         │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Tareas de Implementación

### FASE 1: Backend - Limpiar Output (URGENTE)

#### 1.1 Mejorar Post-procesador de Referencias
**Archivo**: `backend/app/services/rag_service_v5.py`

Patrones a limpiar:
```python
# Patrón 1: Nombre cv_xxx [cv_xxx](cv_xxx)
"**Aisha Nkosi Staff** cv_a3a1761e [cv_a3a1761e](cv_a3a1761e)"
→ "**[Aisha Nkosi](cv:cv_a3a1761e)**"

# Patrón 2: **Palabra** cv_xxx [cv_xxx](cv_xxx) en medio de texto
"AWS Certified **Solutions** cv_5c64ca1d [cv_5c64ca1d](cv_5c64ca1d) Architect"
→ "AWS Certified Solutions Architect"

# Patrón 3: Nombre cv_xxx al final de oración
"Consider interviewing Aisha Nkosi Staff cv_a3a1761e"
→ "Consider interviewing **[Aisha Nkosi](cv:cv_a3a1761e)**"
```

#### 1.2 Mejorar Prompt del LLM
**Archivo**: `backend/app/services/reasoning_service.py`

Cambios:
- Si query no tiene criterios, el LLM debe decir qué criterios usará
- Prohibir referencias rotas en el output
- Forzar tabla con formato correcto

### FASE 2: Backend - Pipeline Metrics

#### 2.1 Agregar métricas de tiempo por paso
**Archivo**: `backend/app/services/rag_service_v5.py`

```python
pipeline_steps = [
    {"step": "query_understanding", "duration_ms": 200, "status": "completed"},
    {"step": "retrieval", "duration_ms": 1300, "results": 15, "status": "completed"},
    {"step": "analysis", "duration_ms": 2100, "status": "completed"},
    {"step": "generation", "duration_ms": 1500, "status": "completed"},
]
```

#### 2.2 Incluir pasos en respuesta API
Agregar `pipeline_steps` al response JSON

### FASE 3: Frontend - Componentes

#### 3.1 PipelineStepsPanel (NUEVO)
- Muestra pasos reales del pipeline
- Lee de `response.pipeline_steps`
- Desplegable, guardado con el mensaje

#### 3.2 ReasoningPanel (MODIFICAR)
- Solo muestra razonamiento del LLM
- Separado de los pasos del pipeline

#### 3.3 AnalysisTable (NUEVO)
- Renderiza tabla HTML desde markdown
- Botón "Copy Table"
- Links de candidatos clickeables

#### 3.4 Arreglar renderizado de markdown
- No mostrar en code block
- Renderizar como HTML

---

## Orden de Ejecución

1. **AHORA**: Fix post-procesador backend (referencias rotas)
2. **AHORA**: Fix prompt LLM (mejor razonamiento)
3. **DESPUÉS**: Agregar pipeline_steps al backend
4. **DESPUÉS**: Crear componentes frontend separados
5. **FINAL**: Conectar todo y probar

---

## Archivos a Modificar

| Archivo | Cambio |
|---------|--------|
| `backend/app/services/rag_service_v5.py` | Mejorar `_clean_broken_cv_references()`, agregar pipeline_steps |
| `backend/app/services/reasoning_service.py` | Mejorar prompt para casos sin criterios |
| `frontend/src/components/Message.jsx` | Separar componentes, arreglar renderizado |
| `frontend/src/App.jsx` | Conectar pipeline_steps al loading indicator |
