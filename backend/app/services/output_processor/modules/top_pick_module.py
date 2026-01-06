"""
TOP PICK MODULE

Highlights the #1 ranked candidate with detailed justification.
Used by: RankingStructure, JobMatchStructure

Output format:
### 🌟 Top Recommendation
**John Smith** is the strongest candidate because...
"""

import logging
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TopPickData:
    """Top candidate recommendation."""
    candidate_name: str
    cv_id: str
    overall_score: float
    key_strengths: List[str] = field(default_factory=list)
    justification: str = ""
    runner_up: str = ""
    runner_up_cv_id: str = ""


class TopPickModule:
    """
    Module for highlighting the top candidate recommendation.
    
    Generates a detailed justification for the #1 pick.
    """
    
    def extract(
        self,
        ranked_candidates: List[Dict[str, Any]],
        llm_output: str = "",
        criteria: List[Dict[str, Any]] = None
    ) -> Optional[TopPickData]:
        """
        Extract top pick from ranked candidates.
        
        Args:
            ranked_candidates: List of ranked candidate dicts
            llm_output: LLM response for additional context
            criteria: Ranking criteria used
            
        Returns:
            TopPickData with top candidate info
        """
        if not ranked_candidates:
            return None
        
        # Get top candidate
        top = ranked_candidates[0]
        
        # Get runner-up if available
        runner_up = ""
        runner_up_cv_id = ""
        if len(ranked_candidates) > 1:
            runner_up = ranked_candidates[1].get("candidate_name", "")
            runner_up_cv_id = ranked_candidates[1].get("cv_id", "")
        
        # Identify key strengths
        strengths = top.get("strengths", [])
        if not strengths:
            # Derive from criterion scores
            scores = top.get("criterion_scores", {})
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            strengths = [name for name, score in sorted_scores[:3] if score >= 70]
        
        # Generate justification
        justification = self._generate_justification(top, criteria, llm_output)
        
        logger.info(f"[TOP_PICK_MODULE] Top pick: {top.get('candidate_name')}")
        
        return TopPickData(
            candidate_name=top.get("candidate_name", "Unknown"),
            cv_id=top.get("cv_id", ""),
            overall_score=top.get("overall_score", 0),
            key_strengths=strengths,
            justification=justification,
            runner_up=runner_up,
            runner_up_cv_id=runner_up_cv_id
        )
    
    def _generate_justification(
        self,
        candidate: Dict[str, Any],
        criteria: List[Dict[str, Any]] = None,
        llm_output: str = ""
    ) -> str:
        """Generate justification for top pick."""
        parts = []
        
        name = candidate.get("candidate_name", "This candidate")
        score = candidate.get("overall_score", 0)
        
        parts.append(f"{name} emerges as the top choice with an overall score of {score:.0f}%.")
        
        # Add criterion-specific justifications (only if valid criteria, not candidate names)
        criterion_scores = candidate.get("criterion_scores", {})
        if criterion_scores:
            top_criteria = sorted(
                criterion_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            strengths_text = []
            for crit_name, crit_score in top_criteria:
                # FILTER: Skip if criterion name looks like a candidate name (contains spaces + capitalized)
                # Valid criteria: "Leadership", "Experience", "Technical Skills"
                # Invalid: "Isabel Mendoza", "Rajiv Kapoor"
                words = crit_name.split()
                if len(words) >= 2 and all(w[0].isupper() for w in words if len(w) > 1):
                    # Looks like a person's name, skip
                    continue
                if crit_score >= 70:
                    strengths_text.append(f"{crit_name} ({crit_score:.0f}%)")
            
            if strengths_text:
                parts.append(f"Key strengths include: {', '.join(strengths_text)}.")
        
        # Try to extract LLM justification for this specific candidate
        if llm_output:
            llm_justification = self._extract_llm_justification(llm_output, name)
            if llm_justification:
                parts.append(llm_justification)
        
        return " ".join(parts)
    
    def _extract_llm_justification(self, llm_output: str, candidate_name: str) -> str:
        """Extract justification from LLM output."""
        patterns = [
            rf'{re.escape(candidate_name)}[^.]*(?:stands out|excels|demonstrates|shows)[^.]+\.',
            rf'(?:recommend|top choice|best fit)[^.]*{re.escape(candidate_name)}[^.]+\.',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, llm_output, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return ""
    
    def format(self, data: TopPickData) -> str:
        """
        Format top pick data into markdown.
        
        Args:
            data: TopPickData to format
            
        Returns:
            Formatted markdown string
        """
        if not data:
            return ""
        
        lines = [
            "### 🌟 Top Recommendation",
            "",
            f"**[📄](cv:{data.cv_id}) {data.candidate_name}** — Score: **{data.overall_score:.0f}%**",
            "",
        ]
        
        if data.justification:
            lines.append(data.justification)
            lines.append("")
        
        if data.key_strengths:
            lines.append("**Key Strengths:**")
            for strength in data.key_strengths:
                lines.append(f"- ✅ {strength}")
            lines.append("")
        
        if data.runner_up:
            lines.append(
                f"*Runner-up: [📄](cv:{data.runner_up_cv_id}) {data.runner_up}*"
            )
        
        return "\n".join(lines)
