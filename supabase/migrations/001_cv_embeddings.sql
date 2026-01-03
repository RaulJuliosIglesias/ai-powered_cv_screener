-- ============================================
-- CV Screener - Supabase pgvector Schema
-- Migration: 001_cv_embeddings
-- ============================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- Table: cvs (CV metadata)
-- ============================================
CREATE TABLE IF NOT EXISTS cvs (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    chunk_count INTEGER DEFAULT 0,
    indexed_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_cvs_filename ON cvs(filename);
CREATE INDEX IF NOT EXISTS idx_cvs_indexed_at ON cvs(indexed_at DESC);

-- ============================================
-- Table: cv_embeddings (Vector embeddings)
-- ============================================
CREATE TABLE IF NOT EXISTS cv_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cv_id TEXT NOT NULL REFERENCES cvs(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768),  -- nomic-embed-text-v1.5 dimensions
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint to prevent duplicate chunks
    CONSTRAINT unique_cv_chunk UNIQUE (cv_id, chunk_index)
);

-- Index for vector similarity search (IVFFlat)
CREATE INDEX IF NOT EXISTS idx_cv_embeddings_vector 
ON cv_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Index for filtering by cv_id
CREATE INDEX IF NOT EXISTS idx_cv_embeddings_cv_id ON cv_embeddings(cv_id);

-- Index for faster content search
CREATE INDEX IF NOT EXISTS idx_cv_embeddings_created_at ON cv_embeddings(created_at DESC);

-- ============================================
-- Function: match_cv_embeddings
-- Vector similarity search using cosine distance
-- ============================================
CREATE OR REPLACE FUNCTION match_cv_embeddings(
    query_embedding VECTOR(768),
    match_count INT DEFAULT 5,
    match_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id UUID,
    cv_id TEXT,
    filename TEXT,
    chunk_index INTEGER,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ce.id,
        ce.cv_id,
        ce.filename,
        ce.chunk_index,
        ce.content,
        ce.metadata,
        (1 - (ce.embedding <=> query_embedding))::FLOAT AS similarity
    FROM cv_embeddings ce
    WHERE (1 - (ce.embedding <=> query_embedding)) > match_threshold
    ORDER BY ce.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================
-- Function: match_cv_embeddings_filtered
-- Vector search with CV ID filtering
-- ============================================
CREATE OR REPLACE FUNCTION match_cv_embeddings_filtered(
    query_embedding VECTOR(768),
    filter_cv_ids TEXT[],
    match_count INT DEFAULT 5,
    match_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id UUID,
    cv_id TEXT,
    filename TEXT,
    chunk_index INTEGER,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ce.id,
        ce.cv_id,
        ce.filename,
        ce.chunk_index,
        ce.content,
        ce.metadata,
        (1 - (ce.embedding <=> query_embedding))::FLOAT AS similarity
    FROM cv_embeddings ce
    WHERE ce.cv_id = ANY(filter_cv_ids)
      AND (1 - (ce.embedding <=> query_embedding)) > match_threshold
    ORDER BY ce.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================
-- Function: delete_cv_by_id
-- Delete CV and all its embeddings
-- ============================================
CREATE OR REPLACE FUNCTION delete_cv_by_id(target_cv_id TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN
    -- Delete embeddings (cascade should handle this, but explicit is clearer)
    DELETE FROM cv_embeddings WHERE cv_id = target_cv_id;
    
    -- Delete CV metadata
    DELETE FROM cvs WHERE id = target_cv_id;
    
    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$;

-- ============================================
-- Function: get_cv_stats
-- Get statistics about indexed CVs
-- ============================================
CREATE OR REPLACE FUNCTION get_cv_stats()
RETURNS TABLE (
    total_cvs BIGINT,
    total_chunks BIGINT,
    avg_chunks_per_cv NUMERIC,
    oldest_cv TIMESTAMPTZ,
    newest_cv TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*) FROM cvs)::BIGINT AS total_cvs,
        (SELECT COUNT(*) FROM cv_embeddings)::BIGINT AS total_chunks,
        COALESCE((SELECT AVG(chunk_count)::NUMERIC FROM cvs), 0) AS avg_chunks_per_cv,
        (SELECT MIN(indexed_at) FROM cvs) AS oldest_cv,
        (SELECT MAX(indexed_at) FROM cvs) AS newest_cv;
END;
$$;

-- ============================================
-- Row Level Security (Optional but recommended)
-- ============================================
-- ALTER TABLE cvs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE cv_embeddings ENABLE ROW LEVEL SECURITY;

-- Create policies for service role access
-- CREATE POLICY "Service role full access to cvs" ON cvs
--     FOR ALL USING (auth.role() = 'service_role');

-- CREATE POLICY "Service role full access to cv_embeddings" ON cv_embeddings
--     FOR ALL USING (auth.role() = 'service_role');

-- ============================================
-- Grant permissions
-- ============================================
GRANT ALL ON cvs TO service_role;
GRANT ALL ON cv_embeddings TO service_role;
GRANT EXECUTE ON FUNCTION match_cv_embeddings TO service_role;
GRANT EXECUTE ON FUNCTION match_cv_embeddings_filtered TO service_role;
GRANT EXECUTE ON FUNCTION delete_cv_by_id TO service_role;
GRANT EXECUTE ON FUNCTION get_cv_stats TO service_role;
