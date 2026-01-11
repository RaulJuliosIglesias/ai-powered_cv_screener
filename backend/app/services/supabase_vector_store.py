"""
FASE 7: Supabase Vector Store Service

Provides vector storage and retrieval using Supabase pgvector.
This will be the PRIMARY source in V10.

Features:
- Vector similarity search with pgvector
- Hybrid search (vector + BM25 full-text)
- Metadata-based filtering (FASE 1 fields)
- Automatic metadata extraction and storage
"""

import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SupabaseSearchResult:
    """Result from Supabase vector search."""
    id: str
    cv_id: str
    filename: str
    content: str
    metadata: Dict[str, Any]
    similarity: float
    text_rank: float = 0.0
    combined_score: float = 0.0


class SupabaseVectorStore:
    """
    FASE 7: Vector store using Supabase pgvector.
    
    This service handles:
    - Storing CV chunks with embeddings
    - Storing structured metadata (FASE 1 fields)
    - Vector similarity search
    - Hybrid search (vector + full-text)
    - Metadata-filtered search
    """
    
    def __init__(self):
        """Initialize Supabase client."""
        self._client = None
        self._initialized = False
        
    def _get_client(self):
        """Lazy initialization of Supabase client."""
        if self._client is None:
            try:
                from supabase import create_client
                
                url = settings.SUPABASE_URL
                key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY
                
                if not url or not key:
                    logger.warning("[SUPABASE] Missing SUPABASE_URL or SUPABASE_KEY")
                    return None
                
                self._client = create_client(url, key)
                self._initialized = True
                logger.info("[SUPABASE] Client initialized successfully")
                
            except ImportError:
                logger.error("[SUPABASE] supabase-py not installed. Run: pip install supabase")
                return None
            except Exception as e:
                logger.error(f"[SUPABASE] Failed to initialize client: {e}")
                return None
        
        return self._client
    
    @property
    def is_available(self) -> bool:
        """Check if Supabase is available."""
        return self._get_client() is not None
    
    # =========================================================================
    # STORAGE METHODS
    # =========================================================================
    
    async def store_cv(
        self,
        cv_id: str,
        filename: str,
        chunks: List[Dict],
        embeddings: List[List[float]],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Store a complete CV with chunks, embeddings, and metadata.
        
        Args:
            cv_id: Unique CV identifier
            filename: Original filename
            chunks: List of chunk dictionaries with content
            embeddings: List of embedding vectors (one per chunk)
            metadata: Enriched metadata from FASE 1 extraction
            
        Returns:
            True if successful, False otherwise
        """
        client = self._get_client()
        if not client:
            return False
        
        try:
            # 1. Upsert CV record
            cv_data = {
                "id": cv_id,
                "filename": filename,
                "chunk_count": len(chunks),
                "metadata": json.dumps(metadata) if isinstance(metadata, dict) else metadata
            }
            
            client.table("cvs").upsert(cv_data).execute()
            logger.info(f"[SUPABASE] Stored CV: {cv_id}")
            
            # 2. Delete existing chunks for this CV (for re-indexing)
            client.table("cv_embeddings").delete().eq("cv_id", cv_id).execute()
            
            # 3. Insert chunks with embeddings
            chunk_records = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_meta = chunk.get("metadata", {})
                chunk_records.append({
                    "cv_id": cv_id,
                    "filename": filename,
                    "chunk_index": i,
                    "content": chunk.get("content", ""),
                    "embedding": embedding,
                    "metadata": json.dumps(chunk_meta) if isinstance(chunk_meta, dict) else chunk_meta
                })
            
            # Batch insert (Supabase handles this efficiently)
            if chunk_records:
                client.table("cv_embeddings").insert(chunk_records).execute()
                logger.info(f"[SUPABASE] Stored {len(chunk_records)} chunks for {cv_id}")
            
            # 4. Store structured metadata using RPC function
            await self._store_cv_metadata(cv_id, metadata)
            
            return True
            
        except Exception as e:
            logger.error(f"[SUPABASE] Failed to store CV {cv_id}: {e}")
            return False
    
    async def _store_cv_metadata(self, cv_id: str, metadata: Dict[str, Any]) -> bool:
        """Store structured FASE 1 metadata."""
        client = self._get_client()
        if not client:
            return False
        
        try:
            # Call the upsert_cv_metadata RPC function
            client.rpc("upsert_cv_metadata", {
                "p_cv_id": cv_id,
                "p_candidate_name": metadata.get("candidate_name", "Unknown"),
                "p_metadata": json.dumps(metadata)
            }).execute()
            
            logger.info(f"[SUPABASE] Stored metadata for {cv_id}")
            return True
            
        except Exception as e:
            logger.error(f"[SUPABASE] Failed to store metadata for {cv_id}: {e}")
            return False
    
    async def delete_cv(self, cv_id: str) -> bool:
        """Delete a CV and all its data."""
        client = self._get_client()
        if not client:
            return False
        
        try:
            result = client.rpc("delete_cv_by_id", {"target_cv_id": cv_id}).execute()
            logger.info(f"[SUPABASE] Deleted CV: {cv_id}")
            return True
        except Exception as e:
            logger.error(f"[SUPABASE] Failed to delete CV {cv_id}: {e}")
            return False
    
    # =========================================================================
    # SEARCH METHODS
    # =========================================================================
    
    async def search(
        self,
        embedding: List[float],
        k: int = 10,
        threshold: float = 0.3,
        cv_ids: Optional[List[str]] = None
    ) -> List[SupabaseSearchResult]:
        """
        Vector similarity search.
        
        Args:
            embedding: Query embedding vector
            k: Number of results to return
            threshold: Minimum similarity threshold
            cv_ids: Optional list of CV IDs to filter
            
        Returns:
            List of SupabaseSearchResult objects
        """
        client = self._get_client()
        if not client:
            return []
        
        try:
            if cv_ids:
                # Use filtered search
                result = client.rpc("match_cv_embeddings_filtered", {
                    "query_embedding": embedding,
                    "filter_cv_ids": cv_ids,
                    "match_count": k,
                    "match_threshold": threshold
                }).execute()
            else:
                # Use unfiltered search
                result = client.rpc("match_cv_embeddings", {
                    "query_embedding": embedding,
                    "match_count": k,
                    "match_threshold": threshold
                }).execute()
            
            results = []
            for row in result.data or []:
                results.append(SupabaseSearchResult(
                    id=row.get("id", ""),
                    cv_id=row.get("cv_id", ""),
                    filename=row.get("filename", ""),
                    content=row.get("content", ""),
                    metadata=row.get("metadata", {}),
                    similarity=row.get("similarity", 0.0)
                ))
            
            logger.info(f"[SUPABASE] Vector search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"[SUPABASE] Vector search failed: {e}")
            return []
    
    async def hybrid_search(
        self,
        embedding: List[float],
        query_text: str,
        k: int = 10,
        threshold: float = 0.3,
        cv_ids: Optional[List[str]] = None,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[SupabaseSearchResult]:
        """
        FASE 7: Hybrid search combining vector similarity + full-text search.
        
        Args:
            embedding: Query embedding vector
            query_text: Original query text for BM25
            k: Number of results
            threshold: Similarity threshold
            cv_ids: Optional CV ID filter
            metadata_filters: FASE 1 metadata filters (speaks_french, has_aws_cert, etc.)
            
        Returns:
            List of SupabaseSearchResult objects sorted by combined score
        """
        client = self._get_client()
        if not client:
            return []
        
        try:
            # Build RPC parameters
            params = {
                "query_embedding": embedding,
                "query_text": query_text,
                "match_threshold": threshold,
                "match_count": k,
                "filter_cv_ids": cv_ids
            }
            
            # Add FASE 1 metadata filters if provided
            if metadata_filters:
                if metadata_filters.get("speaks_french"):
                    params["filter_speaks_french"] = True
                if metadata_filters.get("speaks_spanish"):
                    params["filter_speaks_spanish"] = True
                if metadata_filters.get("has_mba"):
                    params["filter_has_mba"] = True
                if metadata_filters.get("has_phd"):
                    params["filter_has_phd"] = True
                if metadata_filters.get("has_aws_cert"):
                    params["filter_has_aws_cert"] = True
                if metadata_filters.get("min_experience"):
                    params["filter_min_experience"] = float(metadata_filters["min_experience"])
            
            result = client.rpc("hybrid_search_cv_chunks", params).execute()
            
            results = []
            for row in result.data or []:
                results.append(SupabaseSearchResult(
                    id=row.get("id", ""),
                    cv_id=row.get("cv_id", ""),
                    filename=row.get("filename", ""),
                    content=row.get("content", ""),
                    metadata=row.get("metadata", {}),
                    similarity=row.get("similarity", 0.0),
                    text_rank=row.get("text_rank", 0.0),
                    combined_score=row.get("combined_score", 0.0)
                ))
            
            logger.info(f"[SUPABASE] Hybrid search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"[SUPABASE] Hybrid search failed: {e}")
            return []
    
    async def search_by_metadata(
        self,
        cv_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        FASE 1: Direct metadata-based search.
        
        For queries like "who speaks French" or "AWS certified candidates".
        
        Args:
            cv_ids: Optional CV ID filter
            filters: Metadata filters (speaks_french, has_aws_cert, etc.)
            limit: Maximum results
            
        Returns:
            List of matching candidates with metadata
        """
        client = self._get_client()
        if not client:
            return []
        
        try:
            params = {
                "filter_cv_ids": cv_ids,
                "result_limit": limit
            }
            
            # Map filters to RPC parameters
            if filters:
                filter_mapping = {
                    "speaks_french": "filter_speaks_french",
                    "speaks_spanish": "filter_speaks_spanish",
                    "speaks_german": "filter_speaks_german",
                    "has_mba": "filter_has_mba",
                    "has_phd": "filter_has_phd",
                    "has_aws_cert": "filter_has_aws_cert",
                    "has_azure_cert": "filter_has_azure_cert",
                    "has_pmp": "filter_has_pmp",
                    "min_experience": "filter_min_experience",
                    "max_experience": "filter_max_experience",
                    "seniority_level": "filter_seniority"
                }
                
                for key, param_name in filter_mapping.items():
                    if key in filters and filters[key] is not None:
                        params[param_name] = filters[key]
            
            result = client.rpc("search_by_metadata", params).execute()
            
            logger.info(f"[SUPABASE] Metadata search returned {len(result.data or [])} results")
            return result.data or []
            
        except Exception as e:
            logger.error(f"[SUPABASE] Metadata search failed: {e}")
            return []
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    async def get_cv_stats(self) -> Dict[str, Any]:
        """Get statistics about indexed CVs."""
        client = self._get_client()
        if not client:
            return {}
        
        try:
            result = client.rpc("get_cv_stats").execute()
            if result.data:
                return result.data[0] if isinstance(result.data, list) else result.data
            return {}
        except Exception as e:
            logger.error(f"[SUPABASE] Failed to get CV stats: {e}")
            return {}
    
    async def get_all_cv_ids(self) -> List[str]:
        """Get all CV IDs in the database."""
        client = self._get_client()
        if not client:
            return []
        
        try:
            result = client.table("cvs").select("id").execute()
            return [row["id"] for row in result.data or []]
        except Exception as e:
            logger.error(f"[SUPABASE] Failed to get CV IDs: {e}")
            return []


# Singleton instance
_supabase_store: Optional[SupabaseVectorStore] = None


def get_supabase_vector_store() -> SupabaseVectorStore:
    """Get the singleton SupabaseVectorStore instance."""
    global _supabase_store
    if _supabase_store is None:
        _supabase_store = SupabaseVectorStore()
    return _supabase_store
