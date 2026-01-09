"""
RANKING STRUCTURE

Structure for ranking candidates for a specific role.
Combines MODULES:
- ThinkingModule
- RankingCriteriaModule
- RankingTableModule
- TopPickModule
- ConclusionModule

This structure is used when user asks for ranking:
- "top 5 candidates for backend"
- "rank candidates for this role"
- "best candidates for senior developer"
"""

import logging
from typing import Dict, Any, List, Optional

from ..modules import ThinkingModule, ConclusionModule, AnalysisModule
from ..modules.ranking_criteria_module import RankingCriteriaModule
from ..modules.ranking_table_module import RankingTableModule
from ..modules.top_pick_module import TopPickModule

logger = logging.getLogger(__name__)


class RankingStructure:
    """
    Assembles the Ranking Structure using modules.
    
    This STRUCTURE combines modules to create ranked candidate view.
    """
    
    def __init__(self):
        self.thinking_module = ThinkingModule()
        self.analysis_module = AnalysisModule()
        self.ranking_criteria_module = RankingCriteriaModule()
        self.ranking_table_module = RankingTableModule()
        self.top_pick_module = TopPickModule()
        self.conclusion_module = ConclusionModule()
    
    def assemble(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        query: str = "",
        job_context: str = "",
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Assemble all components of Ranking Structure.
        
        Args:
            llm_output: Raw LLM response
            chunks: CV chunks with metadata
            query: Original ranking query
            job_context: Optional job description context
            
        Returns:
            dict with structure_type and all components for frontend
        """
        logger.info(f"[RANKING_STRUCTURE] Assembling ranking for: {query[:50]}...")
        
        # Extract thinking from LLM output
        thinking = self.thinking_module.extract(llm_output)
        
        # Extract ranking criteria
        criteria_data = self.ranking_criteria_module.extract(
            query=query,
            llm_output=llm_output,
            job_context=job_context
        )
        
        # Generate ranking table
        criteria_list = criteria_data.to_dict()["criteria"] if criteria_data else []
        ranking_data = self.ranking_table_module.extract(
            chunks=chunks,
            criteria=criteria_list,
            llm_output=llm_output
        )
        
        # Generate top pick recommendation
        ranked_list = ranking_data.to_dict()["ranked"] if ranking_data else []
        top_pick_data = self.top_pick_module.extract(
            ranked_candidates=ranked_list,
            llm_output=llm_output,
            criteria=criteria_list
        )
        
        # Extract conclusion - ensure consistency with ranking data
        conclusion = self.conclusion_module.extract(llm_output)
        
        # Check if conclusion mentions top candidate, if not generate consistent conclusion
        if conclusion and top_pick_data:
            top_candidate_name = top_pick_data.candidate_name.lower()
            conclusion_lower = conclusion.lower()
            if top_candidate_name not in conclusion_lower:
                logger.info(f"[RANKING_STRUCTURE] Conclusion doesn't mention top candidate {top_pick_data.candidate_name}, generating consistent conclusion")
                conclusion = self._generate_consistent_conclusion(top_pick_data, ranked_list)
        elif not conclusion and top_pick_data:
            conclusion = self._generate_consistent_conclusion(top_pick_data, ranked_list)
        
        # Extract analysis - ensure consistency with ranking data
        # First try to extract from LLM, but if it mentions different candidates, use ranking data
        analysis = self.analysis_module.extract(llm_output, "", conclusion or "")
        
        # Check if analysis mentions top candidate, if not generate fallback
        if analysis and top_pick_data:
            top_candidate_name = top_pick_data.candidate_name.lower()
            analysis_lower = analysis.lower()
            if top_candidate_name not in analysis_lower:
                logger.info(f"[RANKING_STRUCTURE] Analysis doesn't mention top candidate {top_pick_data.candidate_name}, generating fallback")
                analysis = self._generate_consistent_analysis(ranking_data, top_pick_data, criteria_list)
        elif not analysis:
            analysis = self._generate_consistent_analysis(ranking_data, top_pick_data, criteria_list)
        
        return {
            "structure_type": "ranking",
            "query": query,
            "thinking": thinking,
            "analysis": analysis,
            "criteria": criteria_data.to_dict() if criteria_data else None,
            "ranking_table": ranking_data.to_dict() if ranking_data else None,
            "top_pick": {
                "candidate_name": top_pick_data.candidate_name,
                "cv_id": top_pick_data.cv_id,
                "overall_score": top_pick_data.overall_score,
                "key_strengths": top_pick_data.key_strengths,
                "justification": top_pick_data.justification,
                "runner_up": top_pick_data.runner_up,
                "runner_up_cv_id": top_pick_data.runner_up_cv_id
            } if top_pick_data else None,
            "total_ranked": len(ranked_list),
            "conclusion": conclusion,
            "raw_content": llm_output
        }
    
    def _generate_consistent_analysis(self, ranking_data, top_pick_data, criteria_list):
        """
        Generate analysis that is consistent with the ranking data.
        
        This ensures the analysis mentions the same top candidates as the ranking table.
        """
        if not ranking_data or not top_pick_data:
            return None
        
        ranked_dict = ranking_data.to_dict()
        ranked_candidates = ranked_dict.get("ranked", [])
        
        if not ranked_candidates:
            return None
        
        parts = []
        
        # 1. Total candidates analyzed
        total_candidates = len(ranked_candidates)
        parts.append(f"Analyzed {total_candidates} candidates based on the specified criteria.")
        
        # 2. Top candidates with CONCRETE DATA (experience years)
        if len(ranked_candidates) >= 2:
            top_name = top_pick_data.candidate_name
            top_score = top_pick_data.overall_score
            top_exp = ranked_candidates[0].get("experience_years", 0)
            runner_up = ranked_candidates[1].get("candidate_name", "Unknown")
            runner_up_score = ranked_candidates[1].get("overall_score", 0)
            runner_up_exp = ranked_candidates[1].get("experience_years", 0)
            
            # Include experience years in the analysis
            if top_exp > 0:
                parts.append(f"{top_name} emerges as the top choice with {top_exp:.0f} years of experience and an overall score of {top_score:.0f}%.")
            else:
                parts.append(f"{top_name} emerges as the top choice with an overall score of {top_score:.0f}%.")
            
            if runner_up_exp > 0:
                parts.append(f"Runner-up: {runner_up} with {runner_up_exp:.0f} years of experience ({runner_up_score:.0f}%).")
            else:
                parts.append(f"Runner-up: {runner_up} with {runner_up_score:.0f}%.")
        
        # 3. Score distribution
        scores = [c.get("overall_score", 0) for c in ranked_candidates]
        high_scores = [c for c in ranked_candidates if c.get("overall_score", 0) >= 70]
        medium_scores = [c for c in ranked_candidates if 40 <= c.get("overall_score", 0) < 70]
        low_scores = [c for c in ranked_candidates if c.get("overall_score", 0) < 40]
        
        if high_scores:
            high_names = [c.get("candidate_name", "Unknown") for c in high_scores[:3]]
            parts.append(f"{len(high_scores)} candidates have high match scores (≥70%): {', '.join(high_names)}.")
        
        if medium_scores:
            parts.append(f"{len(medium_scores)} candidates have medium match scores (40-69%).")
        
        if low_scores:
            parts.append(f"{len(low_scores)} candidates have low match scores (<40%).")
        
        # 4. Key strengths of top candidate - FILTER OUT CANDIDATE NAMES
        if top_pick_data.key_strengths:
            # Filter out items that look like person names (2+ capitalized words)
            valid_strengths = []
            for strength in top_pick_data.key_strengths[:5]:  # Check more items
                words = strength.split()
                # Skip if looks like a person name
                if len(words) >= 2 and all(w[0].isupper() for w in words if len(w) > 1):
                    logger.debug(f"[RANKING_STRUCTURE] Skipping likely person name in strengths: {strength}")
                    continue
                valid_strengths.append(strength)
                if len(valid_strengths) >= 3:
                    break
            
            if valid_strengths:
                strengths_text = ", ".join(valid_strengths)
                parts.append(f"Key strengths of the top candidate include: {strengths_text}.")
        
        # 5. Criteria used - FILTER OUT CANDIDATE NAMES
        if criteria_list:
            valid_criteria = []
            for c in criteria_list[:10]:  # Check more items
                criterion_name = c.get("name", "Unknown")
                words = criterion_name.split()
                # Skip if looks like a person name (2+ capitalized words)
                if len(words) >= 2 and all(w[0].isupper() for w in words if len(w) > 1):
                    logger.debug(f"[RANKING_STRUCTURE] Skipping likely person name in criteria: {criterion_name}")
                    continue
                valid_criteria.append(criterion_name)
                if len(valid_criteria) >= 3:
                    break
            
            if valid_criteria:
                parts.append(f"Primary evaluation criteria: {', '.join(valid_criteria)}.")
        
        return " ".join(parts)
    
    def _generate_consistent_conclusion(self, top_pick_data, ranked_candidates):
        """
        Generate conclusion that is consistent with the ranking data.
        
        This ensures the conclusion mentions the same top candidate as the ranking table.
        """
        if not top_pick_data:
            return None
        
        parts = []
        
        # Top candidate recommendation
        top_name = top_pick_data.candidate_name
        top_score = top_pick_data.overall_score
        
        parts.append(f"{top_name} is the recommended candidate with an overall score of {top_score:.0f}%.")
        
        # Justification
        if top_pick_data.justification:
            parts.append(top_pick_data.justification)
        
        # Key strengths - FILTER OUT CANDIDATE NAMES
        if top_pick_data.key_strengths:
            # Filter out items that look like person names (2+ capitalized words)
            valid_strengths = []
            for strength in top_pick_data.key_strengths[:5]:  # Check more items
                words = strength.split()
                # Skip if looks like a person name
                if len(words) >= 2 and all(w[0].isupper() for w in words if len(w) > 1):
                    logger.debug(f"[RANKING_STRUCTURE] Skipping likely person name in conclusion strengths: {strength}")
                    continue
                valid_strengths.append(strength)
                if len(valid_strengths) >= 3:
                    break
            
            if valid_strengths:
                strengths_text = ", ".join(valid_strengths)
                parts.append(f"Key strengths: {strengths_text}.")
        
        # Runner-up mention
        if top_pick_data.runner_up and len(ranked_candidates) > 1:
            parts.append(f"Runner-up: {top_pick_data.runner_up}.")
        
        return " ".join(parts)
