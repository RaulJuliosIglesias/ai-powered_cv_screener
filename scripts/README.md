# 🛠️ Scripts

Utility scripts for development, testing, and setup.

## Scripts Disponibles

### `demo_queries.py`
Demo script that runs sample queries against the API to showcase RAG pipeline capabilities.

```bash
python scripts/demo_queries.py --base-url http://localhost:8000 --mode local
```

### `test_cloud_mode.py`
Diagnostic script to verify cloud mode configuration (Supabase + OpenRouter).

```bash
python scripts/test_cloud_mode.py
```

### `test_cloud_upload.py`
Tests the complete cloud upload flow: embeddings creation and Supabase storage.

```bash
python scripts/test_cloud_upload.py
```

### `run_supabase_setup.py`
One-time setup script to initialize Supabase tables and storage bucket.

```bash
python scripts/run_supabase_setup.py
```

### `setup_supabase_complete.sql`
SQL script with all table definitions for manual Supabase setup via SQL Editor.

## Notas

- Todos los scripts asumen que se ejecutan desde la raíz del proyecto
- Requieren que el entorno virtual de Python esté activado
- Los scripts de cloud requieren credenciales en `backend/.env`
