# CV Screener - Deployment Guide

This guide covers deployment options for the CV Screener application using Docker, Kubernetes, and Railway.

## 🌐 Live Production

| Environment | URL | Status |
|-------------|-----|--------|
| **Production** | [https://ai-poweredcvscreener-production.up.railway.app/](https://ai-poweredcvscreener-production.up.railway.app/) | ✅ Live |
| **API Docs** | [https://ai-poweredcvscreener-production.up.railway.app/docs](https://ai-poweredcvscreener-production.up.railway.app/docs) | ✅ Live |

> **Current Deployment**: Railway (Monolith) + Supabase (Database + Storage)

---

## Table of Contents

- [Production Architecture](#production-architecture)
- [Architecture Overview](#architecture-overview)
- [Quick Start with Docker Compose](#quick-start-with-docker-compose)
- [Railway Deployment](#railway-deployment) ← **Recommended**
- [Kubernetes Deployment](#kubernetes-deployment)
- [Environment Variables](#environment-variables)
- [User API Key Configuration](#user-api-key-configuration)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│                    (React + Vite + Nginx)                   │
│                         Port: 80                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          │ /api/* proxy
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                         Backend                              │
│                   (FastAPI + Uvicorn)                       │
│                        Port: 8000                            │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   RAG       │  │  OpenRouter │  │   ChromaDB/Supabase │  │
│  │  Pipeline   │  │   API       │  │     Vector Store    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key Feature**: Users provide their own OpenRouter API key through the frontend Settings panel - no server-side API key required for basic operation.

---

## Quick Start with Docker Compose

### Development Mode

```bash
# Start development environment with hot reload
docker-compose -f docker-compose.dev.yml up --build

# Access:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Production Mode

```bash
# Build and start production containers
docker-compose up --build -d

# Access:
# - Application: http://localhost (port 80)
# - Backend proxied through /api
```

### Build Individual Images

```bash
# Backend
cd backend
docker build -t cv-screener-backend:latest .

# Frontend
cd frontend
docker build -t cv-screener-frontend:latest .
```

---

## Railway Deployment

> **This is the recommended deployment method** - it's what powers the production instance.

Railway supports single-container deployments. We provide a monolith Dockerfile that combines frontend and backend.

### Production Instance

The live production is deployed using this exact configuration:

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAILWAY (Production)                          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Dockerfile.railway (Monolith)               │    │
│  │                                                          │    │
│  │   Stage 1: Build Frontend (React + Vite)                │    │
│  │      ↓                                                   │    │
│  │   Stage 2: Install Python Dependencies                  │    │
│  │      ↓                                                   │    │
│  │   Stage 3: Final Image (~2GB)                           │    │
│  │      • FastAPI serves /api/*                            │    │
│  │      • Static files served from /app/static             │    │
│  │                                                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    SUPABASE (Free Tier)                  │    │
│  │   • PostgreSQL + pgvector (768-dim embeddings)          │    │
│  │   • Storage bucket: cv-pdfs                             │    │
│  │   • Tables: cvs, cv_embeddings, sessions, messages      │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Why Railway + Monolith?

1. **Simplicity**: Single container = single deployment = no networking issues
2. **Cost Effective**: ~$5/month with moderate usage (pay-per-use)
3. **Fast Deploys**: Git push → auto-deploy in ~3 minutes
4. **Zero Config SSL**: HTTPS provided automatically
5. **No Cold Starts**: Unlike serverless, the container stays warm

### Option 1: One-Click Deploy (Recommended)

1. Fork this repository to your GitHub account
2. Go to [Railway](https://railway.app)
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your forked repository
5. Railway will auto-detect the `Dockerfile.railway`
6. **Set environment variables** (see below)

### Option 2: Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

### Railway Environment Variables

Set these in Railway Dashboard → Variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `DEFAULT_MODE` | **Yes** | Set to `cloud` for production |
| `SUPABASE_URL` | **Yes** | Your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | **Yes** | Supabase service role key |
| `CORS_ORIGINS` | No | Comma-separated allowed origins (auto-configured) |
| `LOG_LEVEL` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`) |

> **Important**: `OPENROUTER_API_KEY` is **NOT required** on the server. Users provide their own keys through the Settings panel in the UI. This design:
> - Eliminates server-side LLM costs
> - Gives users full control over their API usage
> - Allows users to choose their preferred OpenRouter models

### Railway File Structure

```
├── Dockerfile.railway      # Monolith build (frontend + backend)
├── nginx.railway.conf      # Nginx config for Railway
├── start.railway.sh        # Startup script
├── railway.json            # Railway configuration
└── railway.toml            # Alternative Railway config
```

---

## Kubernetes Deployment

For production-grade deployments with scaling and high availability.

### Prerequisites

- Kubernetes cluster (GKE, EKS, AKS, or local minikube)
- kubectl configured
- Container registry (Docker Hub, GCR, ECR)

### Build and Push Images

```bash
# Set your registry
export REGISTRY=your-registry.com/cv-screener

# Build and push backend
docker build -t $REGISTRY/backend:latest ./backend
docker push $REGISTRY/backend:latest

# Build and push frontend
docker build -t $REGISTRY/frontend:latest ./frontend
docker push $REGISTRY/frontend:latest
```

### Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets (edit secrets.yaml first!)
kubectl apply -f k8s/secrets.yaml

# Create ConfigMap
kubectl apply -f k8s/configmap.yaml

# Create Persistent Volumes
kubectl apply -f k8s/persistent-volumes.yaml

# Deploy backend
kubectl apply -f k8s/backend-deployment.yaml

# Deploy frontend
kubectl apply -f k8s/frontend-deployment.yaml

# Create Ingress (edit domain first!)
kubectl apply -f k8s/ingress.yaml

# Optional: Enable autoscaling
kubectl apply -f k8s/hpa.yaml
```

### Kubernetes Files

```
k8s/
├── namespace.yaml           # cv-screener namespace
├── secrets.yaml             # API keys and credentials
├── configmap.yaml           # Non-sensitive configuration
├── persistent-volumes.yaml  # Storage for CVs and ChromaDB
├── backend-deployment.yaml  # Backend Deployment + Service
├── frontend-deployment.yaml # Frontend Deployment + Service
├── ingress.yaml             # Ingress with TLS
└── hpa.yaml                 # Horizontal Pod Autoscaler
```

### Verify Deployment

```bash
# Check pods
kubectl get pods -n cv-screener

# Check services
kubectl get svc -n cv-screener

# View logs
kubectl logs -f deployment/cv-screener-backend -n cv-screener

# Port forward for testing
kubectl port-forward svc/cv-screener-frontend 8080:80 -n cv-screener
```

---

## Environment Variables

### Backend Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_MODE` | `local` | `local` or `cloud` |
| `API_HOST` | `0.0.0.0` | API bind address |
| `API_PORT` | `8000` | API port |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MAX_FILE_SIZE_MB` | `10` | Max upload size |
| `MAX_FILES_PER_UPLOAD` | `50` | Max files per upload |

### API Keys (Optional Server-Side)

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | Default OpenRouter key (users can override) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `HUGGINGFACE_API_KEY` | HuggingFace API for advanced features |
| `GOOGLE_API_KEY` | Google AI Studio key |

---

## User API Key Configuration

### How It Works

1. **Users open Settings** in the frontend (gear icon)
2. **Enter their OpenRouter API key** in the designated field
3. **Key is stored in browser localStorage** (secure, client-side only)
4. **Every API request includes the key** via `X-OpenRouter-Key` header
5. **Backend uses client key** if provided, falls back to server key

### Security Considerations

- ✅ API keys never leave the user's browser (stored in localStorage)
- ✅ Keys are sent via HTTPS headers, not in URL
- ✅ Server can operate without any API keys configured
- ✅ Each user controls their own usage and billing

### Getting an OpenRouter API Key

1. Go to [OpenRouter](https://openrouter.ai/keys)
2. Create a free account
3. Generate an API key
4. Paste it in CV Screener Settings

---

## Troubleshooting

### Common Issues

**Container won't start**
```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend
```

**API requests failing**
- Verify CORS_ORIGINS includes your frontend URL
- Check API key is valid at https://openrouter.ai/keys
- Ensure backend is healthy: `curl http://localhost:8000/api/health`

**Railway deployment stuck**
- Check build logs in Railway dashboard
- Verify Dockerfile.railway exists at root
- Ensure PORT environment variable is used

**Kubernetes pods not ready**
```bash
kubectl describe pod <pod-name> -n cv-screener
kubectl logs <pod-name> -n cv-screener
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/api/health

# Frontend health (nginx)
curl http://localhost/health

# API key status
curl http://localhost:8000/api/api-key-status
```

---

## Production Deployment Checklist

### Pre-Deployment
- [ ] Supabase project created with pgvector extension enabled
- [ ] Run `scripts/setup_supabase_complete.sql` to create tables and RPC functions
- [ ] Create storage bucket `cv-pdfs` with public read access
- [ ] Verify Supabase service role key has correct permissions

### Railway Setup
- [ ] Connect GitHub repository to Railway
- [ ] Set all required environment variables
- [ ] Verify health check passes: `https://your-app.railway.app/api/health`
- [ ] Test CV upload and chat functionality

### Post-Deployment
- [ ] Monitor Railway logs for errors
- [ ] Check Supabase dashboard for database activity
- [ ] Verify embeddings are being stored correctly (768 dimensions)

---

## Next Steps (Roadmap)

| Version | Feature | Status | Cost Impact |
|---------|---------|--------|-------------|
| **V10** | Supabase Auth + RLS | 📋 Planned | $0/month |
| **V11** | PostgreSQL FTS + LangGraph | 📋 Planned | $0/month |
| **V12** | Multi-provider deploy (Vercel + Render) | 📋 Planned | $0/month |

See [Roadmap Documentation](./docs/roadmap/README.md) for full details.

---

## Support

For issues and feature requests, please open a GitHub issue.

---

<div align="center">

**[← Back to README](./README.md)** · **[Live Demo →](https://ai-poweredcvscreener-production.up.railway.app/)**

</div>
