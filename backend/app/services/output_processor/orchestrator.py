"""
Orchestrator - Assembles structured output using ONLY modular components.

This is the MAIN ENTRY POINT that RAG service calls.
It coordinates processor and modules to build final output SEQUENTIALLY.

DO NOT create parallel assembly logic - use modules parametrically.
"""

import logging
import re
from typing import List, Dict, Any

from app.models.structured_output import StructuredOutput
from app.utils.debug_logger import log_orchestrator_processing, log_red_flags_module, log_event
from .processor import OutputProcessor
from .modules import (
    ThinkingModule,
    DirectAnswerModule,
    AnalysisModule,
    TableModule,
    ConclusionModule,
    # Enhanced modules (v5.1)
    GapAnalysisModule,
    RedFlagsModule,
    TimelineModule,
)

logger = logging.getLogger(__name__)


class OutputOrchestrator:
    """
    Main orchestrator - RAG service calls this.
    
    Coordinates:
    1. Extraction (via OutputProcessor using modules)
    2. Sequential assembly (using each module's format method)
    """
    
    def __init__(self):
        """Initialize with processor and modules."""
        self.processor = OutputProcessor()
        
        # Core module instances for formatting
        self.thinking_module = ThinkingModule()
        self.direct_answer_module = DirectAnswerModule()
        self.analysis_module = AnalysisModule()
        self.table_module = TableModule()
        self.conclusion_module = ConclusionModule()
        
        # Enhanced modules (v5.1)
        self.gap_analysis_module = GapAnalysisModule()
        self.red_flags_module = RedFlagsModule()
        self.timeline_module = TimelineModule()
        
        logger.info("[ORCHESTRATOR] Initialized with enhanced modules")
    
    def process(
        self,
        raw_llm_output: str,
        chunks: List[Dict[str, Any]] = None,
        query: str = "",
        query_type: str = "comparison",  # "comparison", "single_candidate", "red_flags"
        candidate_name: str = None
    ) -> tuple[StructuredOutput, str]:
        """
        Process LLM output into structured components and formatted answer.
        
        This is the MAIN METHOD that RAG service calls.
        
        Args:
            raw_llm_output: Raw text from LLM
            chunks: Retrieved CV chunks for fallback
            query: Original user query for enhanced modules (gap analysis, etc.)
            query_type: Type of query - determines output structure
                - "comparison": Multi-candidate comparison (default)
                - "single_candidate": Individual candidate profile
                - "red_flags": Red flags specific query
            candidate_name: Name of candidate for single_candidate queries
            
        Returns:
            Tuple of (StructuredOutput, formatted_answer_string)
        """
        logger.info(f"[ORCHESTRATOR] Processing with query_type={query_type}")
        logger.info("[ORCHESTRATOR] Starting processing")
        
        # STEP 0: PRE-PROCESS - Clean raw LLM output before any module processing
        cleaned_llm_output = self._pre_clean_llm_output(raw_llm_output)
        
        # STEP 1: Extract all components using processor (which uses modules)
        structured = self.processor.process(cleaned_llm_output, chunks)
        
        logger.info(
            f"[ORCHESTRATOR] Components extracted: "
            f"thinking={bool(structured.thinking)}, "
            f"table={bool(structured.table_data)}, "
            f"conclusion={bool(structured.conclusion)}, "
            f"analysis={bool(structured.analysis)}"
        )
        
        # STEP 1.5: Generate fallback analysis if none was extracted
        if not structured.analysis:
            fallback_analysis = self.analysis_module.generate_fallback(
                structured.direct_answer,
                structured.table_data,
                structured.conclusion
            )
            if fallback_analysis:
                structured.analysis = fallback_analysis
                logger.info(f"[ORCHESTRATOR] Generated fallback analysis: {len(fallback_analysis)} chars")
        
        # STEP 1.6: CRITICAL - Format candidate references with ÚNICO formato
        # Primero extraer nombres de candidatos de la tabla para detectarlos en texto
        candidate_map = {}  # {nombre: cv_id}
        if structured.table_data and hasattr(structured.table_data, 'rows'):
            for row in structured.table_data.rows:
                if hasattr(row, 'candidate_name') and hasattr(row, 'cv_id'):
                    candidate_map[row.candidate_name] = row.cv_id
        
        # Convierte [Nombre](cv_xxx) -> [📄](cv:cv_xxx) **Nombre**
        # Y también detecta nombres en texto plano y los convierte
        if structured.direct_answer:
            structured.direct_answer = self._format_candidate_references(structured.direct_answer, candidate_map)
        if structured.analysis:
            structured.analysis = self._format_candidate_references(structured.analysis, candidate_map)
        if structured.conclusion:
            structured.conclusion = self._format_candidate_references(structured.conclusion, candidate_map)
        
        # STEP 1.7: Extract enhanced modules (v5.1) from chunks
        if chunks:
            # Gap Analysis - uses query for requirement extraction
            gap_data = self.gap_analysis_module.extract(
                llm_output=cleaned_llm_output,
                chunks=chunks,
                query=query
            )
            if gap_data:
                structured.gap_analysis = gap_data.to_dict()
                logger.info(f"[ORCHESTRATOR] Gap analysis: {len(gap_data.skill_gaps)} gaps detected")
            
            # Red Flags
            # DEBUG LOGGING: Log chunk metadata before red flags extraction
            if chunks:
                first_meta = chunks[0].get("metadata", {})
                log_event("RED_FLAGS_INPUT", {
                    "chunk_count": len(chunks),
                    "first_chunk_metadata_keys": list(first_meta.keys()),
                    "first_chunk_job_hopping_score": first_meta.get("job_hopping_score"),
                    "first_chunk_avg_tenure": first_meta.get("avg_tenure_years"),
                    "first_chunk_total_exp": first_meta.get("total_experience_years"),
                })
            
            red_flags_data = self.red_flags_module.extract(
                chunks=chunks,
                llm_output=cleaned_llm_output
            )
            # Store the original object for later formatting (avoid reconstruction issues)
            self._last_red_flags_data = red_flags_data
            if red_flags_data:
                structured.red_flags = red_flags_data.to_dict()
                logger.info(f"[ORCHESTRATOR] Red flags: {len(red_flags_data.flags)} flags detected")
                
                # DEBUG LOGGING: Log red flags results
                log_red_flags_module(
                    red_flags_data.flags,
                    red_flags_data.high_risk_candidates,
                    red_flags_data.clean_candidates
                )
            
            # Timeline
            timeline_data = self.timeline_module.extract(
                chunks=chunks,
                llm_output=cleaned_llm_output
            )
            if timeline_data:
                structured.timeline = timeline_data.to_dict()
                logger.info(f"[ORCHESTRATOR] Timeline: {len(timeline_data.timelines)} candidates")
        
        # STEP 2: Assemble output SEQUENTIALLY using module format methods
        parts = []
        
        # 1. Thinking block (collapsible dropdown)
        if structured.thinking:
            formatted_thinking = self.thinking_module.format(structured.thinking)
            parts.append(formatted_thinking)
        
        # 2. Direct answer (no label)
        formatted_answer = self.direct_answer_module.format(structured.direct_answer)
        parts.append(formatted_answer)
        
        # 3. Analysis (ALWAYS present - fallback generated if needed)
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
        
        # SINGLE CANDIDATE: MANDATORY Risk Assessment module at the END
        # This module MUST appear for ALL single candidate queries
        if query_type == "single_candidate":
            logger.info(f"[ORCHESTRATOR] Building MANDATORY Risk Assessment for single candidate: {candidate_name}")
            risk_assessment = self._build_risk_assessment_section(chunks or [], candidate_name)
            if risk_assessment:
                parts.append(risk_assessment)
                logger.info(f"[ORCHESTRATOR] Risk Assessment ADDED ({len(risk_assessment)} chars)")
            else:
                # This should NEVER happen - _build_risk_assessment_section always returns content
                logger.error(f"[ORCHESTRATOR] Risk Assessment returned empty! This is a bug.")
                # Add fallback section anyway
                fallback = """---

### ⚠️ Risk Assessment

| Factor | Status | Details |
|:-------|:------:|:--------|
| **🚩 Red Flags** | ✅ None Detected | Clean profile |
| **🔄 Job Hopping** | ✅ Low | No data available |
| **⏸️ Employment Gaps** | ✅ None | No data available |
| **📊 Stability** | ✅ Stable | No data available |
| **🎯 Experience Level** | N/A | No data available |"""
                parts.append(fallback)
                logger.info(f"[ORCHESTRATOR] Risk Assessment FALLBACK added")
        
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
    
    def _build_risk_assessment_section(self, chunks: List[Dict[str, Any]], candidate_name: str = None) -> str:
        """
        Build Risk Assessment section for single candidate queries.
        
        MANDATORY MODULE - This ALWAYS returns a valid section for single candidate queries.
        Appears at the END of individual candidate profiles.
        Uses pre-calculated metadata from chunks.
        
        5 Components:
        1. 🚩 Red Flags - Overall risk status
        2. 🔄 Job Hopping - Mobility score and avg tenure
        3. ⏸️ Employment Gaps - Gap detection
        4. 📊 Stability - Career stability assessment
        5. 🎯 Experience Level - Seniority classification
        """
        logger.info(f"[RISK_ASSESSMENT] Building section for candidate: {candidate_name}")
        
        # Default values - will be overwritten if metadata is found
        score = 0.0
        tenure = 0.0
        exp = 0.0
        gaps = 0
        position_count = 0
        current_role = "N/A"
        current_company = "N/A"
        metadata_found = False
        
        # Find chunks for the target candidate
        target_chunks = chunks if chunks else []
        if candidate_name and chunks:
            target_chunks = [c for c in chunks if candidate_name.lower() in c.get("metadata", {}).get("candidate_name", "").lower()]
            if not target_chunks:
                target_chunks = chunks[:5]  # Fallback to first chunks
        
        logger.info(f"[RISK_ASSESSMENT] Analyzing {len(target_chunks)} chunks")
        
        # Extract metadata from chunks - try ALL chunks to find valid data
        for chunk in target_chunks:
            meta = chunk.get("metadata", {})
            
            # Try to get any available metric
            jh = meta.get("job_hopping_score")
            te = meta.get("total_experience_years")
            at = meta.get("avg_tenure_years")
            pc = meta.get("position_count")
            eg = meta.get("employment_gaps_count", 0)
            cr = meta.get("current_role")
            cc = meta.get("current_company")
            
            # Update values if we found something
            if jh is not None:
                score = float(jh)
                metadata_found = True
            if te is not None:
                exp = float(te)
                metadata_found = True
            if at is not None:
                tenure = float(at)
                metadata_found = True
            if pc is not None:
                position_count = int(pc)
                metadata_found = True
            if eg:
                gaps = int(eg)
            if cr and cr != "N/A":
                current_role = cr
            if cc and cc != "N/A":
                current_company = cc
            
            # If we found enough data, stop searching
            if metadata_found and (score > 0 or exp > 0 or tenure > 0):
                break
        
        logger.info(f"[RISK_ASSESSMENT] Metadata found: {metadata_found}, score={score}, exp={exp}, tenure={tenure}")
        
        # Determine statuses with icons (works even with default 0 values)
        if score < 0.3:
            jh_status, jh_icon = "Low", "✅"
        elif score < 0.5:
            jh_status, jh_icon = "Moderate", "⚡"
        else:
            jh_status, jh_icon = "High", "⚠️"
        
        gaps_status = "None" if gaps == 0 else f"{gaps} detected"
        gaps_icon = "✅" if gaps == 0 else "⚠️"
        
        stability = "Stable" if score < 0.3 else "Moderate" if score < 0.6 else "Unstable"
        stability_icon = "✅" if score < 0.3 else "⚡" if score < 0.6 else "⚠️"
        
        exp_level = "Entry" if exp < 3 else "Mid" if exp < 7 else "Senior" if exp < 15 else "Executive"
        
        has_flags = score > 0.5 or (tenure > 0 and tenure < 1.5) or gaps > 0
        rf_status = "Issues Found" if has_flags else "None Detected"
        rf_icon = "⚠️" if has_flags else "✅"
        
        # ALWAYS build and return the Risk Assessment table
        section = f"""---

### ⚠️ Risk Assessment

| Factor | Status | Details |
|:-------|:------:|:--------|
| **🚩 Red Flags** | {rf_icon} {rf_status} | {"High mobility or gaps detected" if has_flags else "Clean profile - no concerns"} |
| **🔄 Job Hopping** | {jh_icon} {jh_status} | Score: {score:.0%}, Avg tenure: {tenure:.1f} years |
| **⏸️ Employment Gaps** | {gaps_icon} {gaps_status} | {"Continuous employment history" if gaps == 0 else "Verify reasons during interview"} |
| **📊 Stability** | {stability_icon} {stability} | {position_count or 'N/A'} positions over {exp:.0f} years |
| **🎯 Experience Level** | {exp_level} | {current_role} @ {current_company} |"""
        
        logger.info(f"[RISK_ASSESSMENT] Section built: {len(section)} chars")
        return section


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
