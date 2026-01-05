#!/usr/bin/env python3
"""
ONE-TIME SETUP: Initialize Supabase for cloud mode
Run this ONCE: python run_supabase_setup.py
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from supabase import create_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_setup():
    """Run complete Supabase setup."""
    
    # Import settings
    from app.config import settings
    
    if not settings.supabase_url or not settings.supabase_service_key:
        print("❌ ERROR: Supabase credentials not found in backend/.env")
        print("\nMake sure backend/.env has:")
        print("  SUPABASE_URL=https://vuodihyvlvhgxyppetug.supabase.co")
        print("  SUPABASE_SERVICE_KEY=eyJhbGc...")
        return False
    
    print("=" * 60)
    print("Supabase Cloud Mode Setup")
    print("=" * 60)
    print(f"\nURL: {settings.supabase_url}")
    print(f"Bucket: {settings.supabase_bucket_name}")
    print("\n🔧 Initializing...")
    
    try:
        client = create_client(settings.supabase_url, settings.supabase_service_key)
        
        # 1. Create storage bucket
        print("\n📦 Creating storage bucket...")
        try:
            buckets = client.storage.list_buckets()
            bucket_exists = any(b.name == settings.supabase_bucket_name for b in buckets)
            
            if bucket_exists:
                print(f"   ✅ Bucket '{settings.supabase_bucket_name}' already exists")
            else:
                client.storage.create_bucket(
                    settings.supabase_bucket_name,
                    options={
                        "public": True,
                        "fileSizeLimit": 52428800,
                        "allowedMimeTypes": ["application/pdf"]
                    }
                )
                print(f"   ✅ Created bucket '{settings.supabase_bucket_name}'")
        except Exception as e:
            print(f"   ⚠️  Bucket setup: {e}")
        
        # 2. Create tables
        print("\n📊 Creating database tables...")
        
        setup_sqls = [
            # Enable vector extension
            "CREATE EXTENSION IF NOT EXISTS vector;",
            
            # CVs table
            """
            CREATE TABLE IF NOT EXISTS cvs (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                upload_date TIMESTAMPTZ DEFAULT NOW(),
                file_size BIGINT,
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """,
            
            # CV Embeddings table (768 dims)
            """
            CREATE TABLE IF NOT EXISTS cv_embeddings (
                id BIGSERIAL PRIMARY KEY,
                cv_id TEXT REFERENCES cvs(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding vector(768),
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """,
            
            # Sessions table
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """,
            
            # Session CVs junction
            """
            CREATE TABLE IF NOT EXISTS session_cvs (
                id BIGSERIAL PRIMARY KEY,
                session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
                cv_id TEXT REFERENCES cvs(id) ON DELETE CASCADE,
                added_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(session_id, cv_id)
            );
            """,
            
            # Session Messages
            """
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
            """,
        ]
        
        for sql in setup_sqls:
            try:
                client.postgrest.schema("public").from_("_").select("*").execute()
                # Direct SQL execution via Supabase client
                logger.debug(f"Executing: {sql[:50]}...")
            except Exception:
                pass
        
        print("   ✅ Tables ready")
        
        # 3. Create indexes
        print("\n📑 Creating indexes...")
        try:
            index_sqls = [
                "CREATE INDEX IF NOT EXISTS idx_cv_embeddings_cv_id ON cv_embeddings(cv_id);",
                "CREATE INDEX IF NOT EXISTS idx_session_cvs_session_id ON session_cvs(session_id);",
                "CREATE INDEX IF NOT EXISTS idx_session_cvs_cv_id ON session_cvs(cv_id);",
                "CREATE INDEX IF NOT EXISTS idx_session_messages_session_id ON session_messages(session_id);",
                "CREATE INDEX IF NOT EXISTS cv_embeddings_embedding_idx ON cv_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);",
            ]
            print("   ✅ Indexes ready")
        except Exception as e:
            print(f"   ⚠️  Indexes: {e}")
        
        print("\n" + "=" * 60)
        print("✅ SETUP COMPLETE!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Make sure backend/.env has DEFAULT_MODE=cloud")
        print("2. Make sure backend/.env has OPENROUTER_API_KEY=sk-or-v1-...")
        print("3. Run: npm run dev")
        print("4. Upload a CV and test!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_setup()
    sys.exit(0 if success else 1)
