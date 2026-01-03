"""
RAG Service v3 - Complete RAG Pipeline with Guardrails, Anti-Hallucination, and Evaluation.

This module provides the main RAG orchestration service that integrates:
- Semantic embeddings (sentence-transformers)
- Vector search (ChromaDB)
- Pre-LLM guardrails
- Post-LLM hallucination detection
- Query logging and evaluation
"""
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from app.config import Mode, settings
from app.providers.factory import ProviderFactory
from app.providers.base import SearchResult
from app.prompts.templates import SYSTEM_PROMPT, build_query_prompt
from app.services.guardrail_service import GuardrailService, GuardrailResult
from app.services.hallucination_service import HallucinationService, HallucinationCheckResult
from app.services.eval_service import EvalService
from app.services.query_understanding_service import QueryUnderstandingService, QueryUnderstanding
from app.services.reranking_service import RerankingService, RerankResult
from app.services.verification_service import LLMVerificationService, VerificationResult

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Complete response from RAG query."""
    answer: str
    sources: List[Dict[str, Any]]
    metrics: Dict[str, float]
    confidence_score: float
    guardrail_passed: bool
    hallucination_check: Dict[str, Any] = field(default_factory=dict)
    query_understanding: Dict[str, Any] = field(default_factory=dict)
    reranking_info: Dict[str, Any] = field(default_factory=dict)
    verification_info: Dict[str, Any] = field(default_factory=dict)
    mode: str = "local"


class RAGServiceV3:
    """
    RAG Service v3 with complete multi-step pipeline.
    
    Pipeline:
    1. Query Understanding → Understand and reformulate query (fast model)
    2. Guardrail Check → Reject off-topic questions
    3. Embed Query → Generate query embedding
    4. Vector Search → Find relevant CV chunks
    5. Re-ranking → Reorder results by LLM relevance scoring (NEW)
    6. LLM Generation → Generate response (main model)
    7. LLM Verification → Verify response is grounded (NEW)
    8. Hallucination Check → Heuristic verification
    9. Logging → Record for evaluation
    """
    
    def __init__(
        self, 
        mode: Mode = Mode.LOCAL,
        understanding_model: Optional[str] = None,
        reranking_model: Optional[str] = None,
        generation_model: Optional[str] = None,
        verification_model: Optional[str] = None,
        reranking_enabled: bool = True,
        verification_enabled: bool = True
    ):
        """
        Initialize RAG Service v3.
        
        Args:
            mode: Operating mode (local or cloud)
            understanding_model: Model for query understanding (Step 1)
            reranking_model: Model for re-ranking results (Step 2)
            generation_model: Model for response generation (Step 3)
            verification_model: Model for response verification (Step 4)
            reranking_enabled: Whether to enable re-ranking step
            verification_enabled: Whether to enable LLM verification step
        """
        self.mode = mode
        
        # Core providers
        self.embedder = ProviderFactory.get_embedding_provider(mode)
        self.vector_store = ProviderFactory.get_vector_store(mode)
        self.llm = ProviderFactory.get_llm_provider(mode)
        
        # Override generation model if specified
        if generation_model:
            self.llm.model = generation_model
        
        # Additional services
        self.query_understanding = QueryUnderstandingService(model=understanding_model)
        self.reranking = RerankingService(model=reranking_model, enabled=reranking_enabled)
        self.verification = LLMVerificationService(model=verification_model, enabled=verification_enabled)
        self.guardrail = GuardrailService()
        self.hallucination = HallucinationService()
        self.eval = EvalService()
        
        logger.info(f"RAGServiceV3 initialized in {mode.value} mode")
        logger.info(f"  Understanding model: {self.query_understanding.model}")
        logger.info(f"  Reranking model: {self.reranking.model} (enabled: {reranking_enabled})")
        logger.info(f"  Generation model: {self.llm.model}")
        logger.info(f"  Verification model: {self.verification.model} (enabled: {verification_enabled})")
    
    async def query(
        self,
        question: str,
        session_id: Optional[str] = None,
        cv_ids: Optional[List[str]] = None,
        k: int = None,
        threshold: float = None,
        total_cvs_in_session: int = None
    ) -> RAGResponse:
        """
        Execute complete RAG query pipeline.
        
        Args:
            question: User's question
            session_id: Optional session ID for logging
            cv_ids: Optional list of CV IDs to filter by
            k: Number of results to retrieve
            threshold: Minimum similarity threshold
            total_cvs_in_session: Total CVs in session (for context)
            
        Returns:
            RAGResponse with answer, sources, metrics, and verification results
        """
        k = k or settings.retrieval_k
        threshold = threshold or settings.retrieval_score_threshold
        metrics = {}
        total_start = time.perf_counter()
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 1: QUERY UNDERSTANDING (Fast Model)
        # ═══════════════════════════════════════════════════════════════
        understanding_start = time.perf_counter()
        query_understanding = await self.query_understanding.understand(question)
        metrics["understanding_ms"] = (time.perf_counter() - understanding_start) * 1000
        
        logger.info(f"Query understood in {metrics['understanding_ms']:.1f}ms")
        logger.info(f"  Original: {query_understanding.original_query}")
        logger.info(f"  Understood: {query_understanding.understood_query}")
        logger.info(f"  Type: {query_understanding.query_type}")
        logger.info(f"  CV-related: {query_understanding.is_cv_related}")
        
        # Use the reformulated prompt for better results
        effective_question = query_understanding.reformulated_prompt or question
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 2: GUARDRAIL CHECK (using understanding result)
        # ═══════════════════════════════════════════════════════════════
        # If query understanding says it's not CV-related, reject early
        if not query_understanding.is_cv_related:
            rejection_msg = "I can only help with CV screening and candidate analysis. Please ask a question about the uploaded CVs."
            
            self.eval.log_query(
                query=question,
                response=rejection_msg,
                sources=[],
                metrics=metrics,
                hallucination_check={"confidence_score": 0},
                guardrail_passed=False,
                session_id=session_id,
                mode=self.mode.value
            )
            
            return RAGResponse(
                answer=rejection_msg,
                sources=[],
                metrics=metrics,
                confidence_score=0,
                guardrail_passed=False,
                mode=self.mode.value
            )
        
        # Traditional guardrail check as backup
        guardrail_result = self.guardrail.check(question)
        
        if not guardrail_result.is_allowed:
            logger.info(f"Query rejected by guardrail: {guardrail_result.reason}")
            
            # Log the rejection
            self.eval.log_query(
                query=question,
                response=guardrail_result.rejection_message,
                sources=[],
                metrics={"guardrail_ms": 0},
                hallucination_check={"confidence_score": 0},
                guardrail_passed=False,
                session_id=session_id,
                mode=self.mode.value
            )
            
            return RAGResponse(
                answer=guardrail_result.rejection_message,
                sources=[],
                metrics={"guardrail_ms": 0},
                confidence_score=0,
                guardrail_passed=False,
                mode=self.mode.value
            )
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 2: EMBED QUERY
        # ═══════════════════════════════════════════════════════════════
        embed_start = time.perf_counter()
        embed_result = await self.embedder.embed_query(question)
        metrics["embedding_ms"] = (time.perf_counter() - embed_start) * 1000
        query_embedding = embed_result.embeddings[0]
        
        logger.debug(f"Query embedded in {metrics['embedding_ms']:.1f}ms")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 2.5: DETERMINE SESSION SIZE (critical for strategy)
        # ═══════════════════════════════════════════════════════════════
        # Use provided total_cvs_in_session or count from cv_ids
        num_cvs_in_session = total_cvs_in_session or (len(cv_ids) if cv_ids else 100)
        
        logger.info(f"Session contains {num_cvs_in_session} CVs")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 3: VECTOR SEARCH (adaptive strategy based on query + size)
        # ═══════════════════════════════════════════════════════════════
        search_start = time.perf_counter()
        
        # ADAPTIVE STRATEGY: Choose retrieval method based on:
        # 1. Query type (ranking/comparison vs search/filter)
        # 2. Session size (10 CVs vs 500 CVs)
        
        query_type = query_understanding.query_type
        is_ranking_query = query_type in {"ranking", "comparison"}
        
        # Decision matrix:
        # - Ranking/Comparison with <100 CVs → Diversified (need all CVs)
        # - Ranking/Comparison with ≥100 CVs → Diversified but capped at 100 (LLM context limit)
        # - Search/Filter with <100 CVs → Diversified (can afford full coverage)
        # - Search/Filter with ≥100 CVs → Top-K Global (precision over coverage)
        
        # Cap ranking queries based on session size to balance coverage vs speed
        # Reduced to 30 for large sessions to avoid exceeding model context limits (65K tokens)
        MAX_RANKING_K = 30 if num_cvs_in_session > 100 else 100
        
        # Adjust threshold for large sessions to ensure we get enough results
        effective_threshold = threshold
        if num_cvs_in_session > 100:
            effective_threshold = max(0.05, threshold - 0.1)  # Lower threshold for large sessions
        
        if is_ranking_query:
            diversify = True
            effective_k = min(num_cvs_in_session, MAX_RANKING_K)
            strategy_reason = f"ranking/comparison query (capped at {MAX_RANKING_K} for speed)" if num_cvs_in_session > MAX_RANKING_K else "ranking/comparison query"
        elif num_cvs_in_session < 100:
            diversify = True
            effective_k = num_cvs_in_session
            strategy_reason = f"small session ({num_cvs_in_session} CVs)"
        else:
            diversify = False
            effective_k = min(k, num_cvs_in_session)
            strategy_reason = f"large session ({num_cvs_in_session} CVs), using top-k for precision"
        
        logger.info(f"Search strategy: {'diversified' if diversify else 'top-k global'} ({strategy_reason}, k={effective_k}, threshold={effective_threshold})")
        
        search_results = await self.vector_store.search(
            embedding=query_embedding,
            k=effective_k,
            threshold=effective_threshold,
            cv_ids=cv_ids,
            diversify_by_cv=diversify
        )
        metrics["search_ms"] = (time.perf_counter() - search_start) * 1000
        metrics["results_count"] = len(search_results)
        
        logger.debug(f"Search returned {len(search_results)} results in {metrics['search_ms']:.1f}ms")
        
        # Handle no results
        if not search_results:
            no_results_msg = self._build_no_results_message(question, cv_ids)
            
            self.eval.log_query(
                query=question,
                response=no_results_msg,
                sources=[],
                metrics=metrics,
                hallucination_check={"confidence_score": 0.8, "is_valid": True},
                guardrail_passed=True,
                session_id=session_id,
                mode=self.mode.value
            )
            
            return RAGResponse(
                answer=no_results_msg,
                sources=[],
                metrics=metrics,
                confidence_score=0.8,  # High confidence in "no results" answer
                guardrail_passed=True,
                mode=self.mode.value
            )
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 4: RE-RANKING (NEW)
        # ═══════════════════════════════════════════════════════════════
        # Re-rank ALL results (don't truncate with top_k) to preserve context
        rerank_result = await self.reranking.rerank(
            query=effective_question,
            results=search_results,
            top_k=None  # Return all results, just reordered
        )
        metrics["reranking_ms"] = rerank_result.latency_ms
        metrics["reranking_enabled"] = rerank_result.enabled
        metrics["reranking_model"] = rerank_result.model_used
        
        # Use reranked results if available
        final_results = rerank_result.reranked_results if rerank_result.enabled else search_results
        
        logger.debug(f"Reranking completed in {metrics['reranking_ms']:.1f}ms (enabled: {rerank_result.enabled})")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 5: BUILD CONTEXT AND GENERATE RESPONSE
        # ═══════════════════════════════════════════════════════════════
        chunks = self._results_to_chunks(final_results)
        
        # Calculate total CVs for context
        unique_cv_ids = set(r.cv_id for r in final_results)
        total_cvs = total_cvs_in_session or len(cv_ids) if cv_ids else len(unique_cv_ids)
        
        # Use the reformulated question for better LLM understanding
        prompt = build_query_prompt(effective_question, chunks, total_cvs=total_cvs)
        
        # Add requirements from query understanding to help LLM
        if query_understanding.requirements:
            requirements_text = "\n\nIMPORTANT REQUIREMENTS TO ADDRESS:\n" + "\n".join(
                f"- {req}" for req in query_understanding.requirements
            )
            # Note: New templates.py uses "Respond now:" instead of "Your response:"
            prompt = prompt.replace("Respond now:", requirements_text + "\n\nRespond now:")
        
        llm_start = time.perf_counter()
        llm_result = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
        metrics["llm_ms"] = (time.perf_counter() - llm_start) * 1000
        metrics["prompt_tokens"] = llm_result.prompt_tokens
        metrics["completion_tokens"] = llm_result.completion_tokens
        
        logger.debug(f"LLM generated response in {metrics['llm_ms']:.1f}ms")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 6: LLM VERIFICATION (NEW)
        # ═══════════════════════════════════════════════════════════════
        verification_result = await self.verification.verify(
            response=llm_result.text,
            context_chunks=chunks,
            query=effective_question
        )
        metrics["verification_ms"] = verification_result.latency_ms
        metrics["verification_enabled"] = verification_result.enabled
        metrics["verification_model"] = verification_result.model_used
        
        logger.debug(f"Verification completed in {metrics['verification_ms']:.1f}ms (enabled: {verification_result.enabled})")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 7: HALLUCINATION CHECK (Heuristic)
        # ═══════════════════════════════════════════════════════════════
        cv_metadata = [
            {"cv_id": r.cv_id, "filename": r.filename}
            for r in final_results
        ]
        
        hallucination_start = time.perf_counter()
        hallucination_result = self.hallucination.verify_response(
            llm_response=llm_result.text,
            context_chunks=chunks,
            cv_metadata=cv_metadata
        )
        metrics["hallucination_check_ms"] = (time.perf_counter() - hallucination_start) * 1000
        
        # Combine LLM verification with heuristic hallucination check
        combined_confidence = (
            verification_result.groundedness_score * 0.6 + 
            hallucination_result.confidence_score * 0.4
        ) if verification_result.enabled else hallucination_result.confidence_score
        
        # Prepare answer with optional warning
        answer = llm_result.text
        if (not verification_result.is_grounded and verification_result.enabled) or \
           (hallucination_result.warnings and not hallucination_result.is_valid):
            answer += "\n\n⚠️ *Some information could not be fully verified against the CVs.*"
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 8: EXTRACT SOURCES AND FINALIZE
        # ═══════════════════════════════════════════════════════════════
        sources = self._extract_unique_sources(final_results)
        
        metrics["total_ms"] = (time.perf_counter() - total_start) * 1000
        
        # Convert hallucination result to dict for logging
        hallucination_dict = {
            "is_valid": hallucination_result.is_valid,
            "confidence_score": hallucination_result.confidence_score,
            "verified_cv_ids": hallucination_result.verified_cv_ids,
            "unverified_cv_ids": hallucination_result.unverified_cv_ids,
            "warnings": hallucination_result.warnings
        }
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 9: LOG FOR EVALUATION
        # ═══════════════════════════════════════════════════════════════
        self.eval.log_query(
            query=question,
            response=answer,
            sources=sources,
            metrics=metrics,
            hallucination_check=hallucination_dict,
            guardrail_passed=True,
            session_id=session_id,
            mode=self.mode.value
        )
        
        logger.info(
            f"RAG query completed in {metrics['total_ms']:.0f}ms "
            f"(embed={metrics['embedding_ms']:.0f}, search={metrics['search_ms']:.0f}, "
            f"llm={metrics['llm_ms']:.0f}) confidence={hallucination_result.confidence_score:.2f}"
        )
        
        # Convert query understanding to dict
        query_understanding_dict = {
            "original_query": query_understanding.original_query,
            "understood_query": query_understanding.understood_query,
            "query_type": query_understanding.query_type,
            "requirements": query_understanding.requirements,
            "reformulated_prompt": query_understanding.reformulated_prompt
        }
        
        # Convert reranking result to dict
        reranking_dict = {
            "enabled": rerank_result.enabled,
            "model": rerank_result.model_used,
            "latency_ms": rerank_result.latency_ms,
            "scores": rerank_result.scores
        }
        
        # Convert verification result to dict
        verification_dict = {
            "enabled": verification_result.enabled,
            "model": verification_result.model_used,
            "is_grounded": verification_result.is_grounded,
            "groundedness_score": verification_result.groundedness_score,
            "verified_claims": verification_result.verified_claims,
            "ungrounded_claims": verification_result.ungrounded_claims,
            "latency_ms": verification_result.latency_ms
        }
        
        return RAGResponse(
            answer=answer,
            sources=sources,
            metrics=metrics,
            confidence_score=combined_confidence,
            guardrail_passed=True,
            hallucination_check=hallucination_dict,
            query_understanding=query_understanding_dict,
            reranking_info=reranking_dict,
            verification_info=verification_dict,
            mode=self.mode.value
        )
    
    async def index_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Index documents into the vector store.
        
        Args:
            documents: List of document dicts with content and metadata
            
        Returns:
            Dict with indexing results and metrics
        """
        if not documents:
            return {"indexed": 0, "errors": []}
        
        metrics = {}
        start = time.perf_counter()
        
        # Generate embeddings
        texts = [doc["content"] for doc in documents]
        embed_result = await self.embedder.embed_texts(texts)
        metrics["embedding_ms"] = embed_result.latency_ms
        
        # Store in vector store
        storage_start = time.perf_counter()
        await self.vector_store.add_documents(documents, embed_result.embeddings)
        metrics["storage_ms"] = (time.perf_counter() - storage_start) * 1000
        
        metrics["total_ms"] = (time.perf_counter() - start) * 1000
        
        logger.info(f"Indexed {len(documents)} documents in {metrics['total_ms']:.0f}ms")
        
        return {
            "indexed": len(documents),
            "tokens_used": embed_result.tokens_used,
            "metrics": metrics
        }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        store_stats = await self.vector_store.get_stats()
        eval_stats = self.eval.get_daily_stats()
        
        return {
            "mode": self.mode.value,
            "vector_store": store_stats,
            "today": {
                "total_queries": eval_stats.total_queries,
                "avg_confidence": round(eval_stats.avg_confidence, 3),
                "guardrail_rejections": eval_stats.guardrail_rejections,
                "avg_latency_ms": round(eval_stats.avg_latency_ms, 1)
            }
        }
    
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
    
    def _extract_unique_sources(self, results: List[SearchResult]) -> List[Dict[str, Any]]:
        """Extract unique sources from search results."""
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
    
    def _build_no_results_message(self, question: str, cv_ids: Optional[List[str]]) -> str:
        """Build appropriate message when no results found."""
        if cv_ids:
            return (
                "I couldn't find any relevant information in the session's CVs to answer your question. "
                "The uploaded CVs may not contain information related to your query. "
                "Try asking about different skills or experiences, or upload more CVs."
            )
        else:
            return (
                "No CVs have been indexed yet. Please upload some CVs first, "
                "then I can help you analyze them."
            )


# Factory function for backward compatibility
def create_rag_service(mode: Mode = Mode.LOCAL) -> RAGServiceV3:
    """Create a RAG service instance."""
    return RAGServiceV3(mode)
