import time
from typing import List, Dict, Any
from dataclasses import dataclass
from app.config import Mode, settings
from app.providers.factory import ProviderFactory
from app.providers.base import SearchResult
from app.prompts.templates import SYSTEM_PROMPT, build_query_prompt


@dataclass
class RAGResponse:
    """Response from RAG query."""
    answer: str
    sources: List[Dict[str, Any]]
    metrics: Dict[str, float]
    mode: str


class RAGService:
    """Main RAG orchestration service with dual mode support."""
    
    def __init__(self, mode: Mode):
        self.mode = mode
        self.embedder = ProviderFactory.get_embedding_provider(mode)
        self.vector_store = ProviderFactory.get_vector_store(mode)
        self.llm = ProviderFactory.get_llm_provider(mode)
    
    async def index_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Index documents into the vector store."""
        if not documents:
            return {"indexed": 0, "errors": []}
        
        metrics = {}
        start = time.perf_counter()
        
        # Generate embeddings
        texts = [doc["content"] for doc in documents]
        embed_result = await self.embedder.embed_texts(texts)
        metrics["embedding_ms"] = embed_result.latency_ms
        
        # Store in vector store
        t0 = time.perf_counter()
        await self.vector_store.add_documents(documents, embed_result.embeddings)
        metrics["storage_ms"] = (time.perf_counter() - t0) * 1000
        
        metrics["total_ms"] = (time.perf_counter() - start) * 1000
        
        return {
            "indexed": len(documents),
            "tokens_used": embed_result.tokens_used,
            "metrics": metrics
        }
    
    async def query(
        self,
        question: str,
        k: int = None,
        threshold: float = None,
        cv_ids: List[str] = None
    ) -> RAGResponse:
        """Query the RAG system. Optionally filter by cv_ids for session-based queries."""
        k = k or settings.retrieval_k
        threshold = threshold or settings.retrieval_score_threshold
        metrics = {}
        
        # 1. Embed the question
        embed_result = await self.embedder.embed_query(question)
        metrics["embedding_ms"] = embed_result.latency_ms
        query_embedding = embed_result.embeddings[0]
        
        # 2. Search for relevant chunks (filtered by cv_ids if provided)
        t0 = time.perf_counter()
        search_results = await self.vector_store.search(
            query_embedding, k=k, threshold=threshold, cv_ids=cv_ids
        )
        metrics["search_ms"] = (time.perf_counter() - t0) * 1000
        
        # 3. Build context from results
        if not search_results:
            return RAGResponse(
                answer="I couldn't find any relevant information in the CVs to answer your question.",
                sources=[],
                metrics=metrics,
                mode=self.mode.value
            )
        
        context = self._build_context(search_results)
        
        # 4. Generate response
        prompt = build_query_prompt(question, self._results_to_chunks(search_results))
        llm_result = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
        metrics["llm_ms"] = llm_result.latency_ms
        
        # 5. Extract unique sources
        sources = self._extract_sources(search_results)
        
        metrics["total_ms"] = metrics["embedding_ms"] + metrics["search_ms"] + metrics["llm_ms"]
        metrics["prompt_tokens"] = llm_result.prompt_tokens
        metrics["completion_tokens"] = llm_result.completion_tokens
        
        return RAGResponse(
            answer=llm_result.text,
            sources=sources,
            metrics=metrics,
            mode=self.mode.value
        )
    
    def _build_context(self, results: List[SearchResult]) -> str:
        """Build context string from search results."""
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[Source {i}: {result.filename}]\n{result.content}"
            )
        return "\n\n---\n\n".join(context_parts)
    
    def _results_to_chunks(self, results: List[SearchResult]) -> List[Dict[str, Any]]:
        """Convert search results to chunk format for prompt building."""
        return [
            {
                "content": r.content,
                "metadata": {
                    "filename": r.filename,
                    "candidate_name": r.metadata.get("candidate_name", "Unknown"),
                    "section_type": r.metadata.get("section_type", "general"),
                    "cv_id": r.cv_id
                }
            }
            for r in results
        ]
    
    def _extract_sources(self, results: List[SearchResult]) -> List[Dict[str, Any]]:
        """Extract unique sources from results."""
        seen = set()
        sources = []
        for result in results:
            if result.cv_id not in seen:
                seen.add(result.cv_id)
                sources.append({
                    "cv_id": result.cv_id,
                    "filename": result.filename,
                    "relevance": round(result.similarity, 3)
                })
        return sources
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        store_stats = await self.vector_store.get_stats()
        return {
            "mode": self.mode.value,
            **store_stats
        }
