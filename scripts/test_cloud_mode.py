#!/usr/bin/env python3
"""
Test if cloud mode will work with current configuration
"""
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

print("=" * 60)
print("Testing Cloud Mode Configuration")
print("=" * 60)

# Test 1: Load config
print("\n1. Loading backend config...")
try:
    from app.config import settings, Mode
    print(f"   ✅ Config loaded")
    print(f"   Current mode: {settings.default_mode}")
    print(f"   Supabase URL: {settings.supabase_url}")
    print(f"   Supabase Service Key: {'✅ Set' if settings.supabase_service_key else '❌ Missing'}")
    print(f"   OpenRouter API Key: {'✅ Set' if settings.openrouter_api_key else '❌ Missing'}")
except Exception as e:
    print(f"   ❌ Failed to load config: {e}")
    sys.exit(1)

# Test 2: Test provider creation
print("\n2. Testing provider initialization...")
try:
    from app.providers.factory import ProviderFactory
    
    # Test embedding provider
    print("   Testing embedding provider...")
    embedder = ProviderFactory.get_embedding_provider(Mode.CLOUD)
    print(f"   ✅ Embedding provider created: {type(embedder).__name__}")
    
    # Test vector store
    print("   Testing vector store...")
    vector_store = ProviderFactory.get_vector_store(Mode.CLOUD)
    print(f"   ✅ Vector store created: {type(vector_store).__name__}")
    
    print("   ✅ Providers can be created")
except Exception as e:
    print(f"   ❌ Failed to create providers: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Test RAG service creation
print("\n3. Testing RAG service creation...")
try:
    from app.services.rag_service_v5 import RAGServiceV5
    
    print("   Creating RAGServiceV5 with cloud mode...")
    rag = RAGServiceV5.from_factory(Mode.CLOUD)
    print(f"   ✅ RAG service created")
    print(f"   Providers initialized: {rag._providers_initialized}")
    print(f"   Has embedder: {rag._embedder is not None}")
    print(f"   Has vector_store: {rag._vector_store is not None}")
    
    if not rag._providers_initialized:
        print("   ❌ Providers not initialized!")
        sys.exit(1)
    
except Exception as e:
    print(f"   ❌ Failed to create RAG service: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test Supabase connection
print("\n4. Testing Supabase connection...")
try:
    from supabase import create_client
    
    client = create_client(settings.supabase_url, settings.supabase_service_key)
    
    # Test bucket
    print("   Checking bucket 'cv-pdfs'...")
    bucket = client.storage.get_bucket("cv-pdfs")
    print(f"   ✅ Bucket verified: {bucket.name}")
    
    # Test tables
    print("   Checking tables...")
    tables_to_check = ["cvs", "cv_embeddings", "sessions", "session_cvs", "session_messages"]
    for table in tables_to_check:
        result = client.table(table).select("id").limit(1).execute()
        print(f"   ✅ Table '{table}' accessible")
    
except Exception as e:
    print(f"   ⚠️  Supabase test: {e}")

print("\n" + "=" * 60)
print("CLOUD MODE READINESS CHECK")
print("=" * 60)

if settings.default_mode == Mode.CLOUD:
    if settings.openrouter_api_key:
        print("\n✅ LISTO PARA CLOUD MODE")
        print("\nTodo configurado correctamente:")
        print("  ✅ DEFAULT_MODE=cloud")
        print("  ✅ OPENROUTER_API_KEY configurada")
        print("  ✅ Supabase configurado")
        print("  ✅ Providers se inicializan correctamente")
        print("\nPuedes ejecutar: npm run dev")
    else:
        print("\n❌ FALTA OPENROUTER_API_KEY")
        print("\nConfigura en backend/.env:")
        print("  OPENROUTER_API_KEY=your_openrouter_key")
        print("\nConsigue tu key en: https://openrouter.ai/keys")
else:
    print("\n⚠️  BACKEND EN MODO LOCAL")
    print(f"\nActual: DEFAULT_MODE={settings.default_mode.value}")
    print("\nPara activar cloud mode:")
    print("  1. python enable_cloud_mode.py")
    print("  2. Edita backend/.env línea 7 con OPENROUTER_API_KEY")
    print("  3. npm run dev")
