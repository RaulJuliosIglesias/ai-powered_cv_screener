"""
JOB MATCH STRUCTURE

Structure for matching candidates against a job description.
Combines MODULES:
- ThinkingModule
- RequirementsModule
- MatchScoreModule
- GapAnalysisModule
- ConclusionModule

This structure is used when user asks for job matching:
- "match candidates to this JD"
- "who fits this role"
- "evaluate against these requirements"
"""

import logging
from typing import Any, Dict, List, Optional

from ..modules import AnalysisModule, ConclusionModule, GapAnalysisModule, ThinkingModule
from ..modules.match_score_module import MatchScoreModule
from ..modules.requirements_module import RequirementsModule

logger = logging.getLogger(__name__)


class JobMatchStructure:
    """
    Assembles the Job Match Structure using modules.
    
    This STRUCTURE combines modules to create job matching view.
    """
    
    def __init__(self):
        self.thinking_module = ThinkingModule()
        self.analysis_module = AnalysisModule()
        self.requirements_module = RequirementsModule()
        self.match_score_module = MatchScoreModule()
        self.gap_analysis_module = GapAnalysisModule()
        self.conclusion_module = ConclusionModule()
    
    def assemble(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        query: str = "",
        job_description: str = "",
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Assemble all components of Job Match Structure.
        
        Args:
            llm_output: Raw LLM response
            chunks: CV chunks with metadata
            query: Original query
            job_description: Job description text
            
        Returns:
            dict with structure_type and all components for frontend
        """
        logger.info("[JOB_MATCH_STRUCTURE] Assembling job match analysis")
        
        # Extract thinking from LLM output
        thinking = self.thinking_module.extract(llm_output)
        
        # Extract requirements from JD - DON'T use raw query as JD
        # If no explicit JD, extract implicit requirements from query context
        requirements_data = None
        if job_description:
            requirements_data = self.requirements_module.extract(
                job_description=job_description,
                llm_output=llm_output
            )
        else:
            # Generate smart requirements from query context
            requirements_data = self._extract_requirements_from_query(query, llm_output, chunks)
        
        # Calculate match scores
        requirements_list = requirements_data.to_dict()["requirements"] if requirements_data else []
        match_data = self.match_score_module.calculate(
            requirements=requirements_list,
            chunks=chunks,
            llm_output=llm_output
        )
        
        # Gap analysis
        gap_data = self.gap_analysis_module.extract(
            llm_output=llm_output,
            chunks=chunks,
            query=query
        )
        
        # Extract conclusion
        conclusion = self.conclusion_module.extract(llm_output)
        
        # PHASE 1.5 FIX: Validate conclusion aligns with best match
        # If conclusion mentions different candidate than best_match, fix it
        if conclusion and match_data and match_data.matches:
            conclusion = self._validate_and_fix_conclusion(
                conclusion=conclusion,
                match_data=match_data,
                query=query
            )
        
        # Extract analysis
        analysis = self.analysis_module.extract(llm_output, "", conclusion or "")
        
        # Get best match - use overall_score for frontend compatibility
        # FIX: Validate candidate data against chunks to avoid corrupt names/scores
        best_match = None
        if match_data and match_data.matches:
            top = match_data.matches[0]
            
            # VALIDATION 1: Ensure candidate_name exists in chunks
            valid_names = set()
            valid_cv_ids = set()
            for chunk in chunks:
                meta = chunk.get("metadata", {})
                name = meta.get("candidate_name", "")
                cv_id = meta.get("cv_id", "") or chunk.get("cv_id", "")
                if name:
                    valid_names.add(name.lower().strip())
                if cv_id:
                    valid_cv_ids.add(cv_id)
            
            # If top candidate name is not valid, try to find a valid one
            if top.candidate_name.lower().strip() not in valid_names:
                logger.warning(f"[JOB_MATCH_STRUCTURE] Invalid candidate name: {top.candidate_name}, searching for valid match")
                # Find first valid candidate from matches
                for match in match_data.matches:
                    if match.candidate_name.lower().strip() in valid_names:
                        top = match
                        logger.info(f"[JOB_MATCH_STRUCTURE] Using valid candidate: {top.candidate_name}")
                        break
            
            # VALIDATION 2: Ensure match score is reasonable (not 0% unless truly no match)
            score = top.overall_match
            if score <= 0 and top.met_requirements:
                # Has met requirements but 0 score - recalculate
                score = max(30, len(top.met_requirements) * 10)
                logger.warning(f"[JOB_MATCH_STRUCTURE] Fixed 0% score to {score}% based on {len(top.met_requirements)} met requirements")
            elif score <= 0:
                # No requirements met, give minimum score
                score = 30  # Minimum floor
                logger.warning(f"[JOB_MATCH_STRUCTURE] Applied minimum score floor: {score}%")
            
            # Build justification from met requirements and strengths
            justification_parts = []
            if top.met_requirements:
                justification_parts.append(f"Meets {len(top.met_requirements)} requirements")
            if top.strengths:
                justification_parts.append("; ".join(top.strengths[:2]))
            justification = ". ".join(justification_parts) if justification_parts else "Best match based on overall profile"
            
            best_match = {
                "candidate_name": top.candidate_name,
                "cv_id": top.cv_id,
                "overall_score": score,  # Frontend expects overall_score - now validated
                "overall_match": score,  # Keep for compatibility
                "key_strengths": top.strengths,  # Frontend expects key_strengths
                "strengths": top.strengths,
                "justification": justification,  # Frontend TopPickCard needs this
                "met_requirements": top.met_requirements,
                "missing_requirements": top.missing_requirements
            }
        
        return {
            "structure_type": "job_match",
            "query": query,
            "thinking": thinking,
            "analysis": analysis,
            "requirements": requirements_data.to_dict() if requirements_data else None,
            "match_scores": match_data.to_dict() if match_data else None,
            "gap_analysis": gap_data.to_dict() if gap_data else None,
            "best_match": best_match,
            "total_candidates": len(match_data.matches) if match_data else 0,
            "conclusion": conclusion,
            "raw_content": llm_output
        }
    
    def _extract_requirements_from_query(
        self,
        query: str,
        llm_output: str,
        chunks: List[Dict[str, Any]]
    ) -> Optional[Any]:
        """
        Extract smart requirements from query context when no explicit JD provided.
        
        Handles queries like:
        - "Who would fit a senior position?" → experience >= 5 years
        - "Who fits a frontend role?" → frontend skills
        - "Match for Python developer" → Python skill
        """
        import re

        from ..modules.requirements_module import Requirement, RequirementsData
        
        query_lower = query.lower()
        requirements = []
        
        # Experience level requirements
        if 'senior' in query_lower or 'lead' in query_lower or 'principal' in query_lower:
            requirements.append(Requirement(
                name="5+ years experience",
                category="required",
                req_type="experience",
                years=5
            ))
        elif 'junior' in query_lower or 'entry' in query_lower:
            requirements.append(Requirement(
                name="0-2 years experience",
                category="preferred",
                req_type="experience",
                years=0
            ))
        elif 'mid' in query_lower:
            requirements.append(Requirement(
                name="3-5 years experience",
                category="required",
                req_type="experience",
                years=3
            ))
        
        # Role-based requirements
        role_skills = {
            'frontend': ['JavaScript', 'React', 'CSS', 'HTML'],
            'backend': ['Python', 'Java', 'Node.js', 'SQL'],
            'fullstack': ['JavaScript', 'Python', 'React', 'SQL'],
            'devops': ['Docker', 'Kubernetes', 'AWS', 'CI/CD'],
            'data': ['Python', 'SQL', 'Machine Learning', 'Analytics'],
            'mobile': ['iOS', 'Android', 'React Native', 'Swift'],
        }
        
        for role, skills in role_skills.items():
            if role in query_lower:
                for skill in skills[:2]:  # Top 2 skills per role
                    requirements.append(Requirement(
                        name=skill,
                        category="preferred",
                        req_type="skill"
                    ))
                break
        
        # Technology mentions in query
        tech_patterns = [
            (r'\bpython\b', 'Python'),
            (r'\bjava\b', 'Java'),
            (r'\breact\b', 'React'),
            (r'\bnode\.?js\b', 'Node.js'),
            (r'\baws\b', 'AWS'),
            (r'\bdocker\b', 'Docker'),
        ]
        
        for pattern, tech in tech_patterns:
            if re.search(pattern, query_lower):
                requirements.append(Requirement(
                    name=tech,
                    category="required",
                    req_type="skill"
                ))
        
        # If still no requirements, extract from LLM output
        if not requirements and llm_output:
            llm_reqs = self.requirements_module._extract_from_llm(llm_output)
            requirements.extend(llm_reqs[:5])  # Limit to top 5
        
        # If still no requirements, create generic based on candidate pool
        if not requirements:
            logger.info("[JOB_MATCH_STRUCTURE] No explicit requirements, using candidate-based scoring")
            # Return None to signal match_score_module to use similarity-based scoring
            return RequirementsData(requirements=[], job_title="General Fit", total_required=0, total_preferred=0)
        
        logger.info(f"[JOB_MATCH_STRUCTURE] Extracted {len(requirements)} requirements from query")
        
        return RequirementsData(
            requirements=requirements,
            job_title=self._extract_role_from_query(query),
            total_required=sum(1 for r in requirements if r.category == "required"),
            total_preferred=sum(1 for r in requirements if r.category != "required")
        )
    
    def _extract_role_from_query(self, query: str) -> str:
        """Extract job role/title from query."""
        import re
        patterns = [
            r'(?:for\s+(?:a\s+)?|fit\s+(?:a\s+)?|match\s+(?:for\s+)?(?:a\s+)?)([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+(?:position|role|job)',
            r'([a-zA-Z]+)\s+(?:developer|engineer|manager|analyst|designer)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).strip().title()
        
        return "Position"
    
    def _validate_and_fix_conclusion(
        self,
        conclusion: str,
        match_data,
        query: str
    ) -> str:
        """
        PHASE 1.5 FIX: Validate that conclusion mentions the correct best match.
        
        If conclusion mentions a different candidate as best fit, replace with
        a conclusion that aligns with the actual match scores.
        
        Args:
            conclusion: LLM-generated conclusion text
            match_data: MatchScoreData with ranked matches
            query: Original user query
            
        Returns:
            Validated/fixed conclusion text
        """
        import re
        
        if not conclusion or not match_data or not match_data.matches:
            return conclusion
        
        best_match = match_data.matches[0]
        best_name = best_match.candidate_name.lower().strip()
        
        # Extract candidate names mentioned in conclusion
        # Pattern: **[Name](cv:id)** or just **Name** or [Name](cv:id)
        mentioned_pattern = r'\*\*\[?([^\]|\*]+)\]?\*\*|\[([^\]]+)\]\(cv:'
        matches = re.findall(mentioned_pattern, conclusion, re.IGNORECASE)
        
        # Also look for "X is the best fit" patterns
        best_fit_pattern = r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,2})\s+is\s+(?:the\s+)?(?:best|most\s+suitable|top|ideal)\s+(?:fit|match|candidate)'
        best_fit_matches = re.findall(best_fit_pattern, conclusion, re.IGNORECASE)
        
        # Flatten matches and get first mentioned candidate
        mentioned_names = []
        for match in matches:
            name = match[0] or match[1]
            if name:
                mentioned_names.append(name.lower().strip())
        
        for name in best_fit_matches:
            if name.lower().strip() not in mentioned_names:
                mentioned_names.insert(0, name.lower().strip())  # Insert at beginning (strongest signal)
        
        # Check if any mentioned candidate as "best fit" matches our actual best match
        first_mentioned = mentioned_names[0] if mentioned_names else None
        
        if first_mentioned:
            # Check if first mention is our best match
            best_name_parts = best_name.split()
            first_parts = first_mentioned.split()
            
            # Match if any significant name part matches
            is_match = (
                best_name in first_mentioned or 
                first_mentioned in best_name or
                any(p in first_mentioned for p in best_name_parts if len(p) > 3) or
                any(p in best_name for p in first_parts if len(p) > 3)
            )
            
            if not is_match:
                # MISMATCH DETECTED - conclusion mentions wrong candidate
                logger.warning(
                    f"[JOB_MATCH_STRUCTURE] Conclusion mismatch: mentions '{first_mentioned}' "
                    f"but best match is '{best_name}'. Generating aligned conclusion."
                )
                
                # Generate a conclusion that aligns with the match scores
                return self._generate_aligned_conclusion(best_match, match_data, query)
        
        return conclusion
    
    def _generate_aligned_conclusion(self, best_match, match_data, query: str) -> str:
        """
        Generate a conclusion that is aligned with the match score results.
        
        This is used when the LLM's conclusion contradicts our match scores.
        """
        name = best_match.candidate_name
        cv_id = best_match.cv_id
        score = best_match.overall_match
        
        # Build justification from met requirements
        justification_parts = []
        if best_match.met_requirements:
            justification_parts.append(f"meets {len(best_match.met_requirements)} key requirements")
        if best_match.strengths:
            justification_parts.append("; ".join(best_match.strengths[:2]))
        
        justification = " and ".join(justification_parts) if justification_parts else "best overall match"
        
        conclusion = (
            f"**[{name}](cv:{cv_id})** is the best fit for this position with a {score:.0f}% match score. "
            f"Key factors: {justification}."
        )
        
        # Add runner-up if available
        if len(match_data.matches) >= 2:
            runner = match_data.matches[1]
            runner_name = runner.candidate_name
            runner_cv = runner.cv_id
            runner_score = runner.overall_match
            conclusion += f" Runner-up: **[{runner_name}](cv:{runner_cv})** ({runner_score:.0f}%)."
        
        logger.info(f"[JOB_MATCH_STRUCTURE] Generated aligned conclusion for '{name}'")
        return conclusion
