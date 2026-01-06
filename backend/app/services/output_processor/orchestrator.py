"""
Orchestrator - Routes queries to appropriate STRUCTURES.

ARCHITECTURE:
- MODULES: Individual reusable components (in ./modules/)
- STRUCTURES: Complete output assemblers that combine modules (in ./structures/)
- ORCHESTRATOR: Routes query_type to correct structure

This is the MAIN ENTRY POINT that RAG service calls.
"""

import logging
import re
from typing import List, Dict, Any

from app.models.structured_output import StructuredOutput
from app.utils.debug_logger import log_orchestrator_processing, log_red_flags_module, log_event
from .processor import OutputProcessor

# Import STRUCTURES (which internally use MODULES)
from .structures import (
    SingleCandidateStructure,
    RiskAssessmentStructure,
    ComparisonStructure,
    SearchStructure,
    RankingStructure,
    JobMatchStructure,
    TeamBuildStructure,
    VerificationStructure,
    SummaryStructure,
)

# Import modules for legacy/fallback processing
from .modules import (
    ThinkingModule,
    DirectAnswerModule,
    AnalysisModule,
    TableModule,
    ConclusionModule,
    GapAnalysisModule,
    RedFlagsModule,
    TimelineModule,
)

logger = logging.getLogger(__name__)


class OutputOrchestrator:
    """
    Main orchestrator - Routes queries to appropriate STRUCTURES.
    
    ROUTING:
    - query_type="single_candidate" → SingleCandidateStructure
    - query_type="red_flags"        → RiskAssessmentStructure
    - query_type="comparison"       → ComparisonStructure
    - query_type="search"           → SearchStructure
    - query_type="ranking"          → RankingStructure
    - query_type="job_match"        → JobMatchStructure
    - query_type="team_build"       → TeamBuildStructure
    - query_type="verification"     → VerificationStructure
    - query_type="summary"          → SummaryStructure
    """
    
    def __init__(self):
        """Initialize with structures and legacy processor."""
        # STRUCTURES (combine modules internally)
        self.single_candidate_structure = SingleCandidateStructure()
        self.risk_assessment_structure = RiskAssessmentStructure()
        self.comparison_structure = ComparisonStructure()
        self.search_structure = SearchStructure()
        self.ranking_structure = RankingStructure()
        self.job_match_structure = JobMatchStructure()
        self.team_build_structure = TeamBuildStructure()
        self.verification_structure = VerificationStructure()
        self.summary_structure = SummaryStructure()
        
        # Legacy processor for standard responses
        self.processor = OutputProcessor()
        
        # Legacy module instances for fallback/standard responses
        self.thinking_module = ThinkingModule()
        self.direct_answer_module = DirectAnswerModule()
        self.analysis_module = AnalysisModule()
        self.table_module = TableModule()
        self.conclusion_module = ConclusionModule()
        self.gap_analysis_module = GapAnalysisModule()
        self.red_flags_module = RedFlagsModule()
        self.timeline_module = TimelineModule()
        
        # Risk table module (used by legacy processing)
        from .modules import RiskTableModule
        self.risk_assessment_module = RiskTableModule()
        
        logger.info("[ORCHESTRATOR] Initialized with STRUCTURES architecture")
    
    def process(
        self,
        raw_llm_output: str,
        chunks: List[Dict[str, Any]] = None,
        query: str = "",
        query_type: str = "search",  # "search", "comparison", "single_candidate", "red_flags", etc.
        candidate_name: str = None,
        cv_id: str = None,  # Explicit cv_id from context resolver
        conversation_history: List[Dict[str, str]] = None
    ) -> tuple[StructuredOutput, str]:
        """
        Process LLM output into structured components and formatted answer.
        
        ROUTING based on query_type:
        - "single_candidate" → SingleCandidateStructure
        - "red_flags"        → RiskAssessmentStructure
        - "comparison"       → ComparisonStructure
        - "search"           → Standard response (legacy)
        
        Args:
            raw_llm_output: Raw text from LLM
            chunks: Retrieved CV chunks
            query: Original user query
            query_type: Type of query - determines which STRUCTURE to use
            candidate_name: Name of candidate for single_candidate/red_flags queries
            cv_id: Explicit cv_id (from context resolver) - takes priority over chunks
            
        Returns:
            Tuple of (StructuredOutput, formatted_answer_string)
        """
        # Log conversation context availability
        context_info = "no context"
        if conversation_history:
            context_info = f"{len(conversation_history)} messages ({sum(1 for m in conversation_history if m.get('role') == 'user')} user turns)"
        logger.info(f"[ORCHESTRATOR] ROUTING query_type={query_type} | conversation_context={context_info}")
        logger.info(f"[ORCHESTRATOR] Using appropriate structure for {query_type}")
        
        # STEP 0: PRE-PROCESS - Clean raw LLM output
        cleaned_llm_output = self._pre_clean_llm_output(raw_llm_output)
        
        # Use explicit cv_id if provided (from context resolver), otherwise extract from chunks
        effective_cv_id = cv_id
        if not effective_cv_id and chunks:
            effective_cv_id = chunks[0].get("metadata", {}).get("cv_id", "")
        
        if cv_id:
            logger.info(f"[ORCHESTRATOR] Using explicit cv_id from context resolver: {cv_id}")
        
        # =================================================================
        # ROUTING: Use appropriate STRUCTURE based on query_type
        # =================================================================
        
        if query_type == "single_candidate" and candidate_name:
            # SINGLE CANDIDATE STRUCTURE
            logger.info(f"[ORCHESTRATOR] Using SingleCandidateStructure for {candidate_name} (cv_id={effective_cv_id})")
            structure_data = self.single_candidate_structure.assemble(
                llm_output=cleaned_llm_output,
                chunks=chunks or [],
                candidate_name=candidate_name,
                cv_id=effective_cv_id,
                conversation_history=conversation_history or []
            )
            return self._build_structured_output(structure_data, cleaned_llm_output)
        
        elif query_type == "red_flags" and candidate_name:
            # RISK ASSESSMENT STRUCTURE
            logger.info(f"[ORCHESTRATOR] Using RiskAssessmentStructure for {candidate_name} (cv_id={effective_cv_id})")
            structure_data = self.risk_assessment_structure.assemble(
                llm_output=cleaned_llm_output,
                chunks=chunks or [],
                candidate_name=candidate_name,
                cv_id=effective_cv_id,
                conversation_history=conversation_history or []
            )
            return self._build_structured_output(structure_data, cleaned_llm_output)
        
        elif query_type == "comparison":
            # COMPARISON STRUCTURE
            logger.info("[ORCHESTRATOR] Using ComparisonStructure")
            structure_data = self.comparison_structure.assemble(
                llm_output=cleaned_llm_output,
                chunks=chunks or [],
                conversation_history=conversation_history or []
            )
            return self._build_structured_output(structure_data, cleaned_llm_output)
        
        elif query_type == "search":
            # SEARCH STRUCTURE
            logger.info("[ORCHESTRATOR] Using SearchStructure")
            structure_data = self.search_structure.assemble(
                llm_output=cleaned_llm_output,
                chunks=chunks or [],
                query=query,
                conversation_history=conversation_history or []
            )
            return self._build_structured_output(structure_data, cleaned_llm_output)
        
        elif query_type == "ranking":
            # RANKING STRUCTURE
            logger.info("[ORCHESTRATOR] Using RankingStructure")
            structure_data = self.ranking_structure.assemble(
                llm_output=cleaned_llm_output,
                chunks=chunks or [],
                query=query,
                conversation_history=conversation_history or []
            )
            return self._build_structured_output(structure_data, cleaned_llm_output)
        
        elif query_type == "job_match":
            # JOB MATCH STRUCTURE
            logger.info("[ORCHESTRATOR] Using JobMatchStructure")
            structure_data = self.job_match_structure.assemble(
                llm_output=cleaned_llm_output,
                chunks=chunks or [],
                query=query,
                conversation_history=conversation_history or []
            )
            return self._build_structured_output(structure_data, cleaned_llm_output)
        
        elif query_type == "team_build":
            # TEAM BUILD STRUCTURE
            logger.info("[ORCHESTRATOR] Using TeamBuildStructure")
            structure_data = self.team_build_structure.assemble(
                llm_output=cleaned_llm_output,
                chunks=chunks or [],
                query=query,
                conversation_history=conversation_history or []
            )
            return self._build_structured_output(structure_data, cleaned_llm_output)
        
        elif query_type == "verification":
            # VERIFICATION STRUCTURE
            logger.info("[ORCHESTRATOR] Using VerificationStructure")
            structure_data = self.verification_structure.assemble(
                llm_output=cleaned_llm_output,
                chunks=chunks or [],
                query=query,
                conversation_history=conversation_history or []
            )
            return self._build_structured_output(structure_data, cleaned_llm_output)
        
        elif query_type == "summary":
            # SUMMARY STRUCTURE
            logger.info("[ORCHESTRATOR] Using SummaryStructure")
            structure_data = self.summary_structure.assemble(
                llm_output=cleaned_llm_output,
                chunks=chunks or [],
                query=query,
                conversation_history=conversation_history or []
            )
            return self._build_structured_output(structure_data, cleaned_llm_output)
        
        else:
            # LEGACY: Standard response for unmatched query types
            logger.info(f"[ORCHESTRATOR] Using legacy standard response for query_type={query_type}")
            return self._process_standard_response(cleaned_llm_output, chunks, query, query_type)
    
    def _build_structured_output(
        self, 
        structure_data: Dict[str, Any], 
        raw_content: str
    ) -> tuple[StructuredOutput, str]:
        """
        Build StructuredOutput from structure data.
        
        Args:
            structure_data: Dict from a structure's assemble() method
            raw_content: Original LLM output
            
        Returns:
            Tuple of (StructuredOutput, formatted_answer_string)
        """
        # Create StructuredOutput with structure data
        structured = StructuredOutput(
            direct_answer=structure_data.get("summary", "") or structure_data.get("risk_analysis", ""),
            raw_content=raw_content,
            thinking=structure_data.get("thinking"),
            analysis=structure_data.get("analysis"),
            table_data=None,  # Structures handle their own tables
            conclusion=structure_data.get("conclusion") or structure_data.get("assessment"),
        )
        
        # Add structure-specific data
        structured.structure_type = structure_data.get("structure_type")
        structured.risk_assessment = structure_data.get("risk_table")
        
        # For single candidate, add all profile components
        if structure_data.get("structure_type") == "single_candidate":
            structured.single_candidate_data = {
                "candidate_name": structure_data.get("candidate_name"),
                "cv_id": structure_data.get("cv_id"),
                "summary": structure_data.get("summary"),
                "highlights": structure_data.get("highlights"),
                "career": structure_data.get("career"),
                "skills": structure_data.get("skills"),
                "credentials": structure_data.get("credentials"),
                "risk_table": structure_data.get("risk_table"),
                "conclusion": structure_data.get("conclusion"),
            }
        
        # For risk assessment, add specific components
        elif structure_data.get("structure_type") == "risk_assessment":
            structured.risk_assessment_data = {
                "candidate_name": structure_data.get("candidate_name"),
                "cv_id": structure_data.get("cv_id"),
                "risk_analysis": structure_data.get("risk_analysis"),
                "risk_table": structure_data.get("risk_table"),
                "assessment": structure_data.get("assessment"),
            }
        
        # For comparison, add table_data for comparison table
        elif structure_data.get("structure_type") == "comparison":
            structured.table_data = structure_data.get("table_data")
            structured.analysis = structure_data.get("analysis")
        
        # For search, add results table and analysis
        elif structure_data.get("structure_type") == "search":
            structured.results_table = structure_data.get("results_table")
            structured.total_results = structure_data.get("total_results", 0)
            structured.query = structure_data.get("query", "")
            structured.analysis = structure_data.get("analysis")
        
        # For ranking, add ranking table, top pick and analysis
        elif structure_data.get("structure_type") == "ranking":
            structured.ranking_table = structure_data.get("ranking_table")
            structured.top_pick = structure_data.get("top_pick")
            structured.ranking_criteria = structure_data.get("ranking_criteria")
            structured.analysis = structure_data.get("analysis")
        
        # For job match, add match scores, requirements, gap analysis
        elif structure_data.get("structure_type") == "job_match":
            structured.match_scores = structure_data.get("match_scores")
            structured.requirements = structure_data.get("requirements")
            structured.best_match = structure_data.get("best_match")
            structured.gap_analysis = structure_data.get("gap_analysis")
            structured.total_candidates = structure_data.get("total_candidates", 0)
            structured.analysis = structure_data.get("analysis")
        
        # For team build, add team composition and analysis
        elif structure_data.get("structure_type") == "team_build":
            structured.team_composition = structure_data.get("team_composition")
            structured.skill_coverage = structure_data.get("skill_coverage")
            structured.team_risks = structure_data.get("team_risks")
            structured.team_requirements = structure_data.get("team_requirements")
            structured.analysis = structure_data.get("analysis")
        
        # For verification, add claim/evidence/verdict
        elif structure_data.get("structure_type") == "verification":
            structured.claim = structure_data.get("claim")
            structured.evidence = structure_data.get("evidence")
            structured.verdict = structure_data.get("verdict")
        
        # For summary, add pool stats
        elif structure_data.get("structure_type") == "summary":
            structured.talent_pool = structure_data.get("talent_pool")
            structured.skill_distribution = structure_data.get("skill_distribution")
            structured.experience_distribution = structure_data.get("experience_distribution")
        
        # Build formatted answer (for legacy compatibility)
        formatted_answer = self._format_structure_output(structure_data)
        
        logger.info(f"[ORCHESTRATOR] Built output for structure_type={structure_data.get('structure_type')}")
        
        return structured, formatted_answer
    
    def _format_structure_output(self, structure_data: Dict[str, Any]) -> str:
        """Format structure data into markdown string."""
        parts = []
        
        # Thinking
        if structure_data.get("thinking"):
            parts.append(f":::thinking\n{structure_data['thinking']}\n:::")
        
        # Structure-specific content
        structure_type = structure_data.get("structure_type")
        
        if structure_type == "single_candidate":
            # Format single candidate profile
            if structure_data.get("summary"):
                parts.append(structure_data["summary"])
            # Other sections formatted by frontend
        
        elif structure_type == "risk_assessment":
            # Format risk assessment
            if structure_data.get("risk_analysis"):
                parts.append(structure_data["risk_analysis"])
            if structure_data.get("risk_table"):
                risk_table = structure_data["risk_table"]
                if isinstance(risk_table, dict) and risk_table.get("factors"):
                    parts.append("\n### ⚠️ Risk Assessment\n")
                    parts.append("| Factor | Status | Details |")
                    parts.append("|:-------|:------:|:--------|")
                    for f in risk_table["factors"]:
                        parts.append(f"| **{f['factor']}** | {f['status']} | {f['details']} |")
        
        elif structure_type == "comparison":
            # Format comparison
            if structure_data.get("analysis"):
                parts.append(structure_data["analysis"])
        
        # Conclusion
        if structure_data.get("conclusion") or structure_data.get("assessment"):
            conclusion = structure_data.get("conclusion") or structure_data.get("assessment")
            parts.append(f"\n:::conclusion\n{conclusion}\n:::")
        
        return "\n\n".join(parts)
    
    def _process_standard_response(
        self,
        cleaned_llm_output: str,
        chunks: List[Dict[str, Any]],
        query: str,
        query_type: str = "search"
    ) -> tuple[StructuredOutput, str]:
        """
        Legacy processing for standard search responses.
        """
        # Use legacy processor
        structured = self.processor.process(cleaned_llm_output, chunks)
        
        logger.info(
            f"[ORCHESTRATOR] Legacy components extracted: "
            f"thinking={bool(structured.thinking)}, "
            f"table={bool(structured.table_data)}, "
            f"conclusion={bool(structured.conclusion)}"
        )
        
        # Generate fallback analysis if needed
        if not structured.analysis:
            fallback_analysis = self.analysis_module.generate_fallback(
                structured.direct_answer,
                structured.table_data,
                structured.conclusion
            )
            if fallback_analysis:
                structured.analysis = fallback_analysis
        
        # Format candidate references
        candidate_map = {}
        if structured.table_data and hasattr(structured.table_data, 'rows'):
            for row in structured.table_data.rows:
                if hasattr(row, 'candidate_name') and hasattr(row, 'cv_id'):
                    candidate_map[row.candidate_name] = row.cv_id
        
        if structured.direct_answer:
            structured.direct_answer = self._format_candidate_references(structured.direct_answer, candidate_map)
        if structured.analysis:
            structured.analysis = self._format_candidate_references(structured.analysis, candidate_map)
        if structured.conclusion:
            structured.conclusion = self._format_candidate_references(structured.conclusion, candidate_map)
        
        # Extract enhanced modules if chunks available
        if chunks:
            self._extract_enhanced_modules(structured, cleaned_llm_output, chunks, query)
        
        # Assemble output
        parts = []
        
        if structured.thinking:
            formatted_thinking = self.thinking_module.format(structured.thinking)
            parts.append(formatted_thinking)
        
        formatted_answer = self.direct_answer_module.format(structured.direct_answer)
        parts.append(formatted_answer)
        
        if structured.analysis:
            formatted_analysis = self.analysis_module.format(structured.analysis)
            parts.append(formatted_analysis)
        
        # 4. Table (if exists)
        if structured.table_data:
            formatted_table = self.table_module.format(structured.table_data)
            parts.append(formatted_table)
        
        # 5. Conclusion block
        if structured.conclusion:
            formatted_conclusion = self.conclusion_module.format(structured.conclusion)
            parts.append(formatted_conclusion)
        
        # 6. Enhanced modules (v5.1) - Optional sections after main content
        # These are included in structured output but also formatted for display
        if structured.gap_analysis and structured.gap_analysis.get("skill_gaps"):
            from .modules import GapAnalysisData, SkillGap
            # Reconstruct data object for formatting
            gap_data = self._reconstruct_gap_analysis(structured.gap_analysis)
            if gap_data:
                formatted_gaps = self.gap_analysis_module.format(gap_data)
                if formatted_gaps:
                    parts.append(formatted_gaps)
        
        # MANDATORY: Red Flags Analysis section for ALL queries with chunks
        # This section MUST appear to show either detected flags or "clean candidate" status
        red_flags_formatted = self._format_red_flags_section(structured, query_type)
        if red_flags_formatted:
            parts.append(red_flags_formatted)
            logger.info(f"[ORCHESTRATOR] Red Flags Analysis section ADDED ({len(red_flags_formatted)} chars)")
        
        if structured.timeline and structured.timeline.get("timelines"):
            from .modules import TimelineData, CandidateTimeline
            timeline_data = self._reconstruct_timeline(structured.timeline)
            if timeline_data:
                formatted_timeline = self.timeline_module.format(timeline_data)
                if formatted_timeline:
                    parts.append(formatted_timeline)
        
        # RISK ASSESSMENT MODULE - Format and add for single_candidate and red_flags queries
        if query_type in ("single_candidate", "red_flags") and hasattr(self, '_last_risk_assessment_data'):
            risk_data = self._last_risk_assessment_data
            if risk_data and risk_data.factors:
                formatted_risk = self.risk_assessment_module.format(risk_data)
                if formatted_risk:
                    parts.append(formatted_risk)
                    logger.info(f"[ORCHESTRATOR] Risk Assessment section ADDED ({len(formatted_risk)} chars)")
        
        # Join with double newlines for readability
        final_answer = "\n\n".join(parts)
        
        # CRITICAL: Final cleanup - remove any duplicated paragraphs that slipped through
        final_answer = self._remove_duplicate_paragraphs(final_answer)
        
        # STEP 4: POST-PROCESS - Final cleanup of formatting issues
        final_answer = self._post_clean_output(final_answer)
        
        logger.info(f"[ORCHESTRATOR] Final answer: {len(final_answer)} chars")
        
        return structured, final_answer
    
    def _pre_clean_llm_output(self, text: str) -> str:
        """
        Pre-process raw LLM output BEFORE module extraction.
        
        This handles cases where LLM wraps EVERYTHING in a code block.
        """
        import re
        
        if not text:
            return text
        
        original_len = len(text)
        
        # CRITICAL: Detect if entire output is wrapped in a code block
        # Pattern: ```code\n...content...\n``` or ```\n...content...\n```
        code_block_wrapper = re.match(
            r'^```(?:code|markdown|text|)?\s*\n([\s\S]*?)\n```\s*$',
            text.strip(),
            flags=re.IGNORECASE
        )
        
        if code_block_wrapper:
            text = code_block_wrapper.group(1)
            logger.info(f"[ORCHESTRATOR] Unwrapped content from code block wrapper")
        
        # Also handle partial code blocks at the start
        text = re.sub(r'^```(?:code|markdown|text|)?\s*\n', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\n```\s*$', '', text)
        
        # Remove "code Copy code" artifacts
        text = re.sub(r'^code\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'code\s*Copy\s*code', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bCopy\s+code\b', '', text, flags=re.IGNORECASE)
        
        if len(text) != original_len:
            logger.info(f"[ORCHESTRATOR] Pre-cleaned: {original_len} -> {len(text)} chars")
        
        return text.strip()
    
    def _format_candidate_references(self, text: str, candidate_map: dict = None) -> str:
        """
        Formato ÚNICO para menciones de candidatos en TODAS las secciones.
        
        Convierte: [Nombre](cv:cv_xxx) o [Nombre](cv_xxx) o **[Nombre](cv_xxx)**
        A:         [📄](cv:cv_xxx) **Nombre**
        
        También detecta nombres de candidatos en texto plano y los convierte.
        
        - El icono 📄 es el ÚNICO elemento clicable (abre PDF)
        - El nombre va en negrita, SIN subrayado, SIN link
        """
        if not text:
            return text
        
        candidate_map = candidate_map or {}
        
        # Paso 0: Eliminar negrita externa que el LLM añade alrededor de links
        # **[Nombre](cv_xxx)** -> [Nombre](cv_xxx)
        text = re.sub(
            r'\*\*\[([^\]]+)\]\(([^)]+)\)\*\*',
            r'[\1](\2)',
            text
        )
        
        # Paso 1: Normalizar links sin prefijo cv:
        # [Nombre](cv_xxx) -> [Nombre](cv:cv_xxx)
        text = re.sub(
            r'\[([^\]]+)\]\((cv_[a-z0-9_-]+)\)',
            r'[\1](cv:\2)',
            text,
            flags=re.IGNORECASE
        )
        
        # Paso 2: Convertir al formato final con icono + negrita
        # [Nombre](cv:cv_xxx) -> [📄](cv:cv_xxx) **Nombre**
        text = re.sub(
            r'\[([^\]]+)\]\((cv:cv_[a-z0-9_-]+)\)',
            r'[📄](\2) **\1**',
            text,
            flags=re.IGNORECASE
        )
        
        # Paso 3: Detectar nombres de candidatos en texto plano y convertirlos
        # Solo si tenemos el mapa de candidatos de la tabla
        for name, cv_id in candidate_map.items():
            # Evitar reemplazar si ya está formateado (tiene 📄 antes o ** alrededor)
            # Buscar nombre que NO esté ya formateado
            # Patrón: nombre que no está precedido por 📄 ni rodeado de **
            pattern = rf'(?<!\*\*)(?<!\] )(?<!📄\]\(cv:{cv_id}\) \*\*){re.escape(name)}(?!\*\*)'
            replacement = f'[📄](cv:{cv_id}) **{name}**'
            text = re.sub(pattern, replacement, text, count=1)  # Solo primera ocurrencia
        
        return text
    
    def _post_clean_output(self, text: str) -> str:
        """
        Post-process final output AFTER module formatting.
        
        This catches any formatting issues that slipped through modules.
        """
        import re
        
        if not text:
            return text
        
        original = text
        
        # 1. Fix bold formatting globally: ** Name** -> **Name**
        text = re.sub(r'\*\*\s+', '**', text)  # Remove space after **
        text = re.sub(r'\s+\*\*', '**', text)  # Remove space before **
        
        # 1.5 FIX: Clean up broken markdown links caused by LLM line breaks
        # Pattern: [Name](cv: cv_xxx) or [Name](cv:\ncv_xxx) -> [Name](cv:cv_xxx)
        # The whitespace/newline after "cv:" breaks the link
        text = re.sub(r'\]\(cv:\s+(cv_[a-f0-9_-]+)\)', r'](cv:\1)', text, flags=re.IGNORECASE)
        text = re.sub(r'\]\(\s*cv:\s*', r'](cv:', text, flags=re.IGNORECASE)
        
        # 2. CRITICAL: Ensure ALL cv_id links have cv: prefix for frontend detection
        # Convert [Name](cv_xxx) -> [Name](cv:cv_xxx)
        text = re.sub(
            r'\[([^\]]+)\]\((cv_[a-z0-9_-]+)\)',
            r'[\1](cv:\2)',
            text,
            flags=re.IGNORECASE
        )
        
        # 3. Fix duplicated cv_id references: cv_xxx [cv_xxx](cv_xxx) -> [cv_xxx](cv:cv_xxx)
        text = re.sub(
            r'(cv_[a-z0-9_-]+)\s*\[\1\]\(\1\)',
            r'[\1](cv:\1)',
            text,
            flags=re.IGNORECASE
        )
        text = re.sub(
            r'(cv_[a-z0-9_-]+)\s*\[\1\]\(cv:\1\)',
            r'[\1](cv:\1)',
            text,
            flags=re.IGNORECASE
        )
        
        # 4. Fix triple cv_id: Name cv_xxx [cv_xxx](cv_xxx) -> **Name** cv_xxx
        text = re.sub(
            r'\*\*([^*]+)\*\*\s*(cv_[a-z0-9_-]+)\s*\[\2\]\(\2\)',
            r'**\1** \2',
            text,
            flags=re.IGNORECASE
        )
        text = re.sub(
            r'\*\*([^*]+)\*\*\s*(cv_[a-z0-9_-]+)\s*\[\2\]\(cv:\2\)',
            r'**\1** \2',
            text,
            flags=re.IGNORECASE
        )
        
        # 5. Remove any remaining "code" artifacts at line start
        text = re.sub(r'^code\s*$', '', text, flags=re.MULTILINE)
        
        # 6. Clean up excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        if text != original:
            logger.info(f"[ORCHESTRATOR] Post-cleaned formatting issues")
        
        return text.strip()
    
    def _remove_duplicate_paragraphs(self, text: str) -> str:
        """
        Final pass to remove duplicated paragraphs from assembled output.
        
        This catches cases where the same content appears multiple times
        due to LLM generating duplicates that weren't caught earlier.
        """
        import re
        
        if not text or len(text) < 100:
            return text
        
        paragraphs = text.split('\n\n')
        unique_paragraphs = []
        seen_normalized = set()
        
        for para in paragraphs:
            para_stripped = para.strip()
            if not para_stripped:
                continue
            
            # Normalize: lowercase, remove extra spaces, remove pipes
            normalized = ' '.join(para_stripped.lower().split())
            normalized = re.sub(r'\s*\|\s*', ' ', normalized)
            normalized = re.sub(r'\|[^|]*\|[^|]*\|?', '', normalized)
            normalized = ' '.join(normalized.split())[:150]  # First 150 chars for comparison
            
            # Skip if this is a table line (starts with |)
            if para_stripped.startswith('|'):
                unique_paragraphs.append(para)
                continue
            
            # NEVER remove Red Flags or Risk Assessment sections - they're important analysis
            if any(keyword in para_stripped.lower() for keyword in [
                'red flags', '### red flags', 'risk assessment', '### risk assessment',
                '⚠️ risk assessment', 'red flags analysis', 'job hopping', 'employment gaps'
            ]):
                unique_paragraphs.append(para)
                continue
            
            # Check for duplicate
            is_dup = normalized in seen_normalized
            if not is_dup and len(normalized) > 50:
                # Also check prefix match
                is_dup = any(
                    (normalized.startswith(s[:50]) or s.startswith(normalized[:50]))
                    for s in seen_normalized if len(s) > 30
                )
            
            if not is_dup:
                seen_normalized.add(normalized)
                unique_paragraphs.append(para)
            else:
                logger.debug(f"[ORCHESTRATOR] Removed duplicate paragraph: {para_stripped[:60]}...")
        
        result = '\n\n'.join(unique_paragraphs)
        
        if len(result) < len(text):
            logger.info(f"[ORCHESTRATOR] Removed duplicates: {len(text)} -> {len(result)} chars")
        
        return result
    
    # =========================================================================
    # HELPER METHODS FOR ENHANCED MODULES
    # =========================================================================
    
    def _extract_enhanced_modules(
        self,
        structured: StructuredOutput,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        query: str
    ):
        """Extract enhanced module data from chunks (for legacy standard responses)."""
        # Gap Analysis
        gap_data = self.gap_analysis_module.extract(
            llm_output=llm_output,
            chunks=chunks,
            query=query
        )
        if gap_data:
            structured.gap_analysis = gap_data.to_dict()
        
        # Red Flags
        if chunks:
            first_meta = chunks[0].get("metadata", {})
            log_event("RED_FLAGS_INPUT", {
                "chunk_count": len(chunks),
                "first_chunk_metadata_keys": list(first_meta.keys()),
            })
        
        red_flags_data = self.red_flags_module.extract(
            chunks=chunks,
            llm_output=llm_output
        )
        self._last_red_flags_data = red_flags_data
        if red_flags_data:
            structured.red_flags = red_flags_data.to_dict()
        
        # Timeline
        timeline_data = self.timeline_module.extract(
            chunks=chunks,
            llm_output=llm_output
        )
        if timeline_data:
            structured.timeline = timeline_data.to_dict()
    
    def _format_red_flags_section(self, structured: StructuredOutput, query_type: str) -> str:
        """
        Format Red Flags Analysis section. ALWAYS returns content for single_candidate queries.
        
        This is a MANDATORY module that shows either:
        - Detected red flags with severity levels
        - "No red flags detected" for clean candidates
        
        Args:
            structured: The structured output with red_flags data
            query_type: Type of query (single_candidate, comparison, etc.)
            
        Returns:
            Formatted markdown string for Red Flags Analysis section
        """
        # Try to get the original RedFlagsData object first
        red_flags_data = getattr(self, '_last_red_flags_data', None)
        
        if red_flags_data:
            flag_count = len(red_flags_data.flags) if red_flags_data.flags else 0
            clean_count = len(red_flags_data.clean_candidates) if red_flags_data.clean_candidates else 0
            logger.info(f"[ORCHESTRATOR] Red flags data: {flag_count} flags, {clean_count} clean candidates")
            
            # Use module's format method
            formatted = self.red_flags_module.format(red_flags_data)
            if formatted:
                return formatted
            
            # If format returned empty but we have clean candidates, build manually
            if clean_count > 0:
                names = ", ".join(red_flags_data.clean_candidates[:3])
                return f"### 🚩 Red Flags Analysis\n\n✅ **No se detectaron red flags** para: {names}"
        
        # Fallback: reconstruct from structured.red_flags dict
        elif structured.red_flags:
            from .modules.red_flags_module import RedFlagsData, RedFlag
            flag_count = len(structured.red_flags.get('flags', []))
            clean_count = len(structured.red_flags.get('clean_candidates', []))
            logger.info(f"[ORCHESTRATOR] Red flags from dict: {flag_count} flags, {clean_count} clean")
            
            red_flags_data = self._reconstruct_red_flags(structured.red_flags)
            if red_flags_data:
                formatted = self.red_flags_module.format(red_flags_data)
                if formatted:
                    return formatted
                
                # Manual fallback for clean candidates
                if clean_count > 0:
                    names = ", ".join(structured.red_flags.get('clean_candidates', [])[:3])
                    return f"### 🚩 Red Flags Analysis\n\n✅ **No se detectaron red flags** para: {names}"
        
        # For single_candidate queries, ALWAYS show something
        if query_type == "single_candidate":
            logger.warning("[ORCHESTRATOR] No red flags data but single_candidate query - showing default")
            return "### 🚩 Red Flags Analysis\n\n✅ **No se detectaron red flags significativas.**"
        
        logger.info("[ORCHESTRATOR] No red flags section generated")
        return ""
    
    def _reconstruct_gap_analysis(self, data: Dict[str, Any]):
        """Reconstruct GapAnalysisData from dict for formatting."""
        from .modules import GapAnalysisData, SkillGap
        
        try:
            skill_gaps = [
                SkillGap(
                    skill=g.get("skill", ""),
                    importance=g.get("importance", "preferred"),
                    candidates_missing=g.get("candidates_missing", []),
                    candidates_have=g.get("candidates_have", [])
                )
                for g in data.get("skill_gaps", [])
            ]
            
            return GapAnalysisData(
                required_skills=data.get("required_skills", []),
                skill_gaps=skill_gaps,
                coverage_score=data.get("coverage_score", 0),
                best_coverage_candidate=data.get("best_coverage_candidate"),
                summary=data.get("summary", "")
            )
        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] Failed to reconstruct gap analysis: {e}")
            return None
    
    def _reconstruct_red_flags(self, data: Dict[str, Any]):
        """Reconstruct RedFlagsData from dict for formatting."""
        from .modules import RedFlagsData, RedFlag
        
        try:
            flags = [
                RedFlag(
                    flag_type=f.get("flag_type", ""),
                    severity=f.get("severity", "low"),
                    description=f.get("description", ""),
                    candidate_name=f.get("candidate_name", ""),
                    details=f.get("details", {})
                )
                for f in data.get("flags", [])
            ]
            
            return RedFlagsData(
                flags=flags,
                candidates_with_flags=data.get("candidates_with_flags", {}),
                high_risk_candidates=data.get("high_risk_candidates", []),
                clean_candidates=data.get("clean_candidates", []),
                summary=data.get("summary", "")
            )
        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] Failed to reconstruct red flags: {e}")
            return None
    
    def _reconstruct_timeline(self, data: Dict[str, Any]):
        """Reconstruct TimelineData from dict for formatting."""
        from .modules import TimelineData, CandidateTimeline
        from .modules.timeline_module import TimelineEntry
        
        try:
            timelines = []
            for t in data.get("timelines", []):
                entries = [
                    TimelineEntry(
                        year_start=e.get("year_start", 2000),
                        year_end=e.get("year_end"),
                        title=e.get("title", ""),
                        company=e.get("company", ""),
                        is_current=e.get("is_current", False),
                        duration_years=e.get("duration_years", 0),
                        transition_type=e.get("transition_type", "")
                    )
                    for e in t.get("entries", [])
                ]
                
                timelines.append(CandidateTimeline(
                    candidate_name=t.get("candidate_name", ""),
                    cv_id=t.get("cv_id", ""),
                    entries=entries,
                    career_span_years=t.get("career_span_years", 0),
                    total_companies=t.get("total_companies", 0),
                    progression_score=t.get("progression_score", 0),
                    current_role=t.get("current_role")
                ))
            
            return TimelineData(
                timelines=timelines,
                summary=data.get("summary", "")
            )
        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] Failed to reconstruct timeline: {e}")
            return None
    
# Singleton instance
_orchestrator = None


def get_orchestrator() -> OutputOrchestrator:
    """
    Get singleton orchestrator instance.
    
    This is what RAG service imports and uses.
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = OutputOrchestrator()
    return _orchestrator


def reset_orchestrator():
    """Reset singleton for testing or after code changes."""
    global _orchestrator
    _orchestrator = None
    logger.info("[ORCHESTRATOR] Singleton reset")


# FORCE RESET on module reload - ensures hot-reload picks up code changes
reset_orchestrator()
