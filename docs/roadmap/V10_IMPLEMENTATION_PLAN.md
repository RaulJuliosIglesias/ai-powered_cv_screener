# RAG v10 Implementation Plan

> **Status**: 📋 PLANNED
> 
> **Date**: January 2026
> 
> **Prerequisites**: RAG v9 (TypeScript, GitHub Actions, Cloud Parity) ✅
>
> **💰 Cost Philosophy**: $0 en servicios fijos. Supabase Auth FREE. Deploy en free tiers.

---

## 🗺️ Roadmap Vision: V10 Position

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ROADMAP OVERVIEW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  V8 ✅       V9 ✅              V10 (Current)     V11           V12         │
│  ─────────  ─────────          ─────────         ───           ───         │
│  UX         TypeScript +       Multi-Tenant      Advanced      Simple      │
│  Features   GitHub Actions     + Auth            Features      Deploy      │
│             + Cloud Parity     (FREE tiers)                                 │
│                                                                              │
│  ✅ Done    ✅ Done            • User login      • PG FTS      • Vercel    │
│                                • User signup     • LangGraph     (FREE)    │
│                                • RLS policies    • Analytics   • Render    │
│                                • Usage quotas                    (FREE)    │
│                                                                              │
│  🧪 LOCAL   📘 TYPESCRIPT      🔐 AUTH           🚀 ADVANCED   🌐 PROD     │
│  Completed  + ☁️ CLOUD         Supabase FREE     PG FTS        Free tiers  │
│             + 🔄 CI/CD (FREE)  RLS included      LangGraph     until scale │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Executive Summary

RAG v10 focuses on **Authentication & Multi-Tenant** with **Professional CI/CD**:

### 🎯 Key Objectives

1. **User Authentication** - Login, Signup, OAuth via Supabase Auth
2. **Multi-Tenant Data Isolation** - Row Level Security (RLS)
3. **Professional CI/CD** - Staging environment, automatic deploys

### 📊 Impact

| Pillar | Benefit | ROI |
|--------|---------|-----|
| Auth | Multi-user support, security | Crítico |
| RLS | Data isolation, compliance | Muy Alto |
| CI/CD Pro | Faster, safer deploys | Alto |

---

## Timeline Overview

| Phase | Focus | Duration | Features |
|-------|-------|----------|----------|
| **Phase 1** | Supabase Auth Integration | 4 días | Login, Signup, OAuth |
| **Phase 2** | Row Level Security | 3 días | Data isolation |
| **Phase 3** | User Features | 3 días | Workspaces, quotas |
| **Phase 4** | CI/CD Professional | 3 días | Staging, auto-deploy |
| **Total** | | **13 días** | **4 phases** |

---

## 🔐 Phase 1: Supabase Auth Integration (4 días)

**Objetivo**: Implementar autenticación completa con Supabase Auth.

### 1.1 Auth Configuration
**Time**: 0.5 días | **Priority**: 🔴 CRÍTICA

**Supabase Dashboard Setup**:
1. Enable Email/Password authentication
2. Configure OAuth providers (Google, GitHub)
3. Set redirect URLs
4. Configure email templates

**Environment Variables**:
```bash
# .env (backend)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...  # Only for backend

# .env (frontend)
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
```

---

### 1.2 Backend Auth Middleware
**Time**: 1 día | **Priority**: 🔴 CRÍTICA

**Files to Create**:
```
backend/app/
├── middleware/
│   ├── __init__.py
│   └── auth.py                      # JWT validation middleware
├── dependencies/
│   └── auth.py                      # FastAPI dependencies
└── models/
    └── user.py                      # User model
```

**auth.py** (middleware):
```python
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client
from typing import Optional
import jwt

from app.config import settings

security = HTTPBearer(auto_error=False)

class AuthenticatedUser:
    """Authenticated user from Supabase JWT."""
    def __init__(self, user_id: str, email: str, metadata: dict = None):
        self.id = user_id
        self.email = email
        self.metadata = metadata or {}
    
    @property
    def tier(self) -> str:
        return self.metadata.get('tier', 'free')


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[AuthenticatedUser]:
    """
    Validate Supabase JWT and return authenticated user.
    Returns None if no token provided (for public endpoints).
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    
    try:
        # Verify JWT with Supabase
        supabase = create_client(settings.supabase_url, settings.supabase_service_key)
        user = supabase.auth.get_user(token)
        
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return AuthenticatedUser(
            user_id=user.user.id,
            email=user.user.email,
            metadata=user.user.user_metadata
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


async def require_auth(
    user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """Require authentication for endpoint."""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_pro_tier(
    user: AuthenticatedUser = Depends(require_auth)
) -> AuthenticatedUser:
    """Require Pro tier for endpoint."""
    if user.tier not in ['pro', 'enterprise']:
        raise HTTPException(status_code=403, detail="Pro tier required")
    return user
```

---

### 1.3 Frontend Auth Components
**Time**: 1.5 días | **Priority**: 🔴 CRÍTICA

**Files to Create**:
```
frontend/src/
├── lib/
│   └── supabase.ts                  # Supabase client
├── contexts/
│   └── AuthContext.tsx              # Auth context provider
├── hooks/
│   └── useAuth.ts                   # Auth hook
├── components/auth/
│   ├── LoginForm.tsx                # Email/password login
│   ├── SignupForm.tsx               # Registration form
│   ├── OAuthButtons.tsx             # Google/GitHub buttons
│   ├── ForgotPassword.tsx           # Password reset
│   └── ProtectedRoute.tsx           # Route guard
└── pages/
    ├── Login.tsx                    # Login page
    ├── Signup.tsx                   # Signup page
    └── ResetPassword.tsx            # Password reset page
```

**supabase.ts**:
```typescript
import { createClient } from '@supabase/supabase-js';
import type { Database } from '@/types/database.types';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey);
```

**AuthContext.tsx**:
```typescript
import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, Session } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabase';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  signInWithOAuth: (provider: 'google' | 'github') => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session);
        setUser(session?.user ?? null);
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
  };

  const signUp = async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) throw error;
  };

  const signOut = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
  };

  const signInWithOAuth = async (provider: 'google' | 'github') => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/auth/callback`
      }
    });
    if (error) throw error;
  };

  return (
    <AuthContext.Provider value={{
      user,
      session,
      loading,
      signIn,
      signUp,
      signOut,
      signInWithOAuth
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
```

**ProtectedRoute.tsx**:
```typescript
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredTier?: 'free' | 'pro' | 'enterprise';
}

export function ProtectedRoute({ children, requiredTier }: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check tier if required
  if (requiredTier) {
    const userTier = user.user_metadata?.tier || 'free';
    const tierHierarchy = ['free', 'pro', 'enterprise'];
    if (tierHierarchy.indexOf(userTier) < tierHierarchy.indexOf(requiredTier)) {
      return <Navigate to="/upgrade" replace />;
    }
  }

  return <>{children}</>;
}
```

---

### 1.4 Protected API Endpoints
**Time**: 1 día | **Priority**: 🔴 ALTA

**Modify existing routes** to require authentication:

```python
# backend/app/api/routes_sessions.py

from app.dependencies.auth import require_auth, AuthenticatedUser

@router.post("/")
async def create_session(
    name: str,
    user: AuthenticatedUser = Depends(require_auth)
):
    """Create a new session (requires auth)."""
    session = await session_service.create_session(
        name=name,
        user_id=user.id  # Associate with authenticated user
    )
    return session


@router.get("/")
async def list_sessions(
    user: AuthenticatedUser = Depends(require_auth)
):
    """List user's sessions (filtered by user_id)."""
    sessions = await session_service.list_sessions(user_id=user.id)
    return sessions
```

---

## 🛡️ Phase 2: Row Level Security (3 días)

**Objetivo**: Aislamiento completo de datos por usuario.

### 2.1 Schema Updates
**Time**: 0.5 días | **Priority**: 🔴 CRÍTICA

**SQL Migrations**:
```sql
-- Add user_id to all user-owned tables
ALTER TABLE sessions ADD COLUMN user_id UUID REFERENCES auth.users(id);
ALTER TABLE cvs ADD COLUMN user_id UUID REFERENCES auth.users(id);
ALTER TABLE screening_rules ADD COLUMN user_id UUID REFERENCES auth.users(id);
ALTER TABLE query_cache ADD COLUMN user_id UUID REFERENCES auth.users(id);

-- Create indexes
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_cvs_user_id ON cvs(user_id);
```

---

### 2.2 RLS Policies
**Time**: 1.5 días | **Priority**: 🔴 CRÍTICA

**SQL Policies**:
```sql
-- ===========================================
-- SESSIONS TABLE
-- ===========================================
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

-- Users can only see their own sessions
CREATE POLICY "Users can view own sessions"
ON sessions FOR SELECT
USING (auth.uid() = user_id);

-- Users can only insert their own sessions
CREATE POLICY "Users can create own sessions"
ON sessions FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can only update their own sessions
CREATE POLICY "Users can update own sessions"
ON sessions FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Users can only delete their own sessions
CREATE POLICY "Users can delete own sessions"
ON sessions FOR DELETE
USING (auth.uid() = user_id);


-- ===========================================
-- CVS TABLE
-- ===========================================
ALTER TABLE cvs ENABLE ROW LEVEL SECURITY;

-- Users can only see CVs in their sessions
CREATE POLICY "Users can view own CVs"
ON cvs FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM sessions 
    WHERE sessions.id = cvs.session_id 
    AND sessions.user_id = auth.uid()
  )
);

-- Users can only insert CVs to their sessions
CREATE POLICY "Users can create CVs in own sessions"
ON cvs FOR INSERT
WITH CHECK (
  EXISTS (
    SELECT 1 FROM sessions 
    WHERE sessions.id = cvs.session_id 
    AND sessions.user_id = auth.uid()
  )
);

-- Similar policies for UPDATE and DELETE...


-- ===========================================
-- CV_EMBEDDINGS TABLE
-- ===========================================
ALTER TABLE cv_embeddings ENABLE ROW LEVEL SECURITY;

-- Users can only see embeddings for their CVs
CREATE POLICY "Users can view own embeddings"
ON cv_embeddings FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM cvs 
    JOIN sessions ON cvs.session_id = sessions.id
    WHERE cvs.id = cv_embeddings.cv_id 
    AND sessions.user_id = auth.uid()
  )
);


-- ===========================================
-- SESSION_MESSAGES TABLE
-- ===========================================
ALTER TABLE session_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own messages"
ON session_messages FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM sessions 
    WHERE sessions.id = session_messages.session_id 
    AND sessions.user_id = auth.uid()
  )
);


-- ===========================================
-- SCREENING_RULES TABLE
-- ===========================================
ALTER TABLE screening_rules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own screening rules"
ON screening_rules FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);


-- ===========================================
-- QUERY_CACHE TABLE
-- ===========================================
ALTER TABLE query_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access own cache"
ON query_cache FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);
```

---

### 2.3 Service Key for Backend
**Time**: 1 día | **Priority**: 🔴 ALTA

El backend necesita usar `service_key` para operaciones administrativas:

```python
# backend/app/providers/cloud/supabase_client.py

from supabase import create_client, Client
from app.config import settings

def get_supabase_client(use_service_key: bool = False) -> Client:
    """
    Get Supabase client.
    
    Args:
        use_service_key: If True, use service key (bypasses RLS).
                        Only use for admin operations!
    """
    key = settings.supabase_service_key if use_service_key else settings.supabase_anon_key
    return create_client(settings.supabase_url, key)


# For user operations (respects RLS)
def get_user_client(access_token: str) -> Client:
    """Get Supabase client authenticated as specific user."""
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.auth.set_session(access_token)
    return client
```

---

## 👤 Phase 3: User Features (3 días)

**Objetivo**: Funcionalidades de usuario (perfiles, cuotas, workspaces).

### 3.1 User Profiles Table
**Time**: 0.5 días | **Priority**: 🔴 ALTA

**SQL**:
```sql
-- User profiles with tier and quotas
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  full_name TEXT,
  avatar_url TEXT,
  tier TEXT DEFAULT 'free' CHECK (tier IN ('free', 'pro', 'enterprise')),
  queries_used INT DEFAULT 0,
  queries_limit INT DEFAULT 100,
  cvs_uploaded INT DEFAULT 0,
  cvs_limit INT DEFAULT 50,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.user_profiles (id, email, full_name, avatar_url)
  VALUES (
    NEW.id,
    NEW.email,
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'avatar_url'
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- RLS for profiles
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
ON user_profiles FOR SELECT
USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
ON user_profiles FOR UPDATE
USING (auth.uid() = id);
```

---

### 3.2 Usage Quotas
**Time**: 1 día | **Priority**: 🔴 ALTA

**Quota Configuration**:
```python
# backend/app/models/quotas.py

from dataclasses import dataclass
from enum import Enum

class Tier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class TierLimits:
    queries_per_month: int
    cvs_per_session: int
    sessions_total: int
    max_file_size_mb: int
    export_enabled: bool
    priority_support: bool


TIER_LIMITS = {
    Tier.FREE: TierLimits(
        queries_per_month=100,
        cvs_per_session=10,
        sessions_total=5,
        max_file_size_mb=5,
        export_enabled=False,
        priority_support=False
    ),
    Tier.PRO: TierLimits(
        queries_per_month=1000,
        cvs_per_session=50,
        sessions_total=50,
        max_file_size_mb=10,
        export_enabled=True,
        priority_support=False
    ),
    Tier.ENTERPRISE: TierLimits(
        queries_per_month=10000,
        cvs_per_session=200,
        sessions_total=500,
        max_file_size_mb=25,
        export_enabled=True,
        priority_support=True
    )
}
```

**Quota Enforcement Middleware**:
```python
# backend/app/middleware/quotas.py

from fastapi import HTTPException, Depends
from app.dependencies.auth import require_auth, AuthenticatedUser
from app.models.quotas import TIER_LIMITS, Tier

async def check_query_quota(user: AuthenticatedUser = Depends(require_auth)):
    """Check if user has remaining query quota."""
    limits = TIER_LIMITS[Tier(user.tier)]
    
    # Get current usage from database
    usage = await get_user_usage(user.id)
    
    if usage.queries_this_month >= limits.queries_per_month:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly query limit reached ({limits.queries_per_month}). Upgrade to Pro for more."
        )
    
    return user


async def check_cv_upload_quota(
    session_id: str,
    user: AuthenticatedUser = Depends(require_auth)
):
    """Check if user can upload more CVs to session."""
    limits = TIER_LIMITS[Tier(user.tier)]
    
    # Get current CV count in session
    cv_count = await get_session_cv_count(session_id)
    
    if cv_count >= limits.cvs_per_session:
        raise HTTPException(
            status_code=429,
            detail=f"Session CV limit reached ({limits.cvs_per_session}). Upgrade to Pro for more."
        )
    
    return user
```

---

### 3.3 User Settings UI
**Time**: 1.5 días | **Priority**: 🟡 MEDIA

**Files to Create**:
```
frontend/src/
├── pages/
│   ├── Settings.tsx                 # User settings page
│   └── Billing.tsx                  # Subscription management
├── components/settings/
│   ├── ProfileForm.tsx              # Edit profile
│   ├── UsageStats.tsx               # Query/CV usage
│   ├── TierBadge.tsx                # Show current tier
│   └── UpgradeCard.tsx              # Upgrade CTA
```

**UsageStats.tsx**:
```typescript
import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function UsageStats() {
  const { user } = useAuth();
  const { data: usage } = useQuery({
    queryKey: ['usage', user?.id],
    queryFn: () => api.get('/api/user/usage')
  });

  if (!usage) return null;

  const tier = user?.user_metadata?.tier || 'free';
  const limits = TIER_LIMITS[tier];

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Usage This Month</h3>
      
      {/* Queries */}
      <div>
        <div className="flex justify-between text-sm">
          <span>Queries</span>
          <span>{usage.queries_used} / {limits.queries_per_month}</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-blue-600 h-2 rounded-full"
            style={{ width: `${(usage.queries_used / limits.queries_per_month) * 100}%` }}
          />
        </div>
      </div>

      {/* CVs */}
      <div>
        <div className="flex justify-between text-sm">
          <span>CVs Uploaded</span>
          <span>{usage.cvs_uploaded} / {limits.cvs_total}</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-green-600 h-2 rounded-full"
            style={{ width: `${(usage.cvs_uploaded / limits.cvs_total) * 100}%` }}
          />
        </div>
      </div>

      {tier === 'free' && (
        <UpgradeCard />
      )}
    </div>
  );
}
```

---

## 🚀 Phase 4: CI/CD Professional (3 días)

**Objetivo**: Pipeline de CI/CD profesional con staging y auto-deploy.

### 4.1 Staging Environment
**Time**: 1 día | **Priority**: 🔴 ALTA

**Files to Create**:
```
.github/workflows/
├── deploy-staging.yml               # Deploy to staging
├── deploy-production.yml            # Deploy to production
└── e2e-tests.yml                    # E2E tests on staging
```

**deploy-staging.yml**:
```yaml
name: Deploy to Staging

on:
  push:
    branches: [develop]

env:
  VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
  VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}

jobs:
  deploy-backend-staging:
    name: Deploy Backend (Staging)
    runs-on: ubuntu-latest
    environment: staging
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install Railway CLI
        run: npm install -g @railway/cli
      
      - name: Deploy to Railway (Staging)
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN_STAGING }}
        run: |
          cd backend
          railway up --environment staging

  deploy-frontend-staging:
    name: Deploy Frontend (Staging)
    runs-on: ubuntu-latest
    environment: staging
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install Vercel CLI
        run: npm install -g vercel
      
      - name: Deploy to Vercel (Staging)
        run: |
          cd frontend
          vercel pull --yes --environment=preview --token=${{ secrets.VERCEL_TOKEN }}
          vercel build --token=${{ secrets.VERCEL_TOKEN }}
          vercel deploy --prebuilt --token=${{ secrets.VERCEL_TOKEN }}

  e2e-tests:
    name: E2E Tests
    runs-on: ubuntu-latest
    needs: [deploy-backend-staging, deploy-frontend-staging]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install Playwright
        run: |
          cd frontend
          npm ci
          npx playwright install --with-deps
      
      - name: Run E2E Tests
        env:
          STAGING_URL: ${{ vars.STAGING_URL }}
        run: |
          cd frontend
          npx playwright test --project=chromium
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

---

### 4.2 Production Deploy
**Time**: 1 día | **Priority**: 🔴 ALTA

**deploy-production.yml**:
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      skip_tests:
        description: 'Skip E2E tests'
        required: false
        default: 'false'

jobs:
  # First run all tests
  test:
    name: Run Tests
    uses: ./.github/workflows/ci.yml
    secrets: inherit

  # Deploy backend to production
  deploy-backend:
    name: Deploy Backend (Production)
    runs-on: ubuntu-latest
    needs: test
    environment: production
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Railway (Production)
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN_PRODUCTION }}
        run: |
          npm install -g @railway/cli
          cd backend
          railway up --environment production
      
      - name: Health check
        run: |
          sleep 30
          curl -f ${{ vars.PRODUCTION_API_URL }}/health || exit 1

  # Deploy frontend to production
  deploy-frontend:
    name: Deploy Frontend (Production)
    runs-on: ubuntu-latest
    needs: test
    environment: production
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Vercel (Production)
        run: |
          npm install -g vercel
          cd frontend
          vercel pull --yes --environment=production --token=${{ secrets.VERCEL_TOKEN }}
          vercel build --prod --token=${{ secrets.VERCEL_TOKEN }}
          vercel deploy --prebuilt --prod --token=${{ secrets.VERCEL_TOKEN }}

  # Notify on completion
  notify:
    name: Notify
    runs-on: ubuntu-latest
    needs: [deploy-backend, deploy-frontend]
    if: always()
    
    steps:
      - name: Send Slack notification
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Deployment ${{ job.status }}: ${{ github.repository }}",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Deployment ${{ job.status }}*\nRepo: ${{ github.repository }}\nBranch: ${{ github.ref_name }}\nCommit: ${{ github.sha }}"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

### 4.3 E2E Tests with Playwright
**Time**: 1 día | **Priority**: 🟡 MEDIA

**Files to Create**:
```
frontend/
├── playwright.config.ts             # Playwright configuration
├── e2e/
│   ├── auth.spec.ts                 # Auth flow tests
│   ├── session.spec.ts              # Session management tests
│   ├── query.spec.ts                # RAG query tests
│   └── fixtures/
│       └── test-cv.pdf              # Test PDF file
```

**playwright.config.ts**:
```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  
  use: {
    baseURL: process.env.STAGING_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: process.env.CI ? undefined : {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
});
```

**auth.spec.ts**:
```typescript
import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('should show login page for unauthenticated users', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/.*login/);
  });

  test('should login with valid credentials', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'testpassword123');
    await page.click('button[type="submit"]');
    
    await expect(page).toHaveURL('/dashboard');
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('input[name="email"]', 'invalid@example.com');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    
    await expect(page.locator('.error-message')).toBeVisible();
  });
});
```

---

## 📊 Priority Matrix (V10)

| Feature | Phase | Priority | Effort | Impact |
|---------|-------|----------|--------|--------|
| Auth Config | 1 | 🔴 CRITICAL | 0.5d | Critical |
| Backend Middleware | 1 | 🔴 CRITICAL | 1d | Critical |
| Frontend Auth | 1 | 🔴 CRITICAL | 1.5d | Critical |
| Protected Routes | 1 | 🔴 HIGH | 1d | High |
| Schema Updates | 2 | 🔴 CRITICAL | 0.5d | Critical |
| RLS Policies | 2 | 🔴 CRITICAL | 1.5d | Critical |
| Service Key | 2 | 🔴 HIGH | 1d | High |
| User Profiles | 3 | 🔴 HIGH | 0.5d | High |
| Usage Quotas | 3 | 🔴 HIGH | 1d | High |
| Settings UI | 3 | 🟡 MEDIUM | 1.5d | Medium |
| Staging Deploy | 4 | 🔴 HIGH | 1d | High |
| Production Deploy | 4 | 🔴 HIGH | 1d | High |
| E2E Tests | 4 | 🟡 MEDIUM | 1d | Medium |
| **TOTAL V10** | | | **~13 días** | |

---

## 💰 Cost Estimate (Optimizado para Prototipo)

| Feature | Monthly Cost | Notes |
|---------|-------------|-------|
| Supabase Auth | $0 | Included in FREE tier |
| RLS | $0 | Database feature |
| Vercel (Frontend) | $0 | FREE tier (100GB bandwidth) |
| Render (Backend) | $0 | FREE tier (750h/month, sleeps after 15min inactivity) |
| GitHub Actions | $0 | FREE tier (2000 min/month) |
| **Total V10** | **$0/month** | Hasta 100+ usuarios |

### ⚠️ Cuándo Escalar (Pagar)

| Señal | Acción | Costo |
|-------|--------|-------|
| >100 usuarios activos | Render Starter | $7/month |
| >50K requests/día | Supabase Pro | $25/month |
| Backend lento (sleep) | Render con always-on | $7/month |

**Filosofía**: No pagar hasta que el problema exista.

---

## 📈 Success Metrics

| Metric | Current (V9) | Target (V10) | Improvement |
|--------|--------------|--------------|-------------|
| User Auth | None | Full auth | Multi-user |
| Data Isolation | None | 100% RLS | Security |
| Deploy Time | ~30 min | <5 min | Automated |
| Test Coverage | Unit only | + E2E | Quality |

---

## 📝 V10 Completion Checklist

### Phase 1: Auth
- [ ] Supabase Auth configuration
- [ ] Backend auth middleware
- [ ] Frontend AuthContext
- [ ] Login/Signup pages
- [ ] OAuth (Google, GitHub)
- [ ] Protected routes

### Phase 2: RLS
- [ ] Schema updates (user_id columns)
- [ ] RLS policies for all tables
- [ ] Service key configuration
- [ ] RLS testing

### Phase 3: User Features
- [ ] User profiles table
- [ ] Tier limits implementation
- [ ] Quota enforcement middleware
- [ ] Settings UI
- [ ] Usage stats component

### Phase 4: CI/CD Pro
- [ ] Staging environment setup
- [ ] deploy-staging.yml workflow
- [ ] deploy-production.yml workflow
- [ ] Playwright E2E tests
- [ ] Slack notifications

### Validation
- [ ] Auth flow works end-to-end
- [ ] RLS prevents cross-user data access
- [ ] Quotas enforced correctly
- [ ] Auto-deploy to staging works
- [ ] Production deploy with approval
