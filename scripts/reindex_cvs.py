#!/usr/bin/env python
"""
Script to re-index all CVs with the new SmartChunkingService.

This script will:
1. Find all PDF files in the storage directory
2. Clear the existing vector store
3. Re-process each PDF with SmartChunkingService
4. Create new embeddings with enriched metadata

Usage:
    cd backend
    python ../scripts/reindex_cvs.py

The script will prompt for confirmation before clearing existing data.
"""
import sys
import os
import asyncio
import logging
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import after path setup
import pdfplumber
from app.services.smart_chunking_service import SmartChunkingService
from app.providers.local.vector_store import SimpleVectorStore
from app.providers.local.embeddings import LocalEmbedder


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF file."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text_parts = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n\n".join(text_parts)
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {e}")
        return ""


async def reindex_all_cvs():
    """Re-index all CVs with SmartChunkingService."""
    
    # Find storage directory
    storage_dir = backend_path.parent / "storage"
    if not storage_dir.exists():
        logger.error(f"Storage directory not found: {storage_dir}")
        return
    
    # Find all PDF files
    pdf_files = list(storage_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {storage_dir}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files in {storage_dir}")
    
    # Confirm before proceeding
    print("\n" + "="*60)
    print("CV RE-INDEXING WITH SMART CHUNKING")
    print("="*60)
    print(f"\nThis will:")
    print(f"  1. Clear all existing embeddings")
    print(f"  2. Re-process {len(pdf_files)} PDFs with SmartChunkingService")
    print(f"  3. Create new embeddings with enriched metadata")
    print(f"\nPDF files to process:")
    for pdf in pdf_files[:10]:
        print(f"  - {pdf.name}")
    if len(pdf_files) > 10:
        print(f"  ... and {len(pdf_files) - 10} more")
    
    response = input("\nProceed? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Aborted.")
        return
    
    # Initialize services
    logger.info("Initializing services...")
    chunking_service = SmartChunkingService()
    vector_store = SimpleVectorStore()
    embedder = LocalEmbedder()
    
    # Clear existing data
    logger.info("Clearing existing vector store...")
    await vector_store.delete_all_cvs()
    
    # Process each PDF
    success_count = 0
    error_count = 0
    
    for i, pdf_path in enumerate(pdf_files, 1):
        logger.info(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
        
        try:
            # Extract CV ID from filename (format: cv_xxxxxxxx.pdf)
            cv_id = pdf_path.stem  # e.g., "cv_096e7947"
            
            # Extract text
            text = extract_text_from_pdf(pdf_path)
            if not text:
                logger.warning(f"  No text extracted from {pdf_path.name}")
                error_count += 1
                continue
            
            logger.info(f"  Extracted {len(text)} characters")
            
            # Create chunks with SmartChunkingService
            # Note: we need a better filename for candidate name extraction
            # Try to find original filename from metadata if available
            chunks = chunking_service.chunk_cv(
                text=text,
                cv_id=cv_id,
                filename=pdf_path.name
            )
            
            logger.info(f"  Created {len(chunks)} smart chunks")
            
            # Log extracted metadata from first chunk (summary)
            if chunks:
                summary_chunk = chunks[0]
                meta = summary_chunk.get("metadata", {})
                logger.info(f"  Candidate: {meta.get('candidate_name', 'Unknown')}")
                logger.info(f"  Current Role: {meta.get('current_role', 'Unknown')}")
                logger.info(f"  Experience: {meta.get('total_experience_years', 0)} years")
            
            # Create embeddings
            contents = [chunk["content"] for chunk in chunks]
            embedding_result = await embedder.embed_documents(contents)
            
            # Store in vector store
            await vector_store.add_documents(chunks, embedding_result.embeddings)
            
            logger.info(f"  ✓ Indexed successfully")
            success_count += 1
            
        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
            error_count += 1
    
    # Summary
    print("\n" + "="*60)
    print("RE-INDEXING COMPLETE")
    print("="*60)
    print(f"\nResults:")
    print(f"  ✓ Successfully indexed: {success_count}")
    print(f"  ✗ Errors: {error_count}")
    
    # Show vector store stats
    stats = await vector_store.get_stats()
    print(f"\nVector Store Stats:")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Total CVs: {stats['total_cvs']}")
    print(f"  Storage: {stats['persist_dir']}")


if __name__ == "__main__":
    asyncio.run(reindex_all_cvs())
