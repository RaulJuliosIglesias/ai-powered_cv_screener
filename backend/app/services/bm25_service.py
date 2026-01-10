"""
BM25 Service - Lexical search using BM25 algorithm.

V8 Feature: Combine with vector search for hybrid retrieval.
BM25 excels at exact term matching (names, technologies, companies).
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BM25Result:
    """Result from BM25 search."""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    score: float


@dataclass 
class BM25Index:
    """BM25 index for a collection of documents."""
    documents: List[Dict[str, Any]] = field(default_factory=list)
    doc_ids: List[str] = field(default_factory=list)
    _bm25: Any = None
    _tokenized_corpus: List[List[str]] = field(default_factory=list)
    
    def is_empty(self) -> bool:
        return len(self.documents) == 0


class BM25Service:
    """Service for BM25-based lexical search."""
    
    def __init__(self):
        self._indices: Dict[str, BM25Index] = {}  # session_id -> index
        self._bm25_available = False
        
        try:
            from rank_bm25 import BM25Okapi
            self._bm25_available = True
            logger.info("[BM25] rank-bm25 library available")
        except ImportError:
            logger.warning("[BM25] rank-bm25 not installed. BM25 search unavailable.")
    
    @property
    def is_available(self) -> bool:
        return self._bm25_available
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25.
        
        Simple tokenization that:
        - Lowercases
        - Splits on whitespace and punctuation
        - Removes very short tokens
        - Keeps meaningful terms
        """
        # Lowercase and clean
        text = text.lower()
        
        # Split on non-alphanumeric (keep numbers for years, versions, etc.)
        tokens = re.findall(r'\b[a-z0-9]+\b', text)
        
        # Filter very short tokens (except common tech terms)
        keep_short = {'ai', 'ml', 'ui', 'ux', 'qa', 'db', 'ci', 'cd', 'js', 'ts', 'go', 'c', 'r'}
        tokens = [t for t in tokens if len(t) > 2 or t in keep_short]
        
        return tokens
    
    def build_index(
        self, 
        session_id: str, 
        chunks: List[Dict[str, Any]],
        force_rebuild: bool = False
    ) -> bool:
        """Build BM25 index for a session's chunks.
        
        Args:
            session_id: Session identifier
            chunks: List of chunk dicts with 'content', 'metadata', and 'id'
            force_rebuild: Force rebuild even if index exists
            
        Returns:
            True if index was built successfully
        """
        if not self._bm25_available:
            return False
        
        # Check if we already have an index
        if session_id in self._indices and not force_rebuild:
            existing = self._indices[session_id]
            if len(existing.documents) == len(chunks):
                return True  # Index already exists
        
        from rank_bm25 import BM25Okapi
        
        # Tokenize all documents
        tokenized_corpus = []
        doc_ids = []
        documents = []
        
        for chunk in chunks:
            chunk_id = chunk.get('id') or chunk.get('metadata', {}).get('chunk_id', str(len(documents)))
            content = chunk.get('content', '')
            
            # Include metadata in searchable content for better matching
            metadata = chunk.get('metadata', {})
            searchable = content
            if metadata.get('candidate_name'):
                searchable += f" {metadata['candidate_name']}"
            if metadata.get('filename'):
                searchable += f" {metadata['filename']}"
            if metadata.get('skills'):
                if isinstance(metadata['skills'], list):
                    searchable += " " + " ".join(metadata['skills'])
            
            tokens = self._tokenize(searchable)
            
            if tokens:  # Only add if we have tokens
                tokenized_corpus.append(tokens)
                doc_ids.append(chunk_id)
                documents.append(chunk)
        
        if not tokenized_corpus:
            logger.warning(f"[BM25] No tokens to index for session {session_id}")
            return False
        
        # Build BM25 index
        bm25 = BM25Okapi(tokenized_corpus)
        
        self._indices[session_id] = BM25Index(
            documents=documents,
            doc_ids=doc_ids,
            _bm25=bm25,
            _tokenized_corpus=tokenized_corpus
        )
        
        logger.info(f"[BM25] Built index for session {session_id}: {len(documents)} documents")
        return True
    
    def search(
        self,
        session_id: str,
        query: str,
        k: int = 10,
        threshold: float = 0.0
    ) -> List[BM25Result]:
        """Search using BM25.
        
        Args:
            session_id: Session to search in
            query: Search query
            k: Number of results to return
            threshold: Minimum score threshold
            
        Returns:
            List of BM25Result sorted by score
        """
        if not self._bm25_available:
            return []
        
        index = self._indices.get(session_id)
        if not index or index.is_empty():
            logger.warning(f"[BM25] No index for session {session_id}")
            return []
        
        # Tokenize query
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        # Get BM25 scores
        scores = index._bm25.get_scores(query_tokens)
        
        # Get top-k results
        results = []
        scored_docs = list(zip(range(len(scores)), scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        for doc_idx, score in scored_docs[:k]:
            if score < threshold:
                continue
            
            doc = index.documents[doc_idx]
            results.append(BM25Result(
                chunk_id=index.doc_ids[doc_idx],
                content=doc.get('content', ''),
                metadata=doc.get('metadata', {}),
                score=float(score)
            ))
        
        return results
    
    def clear_index(self, session_id: str):
        """Clear index for a session."""
        if session_id in self._indices:
            del self._indices[session_id]
            logger.info(f"[BM25] Cleared index for session {session_id}")
    
    def clear_all(self):
        """Clear all indices."""
        self._indices.clear()
        logger.info("[BM25] Cleared all indices")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "available": self._bm25_available,
            "indexed_sessions": len(self._indices),
            "total_documents": sum(len(idx.documents) for idx in self._indices.values())
        }


# Singleton instance
_bm25_service: Optional[BM25Service] = None


def get_bm25_service() -> BM25Service:
    """Get singleton BM25 service instance."""
    global _bm25_service
    if _bm25_service is None:
        _bm25_service = BM25Service()
    return _bm25_service
