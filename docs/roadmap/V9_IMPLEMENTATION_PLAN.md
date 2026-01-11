# RAG v9 Implementation Plan

> **Status**: 📋 PLANNED
> 
> **Date**: January 2026
> 
> **Prerequisites**: RAG v8 (Streaming, Export, Hybrid Search, Semantic Cache, Premium Features) ✅ Completed
>
> **💰 Cost Philosophy**: $0 en servicios fijos. Solo pagar por uso (OpenRouter).

---

## 🗺️ Roadmap Vision: V9 Position

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ROADMAP OVERVIEW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  V8 ✅              V9 (Current)        V10               V11        V12    │
│  ─────────────      ─────────           ───               ───        ───    │
│  UX Features        Cloud Parity +      Multi-Tenant      Advanced   Simple │
│  (Completed)        TypeScript +        (Auth)            Features   Deploy │
│                     GitHub Actions                                          │
│                                                                              │
│  • Streaming ✅     • TypeScript        • User login      • PG FTS   • Vercel│
│  • Export ✅        • GitHub Actions    • User signup     • LangGraph• Railway│
│  • Fallback ✅      • Cloud Parity      • RLS policies    • Analytics• Simple│
│  • Hybrid ✅        • Full migration    • Usage quotas                       │
│  • Premium ✅       • Mode parity                                            │
│                                                                              │
│  🧪 LOCAL MODE      📘 TYPESCRIPT       🔐 AUTH           🚀 ADVANCED 🌐 PROD│
│  Completed          + ☁️ CLOUD          Multi-user        LangGraph  Simple  │
│                     + 🔄 CI/CD (FREE)   (Supabase FREE)   PG FTS     Deploy  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Executive Summary

RAG v9 focuses on **three pillars**:

### 🎯 Key Objectives

1. **TypeScript Migration** - Type-safe frontend para mejor mantenibilidad
2. **GitHub Actions CI/CD** - Automatización de tests y quality gates
3. **Cloud Parity** - Supabase funciona IGUAL que local

### 📊 Impact

| Pillar | Benefit | ROI |
|--------|---------|-----|
| TypeScript | -60% runtime errors, mejor DX | Alto |
| GitHub Actions | Automated quality gates | Muy Alto |
| Cloud Parity | Production-ready backend | Crítico |

---

## Timeline Overview

| Phase | Focus | Duration | Features |
|-------|-------|----------|----------|
| **Phase 1** | TypeScript Migration | 5 días | Frontend type-safety |
| **Phase 2** | GitHub Actions CI/CD | 3 días | Tests, linting, deploy |
| **Phase 3** | Cloud Parity | 7 días | Supabase = Local |
| **Total** | | **15 días** | **3 pillars** |

---

## 📘 Phase 1: TypeScript Migration (5 días)

**Objetivo**: Migrar frontend de JavaScript a TypeScript para type-safety y mejor DX.

### 1.1 Setup TypeScript Infrastructure
**Time**: 0.5 días | **Priority**: 🔴 CRÍTICA

**Files to Create/Modify**:
```
frontend/
├── tsconfig.json                    # TypeScript configuration
├── tsconfig.node.json               # Node-specific config
├── vite.config.ts                   # Vite config (rename from .js)
└── src/
    └── vite-env.d.ts                # Vite type definitions
```

**tsconfig.json**:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@/components/*": ["src/components/*"],
      "@/hooks/*": ["src/hooks/*"],
      "@/types/*": ["src/types/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

**Dependencies**:
```bash
npm install -D typescript @types/react @types/react-dom @types/node
```

---

### 1.2 Core Types Definition
**Time**: 1 día | **Priority**: 🔴 CRÍTICA

**Files to Create**:
```
frontend/src/types/
├── index.ts                         # Re-exports
├── api.types.ts                     # API request/response types
├── session.types.ts                 # Session, CV, Message types
├── rag.types.ts                     # RAG response, structured output
├── screening.types.ts               # Screening rules, scores
└── components.types.ts              # Shared component prop types
```

**api.types.ts** (ejemplo):
```typescript
// API Response Types
export interface ApiResponse<T> {
  data: T;
  error?: string;
  status: number;
}

export interface RAGQueryRequest {
  session_id: string;
  question: string;
  cv_ids?: string[];
  k?: number;
  threshold?: number;
  models?: ModelSelection;
}

export interface RAGQueryResponse {
  answer: string;
  sources: Source[];
  structured_output?: StructuredOutput;
  confidence: number;
  metrics: PipelineMetrics;
}

export interface Source {
  cv_id: string;
  filename: string;
  chunk_preview?: string;
}

export interface ModelSelection {
  understanding_model?: string;
  generation_model?: string;
  reranking_model?: string;
  verification_model?: string;
}
```

**session.types.ts** (ejemplo):
```typescript
export interface Session {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  cv_count: number;
}

export interface CV {
  id: string;
  filename: string;
  candidate_name: string;
  upload_date: string;
  metadata: CVMetadata;
}

export interface CVMetadata {
  total_experience_years?: number;
  current_role?: string;
  current_company?: string;
  skills?: string[];
  education?: string[];
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: Source[];
  structured_output?: StructuredOutput;
}
```

**rag.types.ts** (ejemplo):
```typescript
// Structured Output Types (matching backend 9 structures)
export type QueryType = 
  | 'single_candidate'
  | 'comparison'
  | 'ranking'
  | 'talent_pool'
  | 'skills_search'
  | 'experience_filter'
  | 'gap_analysis'
  | 'red_flags'
  | 'general';

export interface StructuredOutput {
  query_type: QueryType;
  structure_name: string;
  modules: ModuleOutput[];
  metadata: OutputMetadata;
}

export interface ModuleOutput {
  module_name: string;
  data: Record<string, unknown>;
  confidence: number;
}

export interface PipelineMetrics {
  total_duration_ms: number;
  stages: StageMetric[];
  tokens_used: TokenUsage;
  cache_hit: boolean;
}

export interface StageMetric {
  stage: string;
  duration_ms: number;
  success: boolean;
}

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost: number;
}
```

---

### 1.3 Component Migration (Priority Files)
**Time**: 2.5 días | **Priority**: 🔴 ALTA

**Migration Order** (por impacto):

| Priority | Component | Lines | Complexity |
|----------|-----------|-------|------------|
| 1 | `ChatMessage.jsx` → `.tsx` | ~200 | Media |
| 2 | `SessionPanel.jsx` → `.tsx` | ~150 | Media |
| 3 | `CVUploader.jsx` → `.tsx` | ~180 | Alta |
| 4 | `output/*.jsx` → `.tsx` | ~500 | Alta |
| 5 | `hooks/*.js` → `.ts` | ~300 | Media |

**Example Migration** (`ChatMessage.tsx`):
```typescript
import React from 'react';
import { Message, StructuredOutput } from '@/types';

interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean;
  onSourceClick?: (cvId: string) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  isStreaming = false,
  onSourceClick
}) => {
  // Component implementation with full type safety
  return (
    <div className={`message ${message.role}`}>
      {/* ... */}
    </div>
  );
};
```

**Files to Migrate** (complete list):
```
frontend/src/
├── components/
│   ├── ChatMessage.jsx → ChatMessage.tsx
│   ├── SessionPanel.jsx → SessionPanel.tsx
│   ├── CVUploader.jsx → CVUploader.tsx
│   ├── ModelSelector.jsx → ModelSelector.tsx
│   ├── SuggestionChips.jsx → SuggestionChips.tsx
│   └── output/
│       ├── SingleCandidateView.jsx → .tsx
│       ├── ComparisonView.jsx → .tsx
│       ├── RankingView.jsx → .tsx
│       └── ... (all output components)
├── hooks/
│   ├── useStreamingQuery.js → useStreamingQuery.ts
│   ├── useSession.js → useSession.ts
│   └── useRAGQuery.js → useRAGQuery.ts
└── utils/
    ├── api.js → api.ts
    └── parsers/
        ├── singleCandidateParser.js → .ts
        └── ... (all parsers)
```

---

### 1.4 Hooks Migration
**Time**: 1 día | **Priority**: 🔴 ALTA

**useStreamingQuery.ts** (ejemplo):
```typescript
import { useState, useCallback, useRef } from 'react';
import { RAGQueryRequest, RAGQueryResponse, PipelineStep } from '@/types';

interface UseStreamingQueryOptions {
  onToken?: (token: string) => void;
  onStep?: (step: PipelineStep) => void;
  onComplete?: (response: RAGQueryResponse) => void;
  onError?: (error: Error) => void;
}

interface UseStreamingQueryReturn {
  query: (request: RAGQueryRequest) => Promise<void>;
  isLoading: boolean;
  response: RAGQueryResponse | null;
  currentStep: string | null;
  streamedText: string;
  error: Error | null;
  abort: () => void;
}

export function useStreamingQuery(
  options: UseStreamingQueryOptions = {}
): UseStreamingQueryReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<RAGQueryResponse | null>(null);
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [streamedText, setStreamedText] = useState('');
  const [error, setError] = useState<Error | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const query = useCallback(async (request: RAGQueryRequest) => {
    // Implementation with full type safety
  }, [options]);

  const abort = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  return {
    query,
    isLoading,
    response,
    currentStep,
    streamedText,
    error,
    abort
  };
}
```

---

## 🔄 Phase 2: GitHub Actions CI/CD (3 días)

**Objetivo**: Automatizar tests, linting, y quality gates en cada PR/push.

### 2.1 Basic CI Pipeline
**Time**: 1 día | **Priority**: 🔴 CRÍTICA

**Files to Create**:
```
.github/
├── workflows/
│   ├── ci.yml                       # Main CI pipeline
│   ├── backend-tests.yml            # Python tests
│   └── frontend-checks.yml          # TypeScript/React checks
└── dependabot.yml                   # Dependency updates
```

**ci.yml** (Main Pipeline):
```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '20'

jobs:
  # ============================================
  # Backend Tests (Python/FastAPI)
  # ============================================
  backend-tests:
    name: Backend Tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./backend

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run linting (ruff)
        run: |
          pip install ruff
          ruff check app/

      - name: Run type checking (mypy)
        run: |
          pip install mypy
          mypy app/ --ignore-missing-imports || true

      - name: Run tests
        env:
          HUGGINGFACE_API_KEY: ${{ secrets.HUGGINGFACE_API_KEY }}
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
        run: |
          pytest tests/ -v --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./backend/coverage.xml
          flags: backend

  # ============================================
  # Frontend Checks (TypeScript/React)
  # ============================================
  frontend-checks:
    name: Frontend Checks
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./frontend

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: TypeScript type check
        run: npm run type-check

      - name: ESLint
        run: npm run lint

      - name: Build check
        run: npm run build

  # ============================================
  # Integration Tests (Optional)
  # ============================================
  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-checks]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}

      - name: Run integration tests
        run: |
          echo "Integration tests placeholder"
          # Add Playwright or similar for E2E tests in future
```

---

### 2.2 Frontend-Specific Workflow
**Time**: 0.5 días | **Priority**: 🔴 ALTA

**frontend-checks.yml**:
```yaml
name: Frontend Quality

on:
  push:
    paths:
      - 'frontend/**'
  pull_request:
    paths:
      - 'frontend/**'

jobs:
  quality:
    name: TypeScript & Lint
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./frontend

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install
        run: npm ci

      - name: TypeScript Check
        run: npx tsc --noEmit

      - name: ESLint
        run: npm run lint -- --max-warnings 0

      - name: Prettier Check
        run: npx prettier --check "src/**/*.{ts,tsx,css}"

      - name: Build
        run: npm run build
```

---

### 2.3 Backend-Specific Workflow
**Time**: 0.5 días | **Priority**: 🔴 ALTA

**backend-tests.yml**:
```yaml
name: Backend Tests

on:
  push:
    paths:
      - 'backend/**'
  pull_request:
    paths:
      - 'backend/**'

jobs:
  test:
    name: Python Tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./backend

    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov ruff mypy

      - name: Ruff lint
        run: ruff check app/ --output-format=github

      - name: Ruff format check
        run: ruff format app/ --check

      - name: Type check
        run: mypy app/ --ignore-missing-imports || true

      - name: Run tests
        run: pytest tests/ -v --tb=short

  security:
    name: Security Scan
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./backend

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install bandit
        run: pip install bandit

      - name: Run security scan
        run: bandit -r app/ -ll -ii
```

---

### 2.4 Dependabot Configuration
**Time**: 0.5 días | **Priority**: 🟡 MEDIA

**dependabot.yml**:
```yaml
version: 2
updates:
  # Python dependencies
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 5
    labels:
      - "dependencies"
      - "python"
    commit-message:
      prefix: "deps(py):"

  # Node.js dependencies
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 5
    labels:
      - "dependencies"
      - "javascript"
    commit-message:
      prefix: "deps(npm):"

  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "monthly"
    labels:
      - "dependencies"
      - "ci"
```

---

### 2.5 Pre-commit Hooks (Local)
**Time**: 0.5 días | **Priority**: 🟡 MEDIA

**Files to Create**:
```
.pre-commit-config.yaml
```

**.pre-commit-config.yaml**:
```yaml
repos:
  # Python
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  # General
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=1000']

  # TypeScript/JavaScript
  - repo: local
    hooks:
      - id: eslint
        name: ESLint
        entry: npm run lint --prefix frontend
        language: system
        files: \.(ts|tsx|js|jsx)$
        pass_filenames: false
```

---

## ☁️ Phase 3: Cloud Parity (7 días)

**Objetivo**: Que el modo CLOUD (Supabase) funcione **exactamente igual** que LOCAL.

### 3.1 Supabase Schema Complete
**Time**: 1 día | **Priority**: 🔴 CRÍTICA

Ver schema completo en V8_IMPLEMENTATION_PLAN.md sección "V9 Supabase Schema".

**Key Tables**:
- `sessions` - Session management
- `cvs` - CV metadata + PDF reference
- `cv_embeddings` - Vector embeddings (768 dims)
- `session_messages` - Chat history
- `screening_rules` - Auto-screening rules
- `query_cache` - Semantic cache

---

### 3.2 PDF Storage Migration
**Time**: 1.5 días | **Priority**: 🔴 ALTA

**Files to Modify**:
```
backend/app/providers/cloud/
├── pdf_storage.py                   # Supabase Storage integration
└── __init__.py
```

---

### 3.3 Session Persistence
**Time**: 1.5 días | **Priority**: 🔴 ALTA

**Files to Modify**:
```
backend/app/providers/cloud/
├── sessions.py                      # Supabase sessions table
└── messages.py                      # Supabase messages table
```

---

### 3.4 Hybrid Search (PostgreSQL FTS)
**Time**: 1.5 días | **Priority**: 🔴 ALTA

Migrar BM25 local a PostgreSQL Full-Text Search.

**SQL**:
```sql
-- Full-Text Search column
ALTER TABLE cvs ADD COLUMN fts_content tsvector 
  GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

-- GIN index for fast search
CREATE INDEX cvs_fts_idx ON cvs USING GIN(fts_content);

-- Search function
CREATE OR REPLACE FUNCTION hybrid_search(
  query_text TEXT,
  query_embedding vector(768),
  match_count INT DEFAULT 10,
  session_filter UUID DEFAULT NULL
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  similarity FLOAT,
  bm25_score FLOAT,
  combined_score FLOAT
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    ce.id,
    ce.chunk_text as content,
    1 - (ce.embedding <=> query_embedding) as similarity,
    ts_rank(c.fts_content, plainto_tsquery('english', query_text)) as bm25_score,
    (0.5 * (1 - (ce.embedding <=> query_embedding))) + 
    (0.5 * ts_rank(c.fts_content, plainto_tsquery('english', query_text))) as combined_score
  FROM cv_embeddings ce
  JOIN cvs c ON ce.cv_id = c.id
  WHERE (session_filter IS NULL OR c.session_id = session_filter)
  ORDER BY combined_score DESC
  LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
```

---

### 3.5 Semantic Cache (Supabase)
**Time**: 1.5 días | **Priority**: 🟡 MEDIA

**Files to Create**:
```
backend/app/providers/cloud/
└── cache_provider.py                # Supabase cache implementation
```

---

## 📊 Priority Matrix (V9)

| Feature | Phase | Priority | Effort | Impact |
|---------|-------|----------|--------|--------|
| TypeScript Setup | 1 | 🔴 CRITICAL | 0.5d | High |
| Core Types | 1 | 🔴 CRITICAL | 1d | Very High |
| Component Migration | 1 | 🔴 HIGH | 2.5d | High |
| Hooks Migration | 1 | 🔴 HIGH | 1d | High |
| CI Pipeline (main) | 2 | 🔴 CRITICAL | 1d | Very High |
| Frontend Checks | 2 | 🔴 HIGH | 0.5d | High |
| Backend Tests | 2 | 🔴 HIGH | 0.5d | High |
| Dependabot | 2 | 🟡 MEDIUM | 0.5d | Medium |
| Pre-commit | 2 | 🟡 MEDIUM | 0.5d | Medium |
| Supabase Schema | 3 | 🔴 CRITICAL | 1d | Critical |
| PDF Storage | 3 | 🔴 HIGH | 1.5d | High |
| Sessions | 3 | 🔴 HIGH | 1.5d | High |
| Hybrid Search (PG) | 3 | 🔴 HIGH | 1.5d | High |
| Semantic Cache | 3 | 🟡 MEDIUM | 1.5d | Medium |
| **TOTAL V9** | | | **~15 días** | |

---

## 📅 Recommended Schedule (15 días)

### Week 1: TypeScript Foundation
| Day | Task | Output |
|-----|------|--------|
| 1 | TypeScript setup + core types | tsconfig, base types |
| 2-3 | Component migration (priority) | ChatMessage, SessionPanel |
| 4 | Output components migration | All output/*.tsx |
| 5 | Hooks migration | All hooks in TypeScript |

### Week 2: CI/CD + Cloud Start
| Day | Task | Output |
|-----|------|--------|
| 6 | Main CI pipeline | ci.yml working |
| 7 | Frontend + Backend workflows | Separate workflows |
| 8 | Dependabot + Pre-commit | Automation setup |
| 9 | Supabase schema | All tables created |
| 10 | PDF Storage migration | Upload to Supabase Storage |

### Week 3: Cloud Parity Complete
| Day | Task | Output |
|-----|------|--------|
| 11-12 | Session + Messages persistence | Full chat history |
| 13-14 | Hybrid Search (PostgreSQL FTS) | Combined search working |
| 15 | Semantic Cache + Testing | Cloud parity achieved |

---

## 💰 Cost Estimate

| Feature | Monthly Cost | Notes |
|---------|-------------|-------|
| TypeScript | $0 | Dev tooling only |
| GitHub Actions | $0 | Free tier (2000 min/month) |
| Supabase (Free) | $0 | 500MB DB, 1GB storage |
| Supabase (Pro) | $25 | If needed for scale |
| **Total V9** | **$0-25/month** | |

---

## 📈 Success Metrics

| Metric | Current (V8) | Target (V9) | Improvement |
|--------|--------------|-------------|-------------|
| Type Coverage | 0% | 90%+ | Type safety |
| CI Pass Rate | N/A | 95%+ | Quality gates |
| Cloud Parity | 60% | 100% | Full feature parity |
| Deploy Time | Manual | <5 min | Automated |

---

## 🔧 Dependencies (V9)

### Frontend (package.json additions)
```json
{
  "devDependencies": {
    "typescript": "^5.3.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@types/node": "^20.0.0",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "@typescript-eslint/parser": "^6.0.0"
  },
  "scripts": {
    "type-check": "tsc --noEmit",
    "lint": "eslint src/ --ext .ts,.tsx"
  }
}
```

### Backend (requirements.txt additions)
```
# Development/CI
ruff>=0.1.9
mypy>=1.8.0
pytest>=7.4.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
bandit>=1.7.0
```

---

## 🚀 Quick Start

```bash
# 1. Create feature branch
git checkout -b feature/v9-typescript-cicd

# 2. Start with TypeScript setup
cd frontend
npm install -D typescript @types/react @types/react-dom
npx tsc --init

# 3. Create GitHub Actions
mkdir -p .github/workflows
# Create ci.yml

# 4. Test CI locally
act push  # Using nektos/act for local testing

# 5. Migrate components incrementally
# Start with ChatMessage.jsx → ChatMessage.tsx
```

---

## 📝 V9 Completion Checklist

### Phase 1: TypeScript
- [ ] TypeScript configuration (tsconfig.json)
- [ ] Core types (api, session, rag, screening)
- [ ] ChatMessage.tsx migration
- [ ] SessionPanel.tsx migration
- [ ] CVUploader.tsx migration
- [ ] Output components migration
- [ ] Hooks migration (useStreamingQuery, useSession)
- [ ] Parsers migration

### Phase 2: GitHub Actions
- [ ] Main CI pipeline (ci.yml)
- [ ] Frontend checks workflow
- [ ] Backend tests workflow
- [ ] Dependabot configuration
- [ ] Pre-commit hooks

### Phase 3: Cloud Parity
- [ ] Supabase schema complete
- [ ] PDF Storage (Supabase bucket)
- [ ] Sessions persistence
- [ ] Chat history persistence
- [ ] Hybrid Search (PostgreSQL FTS)
- [ ] Semantic Cache (Supabase table)

### Validation
- [ ] All TypeScript files compile without errors
- [ ] All CI checks pass
- [ ] Cloud mode works identical to Local mode
- [ ] No regressions in functionality
