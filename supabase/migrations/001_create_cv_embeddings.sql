-- ============================================
-- ENABLE PGVECTOR EXTENSION
-- ============================================
create extension if not exists vector;

-- ============================================
-- CV EMBEDDINGS TABLE
-- ============================================
create table if not exists cv_embeddings (
  id uuid primary key default gen_random_uuid(),
  cv_id text not null,
  filename text not null,
  chunk_index integer not null,
  content text not null,
  embedding vector(768),                 -- 768 dimensions for nomic-embed
  metadata jsonb default '{}',
  created_at timestamptz default now(),
  
  -- Unique constraint to prevent duplicates
  unique(cv_id, chunk_index)
);

-- Index for fast vector similarity search
create index if not exists cv_embeddings_embedding_idx 
on cv_embeddings 
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

-- Index for filtering by cv_id
create index if not exists cv_embeddings_cv_id_idx on cv_embeddings(cv_id);

-- ============================================
-- CV METADATA TABLE (for listing)
-- ============================================
create table if not exists cvs (
  id text primary key,
  filename text not null,
  indexed_at timestamptz default now(),
  chunk_count integer default 0,
  metadata jsonb default '{}'
);

-- ============================================
-- VECTOR SEARCH FUNCTION
-- ============================================
create or replace function match_cv_embeddings(
  query_embedding vector(768),
  match_count int default 5,
  match_threshold float default 0.3
)
returns table (
  id uuid,
  cv_id text,
  filename text,
  chunk_index integer,
  content text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    cv_embeddings.id,
    cv_embeddings.cv_id,
    cv_embeddings.filename,
    cv_embeddings.chunk_index,
    cv_embeddings.content,
    cv_embeddings.metadata,
    1 - (cv_embeddings.embedding <=> query_embedding) as similarity
  from cv_embeddings
  where 1 - (cv_embeddings.embedding <=> query_embedding) > match_threshold
  order by cv_embeddings.embedding <=> query_embedding
  limit match_count;
$$;

-- ============================================
-- DELETE CV FUNCTION
-- ============================================
create or replace function delete_cv(target_cv_id text)
returns void
language sql
as $$
  delete from cv_embeddings where cv_id = target_cv_id;
  delete from cvs where id = target_cv_id;
$$;
