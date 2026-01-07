# Implementation Plan: Unified Candidate Format

## Objective
Create ONE format to display candidate names in ALL sections (Direct Answer, Analysis, Table, Conclusion).

## Target Format
```
[📄](cv:cv_xxx) **Candidate Name**
```
- **Icon 📄**: Clickable, opens the CV PDF
- **Name**: In bold, WITHOUT underline, WITHOUT link

---

## STEP 1: Backend - Create formatting function

### File
`backend/app/services/output_processor/orchestrator.py`

### Task 1.1: Create method `_format_candidate_references()`
```python
def _format_candidate_references(self, text: str) -> str:
    """
    UNIFIED format for candidate mentions.
    Converts: [Name](cv:cv_xxx) -> [📄](cv:cv_xxx) **Name**
    """
    if not text:
        return text
    
    # Pattern: [Name](cv:cv_xxx) or [Name](cv_xxx)
    pattern = r'\[([^\]]+)\]\((cv:)?(cv_[a-z0-9_-]+)\)'
    replacement = r'[📄](cv:\3) **\1**'
    return re.sub(pattern, replacement, text, flags=re.IGNORECASE)
```

### Task 1.2: Method location
- Add after the `_fix_cv_links()` method
- Approximate line: ~200

### Verification
- [ ] Method created
- [ ] Regex pattern correct
- [ ] Replacement generates correct format

---

## STEP 2: Backend - Apply function to sections

### File
`backend/app/services/output_processor/orchestrator.py`

### Task 2.1: Modify `process()` method
In the `process()` method, after STEP 1.6 (_fix_cv_links), add:

```python
# STEP 1.7: Format candidate references with icon + bold name
if structured.direct_answer:
    structured.direct_answer = self._format_candidate_references(structured.direct_answer)
if structured.analysis:
    structured.analysis = self._format_candidate_references(structured.analysis)
if structured.conclusion:
    structured.conclusion = self._format_candidate_references(structured.conclusion)
```

### Task 2.2: Remove redundant `_fix_cv_links()`
- `_fix_cv_links()` is no longer needed if `_format_candidate_references()` does everything
- Or keep both in sequence

### Verification
- [ ] direct_answer formatted
- [ ] analysis formatted
- [ ] conclusion formatted

---

## STEP 3: Frontend - Modify cvLinkRenderer

### File
`frontend/src/components/output/StructuredOutputRenderer.jsx`

### Task 3.1: Modify `cvLinkRenderer` to detect icon
The markdown `[📄](cv:cv_xxx)` renders as a link with text "📄".

```jsx
const cvLinkRenderer = ({ href, children }) => {
    // Detectar si es un link de CV
    let cvId = null;
    if (href?.startsWith('cv:')) {
        cvId = href.replace('cv:', '');
    } else if (href?.match(/cv_[a-z0-9_-]+/i)) {
        const match = href.match(/cv_[a-z0-9_-]+/i);
        if (match) cvId = match[0];
    }
    
    // Si es CV link, renderizar solo el icono como botón
    if (cvId) {
        return (
            <button
                onClick={() => onOpenCV ? onOpenCV(cvId, '') : null}
                className="inline-flex items-center justify-center w-5 h-5 bg-blue-600/30 text-blue-400 hover:bg-blue-600/50 rounded transition-colors"
                title="View CV"
            >
                <FileText className="w-3 h-3" />
            </button>
        );
    }
    
    // Link normal
    return (
        <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
            {children}
        </a>
    );
};
```

### Tarea 3.2: Verificar que `**Nombre**` se renderiza en negrita
- ReactMarkdown ya convierte `**texto**` a `<strong>`
- No necesita modificación

### Verificación
- [ ] Icono renderiza como botón clicable
- [ ] Nombre renderiza en negrita (sin subrayado)
- [ ] Click en icono abre PDF

---

## PASO 4: Backend - Mejorar Analysis Module

### Archivo
`backend/app/services/output_processor/modules/analysis_module.py`

### Tarea 4.1: Mejorar `generate_fallback()`
El fallback debe generar RAZONAMIENTO, no repetir direct_answer.

```python
def generate_fallback(self, direct_answer: str, table_data, conclusion: str) -> Optional[str]:
    """
    Genera análisis con razonamiento real.
    
    Contenido:
    - Número de candidatos analizados
    - Criterios de selección
    - Por qué se eligieron los candidatos de la tabla
    """
    parts = []
    
    if table_data and hasattr(table_data, 'rows') and table_data.rows:
        num = len(table_data.rows)
        parts.append(f"Se analizaron {num} candidato(s) para este rol.")
        
        # Analizar match scores
        high_match = [r for r in table_data.rows if r.match_score >= 70]
        if high_match:
            parts.append(f"{len(high_match)} candidato(s) tienen match score alto (≥70%).")
        
        low_match = [r for r in table_data.rows if r.match_score < 50]
        if low_match:
            parts.append(f"{len(low_match)} candidato(s) no cumplen con los requisitos principales.")
    
    return " ".join(parts) if parts else None
```

### Tarea 4.2: Mejorar extracción de análisis del LLM
Si el LLM genera análisis igual al direct_answer, descartarlo y usar fallback.

### Verificación
- [ ] Analysis != Direct Answer
- [ ] Analysis contiene razonamiento
- [ ] Analysis menciona criterios de selección

---

## PASO 5: Backend - Mejorar Direct Answer Module

### Archivo
`backend/app/services/output_processor/modules/direct_answer_module.py`

### Tarea 5.1: Limpiar frases innecesarias
Eliminar frases como:
- "Here is the detailed analysis"
- "Here is the detailed analysis:"
- "Below is the analysis"

```python
def _clean_direct_answer(self, text: str) -> str:
    # Eliminar frases de transición al análisis
    patterns_to_remove = [
        r'\.\s*Here is the detailed analysis[:\.]?',
        r'\.\s*Below is the analysis[:\.]?',
        r'\.\s*See the analysis below[:\.]?',
    ]
    for pattern in patterns_to_remove:
        text = re.sub(pattern, '.', text, flags=re.IGNORECASE)
    return text.strip()
```

### Tarea 5.2: Aplicar limpieza en `extract()`
Llamar `_clean_direct_answer()` antes de retornar.

### Verificación
- [ ] Direct Answer es breve
- [ ] No contiene "Here is the detailed analysis"
- [ ] Termina con punto

---

## PASO 6: Build y Verificación

### Tarea 6.1: Build Frontend
```bash
cd frontend
npm run build
```

### Tarea 6.2: Iniciar aplicación
```bash
npm run dev
```

### Tarea 6.3: Pruebas manuales

#### Test 1: Query "mejor candidato para 3D art"
- [ ] Direct Answer: Respuesta breve con [📄] **Nombre**
- [ ] Analysis: Razonamiento con [📄] **Nombre**
- [ ] Table: [📄] Nombre (ya funciona)
- [ ] Conclusion: Resumen con [📄] **Nombre**

#### Test 2: Query "comparativa frontend y fullstack"
- [ ] Múltiples candidatos con formato correcto
- [ ] Match scores variados
- [ ] Iconos clicables en todas las secciones

#### Test 3: Verificar PDFs
- [ ] Click en icono abre PDF correcto
- [ ] URL: /api/cvs/{cv_id}/pdf

---

## Checklist Final

### Backend
- [ ] `_format_candidate_references()` creado
- [ ] Aplicado a direct_answer, analysis, conclusion
- [ ] Analysis genera razonamiento real
- [ ] Direct Answer limpio de frases innecesarias

### Frontend
- [ ] cvLinkRenderer detecta nuevo formato
- [ ] Icono es botón clicable
- [ ] Nombre en negrita sin subrayado
- [ ] PDFs se abren correctamente

### Consistencia
- [ ] Mismo formato en TODAS las secciones
- [ ] NO hay links subrayados en nombres
- [ ] SOLO el icono es clicable

---

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `orchestrator.py` | `_format_candidate_references()`, modificar `process()` |
| `StructuredOutputRenderer.jsx` | Modificar `cvLinkRenderer` |
| `analysis_module.py` | Mejorar `generate_fallback()` |
| `direct_answer_module.py` | Añadir `_clean_direct_answer()` |
