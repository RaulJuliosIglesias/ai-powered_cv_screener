import google.generativeai as genai
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import asyncio

from app.config import get_settings
from app.utils.exceptions import RAGError
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService
from app.prompts.templates import (
    SYSTEM_PROMPT,
    build_query_prompt,
    NO_RESULTS_TEMPLATE,
    WELCOME_MESSAGE,
)


class RAGService:
    """Service for RAG-powered CV querying."""
    
    def __init__(self):
        self.settings = get_settings()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService()
        self._init_llm()
        
        # Conversation history storage (in-memory, could be Redis in production)
        self.conversations: Dict[str, List[Dict]] = {}
    
    def _init_llm(self):
        """Initialize the Gemini LLM."""
        try:
            genai.configure(api_key=self.settings.google_api_key)
            
            generation_config = {
                "temperature": self.settings.llm_temperature,
                "max_output_tokens": self.settings.llm_max_tokens,
                "top_p": 0.95,
                "top_k": 40,
            }
            
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            
            self.model = genai.GenerativeModel(
                model_name=self.settings.llm_model,
                generation_config=generation_config,
                safety_settings=safety_settings,
                system_instruction=SYSTEM_PROMPT,
            )
            
        except Exception as e:
            raise RAGError(f"Failed to initialize LLM: {str(e)}")
    
    def retrieve(
        self,
        query: str,
        k: int = None,
        score_threshold: float = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks for a query."""
        try:
            k = k or self.settings.retrieval_k
            score_threshold = score_threshold or self.settings.retrieval_score_threshold
            
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embedding(query)
            
            # Search vector store
            results = self.vector_store.search(
                query_embedding=query_embedding,
                k=k,
                score_threshold=score_threshold,
            )
            
            return results
            
        except Exception as e:
            raise RAGError(f"Retrieval failed: {str(e)}")
    
    def generate(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a response using the LLM."""
        try:
            # Build prompt
            if not context_chunks:
                response_text = NO_RESULTS_TEMPLATE.format(question=query)
                prompt_tokens = 0
                completion_tokens = len(response_text) // 4
            else:
                prompt = build_query_prompt(query, context_chunks)
                
                # Get conversation history if exists
                history = []
                if conversation_id and conversation_id in self.conversations:
                    history = self.conversations[conversation_id][-5:]  # Last 5 exchanges
                
                # Generate response
                chat = self.model.start_chat(history=history)
                response = chat.send_message(prompt)
                
                response_text = response.text
                
                # Estimate token usage
                prompt_tokens = len(prompt) // 4
                completion_tokens = len(response_text) // 4
                
                # Store in conversation history
                if conversation_id:
                    if conversation_id not in self.conversations:
                        self.conversations[conversation_id] = []
                    self.conversations[conversation_id].append({
                        "role": "user",
                        "parts": [query]
                    })
                    self.conversations[conversation_id].append({
                        "role": "model", 
                        "parts": [response_text]
                    })
            
            # Extract sources
            sources = self._extract_sources(context_chunks)
            
            # Calculate cost (Gemini pricing)
            input_cost = (prompt_tokens / 1_000_000) * 0.075
            output_cost = (completion_tokens / 1_000_000) * 0.30
            total_cost = input_cost + output_cost
            
            return {
                "response": response_text,
                "sources": sources,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "estimated_cost_usd": total_cost,
                }
            }
            
        except Exception as e:
            raise RAGError(f"Generation failed: {str(e)}")
    
    def _extract_sources(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract source information from retrieved chunks."""
        sources = []
        seen_cvs = set()
        
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            cv_id = metadata.get("cv_id", "")
            
            if cv_id and cv_id not in seen_cvs:
                seen_cvs.add(cv_id)
                sources.append({
                    "cv_id": cv_id,
                    "filename": metadata.get("filename", "Unknown"),
                    "relevance_score": chunk.get("score", 0),
                    "matched_chunk": chunk.get("content", "")[:200] + "...",
                })
        
        return sources
    
    async def query_async(
        self,
        question: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Async query method for API usage."""
        loop = asyncio.get_event_loop()
        
        # Run retrieval
        chunks = await loop.run_in_executor(None, self.retrieve, question)
        
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # Run generation
        result = await loop.run_in_executor(
            None,
            lambda: self.generate(question, chunks, conversation_id)
        )
        
        result["conversation_id"] = conversation_id
        return result
    
    def query(
        self,
        question: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synchronous query method."""
        # Retrieve relevant chunks
        chunks = self.retrieve(question)
        
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # Generate response
        result = self.generate(question, chunks, conversation_id)
        result["conversation_id"] = conversation_id
        
        return result
    
    def get_welcome_message(self) -> str:
        """Get the welcome message for new users."""
        return WELCOME_MESSAGE
    
    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a conversation's history."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get RAG service statistics."""
        vector_stats = self.vector_store.get_collection_stats()
        
        return {
            "cvs_indexed": vector_stats["total_cvs"],
            "total_chunks": vector_stats["total_chunks"],
            "active_conversations": len(self.conversations),
        }
