# RAG v12 Implementation Plan

> **Status**: 📋 PLANNED
> 
> **Date**: January 2026
> 
> **Prerequisites**: RAG v11 (PG FTS, LangGraph, Analytics) ✅
>
> **💰 Cost Philosophy**: $0 hasta tener usuarios. Free tiers everywhere. Sin Kubernetes hasta escalar.

---

## 🗺️ Roadmap Vision: V12 Position

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ROADMAP OVERVIEW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  V8 ✅    V9 ✅         V10 ✅          V11 ✅          V12 (Current)       │
│  ───────  ───────       ───────         ───────         ───────             │
│  UX       TypeScript    Multi-Tenant    Advanced        Simple              │
│  Features + CI/CD       + Auth          Features        Deploy              │
│           + Cloud                                                            │
│                                                                              │
│  ✅ Done  ✅ Done       ✅ Done         ✅ Done         • Vercel (FREE)     │
│                                                         • Render (FREE)     │
│                                                         • Supabase (FREE)   │
│                                                         • GitHub Actions    │
│                                                                              │
│  🧪 LOCAL 📘 TS         🔐 AUTH         🚀 ADVANCED     🌐 PRODUCTION       │
│  Done     + ☁️ CLOUD    Supabase FREE   PG FTS          $0 hasta escalar    │
│           + 🔄 CI/CD    RLS included    LangGraph       Free tiers          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ❌ Por Qué NO Kubernetes (Todavía)

| Factor | Kubernetes | Free Tiers (Vercel + Render) |
|--------|------------|------------------------------|
| **Costo** | $50-200/mes mínimo | $0 |
| **Complejidad** | Alta (clusters, pods, helm) | Baja (git push = deploy) |
| **Tu escala actual** | 0 usuarios | Suficiente para ~100 usuarios |
| **Tiempo setup** | 2-5 días | 2 horas |
| **Mantenimiento** | Constante | Cero |

**Filosofía**: No pagar por infraestructura hasta que el producto valide que hay demanda.

---

## Executive Summary

RAG v12 focuses on **deploy simple y gratuito**:

### 🎯 Key Objectives

1. **Frontend en Vercel** - Deploy automático, CDN global, $0
2. **Backend en Render** - Free tier con 750h/mes, $0
3. **Database en Supabase** - Ya lo tienes, $0
4. **CI/CD con GitHub Actions** - Ya configurado en V9, $0

### 📊 Stack de Producción ($0/mes)

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION STACK (FREE)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   [Usuario]                                                      │
│       │                                                          │
│       ▼                                                          │
│   ┌─────────────┐                                               │
│   │   Vercel    │  Frontend (React/TypeScript)                  │
│   │   (FREE)    │  - CDN global                                 │
│   │   100GB/mes │  - HTTPS automático                           │
│   └─────────────┘  - Preview deploys                            │
│       │                                                          │
│       ▼                                                          │
│   ┌─────────────┐                                               │
│   │   Render    │  Backend (FastAPI/Python)                     │
│   │   (FREE)    │  - 750h/mes                                   │
│   │   512MB RAM │  - Sleep después 15min inactividad            │
│   └─────────────┘  - Wake up en ~30s                            │
│       │                                                          │
│       ▼                                                          │
│   ┌─────────────┐                                               │
│   │  Supabase   │  Database + Auth + Storage                    │
│   │   (FREE)    │  - 500MB DB                                   │
│   │   pgvector  │  - 1GB storage                                │
│   └─────────────┘  - 50K auth users                             │
│       │                                                          │
│       ▼                                                          │
│   ┌─────────────┐                                               │
│   │ OpenRouter  │  LLM APIs (pay-per-use)                       │
│   │  (per-use)  │  - Gemini FREE tier                           │
│   │   ~$1-5/mes │  - GPT-4o-mini $0.15/1M tokens                │
│   └─────────────┘                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Timeline Overview

| Phase | Focus | Duration | Features |
|-------|-------|----------|----------|
| **Phase 1** | Vercel Setup (Frontend) | 1 día | Deploy, dominio, env vars |
| **Phase 2** | Render Setup (Backend) | 1 día | Deploy, health checks |
| **Phase 3** | Conectar Todo | 0.5 días | CORS, URLs de producción |
| **Phase 4** | Monitoring Básico | 0.5 días | Logs, alertas simples |
| **Total** | | **3 días** | **Producción lista** |

---

## 🌐 Phase 1: Frontend en Vercel (1 día)

### 1.1 Conectar Repositorio
**Time**: 15 min | **Priority**: 🔴 CRÍTICA

1. Ir a [vercel.com](https://vercel.com)
2. "Import Project" → Seleccionar repo de GitHub
3. Root Directory: `frontend`
4. Framework Preset: `Vite`

### 1.2 Environment Variables
**Time**: 15 min | **Priority**: 🔴 CRÍTICA

```bash
# En Vercel Dashboard → Settings → Environment Variables
VITE_API_URL=https://cv-screener-api.onrender.com
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
```

### 1.3 Build Settings
**Time**: 10 min | **Priority**: 🔴 CRÍTICA

```yaml
# vercel.json (crear en frontend/)
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite"
}
```

### 1.4 Dominio Personalizado (Opcional)
**Time**: 30 min | **Priority**: 🟢 BAJA

- Vercel da dominio gratis: `cv-screener.vercel.app`
- O conectar dominio propio en Settings → Domains

---

## 🖥️ Phase 2: Backend en Render (1 día)

### 2.1 Crear Web Service
**Time**: 30 min | **Priority**: 🔴 CRÍTICA

1. Ir a [render.com](https://render.com)
2. "New" → "Web Service"
3. Conectar repo GitHub
4. Configurar:

```yaml
# render.yaml (crear en root del proyecto)
services:
  - type: web
    name: cv-screener-api
    env: python
    region: oregon  # Cerca de Supabase si está en us-west
    plan: free
    buildCommand: |
      cd backend
      pip install -r requirements.txt
    startCommand: |
      cd backend
      uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: OPENROUTER_API_KEY
        sync: false  # Configurar manualmente
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_KEY
        sync: false
      - key: HUGGINGFACE_API_KEY
        sync: false
      - key: DEFAULT_MODE
        value: cloud
```

### 2.2 Environment Variables en Render
**Time**: 15 min | **Priority**: 🔴 CRÍTICA

```bash
# En Render Dashboard → Environment
OPENROUTER_API_KEY=sk-or-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...  # Service key, no anon
SUPABASE_ANON_KEY=eyJ...
HUGGINGFACE_API_KEY=hf_...
DEFAULT_MODE=cloud
CORS_ORIGINS=https://cv-screener.vercel.app,https://tu-dominio.com
```

### 2.3 Health Check Endpoint
**Time**: 15 min | **Priority**: 🔴 ALTA

Verificar que existe en `backend/app/main.py`:

```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "8.0"}
```

---

## 🔗 Phase 3: Conectar Todo (0.5 días)

### 3.1 Actualizar CORS en Backend
**Time**: 15 min | **Priority**: 🔴 CRÍTICA

En `backend/app/config.py`, asegurar que CORS incluye Vercel:

```python
cors_origins: str = "https://cv-screener.vercel.app,http://localhost:5173"
```

### 3.2 Actualizar API URL en Frontend
**Time**: 15 min | **Priority**: 🔴 CRÍTICA

En `frontend/src/lib/api.ts`:

```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

### 3.3 Verificar Supabase Policies
**Time**: 30 min | **Priority**: 🔴 ALTA

Asegurar que RLS policies permiten acceso desde producción:
- Verificar que `user_id` se propaga correctamente
- Probar auth flow end-to-end

---

## 📊 Phase 4: Monitoring Básico (0.5 días)

### 4.1 Logs en Render
**Time**: 15 min | **Priority**: 🟡 MEDIA

- Render Dashboard → Logs (incluido gratis)
- Configurar retención: 7 días (gratis)

### 4.2 Alertas Simples
**Time**: 30 min | **Priority**: 🟡 MEDIA

**Opción 1: UptimeRobot (gratis)**
- Crear cuenta en [uptimerobot.com](https://uptimerobot.com)
- Monitorear: `https://cv-screener-api.onrender.com/health`
- Alerta por email si cae

**Opción 2: GitHub Actions (ya tienes)**
```yaml
# .github/workflows/health-check.yml
name: Health Check
on:
  schedule:
    - cron: '0 */6 * * *'  # Cada 6 horas

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - name: Check API health
        run: |
          response=$(curl -s -o /dev/null -w "%{http_code}" https://cv-screener-api.onrender.com/health)
          if [ $response != "200" ]; then
            echo "API is down!"
            exit 1
          fi
```

---

## ⚠️ Limitaciones del Free Tier

### Render Free Tier
| Limitación | Impacto | Workaround |
|------------|---------|------------|
| Sleep después 15min | Primera request lenta (~30s) | Mostrar loading spinner |
| 750h/mes | ~25h/día | Suficiente para demo |
| 512MB RAM | Puede ser justo | Optimizar imports |

### Vercel Free Tier
| Limitación | Impacto | Workaround |
|------------|---------|------------|
| 100GB bandwidth/mes | Suficiente para ~10K usuarios | Ninguno |
| Serverless timeout 10s | N/A (frontend estático) | N/A |

### Supabase Free Tier
| Limitación | Impacto | Workaround |
|------------|---------|------------|
| 500MB DB | ~50K CVs con embeddings | Suficiente |
| 1GB storage | ~200 PDFs | Suficiente |
| Pause after 1 week inactivity | Puede pausarse | Ping periódico |

---

## 💰 Cost Estimate

| Service | Monthly Cost | Notes |
|---------|-------------|-------|
| Vercel (Frontend) | $0 | Free tier |
| Render (Backend) | $0 | Free tier |
| Supabase | $0 | Free tier |
| GitHub Actions | $0 | Free tier (2000 min/mes) |
| OpenRouter (LLM) | ~$1-5 | Pay per use (Gemini free + GPT backup) |
| HuggingFace | $0 | Free tier (30K req/hour) |
| Dominio (opcional) | $10-15/año | Solo si quieres .com |
| **Total V12** | **$0-5/month** | Solo pagas por LLM usage |

### 📈 Cuándo Escalar (Salir de Free Tier)

| Señal | Acción | Costo Mensual |
|-------|--------|---------------|
| Backend lento constantemente | Render Starter | +$7 |
| >100 usuarios concurrentes | Render Standard | +$25 |
| >500MB en DB | Supabase Pro | +$25 |
| >100GB bandwidth | Vercel Pro | +$20 |
| Necesitas SLA/uptime | Todo Pro | ~$77/mes |

**Regla**: No escalar hasta que el problema exista y afecte usuarios.

---

## 🚀 Quick Start

```bash
# 1. Deploy Frontend a Vercel
# - Conectar repo en vercel.com
# - Configurar env vars
# - Deploy automático en cada push a main

# 2. Deploy Backend a Render
# - Conectar repo en render.com
# - Configurar render.yaml
# - Configurar env vars
# - Deploy automático en cada push a main

# 3. Verificar
curl https://cv-screener-api.onrender.com/health
# {"status": "healthy", "version": "8.0"}

# 4. Abrir frontend
open https://cv-screener.vercel.app
```

---

## 📝 V12 Completion Checklist

### Phase 1: Vercel
- [ ] Conectar repo a Vercel
- [ ] Configurar build settings
- [ ] Añadir env vars (VITE_*)
- [ ] Verificar deploy preview
- [ ] Deploy a producción

### Phase 2: Render
- [ ] Conectar repo a Render
- [ ] Crear render.yaml
- [ ] Añadir env vars
- [ ] Verificar health check
- [ ] Deploy a producción

### Phase 3: Conectar
- [ ] Actualizar CORS en backend
- [ ] Actualizar API_URL en frontend
- [ ] Probar auth flow
- [ ] Probar upload CV
- [ ] Probar queries RAG

### Phase 4: Monitoring
- [ ] Verificar logs en Render
- [ ] Configurar UptimeRobot (o similar)
- [ ] Documentar URLs de producción

### Validation
- [ ] Frontend accesible en Vercel URL
- [ ] Backend responde en Render URL
- [ ] Auth funciona end-to-end
- [ ] RAG queries funcionan
- [ ] Costo mensual = $0 (excepto LLM usage)

---

## 🔮 Futuro: Cuándo Migrar a Kubernetes

Solo considerar K8s cuando:
- [ ] >1000 usuarios activos mensuales
- [ ] Necesitas auto-scaling real
- [ ] Necesitas múltiples regiones
- [ ] Tienes presupuesto de >$200/mes para infra
- [ ] Tienes DevOps dedicado

**Hasta entonces**: Vercel + Render + Supabase es suficiente y GRATIS.
