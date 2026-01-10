# V8 Testing Guide

Guía práctica para testear todas las features implementadas en V8.

## 🚀 Arrancar el Sistema

### 1. Backend (Terminal 1)
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```

### 3. Abrir en navegador
```
http://localhost:5173
```

---

## ✅ Checklist de Testing Manual

### **Phase 1.1: Streaming Tokens**
**Cómo testear:**
1. Sube 2-3 CVs a una sesión
2. Haz una pregunta como: "¿Quién es el mejor candidato para un puesto de Python developer?"
3. **Observa**: Los tokens deben aparecer uno a uno en tiempo real (no todo el texto de golpe)
4. Verás un indicador "⚡ Live streaming..." mientras genera

**Qué buscar:**
- El texto aparece progresivamente (como si alguien estuviera escribiendo)
- Hay un cursor parpadeante `▊` mientras genera
- Los pasos del pipeline se muestran arriba (Query → Embed → Search → Rank → Generate)

---

### **Phase 1.2: Export PDF/CSV**
**Cómo testear:**
1. Después de hacer una consulta que genere un ranking
2. Busca el botón **"Exportar"** (con icono de descarga ⬇️)
3. Click → Dropdown con opciones PDF y CSV
4. Descarga ambos formatos

**Qué buscar:**
- CSV: Se abre en Excel/Google Sheets con los candidatos rankeados
- PDF: Documento profesional con tabla de candidatos y scores

**API directa (opcional):**
```bash
# CSV
curl "http://localhost:8000/api/export/{session_id}/csv?mode=local" -o report.csv

# PDF
curl "http://localhost:8000/api/export/{session_id}/pdf?mode=local" -o report.pdf
```

---

### **Phase 1.3: Fallback Chain**
**Cómo testear:**
Esta feature es automática - actúa cuando un modelo falla.

**Ver estado:**
```bash
curl http://localhost:8000/api/v8/fallback/status
```

**Simular (opcional):** Cambia temporalmente el modelo a uno inválido y verás en los logs:
```
[FALLBACK] Trying model xxx (attempt 1)
[FALLBACK] xxx failed: api_error
[FALLBACK] Trying model google/gemini-2.0-flash-001 (attempt 2)
```

---

### **Phase 2.1: Hybrid Search (BM25 + Vector)**
**Cómo testear:**
1. Sube CVs con diferentes tecnologías
2. Busca: "candidatos con experiencia en React y Node.js"
3. **Observa los logs del backend** o la respuesta

**Qué buscar:**
- En los logs verás: `[HYBRID_SEARCH] BM25 scores: ...`
- La búsqueda combina similitud semántica (vectores) + keyword matching (BM25)

**API directa:**
```bash
curl "http://localhost:8000/api/v8/hybrid-search/test?query=Python%20developer&session_id={id}&mode=local"
```

---

### **Phase 2.2: Semantic Cache**
**Cómo testear:**
1. Haz una pregunta: "¿Quién tiene más experiencia en Python?"
2. Espera la respuesta completa
3. **Haz la misma pregunta otra vez** (o muy similar)
4. La segunda respuesta debe ser INSTANTÁNEA

**Qué buscar:**
- Primera vez: Pipeline completo (5-15 segundos)
- Segunda vez: Cache hit instantáneo (<1 segundo)
- En logs: `[SEMANTIC_CACHE] Cache HIT! similarity=0.95`

**Ver cache:**
```bash
curl "http://localhost:8000/api/v8/semantic-cache/stats?mode=local"
```

---

### **Phase 2.3: Source Attribution**
**Cómo testear:**
1. Haz cualquier pregunta sobre candidatos
2. En la respuesta, busca la sección **"Fuentes"** o **"Sources"**
3. Cada afirmación debe tener referencias a los CVs

**Qué buscar:**
- Links/badges con nombres de candidatos
- Click en una fuente → Abre el CV relevante
- Chunks específicos citados

---

### **Phase 3.1: Auto-Screening Rules**
**Cómo testear:**

**Crear regla:**
```bash
curl -X POST "http://localhost:8000/api/v8/screening-rules?mode=local" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Python Senior",
    "conditions": [
      {"field": "skills", "operator": "contains", "value": "Python"},
      {"field": "experience_years", "operator": "gte", "value": 5}
    ],
    "action": "highlight",
    "priority": 1
  }'
```

**Ver reglas:**
```bash
curl "http://localhost:8000/api/v8/screening-rules?mode=local"
```

---

### **Phase 3.2: Candidate Scoring**
**Cómo testear:**
1. Haz una pregunta de ranking: "Rankea los candidatos para un puesto de Full Stack"
2. **Observa**: Cada candidato tiene un score numérico (0-100%)
3. Los scores se basan en match de skills, experiencia, etc.

**Qué buscar:**
- Tabla con columnas: Rank, Nombre, Score, Skills
- Scores varían según relevancia a la query

---

### **Phase 3.3: Interview Questions**
**Cómo testear:**
1. Pregunta: "Genera preguntas de entrevista para [nombre del candidato]"
2. O: "¿Qué preguntas técnicas le harías a los candidatos de Python?"

**Qué buscar:**
- Preguntas personalizadas basadas en el CV del candidato
- Mix de preguntas técnicas y conductuales

---

## 🔍 Verificación Rápida por API

### Endpoints de V8 disponibles:
```bash
# Verificar que V8 está activo
curl http://localhost:8000/api/v8/status

# Hybrid Search
curl "http://localhost:8000/api/v8/hybrid-search/stats?mode=local"

# Semantic Cache
curl "http://localhost:8000/api/v8/semantic-cache/stats?mode=local"

# Fallback Chain
curl http://localhost:8000/api/v8/fallback/status

# Screening Rules
curl "http://localhost:8000/api/v8/screening-rules?mode=local"

# Export formats disponibles
curl "http://localhost:8000/api/export/{session_id}/formats?mode=local"
```

---

## 📊 Ver Logs Detallados

En el backend, los logs muestran todo lo que pasa:

```bash
# Filtrar logs de V8 features
grep -E "HYBRID_SEARCH|SEMANTIC_CACHE|FALLBACK|EXPORT|SCREENING" backend.log
```

O simplemente observa la terminal donde corre el backend.

---

## 🧪 Tests Automatizados

```bash
cd backend

# Correr todos los tests
pytest tests/ -v

# Tests específicos de V8 (si existen)
pytest tests/ -v -k "v8 or export or cache or hybrid"
```

---

## ❓ Troubleshooting

| Problema | Solución |
|----------|----------|
| Export PDF falla | Verificar: `pip show fpdf2` |
| BM25 no funciona | Verificar: `pip show rank-bm25` |
| Cache no hace hit | Asegúrate de usar la misma sesión |
| Streaming no se ve | Verifica que el frontend está en modo correcto |

