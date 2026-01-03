"""
LangChain RAG Service - Wrapper around existing RAG pipeline.

This service demonstrates LangChain integration while preserving
the existing 2-step pipeline with QueryUnderstanding, Guardrails,
Hallucination detection, and Eval logging.
"""
import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import OpenAIEmbeddings

from app.config import settings
from app.models.schemas import Mode
from app.prompts.templates import SYSTEM_PROMPT, QUERY_TEMPLATE
from app.services.query_understanding_service import QueryUnderstandingService
from app.services.guardrail_service import GuardrailService
from app.services.hallucination_service import HallucinationService
from app.services.eval_service import EvalService
from app.providers.base import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class LangChainRAGResponse:
    """Response from LangChain RAG query."""
    answer: str
    sources: List[Dict[str, Any]]
    metrics: Dict[str, float]
    confidence_score: float = 0.0
    guardrail_passed: bool = True
    hallucination_check: Dict[str, Any] = field(default_factory=dict)
    mode: str = "langchain"
    query_understanding: Optional[Dict[str, Any]] = None


class LangChainRAGService:
    """
    RAG Service using LangChain components.
    
    Wraps LangChain's LCEL (LangChain Expression Language) while
    preserving the existing pipeline:
    
    Query → QueryUnderstanding → Guardrails → LangChain RAG → Hallucination Check → Eval Log
    """
    
    def __init__(
        self,
        mode: Mode = Mode.CLOUD,
        understanding_model: Optional[str] = None,
        generation_model: Optional[str] = None
    ):
        self.mode = mode
        
        # Initialize existing services (KEEP THESE!)
        self.query_understanding = QueryUnderstandingService(model=understanding_model)
        self.guardrail = GuardrailService()
        self.hallucination = HallucinationService()
        self.eval_service = EvalService()
        
        # LangChain components
        self._llm = None
        self._embeddings = None
        self._vector_store = None
        self._chain = None
        
        # Model configuration
        self.generation_model = generation_model or "gemini-1.5-flash"
        
        logger.info(f"LangChainRAGService initialized in {mode} mode")
        logger.info(f"  Generation model: {self.generation_model}")
    
    @property
    def llm(self):
        """Lazy initialization of LangChain LLM."""
        if self._llm is None:
            # Use Google Gemini via LangChain
            if settings.google_api_key:
                self._llm = ChatGoogleGenerativeAI(
                    model=self.generation_model,
                    google_api_key=settings.google_api_key,
                    temperature=0.1,
                    max_output_tokens=2048
                )
                logger.info(f"Using Google Gemini LLM: {self.generation_model}")
            else:
                # Fallback: Use OpenRouter via custom wrapper
                from app.providers.cloud.llm import OpenRouterLLMProvider
                self._llm = LangChainOpenRouterWrapper(
                    model=self.generation_model
                )
                logger.info(f"Using OpenRouter LLM wrapper: {self.generation_model}")
        return self._llm
    
    def _get_vector_store(self):
        """Get vector store based on mode."""
        if self.mode == Mode.CLOUD:
            from app.providers.cloud.vector_store import SupabaseVectorStore as CustomSupabaseStore
            return CustomSupabaseStore()
        else:
            from app.providers.local.vector_store import SimpleVectorStore
            return SimpleVectorStore()
    
    def _get_embeddings_provider(self):
        """Get embeddings provider based on mode."""
        if self.mode == Mode.CLOUD:
            from app.providers.cloud.embeddings import OpenRouterEmbeddingProvider
            return OpenRouterEmbeddingProvider()
        else:
            from app.providers.local.embeddings import get_embedding_provider
            return get_embedding_provider()
    
    async def _embed_query(self, query: str) -> List[float]:
        """Embed query using existing provider."""
        provider = self._get_embeddings_provider()
        result = await provider.embed_texts([query])
        return result.embeddings[0]
    
    async def _search_documents(
        self,
        embedding: List[float],
        k: int = 5,
        cv_ids: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Search documents using existing vector store."""
        store = self._get_vector_store()
        return await store.search(
            embedding=embedding,
            k=k,
            cv_ids=cv_ids
        )
    
    def _build_context(self, results: List[SearchResult]) -> str:
        """Build context string from search results."""
        if not results:
            return "No relevant CV information found."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[Source {i}] CV: {result.filename} (ID: {result.cv_id})\n"
                f"Content: {result.content}\n"
                f"Relevance: {result.similarity:.2f}"
            )
        
        return "\n\n---\n\n".join(context_parts)
    
    def _create_langchain_chain(self):
        """Create LangChain LCEL chain for RAG."""
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{question}\n\nContext from CVs:\n{context}")
        ])
        
        # Create chain using LCEL
        chain = (
            {"question": RunnablePassthrough(), "context": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )
        
        return chain
    
    async def query(
        self,
        question: str,
        cv_ids: Optional[List[str]] = None,
        k: int = 5
    ) -> LangChainRAGResponse:
        """
        Execute RAG query using LangChain components.
        
        Pipeline:
        1. Query Understanding (existing service)
        2. Guardrail Check (existing service)
        3. Embedding + Vector Search
        4. LangChain LLM Generation
        5. Hallucination Check (existing service)
        6. Eval Logging (existing service)
        """
        metrics = {}
        total_start = time.perf_counter()
        
        # ========================================
        # STEP 1: Query Understanding (PRESERVED)
        # ========================================
        understanding_start = time.perf_counter()
        query_understanding = await self.query_understanding.understand(question)
        metrics["understanding_ms"] = (time.perf_counter() - understanding_start) * 1000
        
        effective_question = query_understanding.reformulated_prompt or question
        
        logger.info(f"[LangChain] Query understood in {metrics['understanding_ms']:.1f}ms")
        logger.info(f"  Original: {question[:100]}...")
        logger.info(f"  Reformulated: {effective_question[:100]}...")
        
        query_understanding_dict = {
            "original_query": query_understanding.original_query,
            "understood_query": query_understanding.understood_query,
            "query_type": query_understanding.query_type,
            "is_cv_related": query_understanding.is_cv_related,
            "requirements": query_understanding.requirements,
            "reformulated_prompt": query_understanding.reformulated_prompt
        }
        
        # ========================================
        # STEP 2: Guardrail Check (PRESERVED)
        # ========================================
        guardrail_start = time.perf_counter()
        is_allowed, rejection_msg = await self.guardrail.is_cv_related(question)
        metrics["guardrail_ms"] = (time.perf_counter() - guardrail_start) * 1000
        
        if not is_allowed:
            logger.info(f"[LangChain] Query rejected by guardrail: {rejection_msg}")
            self.eval_service.log_query(
                query=question,
                response=rejection_msg,
                sources=[],
                metrics=metrics,
                hallucination_check={},
                guardrail_passed=False
            )
            return LangChainRAGResponse(
                answer=rejection_msg,
                sources=[],
                metrics=metrics,
                guardrail_passed=False,
                query_understanding=query_understanding_dict
            )
        
        # ========================================
        # STEP 3: Embedding + Vector Search
        # ========================================
        embed_start = time.perf_counter()
        query_embedding = await self._embed_query(effective_question)
        metrics["embedding_ms"] = (time.perf_counter() - embed_start) * 1000
        
        search_start = time.perf_counter()
        search_results = await self._search_documents(
            embedding=query_embedding,
            k=k,
            cv_ids=cv_ids
        )
        metrics["search_ms"] = (time.perf_counter() - search_start) * 1000
        
        logger.info(f"[LangChain] Found {len(search_results)} relevant chunks")
        
        if not search_results:
            no_results_msg = "No relevant information found in the uploaded CVs for this query."
            return LangChainRAGResponse(
                answer=no_results_msg,
                sources=[],
                metrics=metrics,
                query_understanding=query_understanding_dict
            )
        
        # ========================================
        # STEP 4: LangChain LLM Generation
        # ========================================
        context = self._build_context(search_results)
        
        # Add requirements from query understanding
        enhanced_question = effective_question
        if query_understanding.requirements:
            reqs = "\n".join(f"- {r}" for r in query_understanding.requirements)
            enhanced_question += f"\n\nSpecific requirements to address:\n{reqs}"
        
        llm_start = time.perf_counter()
        
        try:
            # Use LangChain chain
            chain = self._create_langchain_chain()
            
            # Invoke with context
            answer = await chain.ainvoke({
                "question": enhanced_question,
                "context": context
            })
            
        except Exception as e:
            logger.error(f"[LangChain] LLM error: {e}")
            # Fallback to existing LLM provider
            from app.providers.cloud.llm import OpenRouterLLMProvider
            llm = OpenRouterLLMProvider(model=self.generation_model)
            prompt = QUERY_TEMPLATE.format(context=context, question=enhanced_question)
            result = await llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
            answer = result.text
        
        metrics["llm_ms"] = (time.perf_counter() - llm_start) * 1000
        
        # ========================================
        # STEP 5: Hallucination Check (PRESERVED)
        # ========================================
        cv_metadata = [
            {"cv_id": r.cv_id, "filename": r.filename}
            for r in search_results
        ]
        chunks = [{"content": r.content, "metadata": r.metadata} for r in search_results]
        
        hallucination_check = self.hallucination.verify_response(
            answer,
            chunks,
            cv_metadata
        )
        
        confidence_score = hallucination_check.get("confidence_score", 0.5)
        
        # ========================================
        # STEP 6: Prepare Sources
        # ========================================
        sources = [
            {
                "cv_id": r.cv_id,
                "filename": r.filename,
                "relevance": r.similarity,
                "chunk_index": r.metadata.get("chunk_index", 0) if r.metadata else 0
            }
            for r in search_results
        ]
        
        # ========================================
        # STEP 7: Eval Logging (PRESERVED)
        # ========================================
        metrics["total_ms"] = (time.perf_counter() - total_start) * 1000
        
        self.eval_service.log_query(
            query=question,
            response=answer,
            sources=sources,
            metrics=metrics,
            hallucination_check=hallucination_check,
            guardrail_passed=True
        )
        
        logger.info(
            f"[LangChain] Query completed in {metrics['total_ms']:.0f}ms "
            f"(embed={metrics['embedding_ms']:.0f}, search={metrics['search_ms']:.0f}, "
            f"llm={metrics['llm_ms']:.0f}) confidence={confidence_score:.2f}"
        )
        
        return LangChainRAGResponse(
            answer=answer,
            sources=sources,
            metrics=metrics,
            confidence_score=confidence_score,
            guardrail_passed=True,
            hallucination_check=hallucination_check,
            query_understanding=query_understanding_dict
        )
    
    async def index_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        """Index documents using existing vector store."""
        store = self._get_vector_store()
        await store.add_documents(documents, embeddings)
        logger.info(f"[LangChain] Indexed {len(documents)} documents")


class LangChainOpenRouterWrapper:
    """
    Wrapper to use OpenRouter LLM with LangChain interface.
    
    This allows using OpenRouter models within LangChain chains
    while maintaining compatibility with the existing codebase.
    """
    
    def __init__(self, model: str = "google/gemini-2.0-flash-001"):
        self.model = model
        self._provider = None
    
    @property
    def provider(self):
        if self._provider is None:
            from app.providers.cloud.llm import OpenRouterLLMProvider
            self._provider = OpenRouterLLMProvider(model=self.model)
        return self._provider
    
    async def ainvoke(self, input_data: Any) -> str:
        """Async invoke for LangChain compatibility."""
        if isinstance(input_data, dict):
            # Extract from prompt template output
            content = str(input_data)
        else:
            content = str(input_data)
        
        result = await self.provider.generate(content)
        return result.text
    
    def invoke(self, input_data: Any) -> str:
        """Sync invoke - wraps async."""
        import asyncio
        return asyncio.run(self.ainvoke(input_data))
