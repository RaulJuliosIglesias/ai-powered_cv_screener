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
from typing import Dict, Any, List, Optional

from ..modules import ThinkingModule, ConclusionModule, GapAnalysisModule, AnalysisModule
from ..modules.requirements_module import RequirementsModule
from ..modules.match_score_module import MatchScoreModule

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
        job_description: str = ""
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
        
        # Extract analysis
        analysis = self.analysis_module.extract(llm_output, "", conclusion or "")
        
        # Get best match - use overall_score for frontend compatibility
        best_match = None
        if match_data and match_data.matches:
            top = match_data.matches[0]
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
                "overall_score": top.overall_match,  # Frontend expects overall_score
                "overall_match": top.overall_match,  # Keep for compatibility
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
        from ..modules.requirements_module import RequirementsData, Requirement
        
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
