from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.providers.base import VectorStoreProvider, SearchResult
from app.config import settings


class ChromaVectorStore(VectorStoreProvider):
    """Local vector store using ChromaDB."""
    
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        if not documents:
            return
        
        self.collection.add(
            ids=[doc["id"] for doc in documents],
            embeddings=embeddings,
            documents=[doc["content"] for doc in documents],
            metadatas=[{
                "cv_id": doc["cv_id"],
                "filename": doc["filename"],
                "chunk_index": doc["chunk_index"],
                **doc.get("metadata", {})
            } for doc in documents]
        )
    
    async def search(
        self,
        embedding: List[float],
        k: int = 5,
        threshold: float = 0.3
    ) -> List[SearchResult]:
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )
        
        search_results = []
        for i in range(len(results["ids"][0])):
            # ChromaDB returns distances, convert to similarity
            distance = results["distances"][0][i]
            similarity = 1 - distance  # For cosine distance
            
            if similarity >= threshold:
                metadata = results["metadatas"][0][i]
                search_results.append(SearchResult(
                    id=results["ids"][0][i],
                    cv_id=metadata.get("cv_id", ""),
                    filename=metadata.get("filename", ""),
                    content=results["documents"][0][i],
                    similarity=similarity,
                    metadata=metadata
                ))
        
        return search_results
    
    async def delete_cv(self, cv_id: str) -> bool:
        try:
            # Get all IDs for this CV
            results = self.collection.get(
                where={"cv_id": cv_id},
                include=[]
            )
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
            return True
        except Exception:
            return False
    
    async def list_cvs(self) -> List[Dict[str, Any]]:
        # Get all unique CVs
        results = self.collection.get(include=["metadatas"])
        
        cvs = {}
        for metadata in results["metadatas"]:
            cv_id = metadata.get("cv_id")
            if cv_id and cv_id not in cvs:
                cvs[cv_id] = {
                    "id": cv_id,
                    "filename": metadata.get("filename", ""),
                    "chunk_count": 0
                }
            if cv_id:
                cvs[cv_id]["chunk_count"] += 1
        
        return list(cvs.values())
    
    async def get_stats(self) -> Dict[str, Any]:
        count = self.collection.count()
        cvs = await self.list_cvs()
        return {
            "total_chunks": count,
            "total_cvs": len(cvs),
            "storage_type": "local_chromadb"
        }
