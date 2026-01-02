import json
import os
import math
import logging
from typing import List, Dict, Any
from app.providers.base import VectorStoreProvider, SearchResult
from app.config import settings

logger = logging.getLogger(__name__)


class SimpleVectorStore(VectorStoreProvider):
    """Simple in-memory vector store with JSON persistence. No external dependencies."""
    
    def __init__(self):
        self.storage_path = os.path.join(settings.chroma_persist_dir, "vectors.json")
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)
        self.documents: List[Dict[str, Any]] = []
        self.embeddings: List[List[float]] = []
        self._load()
        logger.info(f"SimpleVectorStore initialized with {len(self.documents)} documents")
    
    def _load(self):
        """Load from disk."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.documents = data.get("documents", [])
                    self.embeddings = data.get("embeddings", [])
            except Exception as e:
                logger.warning(f"Failed to load vector store: {e}")
                self.documents = []
                self.embeddings = []
    
    def _save(self):
        """Save to disk."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "documents": self.documents,
                    "embeddings": self.embeddings
                }, f)
        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        if not documents:
            return
        
        for doc, emb in zip(documents, embeddings):
            self.documents.append({
                "id": doc["id"],
                "cv_id": doc["cv_id"],
                "filename": doc["filename"],
                "content": doc["content"],
                "chunk_index": doc["chunk_index"],
                "metadata": doc.get("metadata", {})
            })
            self.embeddings.append(emb)
        
        self._save()
        logger.info(f"Added {len(documents)} documents. Total: {len(self.documents)}")
    
    async def search(
        self,
        embedding: List[float],
        k: int = 5,
        threshold: float = 0.3
    ) -> List[SearchResult]:
        if not self.documents:
            return []
        
        # Calculate similarities
        similarities = []
        for i, emb in enumerate(self.embeddings):
            sim = self._cosine_similarity(embedding, emb)
            if sim >= threshold:
                similarities.append((i, sim))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top k
        results = []
        for idx, sim in similarities[:k]:
            doc = self.documents[idx]
            results.append(SearchResult(
                id=doc["id"],
                cv_id=doc["cv_id"],
                filename=doc["filename"],
                content=doc["content"],
                similarity=sim,
                metadata=doc.get("metadata", {})
            ))
        
        return results
    
    async def delete_cv(self, cv_id: str) -> bool:
        try:
            indices_to_remove = [
                i for i, doc in enumerate(self.documents)
                if doc["cv_id"] == cv_id
            ]
            for idx in reversed(indices_to_remove):
                del self.documents[idx]
                del self.embeddings[idx]
            self._save()
            return True
        except Exception:
            return False
    
    async def list_cvs(self) -> List[Dict[str, Any]]:
        cvs = {}
        for doc in self.documents:
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
        cvs = await self.list_cvs()
        return {
            "total_chunks": len(self.documents),
            "total_cvs": len(cvs),
            "storage_type": "simple_json"
        }


# Alias for compatibility
ChromaVectorStore = SimpleVectorStore
