"""
ADAPTIVE STRUCTURE BUILDER - Main Orchestrator for Smart Dynamic Output

This is the MAIN ENTRY POINT for the adaptive system.
It coordinates all components to build a complete dynamic response.

Flow:
1. QueryAnalyzer → Understand intent and detect attributes
2. SchemaInferenceEngine → Determine table structure
3. SmartDataExtractor → Extract data from chunks
4. DynamicTableGenerator → Build the table
5. AdaptiveAnalysisGenerator → Generate analysis
6. Assemble final structure

The output structure is NEVER fixed - it adapts completely to the query.
"""

import logging
from typing import List, Dict, Any, Optional

from .query_analyzer import QueryAnalyzer, QueryAnalysis
from .schema_inference import SchemaInferenceEngine, TableSchema
from .data_extractor import SmartDataExtractor, ExtractionResult
from .table_generator import DynamicTableGenerator, DynamicTable
from .analysis_generator import AdaptiveAnalysisGenerator, AdaptiveAnalysis

logger = logging.getLogger(__name__)


class AdaptiveStructureBuilder:
    """
    Main builder for adaptive/dynamic output structures.
    
    This class:
    1. Coordinates all adaptive components
    2. Builds a complete response structure
    3. Returns data in a format compatible with frontend
    
    Unlike rigid structures, the output here changes based on:
    - What the user is asking
    - What data is available
    - What makes sense to show
    """
    
    def __init__(self):
        """Initialize all adaptive components."""
        self.query_analyzer = QueryAnalyzer()
        self.schema_engine = SchemaInferenceEngine()
        self.data_extractor = SmartDataExtractor()
        self.table_generator = DynamicTableGenerator()
        self.analysis_generator = AdaptiveAnalysisGenerator()
        
        logger.info("[ADAPTIVE_BUILDER] Initialized smart dynamic structure builder")
    
    def build(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        llm_output: str = "",
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Build a complete adaptive structure.
        
        Args:
            query: User's natural language query
            chunks: Retrieved CV chunks with metadata
            llm_output: Optional LLM response for additional context
            conversation_history: Optional conversation context
            
        Returns:
            Complete structure dict ready for frontend
        """
        logger.info(f"[ADAPTIVE_BUILDER] Building adaptive structure for: {query[:60]}...")
        
        # STEP 1: Analyze the query
        analysis = self.query_analyzer.analyze(query, chunks)
        logger.info(f"[ADAPTIVE_BUILDER] Query analysis: intent={analysis.intent.value}, "
                   f"attributes={[a.name for a in analysis.detected_attributes]}")
        
        # STEP 2: Infer schema
        schema = self.schema_engine.infer_schema(analysis, chunks)
        logger.info(f"[ADAPTIVE_BUILDER] Schema inferred: {len(schema.columns)} columns, "
                   f"row_entity={schema.row_entity}")
        
        # STEP 3: Extract data
        extraction_result = self.data_extractor.extract(schema, chunks)
        logger.info(f"[ADAPTIVE_BUILDER] Data extracted: {len(extraction_result.rows)} rows")
        
        # STEP 4: Generate table
        table = self.table_generator.generate(extraction_result)
        logger.info(f"[ADAPTIVE_BUILDER] Table generated: {table.title}")
        
        # STEP 5: Generate analysis
        adaptive_analysis = self.analysis_generator.generate(
            analysis,
            extraction_result,
            table,
            llm_output
        )
        logger.info(f"[ADAPTIVE_BUILDER] Analysis generated: {len(adaptive_analysis.sections)} sections")
        
        # STEP 6: Extract thinking from LLM output (if present)
        thinking = self._extract_thinking(llm_output)
        
        # STEP 7: Assemble final structure
        result = self._assemble_structure(
            query=query,
            analysis=analysis,
            schema=schema,
            table=table,
            adaptive_analysis=adaptive_analysis,
            thinking=thinking,
            llm_output=llm_output
        )
        
        logger.info("[ADAPTIVE_BUILDER] Adaptive structure complete")
        return result
    
    def _extract_thinking(self, llm_output: str) -> Optional[str]:
        """Extract thinking section from LLM output."""
        if not llm_output:
            return None
        
        import re
        
        # Try different thinking formats
        patterns = [
            r':::thinking\n(.*?)\n:::', 
            r'<thinking>(.*?)</thinking>',
            r'\*\*Thinking\*\*:?\s*(.*?)(?=\n\n|\*\*|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, llm_output, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _assemble_structure(
        self,
        query: str,
        analysis: QueryAnalysis,
        schema: TableSchema,
        table: DynamicTable,
        adaptive_analysis: AdaptiveAnalysis,
        thinking: Optional[str],
        llm_output: str
    ) -> Dict[str, Any]:
        """Assemble the final structure dictionary."""
        return {
            # Structure type identifier
            "structure_type": "adaptive",
            
            # Query info
            "query": query,
            "query_analysis": {
                "intent": analysis.intent.value,
                "detected_attributes": [a.name for a in analysis.detected_attributes],
                "suggested_format": analysis.suggested_format.value,
                "confidence": analysis.confidence
            },
            
            # Thinking (if available)
            "thinking": thinking,
            
            # Direct answer - brief summary
            "direct_answer": adaptive_analysis.direct_answer,
            
            # Analysis sections - ordered by priority
            "analysis": adaptive_analysis.to_markdown(),
            "analysis_sections": adaptive_analysis.to_dict()["sections"],
            
            # Dynamic table - the core output
            "dynamic_table": table.to_dict(),
            "table_markdown": self.table_generator.to_markdown(table),
            
            # Conclusion
            "conclusion": adaptive_analysis.conclusion,
            
            # Key findings
            "key_findings": adaptive_analysis.key_findings,
            
            # Metadata
            "total_candidates": len(table.rows) if table.row_entity == "candidate" else None,
            "total_attributes": len(table.rows) if table.row_entity == "attribute" else None,
            "schema_info": {
                "columns": [col["name"] for col in table.columns],
                "row_entity": table.row_entity,
                "title": table.title
            },
            
            # Raw content for fallback
            "raw_content": llm_output
        }
    
    def assemble(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        query: str = "",
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Assemble method for compatibility with orchestrator interface.
        
        This is the method called by the orchestrator.
        """
        return self.build(
            query=query,
            chunks=chunks,
            llm_output=llm_output,
            conversation_history=conversation_history
        )
