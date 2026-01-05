# Supabase Cloud Mode Setup Guide

This guide will help you configure Supabase for the CV Screener RAG system cloud mode.

## Prerequisites

- A Supabase account (free tier works)
- OpenRouter API key for embeddings and LLM

## Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Click **New Project**
3. Fill in:
   - **Name**: cv-screener-rag (or your choice)
   - **Database Password**: Generate a strong password (save it!)
   - **Region**: Choose closest to your users
4. Click **Create new project** (takes ~2 minutes)

## Step 2: Get API Credentials

1. In your project dashboard, go to **Settings** → **API**
2. Copy these values:
   - **Project URL**: `your_supabase_project_url`
   - **Service Role Key** (not anon key!): `your_service_role_key` (very long token)

## Step 3: Run Database Migrations

### Option A: Run Complete Migration (New Database)

1. In Supabase dashboard, go to **SQL Editor**
2. Click **New Query**
3. Copy and paste `backend/migrations/003_create_session_tables.sql`
4. Click **Run** (bottom right)
5. Verify no errors appear

### Option B: Update Existing Database (Already Migrated)

If you already ran the old migration with 384-dimension vectors:

1. In Supabase SQL Editor, run `backend/migrations/004_update_for_pipeline_steps.sql`
2. **WARNING**: This will delete existing embeddings due to dimension change

## Step 4: Create Storage Bucket

1. In Supabase dashboard, go to **Storage**
2. Click **New bucket**
3. Fill in:
   - **Name**: `cv-pdfs`
   - **Public bucket**: ✅ Yes (required for PDF downloads)
4. Click **Create bucket**

### Set Storage Policies

Run this SQL in **SQL Editor**:

```sql
-- Allow public read access to PDFs
CREATE POLICY "Allow public read" ON storage.objects
FOR SELECT USING (bucket_id = 'cv-pdfs');

-- Allow authenticated uploads (service key)
CREATE POLICY "Allow authenticated upload" ON storage.objects
FOR INSERT WITH CHECK (bucket_id = 'cv-pdfs');

-- Allow authenticated delete (service key)
CREATE POLICY "Allow authenticated delete" ON storage.objects
FOR DELETE USING (bucket_id = 'cv-pdfs');
```

## Step 5: Configure Backend

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set:
   ```env
   # Set mode to cloud
   DEFAULT_MODE=cloud

   # Supabase credentials
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_SERVICE_KEY=your_supabase_service_role_key
   SUPABASE_BUCKET_NAME=cv-pdfs

   # OpenRouter (required for cloud mode)
   OPENROUTER_API_KEY=your_openrouter_api_key
   ```

3. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

## Step 6: Verify Setup

### Test 1: Check Database Connection

```bash
cd backend
python -c "
from app.providers.cloud.vector_store import get_supabase_client
client = get_supabase_client()
print('✅ Supabase connected!')
print('Tables:', client.table('sessions').select('id', count='exact').execute())
"
```

### Test 2: Start Backend

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/docs to see API docs.

### Test 3: Complete Workflow

1. **Create Session**:
   ```bash
   curl -X POST "http://localhost:8000/api/sessions?mode=cloud" \
     -H "Content-Type: application/json" \
     -d '{"name": "Test Session", "description": "Testing Supabase"}'
   ```
   → Save the `id` returned

2. **Upload CV**:
   ```bash
   curl -X POST "http://localhost:8000/api/sessions/SESSION_ID/cvs?mode=cloud" \
     -F "files=@path/to/test.pdf"
   ```
   → Wait for processing to complete

3. **Query Chat**:
   ```bash
   curl -X POST "http://localhost:8000/api/sessions/SESSION_ID/chat?mode=cloud" \
     -H "Content-Type: application/json" \
     -d '{"message": "What skills does this candidate have?"}'
   ```

4. **Verify in Supabase**:
   - Go to **Table Editor** → `cvs` (should have 1 row)
   - Go to **Table Editor** → `cv_embeddings` (should have N chunks)
   - Go to **Storage** → `cv-pdfs` (should have PDF file)

## Step 7: Frontend Configuration

1. Edit `frontend/.env.production`:
   ```env
   VITE_API_BASE_URL=http://localhost:8000/api
   VITE_DEFAULT_MODE=cloud
   ```

2. Start frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. Test in UI:
   - Create new chat session
   - Upload CVs → should see progress
   - Ask questions → should get responses
   - Click PDF icon → should open PDF from Supabase

## Troubleshooting

### Error: "Supabase credentials not configured"

**Solution**: Check that `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are set in `.env`

### Error: "Failed to add embedding"

**Possible causes**:
1. **Wrong vector dimension**: Ensure migration used `vector(768)` not `vector(384)`
2. **Network timeout**: Check Supabase project status
3. **RLS policies too strict**: Ensure policies allow service key access

**Fix**:
```sql
-- Check current dimension
SELECT column_name, udt_name 
FROM information_schema.columns 
WHERE table_name = 'cv_embeddings' AND column_name = 'embedding';

-- If shows vector(384), run migration 004 to upgrade
```

### Error: "Bucket not found" or PDF upload fails

**Solution**:
1. Verify bucket exists in Supabase Storage dashboard
2. Verify bucket name matches `SUPABASE_BUCKET_NAME` in `.env`
3. Check bucket is public (required for downloads)

### PDFs not downloading

**Causes**:
1. Bucket not public
2. Storage policies not set
3. File didn't upload

**Fix**:
```sql
-- Check bucket configuration
SELECT * FROM storage.buckets WHERE name = 'cv-pdfs';

-- Verify file exists
SELECT * FROM storage.objects WHERE bucket_id = 'cv-pdfs';
```

## Performance Optimization

### Add Vector Index (For Production)

After uploading CVs, add IVFFlat index for faster searches:

```sql
-- Create index (takes a few minutes with many embeddings)
CREATE INDEX IF NOT EXISTS cv_embeddings_embedding_idx 
ON cv_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### Connection Pooling

For high-traffic deployments, enable Supavisor connection pooling:
1. Go to **Database** → **Connection Pooling**
2. Enable **Transaction Mode**
3. Use pooler connection string in production

## Costs (Free Tier Limits)

- **Database**: 500 MB (plenty for thousands of CVs)
- **Storage**: 1 GB (enough for ~100-200 PDFs)
- **Bandwidth**: 5 GB/month

Upgrade to Pro ($25/month) when you exceed these limits.

## Migration from Local to Cloud

To migrate existing local data:

1. Export CVs from local ChromaDB
2. Switch mode to cloud in `.env`
3. Re-upload CVs through the UI
4. Verify all data migrated correctly

**Note**: Chat history does NOT migrate automatically. Sessions are mode-specific.

## Security Best Practices

1. ✅ **Never commit** `.env` to git
2. ✅ Use **service key** for backend, not anon key
3. ✅ Enable RLS policies on all tables
4. ✅ Set bucket to public only if needed for downloads
5. ✅ Rotate keys periodically
6. ✅ Use environment-specific projects (dev/staging/prod)

## Support

- **Supabase Docs**: https://supabase.com/docs
- **OpenRouter Docs**: https://openrouter.ai/docs
- **Project Issues**: Check GitHub issues

---

**Setup complete!** Your CV Screener RAG system is now running in cloud mode with Supabase. 🚀
