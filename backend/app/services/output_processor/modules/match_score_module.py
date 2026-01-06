"""
MATCH SCORE MODULE

Calculates match percentage between candidates and job requirements.
Used by: JobMatchStructure, RankingStructure

Output format:
| Candidate | Overall Match | Met | Missing |
|-----------|---------------|-----|---------|
| **John** | 85% | 8/10 | AWS, Docker |
"""

import logging
import re
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CandidateMatch:
    """Match analysis for a single candidate."""
    candidate_name: str
    cv_id: str
    overall_match: float  # 0-100%
    met_requirements: List[str] = field(default_factory=list)
    missing_requirements: List[str] = field(default_factory=list)
    partial_requirements: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)


@dataclass
class MatchScoreData:
    """Container for match score results."""
    matches: List[CandidateMatch] = field(default_factory=list)
    total_requirements: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "matches": [
                {
                    "candidate_name": m.candidate_name,
                    "cv_id": m.cv_id,
                    "overall_match": m.overall_match,
                    "met_requirements": m.met_requirements,
                    "missing_requirements": m.missing_requirements,
                    "partial_requirements": m.partial_requirements,
                    "strengths": m.strengths
                }
                for m in self.matches
            ],
            "total_requirements": self.total_requirements
        }


class MatchScoreModule:
    """
    Module for calculating candidate-to-job match scores.
    """
    
    def calculate(
        self,
        requirements: List[Dict[str, Any]],
        chunks: List[Dict[str, Any]],
        llm_output: str = ""
    ) -> Optional[MatchScoreData]:
        """
        Calculate match scores for candidates against requirements.
        
        Args:
            requirements: List of requirement dicts
            chunks: CV chunks with metadata
            llm_output: LLM analysis for additional context
            
        Returns:
            MatchScoreData with match analysis
        """
        if not chunks:
            return None
        
        # Group chunks by candidate
        candidates = self._group_by_candidate(chunks)
        
        # Calculate match for each candidate
        matches = []
        for cv_id, data in candidates.items():
            if requirements:
                # Requirements-based matching
                match = self._calculate_candidate_match(data, requirements)
            else:
                # No requirements - use similarity-based scoring from chunks
                match = self._calculate_similarity_match(data, chunks)
            matches.append(match)
        
        # Sort by overall match descending
        matches.sort(key=lambda x: x.overall_match, reverse=True)
        
        logger.info(f"[MATCH_SCORE_MODULE] Calculated matches for {len(matches)} candidates")
        
        return MatchScoreData(
            matches=matches,
            total_requirements=len(requirements) if requirements else 1
        )
    
    def _group_by_candidate(
        self,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Dict]:
        """Group chunks by candidate and collect skills."""
        candidates = {}
        
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            cv_id = chunk.get("cv_id", "") or meta.get("cv_id", "")
            
            if not cv_id:
                continue
            
            if cv_id not in candidates:
                candidates[cv_id] = {
                    "name": meta.get("candidate_name", "Unknown"),
                    "cv_id": cv_id,
                    "skills": set(),
                    "experience_years": meta.get("total_experience_years", 0),
                    "education": meta.get("education_level", ""),
                    "certifications": set(),
                    "content": ""
                }
            
            # Collect skills
            skills_str = meta.get("skills", "")
            if skills_str:
                for skill in skills_str.split(","):
                    skill = skill.strip().lower()
                    if skill:
                        candidates[cv_id]["skills"].add(skill)
            
            # Collect certifications
            certs_str = meta.get("certifications", "")
            if certs_str:
                for cert in certs_str.split(","):
                    cert = cert.strip().lower()
                    if cert:
                        candidates[cv_id]["certifications"].add(cert)
            
            # Collect content for text matching
            content = chunk.get("content", "")
            if content:
                candidates[cv_id]["content"] += " " + content
        
        return candidates
    
    def _calculate_candidate_match(
        self,
        candidate_data: Dict,
        requirements: List[Dict[str, Any]]
    ) -> CandidateMatch:
        """Calculate match score for a single candidate."""
        met = []
        missing = []
        partial = []
        
        skills = candidate_data.get("skills", set())
        content = candidate_data.get("content", "").lower()
        experience = candidate_data.get("experience_years", 0)
        education = candidate_data.get("education", "").lower()
        certs = candidate_data.get("certifications", set())
        
        for req in requirements:
            req_name = req.get("name", "")
            req_type = req.get("type", "skill")
            req_years = req.get("years")
            req_name_lower = req_name.lower()
            
            matched = False
            partial_match = False
            
            if req_type == "skill":
                # Check if skill is in candidate's skills
                if any(req_name_lower in s or s in req_name_lower for s in skills):
                    matched = True
                elif req_name_lower in content:
                    partial_match = True
                    
            elif req_type == "experience":
                if req_years:
                    if experience >= req_years:
                        matched = True
                    elif experience >= req_years * 0.7:
                        partial_match = True
                else:
                    if experience > 0:
                        matched = True
                        
            elif req_type == "education":
                if req_name_lower in education or req_name_lower in content:
                    matched = True
                    
            elif req_type == "certification":
                if any(req_name_lower in c or c in req_name_lower for c in certs):
                    matched = True
                elif req_name_lower in content:
                    partial_match = True
            
            if matched:
                met.append(req_name)
            elif partial_match:
                partial.append(req_name)
            else:
                missing.append(req_name)
        
        # Calculate overall match percentage
        total = len(requirements) if requirements else 1
        # Full matches count as 1, partial as 0.5
        score = (len(met) + len(partial) * 0.5) / total * 100
        
        # Identify strengths
        strengths = self._identify_strengths(candidate_data, met)
        
        return CandidateMatch(
            candidate_name=candidate_data.get("name", "Unknown"),
            cv_id=candidate_data.get("cv_id", ""),
            overall_match=round(score, 1),
            met_requirements=met,
            missing_requirements=missing,
            partial_requirements=partial,
            strengths=strengths
        )
    
    def _calculate_similarity_match(
        self,
        candidate_data: Dict,
        chunks: List[Dict[str, Any]]
    ) -> CandidateMatch:
        """
        Calculate match score based on chunk similarity scores when no requirements provided.
        Used for generic queries like "who fits a senior position".
        """
        cv_id = candidate_data.get("cv_id", "")
        
        # Get similarity scores for this candidate's chunks
        scores = []
        for chunk in chunks:
            chunk_cv_id = chunk.get("cv_id", "") or chunk.get("metadata", {}).get("cv_id", "")
            if chunk_cv_id == cv_id:
                score = chunk.get("score", 0.5)
                scores.append(score)
        
        # Average similarity score, converted to percentage
        avg_score = sum(scores) / len(scores) if scores else 0.5
        overall_match = round(min(100, avg_score * 100), 1)
        
        # Identify strengths based on candidate data
        strengths = self._identify_strengths(candidate_data, [])
        
        return CandidateMatch(
            candidate_name=candidate_data.get("name", "Unknown"),
            cv_id=cv_id,
            overall_match=overall_match,
            met_requirements=[],
            missing_requirements=[],
            partial_requirements=[],
            strengths=strengths
        )
    
    def _identify_strengths(
        self,
        candidate_data: Dict,
        met_requirements: List[str]
    ) -> List[str]:
        """Identify candidate's key strengths."""
        strengths = []
        
        exp = candidate_data.get("experience_years", 0)
        if exp >= 8:
            strengths.append(f"Senior-level experience ({exp:.0f} years)")
        elif exp >= 5:
            strengths.append(f"Mid-senior experience ({exp:.0f} years)")
        
        skill_count = len(candidate_data.get("skills", set()))
        if skill_count >= 10:
            strengths.append(f"Diverse skill set ({skill_count} skills)")
        
        if len(met_requirements) >= 5:
            strengths.append(f"Strong requirement coverage ({len(met_requirements)} met)")
        
        return strengths[:3]
    
    def format(self, data: MatchScoreData) -> str:
        """Format match data into markdown table."""
        if not data or not data.matches:
            return ""
        
        lines = [
            "### 🎯 Match Scores",
            "",
            "| Candidate | Match | Met | Missing |",
            "|:----------|:-----:|:----|:--------|",
        ]
        
        for m in data.matches:
            met_str = f"{len(m.met_requirements)}/{data.total_requirements}"
            missing_str = ", ".join(m.missing_requirements[:3]) or "None"
            if len(m.missing_requirements) > 3:
                missing_str += f" (+{len(m.missing_requirements) - 3})"
            
            lines.append(
                f"| [📄](cv:{m.cv_id}) **{m.candidate_name}** | "
                f"{m.overall_match:.0f}% | {met_str} | {missing_str} |"
            )
        
        return "\n".join(lines)
