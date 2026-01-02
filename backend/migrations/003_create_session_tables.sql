-- ============================================
-- CV SCREENER - COMPLETE SUPABASE SCHEMA
-- Run this in Supabase SQL Editor
-- ============================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 1. CVS TABLE - Stores CV metadata
-- ============================================
CREATE TABLE IF NOT EXISTS cvs (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    chunk_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 2. CV_EMBEDDINGS TABLE - Stores CV chunks with embeddings
-- ============================================
CREATE TABLE IF NOT EXISTS cv_embeddings (
    id BIGSERIAL PRIMARY KEY,
    cv_id TEXT NOT NULL REFERENCES cvs(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384),  -- Dimension for all-MiniLM-L6-v2
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(cv_id, chunk_index)
);

-- ============================================
-- 3. SESSIONS TABLE - Chat sessions/groups
-- ============================================
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 4. SESSION_CVS TABLE - Links sessions to CVs
-- ============================================
CREATE TABLE IF NOT EXISTS session_cvs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    cv_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    chunk_count INTEGER DEFAULT 0,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 5. SESSION_MESSAGES TABLE - Chat history per session
-- ============================================
CREATE TABLE IF NOT EXISTS session_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]'::jsonb,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_cv_embeddings_cv_id ON cv_embeddings(cv_id);
CREATE INDEX IF NOT EXISTS idx_session_cvs_session_id ON session_cvs(session_id);
CREATE INDEX IF NOT EXISTS idx_session_cvs_cv_id ON session_cvs(cv_id);
CREATE INDEX IF NOT EXISTS idx_session_messages_session_id ON session_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_session_messages_timestamp ON session_messages(timestamp);

-- ============================================
-- VECTOR SIMILARITY SEARCH FUNCTION
-- ============================================
CREATE OR REPLACE FUNCTION match_cv_embeddings(
    query_embedding vector(384),
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

-- ============================================
-- DELETE CV FUNCTION (cascades to embeddings)
-- ============================================
CREATE OR REPLACE FUNCTION delete_cv(target_cv_id TEXT)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM cvs WHERE id = target_cv_id;
END;
$$;

-- ============================================
-- ROW LEVEL SECURITY (optional - allow all for now)
-- ============================================
ALTER TABLE cvs ENABLE ROW LEVEL SECURITY;
ALTER TABLE cv_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_cvs ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_messages ENABLE ROW LEVEL SECURITY;

-- Policies (allow all for service key)
DROP POLICY IF EXISTS "Allow all on cvs" ON cvs;
DROP POLICY IF EXISTS "Allow all on cv_embeddings" ON cv_embeddings;
DROP POLICY IF EXISTS "Allow all on sessions" ON sessions;
DROP POLICY IF EXISTS "Allow all on session_cvs" ON session_cvs;
DROP POLICY IF EXISTS "Allow all on session_messages" ON session_messages;

CREATE POLICY "Allow all on cvs" ON cvs FOR ALL USING (true);
CREATE POLICY "Allow all on cv_embeddings" ON cv_embeddings FOR ALL USING (true);
CREATE POLICY "Allow all on sessions" ON sessions FOR ALL USING (true);
CREATE POLICY "Allow all on session_cvs" ON session_cvs FOR ALL USING (true);
CREATE POLICY "Allow all on session_messages" ON session_messages FOR ALL USING (true);
