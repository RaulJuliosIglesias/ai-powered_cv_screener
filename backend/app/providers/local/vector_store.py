"""
Local Vector Store with JSON persistence.

This module provides persistent vector storage using JSON files with
cosine similarity search. Works without external dependencies.
"""
import json
import os
import math
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.providers.base import VectorStoreProvider, SearchResult
from app.config import settings

logger = logging.getLogger(__name__)


class SimpleVectorStore(VectorStoreProvider):
    """
    Simple vector store with JSON persistence.
    
    Features:
    - No external dependencies (pure Python)
    - JSON persistence to disk
    - Cosine similarity search
    - Metadata filtering support
    """
    
    def __init__(self):
        self._persist_dir = Path(settings.chroma_persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._storage_file = self._persist_dir / "vectors.json"
        self._documents: List[Dict[str, Any]] = []
        self._embeddings: List[List[float]] = []
        self._load()
        logger.info(f"SimpleVectorStore initialized. Documents: {len(self._documents)}")
    
    def _load(self):
        """Load data from disk."""
        if self._storage_file.exists():
            try:
                with open(self._storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._documents = data.get("documents", [])
                    self._embeddings = data.get("embeddings", [])
                logger.debug(f"Loaded {len(self._documents)} documents from disk")
            except Exception as e:
                logger.warning(f"Failed to load vector store: {e}")
                self._documents = []
                self._embeddings = []
    
    def _save(self):
        """Save data to disk."""
        try:
            with open(self._storage_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "documents": self._documents,
                    "embeddings": self._embeddings
                }, f, ensure_ascii=False)
            logger.debug(f"Saved {len(self._documents)} documents to disk")
        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        # Ensure both are flat lists of floats
        if isinstance(a[0], list):
            a = a[0]  # Flatten if nested
        if isinstance(b[0], list):
            b = b[0]  # Flatten if nested
        
        if len(a) != len(b):
            # Handle dimension mismatch by padding/truncating
            min_len = min(len(a), len(b))
            a = a[:min_len]
            b = b[:min_len]
        
        try:
            dot = sum(float(x) * float(y) for x, y in zip(a, b))
            norm_a = math.sqrt(sum(float(x) * float(x) for x in a))
            norm_b = math.sqrt(sum(float(x) * float(x) for x in b))
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)
        except (TypeError, ValueError) as e:
            logger.error(f"Error calculating similarity: {e}. Types: a[0]={type(a[0])}, b[0]={type(b[0])}")
            return 0.0
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        """Add documents with embeddings.
        
        Uses asyncio.to_thread() for disk I/O to avoid blocking the event loop.
        """
        if not documents:
            return
        
        # Build index of existing docs by ID for upsert
        existing_ids = {doc["id"]: i for i, doc in enumerate(self._documents)}
        
        for doc, emb in zip(documents, embeddings):
            doc_data = {
                "id": doc["id"],
                "cv_id": doc["cv_id"],
                "filename": doc["filename"],
                "content": doc["content"],
                "chunk_index": doc["chunk_index"],
                "metadata": doc.get("metadata", {})
            }
            
            if doc["id"] in existing_ids:
                # Update existing
                idx = existing_ids[doc["id"]]
                self._documents[idx] = doc_data
                self._embeddings[idx] = emb
            else:
                # Add new
                self._documents.append(doc_data)
                self._embeddings.append(emb)
        
        # Run save in thread pool to avoid blocking event loop
        await asyncio.to_thread(self._save)
        logger.info(f"Added/updated {len(documents)} documents. Total: {len(self._documents)}")
    
    async def search(
        self,
        embedding: List[float],
        k: int = 10,
        threshold: float = 0.3,
        cv_ids: Optional[List[str]] = None,
        diversify_by_cv: bool = True
    ) -> List[SearchResult]:
        """Search for similar documents.
        
        Args:
            embedding: Query embedding
            k: Max results to return
            threshold: Minimum similarity threshold
            cv_ids: Optional list of CV IDs to filter by
            diversify_by_cv: If True, return top chunk from each CV (better for ranking queries)
                           If False, return global top-k chunks (better for specific searches)
        """
        if not self._documents:
            logger.warning("Search on empty store")
            return []
        
        # Calculate similarities
        similarities = []
        for i, emb in enumerate(self._embeddings):
            doc = self._documents[i]
            
            # Filter by cv_ids if provided
            if cv_ids and doc["cv_id"] not in cv_ids:
                continue
            
            sim = self._cosine_similarity(embedding, emb)
            if sim >= threshold:
                similarities.append((i, sim, doc["cv_id"]))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Build results with diversification
        results = []
        if diversify_by_cv:
            # Get best chunk from each CV (ensures all CVs represented)
            seen_cvs = set()
            for idx, sim, cv_id in similarities:
                if cv_id not in seen_cvs:
                    doc = self._documents[idx]
                    results.append(SearchResult(
                        id=doc["id"],
                        cv_id=doc["cv_id"],
                        filename=doc["filename"],
                        content=doc["content"],
                        similarity=sim,
                        metadata=doc.get("metadata", {})
                    ))
                    seen_cvs.add(cv_id)
                    if len(results) >= k:
                        break
        else:
            # Traditional top-k (may have multiple chunks from same CV)
            for idx, sim, cv_id in similarities[:k]:
                doc = self._documents[idx]
                results.append(SearchResult(
                    id=doc["id"],
                    cv_id=doc["cv_id"],
                    filename=doc["filename"],
                    content=doc["content"],
                    similarity=sim,
                    metadata=doc.get("metadata", {})
                ))
        
        logger.debug(f"Search returned {len(results)} results (threshold={threshold}, diversify={diversify_by_cv})")
        return results
    
    async def delete_cv(self, cv_id: str) -> bool:
        """Delete all chunks for a CV."""
        try:
            indices_to_remove = [
                i for i, doc in enumerate(self._documents)
                if doc["cv_id"] == cv_id
            ]
            
            # Remove in reverse order to maintain indices
            for idx in reversed(indices_to_remove):
                del self._documents[idx]
                del self._embeddings[idx]
            
            self._save()
            logger.info(f"Deleted {len(indices_to_remove)} chunks for CV {cv_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete CV {cv_id}: {e}")
            return False
    
    async def delete_all_cvs(self) -> bool:
        """Delete all documents."""
        try:
            count = len(self._documents)
            self._documents = []
            self._embeddings = []
            self._save()
            logger.info(f"Deleted all {count} documents")
            return True
        except Exception as e:
            logger.error(f"Failed to delete all CVs: {e}")
            return False
    
    async def list_cvs(self) -> List[Dict[str, Any]]:
        """List all unique CVs with their chunk counts."""
        cvs = {}
        for doc in self._documents:
            cv_id = doc["cv_id"]
            if cv_id not in cvs:
                cvs[cv_id] = {
                    "id": cv_id,
                    "filename": doc["filename"],
                    "chunk_count": 0
                }
            cvs[cv_id]["chunk_count"] += 1
        return list(cvs.values())
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        cvs = await self.list_cvs()
        return {
            "total_chunks": len(self._documents),
            "total_cvs": len(cvs),
            "storage_type": "json",
            "persist_dir": str(self._persist_dir)
        }


# Alias for compatibility
ChromaVectorStore = SimpleVectorStore
