"""
Hybrid Search Service - Combines BM25 (lexical) with Vector (semantic) search.

V8 Feature: Better retrieval quality by combining exact term matching with semantic understanding.

How it works:
1. Run BM25 search for exact term matches (names, technologies, companies)
2. Run Vector search for semantic similarity (concepts, context)
3. Fuse results using Reciprocal Rank Fusion (RRF)
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.services.bm25_service import BM25Result, get_bm25_service

logger = logging.getLogger(__name__)

# RRF constant (standard value)
RRF_K = 60


@dataclass
class HybridSearchResult:
    """Result from hybrid search."""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    final_score: float
    bm25_score: Optional[float] = None
    vector_score: Optional[float] = None
    bm25_rank: Optional[int] = None
    vector_rank: Optional[int] = None


@dataclass
class HybridSearchResponse:
    """Complete response from hybrid search."""
    results: List[HybridSearchResult]
    bm25_count: int
    vector_count: int
    fused_count: int
    strategy: str


def reciprocal_rank_fusion(
    rankings: List[List[Tuple[str, float]]],
    k: int = RRF_K
) -> List[Tuple[str, float]]:
    """Apply Reciprocal Rank Fusion to combine multiple rankings.
    
    RRF score = sum over rankings of: 1 / (k + rank)
    
    Args:
        rankings: List of rankings, each is [(doc_id, score), ...]
        k: RRF constant (default 60)
        
    Returns:
        Fused ranking as [(doc_id, rrf_score), ...] sorted by score desc
    """
    rrf_scores: Dict[str, float] = {}
    
    for ranking in rankings:
        for rank, (doc_id, _) in enumerate(ranking, start=1):
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0.0
            rrf_scores[doc_id] += 1.0 / (k + rank)
    
    # Sort by RRF score
    sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_results


class HybridSearchService:
    """Service for hybrid BM25 + Vector search."""
    
    def __init__(self):
        self._bm25_service = get_bm25_service()
        
        # Weight configuration (can be tuned)
        self.bm25_weight = 0.3  # Weight for BM25 in final score
        self.vector_weight = 0.7  # Weight for vector in final score
    
    def build_bm25_index(
        self,
        session_id: str,
        chunks: List[Dict[str, Any]],
        force_rebuild: bool = False
    ) -> bool:
        """Build BM25 index for a session."""
        return self._bm25_service.build_index(session_id, chunks, force_rebuild)
    
    def search(
        self,
        query: str,
        vector_results: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        k: int = 15,
        use_rrf: bool = True,
        bm25_boost_terms: Optional[List[str]] = None
    ) -> HybridSearchResponse:
        """Perform hybrid search combining BM25 and vector results.
        
        Args:
            query: Search query
            vector_results: Results from vector search (list of dicts with 'id', 'content', 'metadata', 'score')
            session_id: Session ID for BM25 index
            k: Number of results to return
            use_rrf: Use Reciprocal Rank Fusion (True) or weighted score (False)
            bm25_boost_terms: Optional terms to boost in BM25 search
            
        Returns:
            HybridSearchResponse with fused results
        """
        # Prepare vector ranking
        vector_ranking: List[Tuple[str, float]] = []
        vector_docs: Dict[str, Dict[str, Any]] = {}
        
        for i, doc in enumerate(vector_results):
            doc_id = doc.get('id') or doc.get('metadata', {}).get('chunk_id', str(i))
            score = doc.get('score', doc.get('similarity', 0.0))
            vector_ranking.append((doc_id, score))
            vector_docs[doc_id] = doc
        
        # Run BM25 search if available
        bm25_ranking: List[Tuple[str, float]] = []
        bm25_docs: Dict[str, BM25Result] = {}
        
        if self._bm25_service.is_available and session_id:
            # Enhance query with boost terms
            search_query = query
            if bm25_boost_terms:
                search_query += " " + " ".join(bm25_boost_terms)
            
            bm25_results = self._bm25_service.search(
                session_id=session_id,
                query=search_query,
                k=k * 2  # Get more for fusion
            )
            
            for result in bm25_results:
                bm25_ranking.append((result.chunk_id, result.score))
                bm25_docs[result.chunk_id] = result
        
        # Decide fusion strategy
        if not bm25_ranking:
            # No BM25 results, use vector only
            strategy = "vector_only"
            final_results = self._vector_only_results(vector_results, k)
        elif not vector_ranking:
            # No vector results, use BM25 only
            strategy = "bm25_only"
            final_results = self._bm25_only_results(bm25_docs, bm25_ranking, k)
        elif use_rrf:
            # Use RRF fusion
            strategy = "rrf_fusion"
            final_results = self._rrf_fusion(
                vector_ranking, vector_docs,
                bm25_ranking, bm25_docs,
                k
            )
        else:
            # Use weighted score fusion
            strategy = "weighted_fusion"
            final_results = self._weighted_fusion(
                vector_ranking, vector_docs,
                bm25_ranking, bm25_docs,
                k
            )
        
        logger.info(
            f"[HYBRID] Strategy={strategy}, BM25={len(bm25_ranking)}, "
            f"Vector={len(vector_ranking)}, Final={len(final_results)}"
        )
        
        return HybridSearchResponse(
            results=final_results,
            bm25_count=len(bm25_ranking),
            vector_count=len(vector_ranking),
            fused_count=len(final_results),
            strategy=strategy
        )
    
    def _vector_only_results(
        self,
        vector_results: List[Dict[str, Any]],
        k: int
    ) -> List[HybridSearchResult]:
        """Convert vector results to hybrid results."""
        results = []
        for i, doc in enumerate(vector_results[:k]):
            doc_id = doc.get('id') or doc.get('metadata', {}).get('chunk_id', str(i))
            results.append(HybridSearchResult(
                chunk_id=doc_id,
                content=doc.get('content', ''),
                metadata=doc.get('metadata', {}),
                final_score=doc.get('score', doc.get('similarity', 0.0)),
                vector_score=doc.get('score', doc.get('similarity', 0.0)),
                vector_rank=i + 1
            ))
        return results
    
    def _bm25_only_results(
        self,
        bm25_docs: Dict[str, BM25Result],
        bm25_ranking: List[Tuple[str, float]],
        k: int
    ) -> List[HybridSearchResult]:
        """Convert BM25 results to hybrid results."""
        results = []
        for rank, (doc_id, score) in enumerate(bm25_ranking[:k], start=1):
            doc = bm25_docs[doc_id]
            results.append(HybridSearchResult(
                chunk_id=doc_id,
                content=doc.content,
                metadata=doc.metadata,
                final_score=score,
                bm25_score=score,
                bm25_rank=rank
            ))
        return results
    
    def _rrf_fusion(
        self,
        vector_ranking: List[Tuple[str, float]],
        vector_docs: Dict[str, Dict[str, Any]],
        bm25_ranking: List[Tuple[str, float]],
        bm25_docs: Dict[str, BM25Result],
        k: int
    ) -> List[HybridSearchResult]:
        """Fuse results using Reciprocal Rank Fusion."""
        # Apply RRF
        fused_ranking = reciprocal_rank_fusion([vector_ranking, bm25_ranking])
        
        # Build results
        results = []
        vector_ranks = {doc_id: rank for rank, (doc_id, _) in enumerate(vector_ranking, start=1)}
        bm25_ranks = {doc_id: rank for rank, (doc_id, _) in enumerate(bm25_ranking, start=1)}
        
        for doc_id, rrf_score in fused_ranking[:k]:
            # Get document data from either source
            if doc_id in vector_docs:
                doc = vector_docs[doc_id]
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
                vector_score = doc.get('score', doc.get('similarity'))
            elif doc_id in bm25_docs:
                doc = bm25_docs[doc_id]
                content = doc.content
                metadata = doc.metadata
                vector_score = None
            else:
                continue
            
            bm25_score = bm25_docs[doc_id].score if doc_id in bm25_docs else None
            
            results.append(HybridSearchResult(
                chunk_id=doc_id,
                content=content,
                metadata=metadata,
                final_score=rrf_score,
                bm25_score=bm25_score,
                vector_score=vector_score,
                bm25_rank=bm25_ranks.get(doc_id),
                vector_rank=vector_ranks.get(doc_id)
            ))
        
        return results
    
    def _weighted_fusion(
        self,
        vector_ranking: List[Tuple[str, float]],
        vector_docs: Dict[str, Dict[str, Any]],
        bm25_ranking: List[Tuple[str, float]],
        bm25_docs: Dict[str, BM25Result],
        k: int
    ) -> List[HybridSearchResult]:
        """Fuse results using weighted scores."""
        # Normalize scores
        max_vector = max(s for _, s in vector_ranking) if vector_ranking else 1.0
        max_bm25 = max(s for _, s in bm25_ranking) if bm25_ranking else 1.0
        
        vector_scores = {doc_id: score / max_vector for doc_id, score in vector_ranking}
        bm25_scores = {doc_id: score / max_bm25 for doc_id, score in bm25_ranking}
        
        # Combine all documents
        all_doc_ids = set(vector_scores.keys()) | set(bm25_scores.keys())
        
        # Calculate weighted scores
        weighted_results = []
        for doc_id in all_doc_ids:
            v_score = vector_scores.get(doc_id, 0.0)
            b_score = bm25_scores.get(doc_id, 0.0)
            final_score = self.vector_weight * v_score + self.bm25_weight * b_score
            weighted_results.append((doc_id, final_score, v_score, b_score))
        
        # Sort by final score
        weighted_results.sort(key=lambda x: x[1], reverse=True)
        
        # Build results
        vector_ranks = {doc_id: rank for rank, (doc_id, _) in enumerate(vector_ranking, start=1)}
        bm25_ranks = {doc_id: rank for rank, (doc_id, _) in enumerate(bm25_ranking, start=1)}
        
        results = []
        for doc_id, final_score, _v_score, _b_score in weighted_results[:k]:
            if doc_id in vector_docs:
                doc = vector_docs[doc_id]
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
            elif doc_id in bm25_docs:
                doc = bm25_docs[doc_id]
                content = doc.content
                metadata = doc.metadata
            else:
                continue
            
            results.append(HybridSearchResult(
                chunk_id=doc_id,
                content=content,
                metadata=metadata,
                final_score=final_score,
                bm25_score=bm25_scores.get(doc_id),
                vector_score=vector_scores.get(doc_id),
                bm25_rank=bm25_ranks.get(doc_id),
                vector_rank=vector_ranks.get(doc_id)
            ))
        
        return results
    
    def clear_session_index(self, session_id: str):
        """Clear BM25 index for a session."""
        self._bm25_service.clear_index(session_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "bm25_available": self._bm25_service.is_available,
            "bm25_weight": self.bm25_weight,
            "vector_weight": self.vector_weight,
            **self._bm25_service.get_stats()
        }


# Singleton instance
_hybrid_service: Optional[HybridSearchService] = None


def get_hybrid_search_service() -> HybridSearchService:
    """Get singleton hybrid search service instance."""
    global _hybrid_service
    if _hybrid_service is None:
        _hybrid_service = HybridSearchService()
    return _hybrid_service
