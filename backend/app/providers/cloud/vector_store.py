from typing import List, Dict, Any
from supabase import create_client, Client
from app.providers.base import VectorStoreProvider, SearchResult
from app.config import settings


class SupabaseVectorStore(VectorStoreProvider):
    """Cloud vector store using Supabase pgvector."""
    
    def __init__(self):
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        if not documents:
            return
        
        records = []
        for doc, embedding in zip(documents, embeddings):
            records.append({
                "cv_id": doc["cv_id"],
                "filename": doc["filename"],
                "chunk_index": doc["chunk_index"],
                "content": doc["content"],
                "embedding": embedding,
                "metadata": doc.get("metadata", {})
            })
        
        # Upsert to handle duplicates
        self.client.table("cv_embeddings").upsert(
            records,
            on_conflict="cv_id,chunk_index"
        ).execute()
        
        # Update CVs table
        unique_cvs = {}
        for doc in documents:
            cv_id = doc["cv_id"]
            if cv_id not in unique_cvs:
                unique_cvs[cv_id] = {
                    "id": cv_id,
                    "filename": doc["filename"],
                    "chunk_count": 0
                }
            unique_cvs[cv_id]["chunk_count"] += 1
        
        for cv_data in unique_cvs.values():
            self.client.table("cvs").upsert(cv_data).execute()
    
    async def search(
        self,
        embedding: List[float],
        k: int = 5,
        threshold: float = 0.3
    ) -> List[SearchResult]:
        response = self.client.rpc(
            "match_cv_embeddings",
            {
                "query_embedding": embedding,
                "match_count": k,
                "match_threshold": threshold
            }
        ).execute()
        
        results = []
        for row in response.data:
            results.append(SearchResult(
                id=str(row["id"]),
                cv_id=row["cv_id"],
                filename=row["filename"],
                content=row["content"],
                similarity=row["similarity"],
                metadata=row.get("metadata", {})
            ))
        
        return results
    
    async def delete_cv(self, cv_id: str) -> bool:
        try:
            self.client.rpc("delete_cv", {"target_cv_id": cv_id}).execute()
            return True
        except Exception:
            return False
    
    async def list_cvs(self) -> List[Dict[str, Any]]:
        response = self.client.table("cvs").select("*").execute()
        return response.data
    
    async def get_stats(self) -> Dict[str, Any]:
        chunks = self.client.table("cv_embeddings").select("id", count="exact").execute()
        cvs = self.client.table("cvs").select("id", count="exact").execute()
        
        return {
            "total_chunks": chunks.count or 0,
            "total_cvs": cvs.count or 0,
            "storage_type": "supabase_pgvector"
        }
