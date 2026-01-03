from typing import List, Dict, Any, Optional
import logging
from app.providers.base import VectorStoreProvider, SearchResult
from app.config import settings

logger = logging.getLogger(__name__)

# Lazy client initialization
_supabase_client = None

def get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        if not settings.supabase_url or not settings.supabase_service_key:
            raise RuntimeError("Supabase credentials not configured")
        _supabase_client = create_client(settings.supabase_url, settings.supabase_service_key)
        logger.info("Supabase vector store client initialized")
    return _supabase_client


class SupabaseVectorStore(VectorStoreProvider):
    """Cloud vector store using Supabase pgvector."""
    
    @property
    def client(self):
        return get_supabase_client()
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        if not documents:
            return
        
        logger.info(f"Adding {len(documents)} documents to Supabase")
        
        # First, ensure CVs exist in cvs table
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
            try:
                self.client.table("cvs").upsert(cv_data).execute()
                logger.info(f"Upserted CV: {cv_data['id']} - {cv_data['filename']}")
            except Exception as e:
                logger.error(f"Failed to upsert CV {cv_data['id']}: {e}")
        
        # Now add embeddings
        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            try:
                record = {
                    "cv_id": doc["cv_id"],
                    "filename": doc["filename"],
                    "chunk_index": doc["chunk_index"],
                    "content": doc["content"],
                    "embedding": embedding,
                    "metadata": doc.get("metadata", {})
                }
                logger.info(f"Inserting embedding {i+1}/{len(documents)} for {doc['cv_id']} chunk {doc['chunk_index']}")
                result = self.client.table("cv_embeddings").upsert(
                    record,
                    on_conflict="cv_id,chunk_index"
                ).execute()
                logger.info(f"Upsert result: {len(result.data) if result.data else 0} rows affected")
            except Exception as e:
                logger.error(f"Failed to add embedding for {doc['cv_id']} chunk {doc['chunk_index']}: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        logger.info(f"Successfully added {len(documents)} embeddings to Supabase")
    
    async def search(
        self,
        embedding: List[float],
        k: int = 5,
        threshold: float = 0.3,
        cv_ids: Optional[List[str]] = None
    ) -> List[SearchResult]:
        logger.info(f"Searching Supabase with k={k}, threshold={threshold}, cv_ids={cv_ids}")
        
        # Use RPC function for vector search
        response = self.client.rpc(
            "match_cv_embeddings",
            {
                "query_embedding": embedding,
                "match_count": k * 2 if cv_ids else k,  # Fetch more if filtering
                "match_threshold": threshold
            }
        ).execute()
        
        results = []
        for row in response.data:
            # Filter by cv_ids if provided
            if cv_ids and row["cv_id"] not in cv_ids:
                continue
            results.append(SearchResult(
                id=str(row["id"]),
                cv_id=row["cv_id"],
                filename=row["filename"],
                content=row["content"],
                similarity=row["similarity"],
                metadata=row.get("metadata", {})
            ))
            if len(results) >= k:
                break
        
        logger.info(f"Found {len(results)} results")
        return results
    
    async def delete_cv(self, cv_id: str) -> bool:
        try:
            # Delete embeddings first
            self.client.table("cv_embeddings").delete().eq("cv_id", cv_id).execute()
            # Then delete from cvs table
            self.client.table("cvs").delete().eq("id", cv_id).execute()
            logger.info(f"Deleted CV {cv_id} from Supabase")
            return True
        except Exception as e:
            logger.error(f"Failed to delete CV {cv_id}: {e}")
            return False
    
    async def delete_all_cvs(self) -> bool:
        """Delete all CVs and embeddings from Supabase."""
        try:
            self.client.table("cv_embeddings").delete().neq("cv_id", "").execute()
            self.client.table("cvs").delete().neq("id", "").execute()
            logger.info("Deleted all CVs from Supabase")
            return True
        except Exception as e:
            logger.error(f"Failed to delete all CVs: {e}")
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
