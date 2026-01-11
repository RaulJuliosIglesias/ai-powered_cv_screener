-- ============================================
-- CV Screener - FASE 1 Enhanced Schema
-- Migration: 002_fase1_enhanced_schema
-- Adds: structured metadata tables, hybrid search
-- ============================================

-- ============================================
-- Table: cv_metadata (Structured CV data)
-- ============================================
CREATE TABLE IF NOT EXISTS cv_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cv_id TEXT NOT NULL REFERENCES cvs(id) ON DELETE CASCADE,
    candidate_name TEXT,
    
    -- Experience
    total_experience_years FLOAT DEFAULT 0,
    current_role TEXT,
    current_company TEXT,
    seniority_level TEXT,  -- junior, mid, senior, lead, executive
    position_count INTEGER DEFAULT 0,
    
    -- Red flags
    job_hopping_score FLOAT DEFAULT 0,
    avg_tenure_years FLOAT DEFAULT 0,
    employment_gaps_count INTEGER DEFAULT 0,
    
    -- Education flags
    education_level TEXT,  -- phd, masters, bachelors, diploma
    education_field TEXT,
    education_institution TEXT,
    graduation_year INTEGER,
    has_mba BOOLEAN DEFAULT FALSE,
    has_phd BOOLEAN DEFAULT FALSE,
    
    -- Language flags (for direct queries like "who speaks French")
    speaks_english BOOLEAN DEFAULT FALSE,
    speaks_french BOOLEAN DEFAULT FALSE,
    speaks_spanish BOOLEAN DEFAULT FALSE,
    speaks_german BOOLEAN DEFAULT FALSE,
    speaks_chinese BOOLEAN DEFAULT FALSE,
    
    -- Certification flags
    has_aws_cert BOOLEAN DEFAULT FALSE,
    has_azure_cert BOOLEAN DEFAULT FALSE,
    has_gcp_cert BOOLEAN DEFAULT FALSE,
    has_pmp BOOLEAN DEFAULT FALSE,
    has_cbap BOOLEAN DEFAULT FALSE,
    has_scrum BOOLEAN DEFAULT FALSE,
    
    -- Contact
    location TEXT,
    
    -- Raw data as JSONB for flexibility
    languages_json JSONB DEFAULT '[]'::jsonb,
    certifications_json JSONB DEFAULT '[]'::jsonb,
    education_json JSONB DEFAULT '[]'::jsonb,
    skills_json JSONB DEFAULT '[]'::jsonb,
    experiences_json JSONB DEFAULT '[]'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_cv_metadata UNIQUE (cv_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_cv_metadata_cv_id ON cv_metadata(cv_id);
CREATE INDEX IF NOT EXISTS idx_cv_metadata_experience ON cv_metadata(total_experience_years);
CREATE INDEX IF NOT EXISTS idx_cv_metadata_seniority ON cv_metadata(seniority_level);

-- Boolean indexes for direct metadata queries
CREATE INDEX IF NOT EXISTS idx_cv_metadata_speaks_french ON cv_metadata(speaks_french) WHERE speaks_french = TRUE;
CREATE INDEX IF NOT EXISTS idx_cv_metadata_speaks_spanish ON cv_metadata(speaks_spanish) WHERE speaks_spanish = TRUE;
CREATE INDEX IF NOT EXISTS idx_cv_metadata_has_mba ON cv_metadata(has_mba) WHERE has_mba = TRUE;
CREATE INDEX IF NOT EXISTS idx_cv_metadata_has_phd ON cv_metadata(has_phd) WHERE has_phd = TRUE;
CREATE INDEX IF NOT EXISTS idx_cv_metadata_has_aws ON cv_metadata(has_aws_cert) WHERE has_aws_cert = TRUE;
CREATE INDEX IF NOT EXISTS idx_cv_metadata_has_pmp ON cv_metadata(has_pmp) WHERE has_pmp = TRUE;

-- ============================================
-- Table: cv_skills (Normalized skills table)
-- ============================================
CREATE TABLE IF NOT EXISTS cv_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cv_id TEXT NOT NULL REFERENCES cvs(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    skill_level INTEGER,  -- 1-10 scale
    is_technical BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cv_skills_cv_id ON cv_skills(cv_id);
CREATE INDEX IF NOT EXISTS idx_cv_skills_name ON cv_skills(skill_name);
CREATE INDEX IF NOT EXISTS idx_cv_skills_name_lower ON cv_skills(LOWER(skill_name));

-- ============================================
-- Table: cv_languages (Normalized languages)
-- ============================================
CREATE TABLE IF NOT EXISTS cv_languages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cv_id TEXT NOT NULL REFERENCES cvs(id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    level TEXT,  -- A1, A2, B1, B2, C1, C2, Native
    is_native BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cv_languages_cv_id ON cv_languages(cv_id);
CREATE INDEX IF NOT EXISTS idx_cv_languages_language ON cv_languages(LOWER(language));

-- ============================================
-- Table: cv_certifications (Normalized certs)
-- ============================================
CREATE TABLE IF NOT EXISTS cv_certifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cv_id TEXT NOT NULL REFERENCES cvs(id) ON DELETE CASCADE,
    certification_name TEXT NOT NULL,
    issuer TEXT,
    year_obtained INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cv_certifications_cv_id ON cv_certifications(cv_id);
CREATE INDEX IF NOT EXISTS idx_cv_certifications_name ON cv_certifications(LOWER(certification_name));

-- ============================================
-- Full-text search column for cv_embeddings
-- ============================================
ALTER TABLE cv_embeddings ADD COLUMN IF NOT EXISTS content_tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

CREATE INDEX IF NOT EXISTS idx_cv_embeddings_fts ON cv_embeddings USING GIN(content_tsv);

-- ============================================
-- Function: hybrid_search_cv_chunks
-- Combines vector similarity + BM25 full-text search
-- ============================================
CREATE OR REPLACE FUNCTION hybrid_search_cv_chunks(
    query_embedding VECTOR(768),
    query_text TEXT,
    match_threshold FLOAT DEFAULT 0.3,
    match_count INT DEFAULT 10,
    filter_cv_ids TEXT[] DEFAULT NULL,
    -- FASE 1: Metadata filters
    filter_speaks_french BOOLEAN DEFAULT NULL,
    filter_speaks_spanish BOOLEAN DEFAULT NULL,
    filter_has_mba BOOLEAN DEFAULT NULL,
    filter_has_phd BOOLEAN DEFAULT NULL,
    filter_has_aws_cert BOOLEAN DEFAULT NULL,
    filter_min_experience FLOAT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    cv_id TEXT,
    filename TEXT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT,
    text_rank FLOAT,
    combined_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH vector_results AS (
        SELECT
            ce.id,
            ce.cv_id,
            ce.filename,
            ce.content,
            ce.metadata,
            (1 - (ce.embedding <=> query_embedding)) AS similarity,
            ts_rank(ce.content_tsv, plainto_tsquery('english', query_text)) AS text_rank
        FROM cv_embeddings ce
        LEFT JOIN cv_metadata cm ON ce.cv_id = cm.cv_id
        WHERE 
            -- CV ID filter
            (filter_cv_ids IS NULL OR ce.cv_id = ANY(filter_cv_ids))
            -- Vector similarity threshold
            AND (1 - (ce.embedding <=> query_embedding)) > match_threshold
            -- FASE 1: Metadata filters
            AND (filter_speaks_french IS NULL OR cm.speaks_french = filter_speaks_french)
            AND (filter_speaks_spanish IS NULL OR cm.speaks_spanish = filter_speaks_spanish)
            AND (filter_has_mba IS NULL OR cm.has_mba = filter_has_mba)
            AND (filter_has_phd IS NULL OR cm.has_phd = filter_has_phd)
            AND (filter_has_aws_cert IS NULL OR cm.has_aws_cert = filter_has_aws_cert)
            AND (filter_min_experience IS NULL OR cm.total_experience_years >= filter_min_experience)
    )
    SELECT
        vr.id,
        vr.cv_id,
        vr.filename,
        vr.content,
        vr.metadata,
        vr.similarity::FLOAT,
        vr.text_rank::FLOAT,
        -- RRF-style combination: weighted average
        ((0.7 * vr.similarity) + (0.3 * COALESCE(vr.text_rank, 0)))::FLOAT AS combined_score
    FROM vector_results vr
    ORDER BY combined_score DESC
    LIMIT match_count;
END;
$$;

-- ============================================
-- Function: search_by_metadata
-- Direct metadata-based search for FASE 1 queries
-- ============================================
CREATE OR REPLACE FUNCTION search_by_metadata(
    filter_cv_ids TEXT[] DEFAULT NULL,
    filter_speaks_french BOOLEAN DEFAULT NULL,
    filter_speaks_spanish BOOLEAN DEFAULT NULL,
    filter_speaks_german BOOLEAN DEFAULT NULL,
    filter_has_mba BOOLEAN DEFAULT NULL,
    filter_has_phd BOOLEAN DEFAULT NULL,
    filter_has_aws_cert BOOLEAN DEFAULT NULL,
    filter_has_azure_cert BOOLEAN DEFAULT NULL,
    filter_has_pmp BOOLEAN DEFAULT NULL,
    filter_min_experience FLOAT DEFAULT NULL,
    filter_max_experience FLOAT DEFAULT NULL,
    filter_seniority TEXT DEFAULT NULL,
    result_limit INT DEFAULT 20
)
RETURNS TABLE (
    cv_id TEXT,
    candidate_name TEXT,
    total_experience_years FLOAT,
    current_role TEXT,
    seniority_level TEXT,
    languages_json JSONB,
    certifications_json JSONB,
    match_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        cm.cv_id,
        cm.candidate_name,
        cm.total_experience_years,
        cm.current_role,
        cm.seniority_level,
        cm.languages_json,
        cm.certifications_json,
        -- Calculate match score based on how many filters matched
        (
            CASE WHEN filter_speaks_french IS NOT NULL AND cm.speaks_french = filter_speaks_french THEN 20 ELSE 0 END +
            CASE WHEN filter_speaks_spanish IS NOT NULL AND cm.speaks_spanish = filter_speaks_spanish THEN 20 ELSE 0 END +
            CASE WHEN filter_has_mba IS NOT NULL AND cm.has_mba = filter_has_mba THEN 20 ELSE 0 END +
            CASE WHEN filter_has_aws_cert IS NOT NULL AND cm.has_aws_cert = filter_has_aws_cert THEN 20 ELSE 0 END +
            CASE WHEN filter_min_experience IS NOT NULL AND cm.total_experience_years >= filter_min_experience THEN 20 ELSE 0 END
        )::FLOAT AS match_score
    FROM cv_metadata cm
    WHERE
        (filter_cv_ids IS NULL OR cm.cv_id = ANY(filter_cv_ids))
        AND (filter_speaks_french IS NULL OR cm.speaks_french = filter_speaks_french)
        AND (filter_speaks_spanish IS NULL OR cm.speaks_spanish = filter_speaks_spanish)
        AND (filter_speaks_german IS NULL OR cm.speaks_german = filter_speaks_german)
        AND (filter_has_mba IS NULL OR cm.has_mba = filter_has_mba)
        AND (filter_has_phd IS NULL OR cm.has_phd = filter_has_phd)
        AND (filter_has_aws_cert IS NULL OR cm.has_aws_cert = filter_has_aws_cert)
        AND (filter_has_azure_cert IS NULL OR cm.has_azure_cert = filter_has_azure_cert)
        AND (filter_has_pmp IS NULL OR cm.has_pmp = filter_has_pmp)
        AND (filter_min_experience IS NULL OR cm.total_experience_years >= filter_min_experience)
        AND (filter_max_experience IS NULL OR cm.total_experience_years <= filter_max_experience)
        AND (filter_seniority IS NULL OR cm.seniority_level = filter_seniority)
    ORDER BY match_score DESC, cm.total_experience_years DESC
    LIMIT result_limit;
END;
$$;

-- ============================================
-- Function: upsert_cv_metadata
-- Insert or update CV metadata
-- ============================================
CREATE OR REPLACE FUNCTION upsert_cv_metadata(
    p_cv_id TEXT,
    p_candidate_name TEXT,
    p_metadata JSONB
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO cv_metadata (
        cv_id,
        candidate_name,
        total_experience_years,
        current_role,
        current_company,
        seniority_level,
        position_count,
        job_hopping_score,
        avg_tenure_years,
        employment_gaps_count,
        education_level,
        education_field,
        has_mba,
        has_phd,
        speaks_english,
        speaks_french,
        speaks_spanish,
        speaks_german,
        speaks_chinese,
        has_aws_cert,
        has_azure_cert,
        has_gcp_cert,
        has_pmp,
        has_cbap,
        has_scrum,
        languages_json,
        certifications_json,
        education_json,
        skills_json
    ) VALUES (
        p_cv_id,
        p_candidate_name,
        COALESCE((p_metadata->>'total_experience_years')::FLOAT, 0),
        p_metadata->>'current_role',
        p_metadata->>'current_company',
        p_metadata->>'seniority_level',
        COALESCE((p_metadata->>'position_count')::INTEGER, 0),
        COALESCE((p_metadata->>'job_hopping_score')::FLOAT, 0),
        COALESCE((p_metadata->>'avg_tenure_years')::FLOAT, 0),
        COALESCE((p_metadata->>'employment_gaps_count')::INTEGER, 0),
        p_metadata->>'education_level',
        p_metadata->>'education_field',
        COALESCE((p_metadata->>'has_mba')::BOOLEAN, FALSE),
        COALESCE((p_metadata->>'has_phd')::BOOLEAN, FALSE),
        COALESCE((p_metadata->>'speaks_english')::BOOLEAN, FALSE),
        COALESCE((p_metadata->>'speaks_french')::BOOLEAN, FALSE),
        COALESCE((p_metadata->>'speaks_spanish')::BOOLEAN, FALSE),
        COALESCE((p_metadata->>'speaks_german')::BOOLEAN, FALSE),
        COALESCE((p_metadata->>'speaks_chinese')::BOOLEAN, FALSE),
        COALESCE((p_metadata->>'has_aws_cert')::BOOLEAN, FALSE),
        COALESCE((p_metadata->>'has_azure_cert')::BOOLEAN, FALSE),
        COALESCE((p_metadata->>'has_gcp_cert')::BOOLEAN, FALSE),
        COALESCE((p_metadata->>'has_pmp')::BOOLEAN, FALSE),
        COALESCE((p_metadata->>'has_cbap')::BOOLEAN, FALSE),
        COALESCE((p_metadata->>'has_scrum')::BOOLEAN, FALSE),
        COALESCE(p_metadata->'languages', '[]'::jsonb),
        COALESCE(p_metadata->'certifications', '[]'::jsonb),
        COALESCE(p_metadata->'education_entries', '[]'::jsonb),
        COALESCE(p_metadata->'skills_with_levels', '[]'::jsonb)
    )
    ON CONFLICT (cv_id) DO UPDATE SET
        candidate_name = EXCLUDED.candidate_name,
        total_experience_years = EXCLUDED.total_experience_years,
        current_role = EXCLUDED.current_role,
        current_company = EXCLUDED.current_company,
        seniority_level = EXCLUDED.seniority_level,
        position_count = EXCLUDED.position_count,
        job_hopping_score = EXCLUDED.job_hopping_score,
        avg_tenure_years = EXCLUDED.avg_tenure_years,
        employment_gaps_count = EXCLUDED.employment_gaps_count,
        education_level = EXCLUDED.education_level,
        education_field = EXCLUDED.education_field,
        has_mba = EXCLUDED.has_mba,
        has_phd = EXCLUDED.has_phd,
        speaks_english = EXCLUDED.speaks_english,
        speaks_french = EXCLUDED.speaks_french,
        speaks_spanish = EXCLUDED.speaks_spanish,
        speaks_german = EXCLUDED.speaks_german,
        speaks_chinese = EXCLUDED.speaks_chinese,
        has_aws_cert = EXCLUDED.has_aws_cert,
        has_azure_cert = EXCLUDED.has_azure_cert,
        has_gcp_cert = EXCLUDED.has_gcp_cert,
        has_pmp = EXCLUDED.has_pmp,
        has_cbap = EXCLUDED.has_cbap,
        has_scrum = EXCLUDED.has_scrum,
        languages_json = EXCLUDED.languages_json,
        certifications_json = EXCLUDED.certifications_json,
        education_json = EXCLUDED.education_json,
        skills_json = EXCLUDED.skills_json,
        updated_at = NOW();
END;
$$;

-- ============================================
-- Grants
-- ============================================
GRANT ALL ON cv_metadata TO service_role;
GRANT ALL ON cv_skills TO service_role;
GRANT ALL ON cv_languages TO service_role;
GRANT ALL ON cv_certifications TO service_role;
GRANT EXECUTE ON FUNCTION hybrid_search_cv_chunks TO service_role;
GRANT EXECUTE ON FUNCTION search_by_metadata TO service_role;
GRANT EXECUTE ON FUNCTION upsert_cv_metadata TO service_role;
