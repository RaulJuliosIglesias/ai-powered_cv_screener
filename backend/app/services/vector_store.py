import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Optional, Dict, Any
from datetime import datetime
import os

from app.config import get_settings
from app.utils.exceptions import VectorStoreError
from app.services.pdf_service import CVChunk


class VectorStoreService:
    """Service for managing ChromaDB vector store operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self._init_client()
        self._init_collection()
    
    def _init_client(self):
        """Initialize ChromaDB client with persistence."""
        try:
            persist_dir = self.settings.chroma_persist_dir
            os.makedirs(persist_dir, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=persist_dir,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )
        except Exception as e:
            raise VectorStoreError(
                f"Failed to initialize ChromaDB client: {str(e)}"
            )
    
    def _init_collection(self):
        """Initialize or get the CV collection."""
        try:
            self.collection = self.client.get_or_create_collection(
                name=self.settings.chroma_collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            raise VectorStoreError(
                f"Failed to initialize collection: {str(e)}"
            )
    
    def add_chunks(
        self,
        chunks: List[CVChunk],
        embeddings: List[List[float]]
    ) -> int:
        """Add CV chunks to the vector store with enriched metadata."""
        try:
            if len(chunks) != len(embeddings):
                raise VectorStoreError(
                    "Number of chunks and embeddings must match",
                    details={"chunks": len(chunks), "embeddings": len(embeddings)}
                )
            
            if not chunks:
                return 0
            
            ids = [f"{chunk.cv_id}_{chunk.chunk_index}" for chunk in chunks]
            documents = [chunk.content for chunk in chunks]
            metadatas = []
            
            for chunk in chunks:
                # Build enriched metadata from chunk
                meta = {
                    "cv_id": chunk.cv_id,
                    "filename": chunk.filename,
                    "candidate_name": chunk.candidate_name or "",
                    "section_type": chunk.section_type,
                    "chunk_index": chunk.chunk_index,
                    "indexed_at": datetime.now().isoformat(),
                    "is_summary": getattr(chunk, 'is_summary_chunk', False),
                }
                
                # Add enriched metadata from chunk.metadata if available
                chunk_meta = chunk.metadata or {}
                
                # Core enriched fields (convert to ChromaDB-compatible types)
                if "total_experience_years" in chunk_meta:
                    meta["total_experience_years"] = float(chunk_meta["total_experience_years"])
                if "seniority_level" in chunk_meta:
                    meta["seniority_level"] = str(chunk_meta["seniority_level"])
                if "current_role" in chunk_meta:
                    meta["current_role"] = str(chunk_meta["current_role"] or "")
                if "current_company" in chunk_meta:
                    meta["current_company"] = str(chunk_meta["current_company"] or "")
                if "has_faang" in chunk_meta:
                    meta["has_faang"] = bool(chunk_meta["has_faang"])
                if "job_hopping_score" in chunk_meta:
                    meta["job_hopping_score"] = float(chunk_meta["job_hopping_score"])
                if "position_count" in chunk_meta:
                    meta["position_count"] = int(chunk_meta["position_count"])
                
                # Experience-specific fields
                if "job_title" in chunk_meta:
                    meta["job_title"] = str(chunk_meta["job_title"])
                if "company" in chunk_meta:
                    meta["company"] = str(chunk_meta["company"])
                if "start_year" in chunk_meta and chunk_meta["start_year"]:
                    meta["start_year"] = int(chunk_meta["start_year"])
                if "end_year" in chunk_meta and chunk_meta["end_year"]:
                    meta["end_year"] = int(chunk_meta["end_year"])
                if "is_current" in chunk_meta:
                    meta["is_current"] = bool(chunk_meta["is_current"])
                if "duration_years" in chunk_meta:
                    meta["duration_years"] = float(chunk_meta["duration_years"])
                
                # Skills as comma-separated string (ChromaDB doesn't support lists)
                if "skills" in chunk_meta and chunk_meta["skills"]:
                    meta["skills"] = ",".join(chunk_meta["skills"][:20])
                
                metadatas.append(meta)
            
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            
            return len(chunks)
            
        except Exception as e:
            if isinstance(e, VectorStoreError):
                raise
            raise VectorStoreError(
                f"Failed to add chunks to vector store: {str(e)}"
            )
    
    def search(
        self,
        query_embedding: List[float],
        k: int = 8,
        score_threshold: float = 0.5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks in the vector store."""
        try:
            where = filter_metadata if filter_metadata else None
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            
            if not results["ids"] or not results["ids"][0]:
                return []
            
            search_results = []
            for i, doc_id in enumerate(results["ids"][0]):
                # Convert distance to similarity score (cosine distance to similarity)
                distance = results["distances"][0][i]
                similarity = 1 - distance  # For cosine distance
                
                if similarity >= score_threshold:
                    search_results.append({
                        "id": doc_id,
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "score": similarity,
                    })
            
            return search_results
            
        except Exception as e:
            raise VectorStoreError(
                f"Failed to search vector store: {str(e)}"
            )
    
    def delete_cv(self, cv_id: str) -> int:
        """Delete all chunks for a specific CV."""
        try:
            # Get all chunks for this CV
            results = self.collection.get(
                where={"cv_id": cv_id},
                include=["metadatas"]
            )
            
            if not results["ids"]:
                return 0
            
            # Delete chunks
            self.collection.delete(ids=results["ids"])
            
            return len(results["ids"])
            
        except Exception as e:
            raise VectorStoreError(
                f"Failed to delete CV from vector store: {str(e)}"
            )
    
    def get_all_cvs(self) -> List[Dict[str, Any]]:
        """Get all unique CVs in the vector store."""
        try:
            results = self.collection.get(include=["metadatas"])
            
            if not results["ids"]:
                return []
            
            # Group by cv_id
            cvs = {}
            for i, metadata in enumerate(results["metadatas"]):
                cv_id = metadata["cv_id"]
                if cv_id not in cvs:
                    cvs[cv_id] = {
                        "id": cv_id,
                        "filename": metadata["filename"],
                        "candidate_name": metadata.get("candidate_name", ""),
                        "indexed_at": metadata.get("indexed_at", ""),
                        "chunk_count": 0,
                    }
                cvs[cv_id]["chunk_count"] += 1
            
            return list(cvs.values())
            
        except Exception as e:
            raise VectorStoreError(
                f"Failed to get CVs from vector store: {str(e)}"
            )
    
    def get_cv_by_id(self, cv_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific CV by ID."""
        try:
            results = self.collection.get(
                where={"cv_id": cv_id},
                include=["metadatas", "documents"]
            )
            
            if not results["ids"]:
                return None
            
            metadata = results["metadatas"][0]
            return {
                "id": cv_id,
                "filename": metadata["filename"],
                "candidate_name": metadata.get("candidate_name", ""),
                "indexed_at": metadata.get("indexed_at", ""),
                "chunk_count": len(results["ids"]),
                "chunks": results["documents"],
            }
            
        except Exception as e:
            raise VectorStoreError(
                f"Failed to get CV from vector store: {str(e)}"
            )
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store collection."""
        try:
            count = self.collection.count()
            cvs = self.get_all_cvs()
            
            return {
                "total_chunks": count,
                "total_cvs": len(cvs),
                "collection_name": self.settings.chroma_collection_name,
            }
            
        except Exception as e:
            raise VectorStoreError(
                f"Failed to get collection stats: {str(e)}"
            )
    
    def clear_collection(self):
        """Clear all data from the collection."""
        try:
            self.client.delete_collection(self.settings.chroma_collection_name)
            self._init_collection()
        except Exception as e:
            raise VectorStoreError(
                f"Failed to clear collection: {str(e)}"
            )
