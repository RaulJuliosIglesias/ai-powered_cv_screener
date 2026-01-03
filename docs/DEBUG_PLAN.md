# Plan de Debug: Query No Funciona

## Problema
- Query se envía pero no hay respuesta
- Se queda en "Understanding query..."
- Error 500 sin logs claros
- No aparece output

## Estrategia de Debug

### 1. Agregar Logs Críticos
- routes_sessions.py: Log al inicio, antes de query(), después de query(), antes de return
- rag_service_v5.py: Log en cada etapa del pipeline
- _build_pipeline_steps: Log para verificar construcción

### 2. Script de Prueba
- Test directo del endpoint con logging completo
- Capturar traceback exacto

### 3. Verificar Excepciones Silenciosas
- Try-catch que no loguean
- Errores en serialización JSON
- Errores en conversión de objetos a dict

### 4. Archivos a Revisar
1. backend/app/api/routes_sessions.py - endpoint chat
2. backend/app/services/rag_service_v5.py - método query() y _build_pipeline_steps()
3. backend/app/services/rag_service_v5.py - _format_answer_with_blocks()

## Implementación
