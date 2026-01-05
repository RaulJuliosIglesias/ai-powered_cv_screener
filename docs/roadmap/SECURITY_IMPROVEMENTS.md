# 🔒 Security Improvements Roadmap

> **Priority**: CRITICAL - Must be implemented before production deployment

This document outlines critical and high-priority security vulnerabilities that need to be addressed before deploying this application to production with real user data.

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
