# 🔒 Security Improvements Roadmap

> **Priority**: CRITICAL - Must be implemented before production deployment

This document outlines critical and high-priority security vulnerabilities that need to be addressed before deploying this application to production with real user data.

---

## 📍 Current State vs Future Vision

### Current Architecture (Local Mode)

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CURRENT STATE                                 │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   👤 Single User (Local)                                               │
│         │                                                              │
│         ▼                                                              │
│   ┌────────────┐     ┌────────────┐     ┌────────────┐                │
│   │  Frontend  │────▶│  Backend   │────▶│  ChromaDB  │                │
│   │  (React)   │     │  (FastAPI) │     │  (Local)   │                │
│   └────────────┘     └────────────┘     └────────────┘                │
│                             │                                          │
│                             │ (Cloud mode only)                        │
│                             ▼                                          │
│                      ┌────────────┐                                    │
│                      │  Supabase  │                                    │
│                      │ (pgvector) │                                    │
│                      └────────────┘                                    │
│                                                                        │
│   ❌ No authentication                                                 │
│   ❌ No user accounts                                                  │
│   ❌ No data isolation                                                 │
│   ❌ Single tenant only                                                │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

**Current Features**:
- ✅ Local mode with ChromaDB (free, no cloud needed)
- ✅ Cloud mode with Supabase pgvector (for embeddings only)
- ✅ PDF upload and RAG pipeline
- ✅ Session management (local JSON or Supabase)
- ❌ No user authentication
- ❌ No multi-tenancy
- ❌ Public API (anyone can access)

### Future Vision (SaaS Multi-Tenant)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FUTURE STATE (SaaS)                             │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   👤 User A        👤 User B        👤 User C                          │
│      │                │                │                               │
│      └────────────────┼────────────────┘                               │
│                       ▼                                                │
│              ┌───────────────┐                                         │
│              │ Supabase Auth │  ◀── Login/Register/OAuth               │
│              │ (JWT tokens)  │                                         │
│              └───────┬───────┘                                         │
│                      │                                                 │
│                      ▼                                                 │
│   ┌────────────┐    ┌────────────┐    ┌────────────┐                  │
│   │  Frontend  │───▶│  Backend   │───▶│  Supabase  │                  │
│   │  (React)   │    │  (FastAPI) │    │ (pgvector) │                  │
│   │ + Auth UI  │    │  + JWT     │    │  + RLS     │                  │
│   └────────────┘    └────────────┘    └────────────┘                  │
│                            │                 │                         │
│                            │                 ▼                         │
│                            │          ┌────────────┐                   │
│                            │          │  Storage   │                   │
│                            │          │ (Private)  │                   │
│                            │          └────────────┘                   │
│                            ▼                                           │
│                     ┌────────────┐                                     │
│                     │ OpenRouter │                                     │
│                     │ (LLM API)  │                                     │
│                     └────────────┘                                     │
│                                                                        │
│   ✅ User authentication (email/password, OAuth)                       │
│   ✅ Multi-tenant data isolation (RLS)                                 │
│   ✅ Private storage with signed URLs                                  │
│   ✅ Per-user rate limiting                                            │
│   ✅ Audit logging                                                     │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 SaaS Implementation Roadmap

### Phase 1: Authentication System (Weeks 1-2)

#### 1.1 Supabase Auth Setup

**Database Changes**:
```sql
-- Add user_id to all tables
ALTER TABLE sessions ADD COLUMN user_id UUID REFERENCES auth.users(id);
ALTER TABLE cvs ADD COLUMN user_id UUID REFERENCES auth.users(id);
ALTER TABLE session_cvs ADD COLUMN user_id UUID REFERENCES auth.users(id);

-- Create indexes for performance
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_cvs_user_id ON cvs(user_id);
```

**Backend Changes** (`backend/app/auth/`):
```python
# New file: backend/app/auth/supabase_auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Validate JWT and return user info."""
    token = credentials.credentials
    
    # Verify with Supabase
    supabase = create_client(settings.supabase_url, settings.supabase_anon_key)
    user = supabase.auth.get_user(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return user
```

**Frontend Changes** (`frontend/src/auth/`):
```jsx
// New file: frontend/src/contexts/AuthContext.jsx
import { createContext, useContext, useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

const AuthContext = createContext({});

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => setUser(session?.user ?? null)
    );

    return () => subscription.unsubscribe();
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading }}>
      {children}
    </AuthContext.Provider>
  );
}
```

#### 1.2 Login/Register UI

**New Components Needed**:
- `LoginPage.jsx` - Email/password login
- `RegisterPage.jsx` - User registration
- `ForgotPasswordPage.jsx` - Password reset
- `AuthCallback.jsx` - OAuth callback handler
- `ProtectedRoute.jsx` - Route guard component

**OAuth Providers** (optional):
- Google
- GitHub
- Microsoft (for enterprise)

---

### Phase 2: Data Isolation (Weeks 3-4)

#### 2.1 Row Level Security Policies

```sql
-- Enable RLS on all tables
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE cvs ENABLE ROW LEVEL SECURITY;
ALTER TABLE cv_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_cvs ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_messages ENABLE ROW LEVEL SECURITY;

-- Sessions: Users can only access their own
CREATE POLICY "Users can view own sessions" ON sessions
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own sessions" ON sessions
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sessions" ON sessions
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own sessions" ON sessions
  FOR DELETE USING (auth.uid() = user_id);

-- CVs: Users can only access their own
CREATE POLICY "Users can view own CVs" ON cvs
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can upload own CVs" ON cvs
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own CVs" ON cvs
  FOR DELETE USING (auth.uid() = user_id);

-- Embeddings: Linked to CVs (inherit access)
CREATE POLICY "Users can view own embeddings" ON cv_embeddings
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM cvs WHERE cvs.id = cv_embeddings.cv_id AND cvs.user_id = auth.uid())
  );

-- Storage policies
CREATE POLICY "Users can upload own PDFs" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'cv-pdfs' AND 
    auth.uid()::text = (storage.foldername(name))[1]
  );

CREATE POLICY "Users can view own PDFs" ON storage.objects
  FOR SELECT USING (
    bucket_id = 'cv-pdfs' AND 
    auth.uid()::text = (storage.foldername(name))[1]
  );
```

#### 2.2 Backend Changes for User Context

```python
# Update all routes to include user context
@router.post("/sessions")
async def create_session(
    request: CreateSessionRequest,
    current_user: dict = Depends(get_current_user)  # Add this
):
    session = session_manager.create_session(
        name=request.name,
        user_id=current_user.id  # Add user_id
    )
    return session

# Update Supabase client to use user JWT
def get_supabase_client_for_user(user_token: str):
    """Create Supabase client with user context (respects RLS)."""
    client = create_client(
        settings.supabase_url,
        settings.supabase_anon_key  # Use anon key, not service_role
    )
    client.auth.set_session(user_token)
    return client
```

---

### Phase 3: Private Storage (Week 4)

#### 3.1 Storage Structure

```
cv-pdfs/
├── {user_id_1}/
│   ├── {cv_id_1}.pdf
│   └── {cv_id_2}.pdf
├── {user_id_2}/
│   └── {cv_id_3}.pdf
└── ...
```

#### 3.2 Signed URL Implementation

```python
# backend/app/providers/cloud/pdf_storage.py

async def upload_pdf(self, user_id: str, cv_id: str, pdf_path: Path) -> str:
    """Upload PDF to user's private folder."""
    file_path = f"{user_id}/{cv_id}.pdf"  # User-scoped path
    
    with open(pdf_path, 'rb') as f:
        self.client.storage.from_(self.bucket_name).upload(
            file_path, f.read(),
            file_options={"content-type": "application/pdf", "upsert": "true"}
        )
    
    # Return signed URL (expires in 1 hour)
    return self.get_signed_url(user_id, cv_id)

def get_signed_url(self, user_id: str, cv_id: str, expires_in: int = 3600) -> str:
    """Generate temporary signed URL for PDF access."""
    file_path = f"{user_id}/{cv_id}.pdf"
    response = self.client.storage.from_(self.bucket_name).create_signed_url(
        file_path, expires_in
    )
    return response['signedURL']
```

---

### Phase 4: Rate Limiting & Monitoring (Week 5)

#### 4.1 Per-User Rate Limiting

```python
# backend/app/middleware/rate_limit.py

from collections import defaultdict
import time

class UserRateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.limits = {
            "upload": {"requests": 10, "window": 60},      # 10 uploads/min
            "chat": {"requests": 30, "window": 60},        # 30 messages/min
            "query": {"requests": 60, "window": 60},       # 60 queries/min
        }
    
    async def check_limit(self, user_id: str, action: str) -> bool:
        key = f"{user_id}:{action}"
        now = time.time()
        limit = self.limits.get(action, {"requests": 100, "window": 60})
        
        # Clean old requests
        self.requests[key] = [
            t for t in self.requests[key] 
            if now - t < limit["window"]
        ]
        
        if len(self.requests[key]) >= limit["requests"]:
            return False
        
        self.requests[key].append(now)
        return True
```

#### 4.2 Audit Logging

```sql
-- Create audit log table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast queries
CREATE INDEX idx_audit_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_created_at ON audit_logs(created_at);
```

---

## 📋 Complete Implementation Checklist

### Prerequisites
| # | Task | Effort | Status |
|---|------|--------|--------|
| 0.1 | Enable Supabase Auth in project settings | Low | ⬜ |
| 0.2 | Configure email templates (confirmation, reset) | Low | ⬜ |
| 0.3 | Set up OAuth providers (optional) | Medium | ⬜ |

### Phase 1: Authentication
| # | Task | Effort | Status |
|---|------|--------|--------|
| 1.1 | Add `user_id` column to all tables | Low | ⬜ |
| 1.2 | Create `backend/app/auth/` module | Medium | ⬜ |
| 1.3 | Add JWT validation middleware | Medium | ⬜ |
| 1.4 | Create `AuthContext` in frontend | Medium | ⬜ |
| 1.5 | Build Login/Register pages | Medium | ⬜ |
| 1.6 | Add `ProtectedRoute` component | Low | ⬜ |
| 1.7 | Update API calls to include JWT | Medium | ⬜ |

### Phase 2: Data Isolation
| # | Task | Effort | Status |
|---|------|--------|--------|
| 2.1 | Create RLS policies for all tables | Medium | ⬜ |
| 2.2 | Update backend to pass user context | Medium | ⬜ |
| 2.3 | Migrate from `service_role` to `anon` key | High | ⬜ |
| 2.4 | Test data isolation between users | Medium | ⬜ |

### Phase 3: Private Storage
| # | Task | Effort | Status |
|---|------|--------|--------|
| 3.1 | Change bucket to private | Low | ⬜ |
| 3.2 | Implement user-scoped storage paths | Medium | ⬜ |
| 3.3 | Implement signed URL generation | Low | ⬜ |
| 3.4 | Update frontend PDF viewer | Low | ⬜ |

### Phase 4: Security Hardening
| # | Task | Effort | Status |
|---|------|--------|--------|
| 4.1 | Implement per-user rate limiting | Medium | ⬜ |
| 4.2 | Add MIME type validation | Low | ⬜ |
| 4.3 | Create audit logging table | Low | ⬜ |
| 4.4 | Add security headers middleware | Low | ⬜ |

### Phase 5: Testing & Launch
| # | Task | Effort | Status |
|---|------|--------|--------|
| 5.1 | Security penetration testing | High | ⬜ |
| 5.2 | Load testing with multiple users | Medium | ⬜ |
| 5.3 | GDPR compliance review | Medium | ⬜ |
| 5.4 | Documentation update | Medium | ⬜ |

---

## ⛔ Critical Priority (P0)

### 1. No Authentication/Authorization

**Current State**: All API endpoints are publicly accessible without any authentication.

**Impact**:
- Anyone can upload, read, and delete CVs
- Access to sensitive candidate data (names, experience, contact info)
- No audit trail of who accessed what

**Files Affected**:
- `backend/app/main.py` - No auth middleware
- `backend/app/api/routes_v2.py` - All endpoints unprotected
- `backend/app/api/routes_sessions.py` - Session endpoints unprotected

**Recommended Solution**:
```python
# Option A: JWT Authentication
from fastapi_jwt_auth import AuthJWT

# Option B: API Key Authentication
from fastapi.security import APIKeyHeader
api_key_header = APIKeyHeader(name="X-API-Key")

# Option C: OAuth2 (for multi-tenant)
from fastapi.security import OAuth2PasswordBearer
```

**Implementation Steps**:
1. Choose authentication strategy (JWT recommended for SPA)
2. Add auth middleware to FastAPI app
3. Protect all sensitive endpoints
4. Add user/tenant isolation to queries

---

### 2. Row Level Security Disabled

**Current State**: RLS policies are set to `USING (true)`, allowing unrestricted access.

**Impact**:
- If `service_role` key is compromised, attacker has full database access
- No data isolation between users/tenants
- Violates principle of least privilege

**Files Affected**:
- `backend/migrations/003_create_session_tables.sql` (lines 142-146)
- `scripts/setup_supabase_complete.sql`

**Current Vulnerable Code**:
```sql
-- VULNERABLE: Allows all operations
CREATE POLICY "Allow all on cvs" ON cvs FOR ALL USING (true);
CREATE POLICY "Allow all on sessions" ON sessions FOR ALL USING (true);
```

**Recommended Solution**:
```sql
-- SECURE: User-based isolation
CREATE POLICY "Users can only see own CVs" ON cvs
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can only insert own CVs" ON cvs
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can only delete own CVs" ON cvs
  FOR DELETE USING (auth.uid() = user_id);
```

**Implementation Steps**:
1. Add `user_id` column to all tables
2. Create proper RLS policies per operation (SELECT, INSERT, UPDATE, DELETE)
3. Test policies with different user contexts
4. Migrate from `service_role` to `anon` key in backend

---

### 3. Public Storage Bucket

**Current State**: The `cv-pdfs` bucket is configured as public.

**Impact**:
- All uploaded CVs are accessible via direct URL without authentication
- Exposes personal data (names, addresses, phone numbers, work history)
- **GDPR/LOPD violation** - personal data publicly accessible

**Files Affected**:
- `backend/app/providers/cloud/pdf_storage.py` (line 54)
- `scripts/setup_supabase_complete.sql` (line 8-10)

**Current Vulnerable Code**:
```python
options={"public": True, ...}
```

**Recommended Solution**:
```python
# 1. Make bucket private
options={"public": False, ...}

# 2. Use signed URLs for access
def get_signed_url(self, cv_id: str, expires_in: int = 3600) -> str:
    """Generate a signed URL that expires."""
    file_path = f"{cv_id}.pdf"
    return self.client.storage.from_(self.bucket_name).create_signed_url(
        file_path, 
        expires_in
    )
```

**Implementation Steps**:
1. Change bucket to private in Supabase dashboard
2. Update `pdf_storage.py` to use `create_signed_url()`
3. Update frontend to request signed URLs from backend
4. Set appropriate expiration times (1 hour recommended)

---

### 4. Service Role Key in Backend

**Current State**: Backend uses `service_role` key which has admin privileges.

**Impact**:
- If backend is compromised, attacker has full Supabase access
- Bypasses all RLS policies
- Can delete entire database

**Files Affected**:
- `backend/app/providers/cloud/vector_store.py`
- `backend/app/providers/cloud/sessions.py`
- `backend/app/providers/cloud/pdf_storage.py`

**Recommended Solution**:
1. Use `anon` key with proper RLS policies
2. Only use `service_role` for admin operations (migrations, setup)
3. Implement proper user context in requests

**Implementation Steps**:
1. Implement RLS policies first (see item #2)
2. Add user authentication (see item #1)
3. Pass user JWT to Supabase client
4. Replace `service_role` with `anon` key in production

---

## 🔴 High Priority (P1)

### 5. No MIME Type Validation

**Current State**: Only file extension is validated, not actual file content.

**Impact**:
- Malicious files disguised as PDFs can be uploaded
- Potential exploitation of PDF parsing library (`pdfplumber`)
- Server-side vulnerabilities from malformed PDFs

**Files Affected**:
- `backend/app/api/routes_v2.py` (lines 204-213)

**Current Vulnerable Code**:
```python
if not file.filename.lower().endswith(".pdf"):
    raise HTTPException(...)
# No actual content validation!
```

**Recommended Solution**:
```python
import magic  # python-magic library

def validate_pdf(content: bytes) -> bool:
    """Validate file is actually a PDF."""
    mime = magic.from_buffer(content, mime=True)
    if mime != "application/pdf":
        return False
    
    # Check PDF header
    if not content.startswith(b"%PDF-"):
        return False
    
    return True
```

**Implementation Steps**:
1. Install `python-magic` library
2. Add MIME type validation before processing
3. Add PDF header validation
4. Consider adding virus scanning for production

---

### 6. Rate Limiting Not Applied

**Current State**: Rate limiter exists but is not applied to endpoints.

**Impact**:
- Denial of Service (DoS) attacks possible
- Abuse of external API keys (OpenRouter) leading to high costs
- Resource exhaustion

**Files Affected**:
- `backend/app/api/dependencies.py` (lines 81-90)
- `backend/app/api/routes_v2.py` - No rate limit dependency
- `backend/app/api/routes_sessions.py` - No rate limit dependency

**Current Code** (not applied):
```python
def get_rate_limiter() -> RateLimiter:
    # Exists but never used as dependency
```

**Recommended Solution**:
```python
from fastapi import Depends

@router.post("/upload")
async def upload_cvs(
    files: List[UploadFile],
    rate_limiter: RateLimiter = Depends(get_rate_limiter)  # Add this
):
    await rate_limiter.check_rate_limit(request)
    # ... rest of handler
```

**Implementation Steps**:
1. Add rate limiter as dependency to all public endpoints
2. Configure appropriate limits per endpoint type
3. Add IP-based and user-based limits
4. Return proper 429 responses with Retry-After header

---

## 📋 Implementation Checklist

| # | Task | Priority | Effort | Status |
|---|------|----------|--------|--------|
| 1 | Make storage bucket private + signed URLs | P0 | Low | ⬜ Pending |
| 2 | Implement proper RLS policies | P0 | Medium | ⬜ Pending |
| 3 | Add API authentication (JWT/API Key) | P0 | Medium | ⬜ Pending |
| 4 | Add MIME type validation | P1 | Low | ⬜ Pending |
| 5 | Apply rate limiting to endpoints | P1 | Low | ⬜ Pending |
| 6 | Migrate from service_role to anon key | P0 | High | ⬜ Pending |

---

## 🚨 Legal Considerations

### GDPR/LOPD Compliance

CVs contain **personal data** protected under:
- **GDPR** (EU General Data Protection Regulation)
- **LOPD** (Spanish Ley Orgánica de Protección de Datos)

**Required Actions**:
1. Implement data access controls (authentication + RLS)
2. Add data retention policies
3. Implement "right to be forgotten" (data deletion)
4. Document data processing activities
5. Obtain explicit consent for CV processing
6. Disclose data transfers to third parties (OpenRouter, Supabase)

---

## 📅 Recommended Timeline

| Week | Tasks |
|------|-------|
| Week 1 | Private bucket + signed URLs, MIME validation |
| Week 2 | RLS policies implementation |
| Week 3 | Authentication system (JWT) |
| Week 4 | Rate limiting, migrate to anon key |
| Week 5 | Testing + security audit |

---

## 📚 Resources

- [Supabase RLS Guide](https://supabase.com/docs/guides/auth/row-level-security)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP API Security Top 10](https://owasp.org/API-Security/)
- [GDPR Compliance Checklist](https://gdpr.eu/checklist/)

---

*Last updated: January 2026*
*Author: Security Analysis*
