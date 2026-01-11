"""
RESULTS TABLE MODULE

Extracts and formats search results table from LLM output and chunks.
Used by: SearchStructure

Output format:
| Candidate | Match Score | Key Skills | Experience |
|-----------|-------------|------------|------------|
| **John** | 95% | Python, AWS | 8 years |
"""

import logging
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Single search result entry."""
    candidate_name: str
    cv_id: str
    match_score: float
    matching_skills: List[str] = field(default_factory=list)
    experience_years: float = 0.0
    current_role: str = ""
    relevance_reason: str = ""


@dataclass
class ResultsTableData:
    """Container for search results."""
    results: List[SearchResult] = field(default_factory=list)
    query_terms: List[str] = field(default_factory=list)
    total_candidates: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "results": [
                {
                    "candidate_name": r.candidate_name,
                    "cv_id": r.cv_id,
                    "match_score": r.match_score,
                    "matching_skills": r.matching_skills,
                    "experience_years": r.experience_years,
                    "current_role": r.current_role,
                    "relevance_reason": r.relevance_reason
                }
                for r in self.results
            ],
            "query_terms": self.query_terms,
            "total_candidates": self.total_candidates
        }


class ResultsTableModule:
    """
    Module for extracting and formatting search results.
    
    Extracts match scores and relevance from chunks and LLM output.
    """
    
    def extract(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
        llm_output: str = ""
    ) -> Optional[ResultsTableData]:
        """
        Extract search results from chunks and LLM output.
        
        Args:
            chunks: Retrieved CV chunks with metadata
            query: Original search query
            llm_output: Raw LLM response for additional context
            
        Returns:
            ResultsTableData with extracted results or None
        """
        if not chunks:
            return None
        
        # Extract query terms for matching
        query_terms = self._extract_query_terms(query)
        
        # Group chunks by candidate
        candidates = {}
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            # cv_id can be at chunk level or in metadata
            cv_id = chunk.get("cv_id", "") or meta.get("cv_id", "")
            name = chunk.get("candidate_name", "") or meta.get("candidate_name", "Unknown")
            
            if cv_id not in candidates:
                candidates[cv_id] = {
                    "name": name,
                    "cv_id": cv_id,
                    "chunks": [],
                    "skills": set(),
                    "experience": meta.get("total_experience_years", 0),
                    "current_role": meta.get("current_role", ""),
                    "score": chunk.get("score", 0.0)
                }
            
            candidates[cv_id]["chunks"].append(chunk)
            
            # Collect skills
            skills_str = meta.get("skills", "")
            if skills_str:
                for skill in skills_str.split(","):
                    skill = skill.strip()
                    if skill:
                        candidates[cv_id]["skills"].add(skill)
            
            # Update score if higher
            chunk_score = chunk.get("score", 0.0)
            if chunk_score > candidates[cv_id]["score"]:
                candidates[cv_id]["score"] = chunk_score
        
        # Build results
        results = []
        for cv_id, data in candidates.items():
            # Calculate match score based on query terms
            matching_skills = self._find_matching_skills(
                list(data["skills"]),
                query_terms
            )
            
            # Normalize score to percentage (0-100)
            # RRF scores can be >1 (sum of 1/(k+rank) across queries), so we need to normalize
            raw_score = data["score"]
            if raw_score > 1.5:
                # Likely already a percentage or RRF sum - normalize to 0-100
                match_score = min(100, raw_score / max(raw_score, 1) * 100)
            elif raw_score > 1.0:
                # RRF score slightly above 1 - scale down to percentage
                match_score = min(100, (raw_score / 2.0) * 100)
            else:
                # Normal similarity score (0-1) - convert to percentage
                match_score = min(100, raw_score * 100)
            
            results.append(SearchResult(
                candidate_name=data["name"],
                cv_id=cv_id,
                match_score=round(match_score, 1),
                matching_skills=matching_skills,
                experience_years=data["experience"],
                current_role=data["current_role"],
                relevance_reason=self._generate_relevance_reason(matching_skills, data)
            ))
        
        # Sort by match score descending
        results.sort(key=lambda x: x.match_score, reverse=True)
        
        logger.info(f"[RESULTS_TABLE_MODULE] Extracted {len(results)} search results")
        
        return ResultsTableData(
            results=results,
            query_terms=query_terms,
            total_candidates=len(results)
        )
    
    def _extract_query_terms(self, query: str) -> List[str]:
        """Extract searchable terms from query."""
        # Remove common words
        stop_words = {
            'who', 'has', 'have', 'with', 'and', 'or', 'the', 'a', 'an',
            'find', 'search', 'looking', 'for', 'candidates', 'people',
            'experience', 'in', 'is', 'are', 'show', 'me', 'list'
        }
        
        words = re.findall(r'\b\w+\b', query.lower())
        terms = [w for w in words if w not in stop_words and len(w) > 2]
        
        return terms
    
    def _find_matching_skills(
        self,
        candidate_skills: List[str],
        query_terms: List[str]
    ) -> List[str]:
        """Find skills that match query terms."""
        matching = []
        
        for skill in candidate_skills:
            skill_lower = skill.lower()
            for term in query_terms:
                if term in skill_lower or skill_lower in term:
                    matching.append(skill)
                    break
        
        return matching[:5]  # Limit to top 5
    
    def _generate_relevance_reason(
        self,
        matching_skills: List[str],
        data: Dict
    ) -> str:
        """Generate a brief reason for relevance."""
        parts = []
        
        if matching_skills:
            parts.append(f"Skills: {', '.join(matching_skills[:3])}")
        
        if data.get("experience", 0) > 0:
            parts.append(f"{data['experience']:.0f}+ years exp")
        
        return " | ".join(parts) if parts else "Profile match"
    
    def format(self, data: ResultsTableData) -> str:
        """
        Format results data into markdown table.
        
        Args:
            data: ResultsTableData to format
            
        Returns:
            Formatted markdown string
        """
        if not data or not data.results:
            return ""
        
        lines = [
            "### 🔍 Search Results",
            "",
            f"Found **{data.total_candidates}** matching candidates:",
            "",
            "| Candidate | Match | Key Skills | Experience | Current Role |",
            "|:----------|:-----:|:-----------|:-----------|:-------------|",
        ]
        
        for r in data.results:
            skills_str = ", ".join(r.matching_skills[:3]) if r.matching_skills else "-"
            exp_str = f"{r.experience_years:.0f} years" if r.experience_years else "-"
            role_str = r.current_role or "-"
            
            lines.append(
                f"| [📄](cv:{r.cv_id}) **{r.candidate_name}** | {r.match_score:.0f}% | "
                f"{skills_str} | {exp_str} | {role_str} |"
            )
        
        return "\n".join(lines)
