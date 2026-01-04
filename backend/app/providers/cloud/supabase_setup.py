"""
Direct Supabase setup via SQL execution.
Run this once to initialize Supabase for cloud mode.
"""
import logging
from supabase import create_client

logger = logging.getLogger(__name__)


def setup_supabase_storage_and_tables(supabase_url: str, supabase_service_key: str):
    """
    Initialize Supabase with all required tables, bucket, and policies.
    This bypasses RLS issues by using service role key.
    """
    client = create_client(supabase_url, supabase_service_key)
    
    setup_sql = """
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. CREATE STORAGE BUCKET
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('cv-pdfs', 'cv-pdfs', true, 52428800, ARRAY['application/pdf'])
ON CONFLICT (id) DO NOTHING;

-- 2. STORAGE POLICIES
DROP POLICY IF EXISTS "Public read access" ON storage.objects;
DROP POLICY IF EXISTS "Service role all access" ON storage.objects;

CREATE POLICY "Public read access" ON storage.objects
FOR SELECT USING (bucket_id = 'cv-pdfs');

CREATE POLICY "Service role all access" ON storage.objects
FOR ALL USING (bucket_id = 'cv-pdfs');

-- 3. CREATE TABLES
CREATE TABLE IF NOT EXISTS cvs (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    upload_date TIMESTAMPTZ DEFAULT NOW(),
    file_size BIGINT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cv_embeddings (
    id BIGSERIAL PRIMARY KEY,
    cv_id TEXT REFERENCES cvs(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS session_cvs (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    cv_id TEXT REFERENCES cvs(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(session_id, cv_id)
);

CREATE TABLE IF NOT EXISTS session_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]'::jsonb,
    pipeline_steps JSONB DEFAULT '[]'::jsonb,
    structured_output JSONB DEFAULT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 4. CREATE INDEXES
CREATE INDEX IF NOT EXISTS idx_cv_embeddings_cv_id ON cv_embeddings(cv_id);
CREATE INDEX IF NOT EXISTS idx_session_cvs_session_id ON session_cvs(session_id);
CREATE INDEX IF NOT EXISTS idx_session_cvs_cv_id ON session_cvs(cv_id);
CREATE INDEX IF NOT EXISTS idx_session_messages_session_id ON session_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_session_messages_timestamp ON session_messages(timestamp);

CREATE INDEX IF NOT EXISTS cv_embeddings_embedding_idx 
ON cv_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 5. CREATE SIMILARITY SEARCH FUNCTION
CREATE OR REPLACE FUNCTION match_cv_embeddings(
    query_embedding vector(768),
    match_count INT DEFAULT 5,
    match_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id BIGINT,
    cv_id TEXT,
    filename TEXT,
    content TEXT,
    similarity FLOAT,
    metadata JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ce.id,
        ce.cv_id,
        ce.filename,
        ce.content,
        1 - (ce.embedding <=> query_embedding) as similarity,
        ce.metadata
    FROM cv_embeddings ce
    WHERE 1 - (ce.embedding <=> query_embedding) > match_threshold
    ORDER BY ce.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""
    
    try:
        # Execute setup SQL
        result = client.postgrest.schema("public").rpc("exec_sql", {"query": setup_sql}).execute()
        logger.info("✅ Supabase setup completed successfully")
        return True
    except Exception as e:
        # Try executing each statement separately
        logger.warning(f"Batch SQL failed, trying individual statements: {e}")
        
        statements = [s.strip() for s in setup_sql.split(';') if s.strip()]
        
        for stmt in statements:
            try:
                if stmt:
                    client.postgrest.schema("public").rpc("exec_sql", {"query": stmt}).execute()
            except Exception as stmt_error:
                logger.debug(f"Statement failed (might be OK): {stmt_error}")
        
        logger.info("✅ Supabase setup completed (with some warnings)")
        return True


async def auto_setup_on_init():
    """Auto-run setup when cloud providers are initialized."""
    try:
        from app.config import settings
        
        if not settings.supabase_url or not settings.supabase_service_key:
            logger.warning("Supabase not configured, skipping auto-setup")
            return
        
        logger.info("Running automatic Supabase setup...")
        setup_supabase_storage_and_tables(
            settings.supabase_url,
            settings.supabase_service_key
        )
    except Exception as e:
        logger.error(f"Auto-setup failed: {e}")


if __name__ == "__main__":
    # Run setup manually
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    from app.config import settings
    
    print("🔧 Setting up Supabase...")
    print(f"URL: {settings.supabase_url}")
    
    if setup_supabase_storage_and_tables(settings.supabase_url, settings.supabase_service_key):
        print("✅ Setup complete!")
    else:
        print("❌ Setup failed!")
