-- ============================================
-- SUPABASE CLOUD MODE - COMPLETE SETUP
-- Execute this entire file in Supabase SQL Editor
-- ============================================

-- 1. CREATE STORAGE BUCKET
-- ============================================
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('cv-pdfs', 'cv-pdfs', true, 52428800, ARRAY['application/pdf'])
ON CONFLICT (id) DO NOTHING;

-- 2. STORAGE POLICIES
-- ============================================
DROP POLICY IF EXISTS "Public read access" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated upload" ON storage.objects;
DROP POLICY IF EXISTS "Service role all access" ON storage.objects;

CREATE POLICY "Public read access" ON storage.objects
FOR SELECT USING (bucket_id = 'cv-pdfs');

CREATE POLICY "Authenticated upload" ON storage.objects
FOR INSERT WITH CHECK (bucket_id = 'cv-pdfs');

CREATE POLICY "Service role all access" ON storage.objects
FOR ALL USING (bucket_id = 'cv-pdfs');

-- 3. CREATE TABLES (if not exist)
-- ============================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- CVs table
CREATE TABLE IF NOT EXISTS cvs (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    upload_date TIMESTAMPTZ DEFAULT NOW(),
    file_size BIGINT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- CV Embeddings table (768 dimensions for nomic-embed)
CREATE TABLE IF NOT EXISTS cv_embeddings (
    id BIGSERIAL PRIMARY KEY,
    cv_id TEXT REFERENCES cvs(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),  -- CRITICAL: 768 for nomic-embed
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Session CVs junction table
CREATE TABLE IF NOT EXISTS session_cvs (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    cv_id TEXT REFERENCES cvs(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(session_id, cv_id)
);

-- Session Messages table
CREATE TABLE IF NOT EXISTS session_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]'::jsonb,
    pipeline_steps JSONB DEFAULT '[]'::jsonb,  -- ADDED
    structured_output JSONB DEFAULT NULL,      -- ADDED
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 4. CREATE INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_cv_embeddings_cv_id ON cv_embeddings(cv_id);
CREATE INDEX IF NOT EXISTS idx_session_cvs_session_id ON session_cvs(session_id);
CREATE INDEX IF NOT EXISTS idx_session_cvs_cv_id ON session_cvs(cv_id);
CREATE INDEX IF NOT EXISTS idx_session_messages_session_id ON session_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_session_messages_timestamp ON session_messages(timestamp);

-- Vector similarity index (IVFFlat)
CREATE INDEX IF NOT EXISTS cv_embeddings_embedding_idx 
ON cv_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 5. CREATE SIMILARITY SEARCH FUNCTION
-- ============================================
CREATE OR REPLACE FUNCTION match_cv_embeddings(
    query_embedding vector(768),  -- CRITICAL: 768 dimensions
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

-- 6. VERIFICATION QUERIES
-- ============================================
DO $$ 
BEGIN
    RAISE NOTICE '=== SETUP COMPLETE ===';
    RAISE NOTICE 'Bucket created: cv-pdfs';
    RAISE NOTICE 'Tables: cvs, cv_embeddings, sessions, session_cvs, session_messages';
    RAISE NOTICE 'Embedding dimension: 768 (nomic-embed-text-v1.5)';
    RAISE NOTICE '';
    RAISE NOTICE 'Run these queries to verify:';
    RAISE NOTICE '1. SELECT * FROM storage.buckets WHERE name = ''cv-pdfs'';';
    RAISE NOTICE '2. SELECT table_name FROM information_schema.tables WHERE table_schema = ''public'';';
    RAISE NOTICE '3. \\d cv_embeddings  (check embedding column)';
END $$;
