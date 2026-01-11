-- ============================================
-- CV Screener - Sessions & Cloud Parity Schema
-- Migration: 002_sessions_schema
-- V9 Implementation Plan
-- ============================================

-- ============================================
-- Table: sessions (Session management)
-- ============================================
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL DEFAULT 'Nueva Sesión',
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    message_count INTEGER DEFAULT 0,
    cv_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for sessions
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC);

-- ============================================
-- Table: session_cvs (CVs linked to sessions)
-- ============================================
CREATE TABLE IF NOT EXISTS session_cvs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    cv_id TEXT NOT NULL REFERENCES cvs(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint to prevent duplicate CV-session links
    CONSTRAINT unique_session_cv UNIQUE (session_id, cv_id)
);

-- Indexes for session_cvs
CREATE INDEX IF NOT EXISTS idx_session_cvs_session_id ON session_cvs(session_id);
CREATE INDEX IF NOT EXISTS idx_session_cvs_cv_id ON session_cvs(cv_id);

-- ============================================
-- Table: session_messages (Chat history)
-- ============================================
CREATE TABLE IF NOT EXISTS session_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]'::jsonb,
    metrics JSONB DEFAULT NULL,
    structured_output JSONB DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    message_index INTEGER NOT NULL DEFAULT 0
);

-- Indexes for session_messages
CREATE INDEX IF NOT EXISTS idx_session_messages_session_id ON session_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_session_messages_created_at ON session_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_session_messages_index ON session_messages(session_id, message_index);

-- ============================================
-- Table: query_cache (Semantic cache)
-- ============================================
CREATE TABLE IF NOT EXISTS query_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_hash TEXT NOT NULL UNIQUE,
    query_text TEXT NOT NULL,
    query_embedding VECTOR(768),
    response_text TEXT NOT NULL,
    sources JSONB DEFAULT '[]'::jsonb,
    structured_output JSONB DEFAULT NULL,
    cv_context_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours'),
    hit_count INTEGER DEFAULT 0,
    last_hit_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for query_cache
CREATE INDEX IF NOT EXISTS idx_query_cache_hash ON query_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_query_cache_expires ON query_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_query_cache_embedding ON query_cache 
    USING ivfflat (query_embedding vector_cosine_ops) WITH (lists = 50);

-- ============================================
-- Table: screening_rules (Auto-screening rules)
-- ============================================
CREATE TABLE IF NOT EXISTS screening_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    rule_type TEXT NOT NULL CHECK (rule_type IN ('required_skill', 'min_experience', 'education', 'location', 'custom')),
    rule_config JSONB NOT NULL,
    weight FLOAT DEFAULT 1.0,
    is_mandatory BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for screening_rules
CREATE INDEX IF NOT EXISTS idx_screening_rules_session ON screening_rules(session_id);

-- ============================================
-- Add session_id to cvs table for direct relationship
-- ============================================
ALTER TABLE cvs ADD COLUMN IF NOT EXISTS session_id UUID REFERENCES sessions(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_cvs_session_id ON cvs(session_id);

-- Add FTS column for hybrid search
ALTER TABLE cvs ADD COLUMN IF NOT EXISTS content TEXT;
ALTER TABLE cvs ADD COLUMN IF NOT EXISTS fts_content tsvector 
    GENERATED ALWAYS AS (to_tsvector('english', COALESCE(content, ''))) STORED;
CREATE INDEX IF NOT EXISTS idx_cvs_fts ON cvs USING GIN(fts_content);

-- ============================================
-- Function: Update session timestamps
-- ============================================
CREATE OR REPLACE FUNCTION update_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE sessions SET updated_at = NOW() WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for session_messages
DROP TRIGGER IF EXISTS trigger_update_session_on_message ON session_messages;
CREATE TRIGGER trigger_update_session_on_message
    AFTER INSERT ON session_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_session_timestamp();

-- Trigger for session_cvs
DROP TRIGGER IF EXISTS trigger_update_session_on_cv ON session_cvs;
CREATE TRIGGER trigger_update_session_on_cv
    AFTER INSERT OR DELETE ON session_cvs
    FOR EACH ROW
    EXECUTE FUNCTION update_session_timestamp();

-- ============================================
-- Function: Update session counts
-- ============================================
CREATE OR REPLACE FUNCTION update_session_counts()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_TABLE_NAME = 'session_messages' THEN
        UPDATE sessions SET message_count = (
            SELECT COUNT(*) FROM session_messages WHERE session_id = COALESCE(NEW.session_id, OLD.session_id)
        ) WHERE id = COALESCE(NEW.session_id, OLD.session_id);
    ELSIF TG_TABLE_NAME = 'session_cvs' THEN
        UPDATE sessions SET cv_count = (
            SELECT COUNT(*) FROM session_cvs WHERE session_id = COALESCE(NEW.session_id, OLD.session_id)
        ) WHERE id = COALESCE(NEW.session_id, OLD.session_id);
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Triggers for count updates
DROP TRIGGER IF EXISTS trigger_update_message_count ON session_messages;
CREATE TRIGGER trigger_update_message_count
    AFTER INSERT OR DELETE ON session_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_session_counts();

DROP TRIGGER IF EXISTS trigger_update_cv_count ON session_cvs;
CREATE TRIGGER trigger_update_cv_count
    AFTER INSERT OR DELETE ON session_cvs
    FOR EACH ROW
    EXECUTE FUNCTION update_session_counts();

-- ============================================
-- Function: Hybrid search (Semantic + FTS)
-- ============================================
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding VECTOR(768),
    match_count INT DEFAULT 10,
    session_filter UUID DEFAULT NULL,
    semantic_weight FLOAT DEFAULT 0.5
)
RETURNS TABLE (
    id UUID,
    cv_id TEXT,
    filename TEXT,
    chunk_index INTEGER,
    content TEXT,
    similarity FLOAT,
    fts_score FLOAT,
    combined_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ce.id,
        ce.cv_id,
        ce.filename,
        ce.chunk_index,
        ce.content,
        (1 - (ce.embedding <=> query_embedding))::FLOAT as similarity,
        COALESCE(ts_rank(c.fts_content, plainto_tsquery('english', query_text)), 0)::FLOAT as fts_score,
        (
            semantic_weight * (1 - (ce.embedding <=> query_embedding)) + 
            (1 - semantic_weight) * COALESCE(ts_rank(c.fts_content, plainto_tsquery('english', query_text)), 0)
        )::FLOAT as combined_score
    FROM cv_embeddings ce
    JOIN cvs c ON ce.cv_id = c.id
    WHERE (session_filter IS NULL OR c.session_id = session_filter)
    ORDER BY (
        semantic_weight * (1 - (ce.embedding <=> query_embedding)) + 
        (1 - semantic_weight) * COALESCE(ts_rank(c.fts_content, plainto_tsquery('english', query_text)), 0)
    ) DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Function: Search with session filter
-- ============================================
CREATE OR REPLACE FUNCTION match_cv_embeddings_by_session(
    query_embedding VECTOR(768),
    target_session_id UUID,
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
    JOIN session_cvs sc ON ce.cv_id = sc.cv_id
    WHERE sc.session_id = target_session_id
      AND (1 - (ce.embedding <=> query_embedding)) > match_threshold
    ORDER BY ce.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================
-- Function: Semantic cache lookup
-- ============================================
CREATE OR REPLACE FUNCTION find_cached_query(
    query_embedding VECTOR(768),
    similarity_threshold FLOAT DEFAULT 0.95
)
RETURNS TABLE (
    id UUID,
    query_text TEXT,
    response_text TEXT,
    sources JSONB,
    structured_output JSONB,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        qc.id,
        qc.query_text,
        qc.response_text,
        qc.sources,
        qc.structured_output,
        (1 - (qc.query_embedding <=> query_embedding))::FLOAT as similarity
    FROM query_cache qc
    WHERE qc.expires_at > NOW()
      AND (1 - (qc.query_embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY qc.query_embedding <=> query_embedding
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Function: Update cache hit
-- ============================================
CREATE OR REPLACE FUNCTION update_cache_hit(cache_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE query_cache 
    SET hit_count = hit_count + 1, 
        last_hit_at = NOW()
    WHERE id = cache_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Function: Clean expired cache
-- ============================================
CREATE OR REPLACE FUNCTION clean_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM query_cache WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Grant permissions
-- ============================================
GRANT ALL ON sessions TO service_role;
GRANT ALL ON session_cvs TO service_role;
GRANT ALL ON session_messages TO service_role;
GRANT ALL ON query_cache TO service_role;
GRANT ALL ON screening_rules TO service_role;
GRANT EXECUTE ON FUNCTION update_session_timestamp TO service_role;
GRANT EXECUTE ON FUNCTION update_session_counts TO service_role;
GRANT EXECUTE ON FUNCTION hybrid_search TO service_role;
GRANT EXECUTE ON FUNCTION match_cv_embeddings_by_session TO service_role;
GRANT EXECUTE ON FUNCTION find_cached_query TO service_role;
GRANT EXECUTE ON FUNCTION update_cache_hit TO service_role;
GRANT EXECUTE ON FUNCTION clean_expired_cache TO service_role;

-- ============================================
-- Storage bucket for PDFs (run manually in Supabase dashboard)
-- ============================================
-- INSERT INTO storage.buckets (id, name, public) 
-- VALUES ('cv-pdfs', 'cv-pdfs', false)
-- ON CONFLICT DO NOTHING;
