-- ============================================
-- UPDATE MIGRATION - Add Pipeline Steps Support
-- Run this if you already have tables created with 003_create_session_tables.sql
-- ============================================

-- Add pipeline_steps and structured_output columns to session_messages if they don't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'session_messages' AND column_name = 'pipeline_steps'
    ) THEN
        ALTER TABLE session_messages ADD COLUMN pipeline_steps JSONB DEFAULT '[]'::jsonb;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'session_messages' AND column_name = 'structured_output'
    ) THEN
        ALTER TABLE session_messages ADD COLUMN structured_output JSONB DEFAULT NULL;
    END IF;
END $$;

-- Update embedding dimension from 384 to 768 if needed
-- WARNING: This will delete existing embeddings!
-- Only run if you're migrating from all-MiniLM-L6-v2 to nomic-embed
DO $$ 
BEGIN
    -- Check current dimension
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'cv_embeddings' 
        AND column_name = 'embedding'
        AND udt_name = 'vector'
    ) THEN
        -- Drop and recreate with new dimension
        -- This will CASCADE delete all existing embeddings
        ALTER TABLE cv_embeddings DROP COLUMN embedding;
        ALTER TABLE cv_embeddings ADD COLUMN embedding vector(768);
        
        -- Recreate the match function with correct dimension
        DROP FUNCTION IF EXISTS match_cv_embeddings(vector, INT, FLOAT);
        
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
        AS $func$
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
        $func$;
        
        RAISE NOTICE 'Updated embedding dimensions to 768. All existing embeddings were deleted.';
    END IF;
END $$;
