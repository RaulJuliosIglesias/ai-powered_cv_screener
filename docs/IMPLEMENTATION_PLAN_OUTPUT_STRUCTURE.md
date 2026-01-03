# Plan de Implementación: Output Estructurado y Razonamiento en Tiempo Real

## Problemas Identificados

1. **CV Management Bug**: Muestra conteo correcto (70 CVs) pero "No CVs" al expandir
2. **Sin feedback durante análisis**: Solo "Analyzing CVs..." sin información de progreso
3. **Output mal formateado**: 
   - Referencias rotas: `cv_9b9409bd [cv_9b9409bd](cv_9b9409bd)`
   - Tabla markdown sin renderizar
   - Links de candidatos no funcionan

---

## Arquitectura de Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                        MESSAGE OUTPUT                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. ReasoningPanel (Desplegable)                        │   │
│  │     - Muestra pasos de análisis en tiempo real          │   │
│  │     - Colapsado por defecto después de completar        │   │
│  │     - Steps: Entendiendo → Buscando → Analizando →      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  2. DirectAnswer                                        │   │
│  │     - Respuesta directa 1-2 líneas                      │   │
│  │     - Con CandidateLinks clickables                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  3. AnalysisTable (Copiable)                            │   │
│  │     - Tabla HTML renderizada correctamente              │   │
│  │     - Botón "Copy Table"                                │   │
│  │     - CandidateLinks en cada fila                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  4. ConclusionPanel                                     │   │
│  │     - Box verde con icono ✓                             │   │
│  │     - Recomendación clara                               │   │
│  │     - CandidateLinks clickables                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Componentes a Crear/Modificar

### 1. `ReasoningPanel.jsx` (NUEVO)
```jsx
// Muestra pasos de análisis en tiempo real
// Props: steps[], isComplete, isExpanded
// Estados: "pending" | "in_progress" | "completed"
```

### 2. `AnalysisTable.jsx` (NUEVO)
```jsx
// Renderiza tabla de candidatos correctamente
// Props: tableData (parsed from markdown)
// Features: Copy button, proper HTML table, CandidateLinks
```

### 3. `CandidateLink.jsx` (MODIFICAR)
```jsx
// Renderiza link clickable a PDF
// Input: **[Nombre](cv:cv_xxx)**
// Output: <a href="/api/cvs/cv_xxx/pdf">Nombre 📄</a>
```

### 4. `ConclusionPanel.jsx` (EXISTE - VERIFICAR)
```jsx
// Box verde con conclusión
// Parsea CandidateLinks dentro del texto
```

### 5. `Message.jsx` (MODIFICAR)
```jsx
// Orquesta todos los componentes
// Parsea el output del LLM en secciones
```

---

## Backend: Formato de Output del LLM

### Estructura esperada:
```
:::reasoning
STEP 1: Entendiendo la consulta...
STEP 2: Buscando en 69 CVs...
STEP 3: Analizando candidatos relevantes...
STEP 4: Comparando experiencia...
STEP 5: Generando recomendación...
:::

**Direct Answer**
Los mejores candidatos son **[Carlos Mendoza](cv:cv_abc123)**, **[María García](cv:cv_def456)** y **[Juan López](cv:cv_ghi789)**.

**Analysis**
| Candidate | Skills | Experience | Score |
|-----------|--------|------------|-------|
| **[Carlos Mendoza](cv:cv_abc123)** | Python, AWS | 5 años | ⭐⭐⭐⭐ |
| **[María García](cv:cv_def456)** | Java, K8s | 4 años | ⭐⭐⭐ |
| **[Juan López](cv:cv_ghi789)** | Go, Docker | 3 años | ⭐⭐⭐ |

:::conclusion
Recomiendo contratar a **[Carlos Mendoza](cv:cv_abc123)** por su experiencia sólida en cloud y liderazgo de equipos. Como segunda opción, **[María García](cv:cv_def456)** ofrece habilidades complementarias.
:::
```

---

## Orden de Implementación

### Fase 1: Fix Bugs Críticos
1. [ ] **FIX CV Management** - Cargar CVs correctamente al expandir sesión
2. [ ] **FIX CandidateLink** - Parsear formato correcto

### Fase 2: Componentes de Output
3. [ ] **ReasoningPanel** - Panel desplegable con pasos
4. [ ] **AnalysisTable** - Tabla copiable bien renderizada
5. [ ] **Message.jsx** - Integrar todos los componentes

### Fase 3: Backend
6. [ ] **Prompt LLM** - Generar formato estructurado correcto
7. [ ] **Streaming** - Enviar pasos de razonamiento en tiempo real

---

## Archivos a Modificar

| Archivo | Cambio |
|---------|--------|
| `frontend/src/components/ReasoningPanel.jsx` | CREAR - Panel de razonamiento |
| `frontend/src/components/AnalysisTable.jsx` | CREAR - Tabla copiable |
| `frontend/src/components/CandidateLink.jsx` | CREAR - Link a PDF |
| `frontend/src/components/Message.jsx` | MODIFICAR - Integrar componentes |
| `frontend/src/App.jsx` | MODIFICAR - Fix CV Management bug |
| `backend/app/services/reasoning_service.py` | MODIFICAR - Prompt estructurado |
| `backend/app/services/rag_service_v5.py` | MODIFICAR - Formato output |
