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
        
        # Check if this is an experience-focused query
        query_lower = query.lower()
        is_experience_query = any(kw in query_lower for kw in ['most experience', 'most total experience', 'highest experience', 'most years'])
        
        ranking_data = self.ranking_table_module.extract(
            chunks=chunks,
            criteria=criteria_list,
            llm_output=llm_output
        )
        
        # PHASE 7.3 FIX: Validate ranking for "most experience" queries
        # If query asks for "most experience", ensure ranking is sorted by experience
        ranked_list = ranking_data.to_dict()["ranked"] if ranking_data else []
        if is_experience_query:
            ranked_list = self._rerank_by_experience(ranked_list, chunks)
            logger.info(f"[RANKING_STRUCTURE] Re-ranked by experience for query: {query[:50]}")
            
            # Update ranking_data with the re-ranked list
            if ranking_data:
                ranking_data.ranked = [
                    RankedCandidate(
                        rank=i+1,
                        candidate_name=r["candidate_name"],
                        cv_id=r["cv_id"],
                        overall_score=r["overall_score"],
                        criterion_scores=r.get("criterion_scores", {}),
                        strengths=r.get("strengths", []),
                        weaknesses=r.get("weaknesses", []),
                        experience_years=r.get("experience_years", 0),
                        avg_tenure=r.get("avg_tenure", 0),
                        job_hopping_score=r.get("job_hopping_score", 0.5),
                        seniority=r.get("seniority", "")
                    )
                    for i, r in enumerate(ranked_list)
                ]
        top_pick_data = self.top_pick_module.extract(
            ranked_candidates=ranked_list,
            llm_output=llm_output,
            criteria=criteria_list
        )
        
        # FIX: Validate top_pick candidate against chunks
        if top_pick_data:
            valid_names = set()
            for chunk in chunks:
                meta = chunk.get("metadata", {})
                name = meta.get("candidate_name", "")
                if name:
                    valid_names.add(name.lower().strip())
            
            # If top_pick name is invalid, find valid one from ranked_list
            if top_pick_data.candidate_name.lower().strip() not in valid_names:
                logger.warning(f"[RANKING_STRUCTURE] Invalid top_pick name: {top_pick_data.candidate_name}")
                for ranked in ranked_list:
                    if ranked.get("candidate_name", "").lower().strip() in valid_names:
                        top_pick_data.candidate_name = ranked["candidate_name"]
                        top_pick_data.cv_id = ranked.get("cv_id", "")
                        top_pick_data.overall_score = ranked.get("overall_score", 50)
                        logger.info(f"[RANKING_STRUCTURE] Using valid candidate: {top_pick_data.candidate_name}")
                        break
            
            # Ensure score is not 0%
            if top_pick_data.overall_score <= 0:
                top_pick_data.overall_score = 50  # Minimum floor
                logger.warning(f"[RANKING_STRUCTURE] Applied score floor: 50%")
        
        # Extract conclusion from LLM
        conclusion = self.conclusion_module.extract(llm_output)
        
        # PHASE 1.1 FIX: Validate conclusion aligns with ranking
        # If LLM conclusion mentions different #1 candidate than our ranking, fix it
        if conclusion and top_pick_data and ranked_list:
            conclusion = self._validate_and_fix_conclusion(
                conclusion=conclusion,
                top_pick=top_pick_data,
                ranked_list=ranked_list,
                query=query
            )
        
        # ONLY generate fallback if LLM provided NO conclusion at all
        if not conclusion and top_pick_data:
            logger.info(f"[RANKING_STRUCTURE] No conclusion from LLM, generating minimal fallback")
            conclusion = self._generate_minimal_fallback_conclusion(top_pick_data, ranked_list)
        
        # Extract analysis from LLM - ALWAYS preserve the LLM's reasoning
        # The LLM explained WHY it chose certain candidates - this is the answer to the user's question
        analysis = self.analysis_module.extract(llm_output, "", conclusion or "")
        
        # PHASE 5.2 + 6.5 FIX: Check if analysis is just a table header (empty table) or too short
        if analysis:
            stripped = analysis.strip()
            should_regenerate = False
            
            # Check 1: Empty or near-empty table
            if stripped.startswith('|'):
                lines = [l for l in stripped.split('\n') if l.strip()]
                # Count actual data rows (not headers or separators)
                data_rows = [l for l in lines if l.strip().startswith('|') and '---' not in l]
                if len(data_rows) <= 1:
                    logger.warning(f"[RANKING_STRUCTURE] Analysis is empty table (only {len(data_rows)} data rows)")
                    should_regenerate = True
            
            # Check 2: Too short to be meaningful (less than 50 chars of actual content)
            if not should_regenerate and len(stripped) < 50:
                logger.warning(f"[RANKING_STRUCTURE] Analysis too short ({len(stripped)} chars)")
                should_regenerate = True
            
            # Check 3: Only contains table header keywords without actual analysis
            header_only_keywords = ['candidate', 'experience', 'score', 'match', 'why']
            if not should_regenerate:
                words = stripped.lower().split()
                keyword_count = sum(1 for w in words if any(k in w for k in header_only_keywords))
                non_keyword_count = len(words) - keyword_count
                if keyword_count > 0 and non_keyword_count < 10:
                    logger.warning(f"[RANKING_STRUCTURE] Analysis is mostly table headers")
                    should_regenerate = True
            
            if should_regenerate:
                analysis = None
        
        # ONLY generate fallback if LLM provided NO analysis at all
        if not analysis:
            logger.info(f"[RANKING_STRUCTURE] No analysis from LLM, generating from ranking data")
            # Generate analysis from actual ranking data
            if ranking_data and top_pick_data:
                analysis = self._generate_consistent_analysis(ranking_data, top_pick_data, criteria_data.criteria if criteria_data else [])
            if not analysis:
                analysis = self._extract_analysis_from_raw(llm_output)
        
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
            "raw_content": llm_output,
            "show_experience_instead_of_score": is_experience_query  # Flag for frontend display
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
    
    def _validate_and_fix_conclusion(
        self,
        conclusion: str,
        top_pick,
        ranked_list: list,
        query: str
    ) -> str:
        """
        PHASE 1.1 FIX: Validate that conclusion mentions the correct top candidate.
        
        If conclusion mentions a different candidate as #1, replace with
        a conclusion that aligns with the actual ranking.
        
        Args:
            conclusion: LLM-generated conclusion text
            top_pick: TopPickData with the actual #1 candidate
            ranked_list: Full ranking list
            query: Original user query
            
        Returns:
            Validated/fixed conclusion text
        """
        import re
        
        if not conclusion or not top_pick:
            return conclusion
        
        top_name = top_pick.candidate_name.lower().strip()
        top_cv_id = top_pick.cv_id
        
        # Extract candidate names mentioned in conclusion
        # Pattern: **[Name](cv:id)** or just **Name** or [Name](cv:id)
        mentioned_pattern = r'\*\*\[?([^\]|\*]+)\]?\*\*|\[([^\]]+)\]\(cv:'
        matches = re.findall(mentioned_pattern, conclusion, re.IGNORECASE)
        
        # Flatten matches and get first mentioned candidate
        mentioned_names = []
        for match in matches:
            name = match[0] or match[1]
            if name:
                mentioned_names.append(name.lower().strip())
        
        # Check if the FIRST mentioned candidate matches our top pick
        first_mentioned = mentioned_names[0] if mentioned_names else None
        
        if first_mentioned:
            # Check if first mention is our top candidate
            top_name_parts = top_name.split()
            first_parts = first_mentioned.split()
            
            # Match if any significant name part matches
            is_match = (
                top_name in first_mentioned or 
                first_mentioned in top_name or
                any(p in first_mentioned for p in top_name_parts if len(p) > 3) or
                any(p in top_name for p in first_parts if len(p) > 3)
            )
            
            if not is_match:
                # MISMATCH DETECTED - conclusion mentions wrong candidate first
                logger.warning(
                    f"[RANKING_STRUCTURE] Conclusion mismatch: mentions '{first_mentioned}' "
                    f"but top pick is '{top_name}'. Generating aligned conclusion."
                )
                
                # Generate a conclusion that aligns with the ranking
                return self._generate_aligned_conclusion(top_pick, ranked_list, query)
        
        return conclusion
    
    def _generate_aligned_conclusion(self, top_pick, ranked_list: list, query: str) -> str:
        """
        Generate a conclusion that is aligned with the ranking results.
        
        This is used when the LLM's conclusion contradicts our ranking.
        """
        top_name = top_pick.candidate_name
        top_cv_id = top_pick.cv_id
        top_score = top_pick.overall_score
        
        # Get experience from ranked_list if available
        top_exp = 0
        for r in ranked_list:
            if r.get("cv_id") == top_cv_id or r.get("candidate_name", "").lower() == top_name.lower():
                top_exp = r.get("experience_years", 0)
                break
        
        # Build conclusion based on query type
        query_lower = query.lower()
        
        if "most experience" in query_lower or "most total" in query_lower:
            # Experience-focused query
            if top_exp > 0:
                conclusion = f"**[{top_name}](cv:{top_cv_id})** has the most total experience with {top_exp:.0f} years."
            else:
                conclusion = f"**[{top_name}](cv:{top_cv_id})** is the candidate with the most total experience based on the available data."
        
        elif "top 5" in query_lower or "top five" in query_lower:
            # Top 5 request
            top_5 = ranked_list[:5] if len(ranked_list) >= 5 else ranked_list
            names = [f"**[{r.get('candidate_name', 'Unknown')}](cv:{r.get('cv_id', '')})**" for r in top_5]
            conclusion = f"The top 5 candidates are: {', '.join(names)}."
        
        elif "top" in query_lower or "best" in query_lower or "rank" in query_lower:
            # General ranking query
            conclusion = (
                f"**[{top_name}](cv:{top_cv_id})** emerges as the top recommendation "
                f"with an overall score of {top_score:.0f}%."
            )
            if len(ranked_list) >= 2:
                runner = ranked_list[1]
                runner_name = runner.get("candidate_name", "Unknown")
                runner_cv = runner.get("cv_id", "")
                conclusion += f" Runner-up: **[{runner_name}](cv:{runner_cv})**."
        
        else:
            # Default conclusion
            conclusion = f"**[{top_name}](cv:{top_cv_id})** is the top recommendation based on the analysis."
        
        logger.info(f"[RANKING_STRUCTURE] Generated aligned conclusion for '{top_name}'")
        return conclusion
    
    def _generate_minimal_fallback_conclusion(self, top_pick_data, ranked_list: list = None):
        """
        Generate a MINIMAL fallback conclusion only when LLM provided nothing.
        This should rarely be used - the LLM's response is preferred.
        """
        if not top_pick_data:
            return None
        
        name = top_pick_data.candidate_name
        cv_id = top_pick_data.cv_id
        score = top_pick_data.overall_score
        
        conclusion = f"**[{name}](cv:{cv_id})** is the top recommendation with {score:.0f}% match."
        
        # Add runner-up if available
        if ranked_list and len(ranked_list) >= 2:
            runner = ranked_list[1]
            runner_name = runner.get("candidate_name", "Unknown")
            runner_cv = runner.get("cv_id", "")
            conclusion += f" Runner-up: **[{runner_name}](cv:{runner_cv})**."
        
        return conclusion
    
    def _rerank_by_experience(self, ranked_list: list, chunks: list) -> list:
        """
        PHASE 7.3 FIX: Re-rank candidates by actual experience years.
        
        Used when query explicitly asks for "most experience" or similar.
        Ensures the candidate with the most years is ranked #1.
        """
        if not ranked_list:
            return ranked_list
        
        # Build experience lookup from chunks
        experience_lookup = {}
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            cv_id = chunk.get("cv_id") or meta.get("cv_id", "")
            exp = meta.get("total_experience_years", 0) or 0
            if cv_id:
                if cv_id not in experience_lookup or exp > experience_lookup[cv_id]:
                    experience_lookup[cv_id] = exp
        
        # Update experience in ranked_list and sort by experience
        for candidate in ranked_list:
            cv_id = candidate.get("cv_id", "")
            if cv_id in experience_lookup:
                candidate["experience_years"] = experience_lookup[cv_id]
        
        # Sort by experience_years descending
        sorted_list = sorted(
            ranked_list,
            key=lambda x: x.get("experience_years", 0),
            reverse=True
        )
        
        # Update ranks and scores based on experience
        max_exp = max((c.get("experience_years", 0) for c in sorted_list), default=1)
        for i, candidate in enumerate(sorted_list):
            candidate["rank"] = i + 1
            exp = candidate.get("experience_years", 0)
            # Score based on experience relative to max
            candidate["overall_score"] = round((exp / max(max_exp, 1)) * 100, 1) if max_exp > 0 else 50
        
        logger.info(f"[RANKING_STRUCTURE] Re-ranked: #1 is {sorted_list[0].get('candidate_name')} with {sorted_list[0].get('experience_years', 0)} years")
        return sorted_list
    
    def _extract_analysis_from_raw(self, llm_output: str) -> str:
        """
        Extract analysis content from raw LLM output when module extraction fails.
        Preserves the LLM's actual reasoning about the user's question.
        """
        import re
        
        # Try to find the Analysis section
        analysis_match = re.search(
            r'###?\s*Analysis\s*\n([\s\S]*?)(?=\n###|\n:::conclusion|$)',
            llm_output,
            re.IGNORECASE
        )
        if analysis_match:
            return analysis_match.group(1).strip()
        
        # Try to find content after thinking block but before conclusion
        post_thinking = re.sub(r':::thinking[\s\S]*?:::', '', llm_output, flags=re.IGNORECASE)
        pre_conclusion = re.sub(r':::conclusion[\s\S]*?:::', '', post_thinking, flags=re.IGNORECASE)
        
        # Remove tables
        content = re.sub(r'\|[^\n]*\|[\s\S]*?\|[^\n]*\|', '', pre_conclusion)
        content = content.strip()
        
        if content and len(content) > 50:
            return content[:1000]  # Limit length
        
        return None
