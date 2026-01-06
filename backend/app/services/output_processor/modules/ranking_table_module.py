"""
RANKING TABLE MODULE

Generates ranked candidate table with scores.
Used by: RankingStructure

Output format:
| Rank | Candidate | Overall | Exp | Skills | Fit |
|------|-----------|---------|-----|--------|-----|
| 🥇 1 | **John** | 92% | 95% | 90% | 88% |
"""

import logging
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RankedCandidate:
    """Candidate with ranking scores."""
    rank: int
    candidate_name: str
    cv_id: str
    overall_score: float
    criterion_scores: Dict[str, float] = field(default_factory=dict)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)


@dataclass
class RankingTableData:
    """Container for ranking results."""
    ranked: List[RankedCandidate] = field(default_factory=list)
    criteria_names: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "ranked": [
                {
                    "rank": r.rank,
                    "candidate_name": r.candidate_name,
                    "cv_id": r.cv_id,
                    "overall_score": r.overall_score,
                    "criterion_scores": r.criterion_scores,
                    "strengths": r.strengths,
                    "weaknesses": r.weaknesses
                }
                for r in self.ranked
            ],
            "criteria_names": self.criteria_names
        }


class RankingTableModule:
    """
    Module for generating ranked candidate tables.
    
    Calculates scores based on criteria and chunk metadata.
    """
    
    def extract(
        self,
        chunks: List[Dict[str, Any]],
        criteria: List[Dict[str, Any]],
        llm_output: str = ""
    ) -> Optional[RankingTableData]:
        """
        Generate ranking table from chunks and criteria.
        
        Args:
            chunks: Retrieved CV chunks with metadata
            criteria: List of ranking criteria with weights
            llm_output: LLM response for additional context
            
        Returns:
            RankingTableData with ranked candidates
        """
        if not chunks:
            return None
        
        # Group chunks by candidate
        candidates = self._group_by_candidate(chunks)
        
        # Calculate scores for each candidate
        ranked_candidates = []
        criteria_names = [c.get("name", f"C{i}") for i, c in enumerate(criteria)]
        
        for cv_id, data in candidates.items():
            scores = self._calculate_scores(data, criteria)
            
            # Calculate overall weighted score
            overall = sum(
                scores.get(c.get("name", ""), 50) * c.get("weight", 0.2)
                for c in criteria
            )
            
            ranked_candidates.append(RankedCandidate(
                rank=0,  # Will be set after sorting
                candidate_name=data["name"],
                cv_id=cv_id,
                overall_score=round(overall, 1),
                criterion_scores={k: round(v, 1) for k, v in scores.items()},
                strengths=self._identify_strengths(scores),
                weaknesses=self._identify_weaknesses(scores)
            ))
        
        # Sort by overall score and assign ranks
        ranked_candidates.sort(key=lambda x: x.overall_score, reverse=True)
        for i, candidate in enumerate(ranked_candidates):
            candidate.rank = i + 1
        
        logger.info(f"[RANKING_TABLE_MODULE] Ranked {len(ranked_candidates)} candidates")
        
        return RankingTableData(
            ranked=ranked_candidates,
            criteria_names=criteria_names
        )
    
    def _group_by_candidate(
        self,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Dict]:
        """Group chunks by candidate."""
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
                    "experience_years": meta.get("total_experience_years", 0),
                    "current_role": meta.get("current_role", ""),
                    "skills": set(),
                    "job_hopping_score": meta.get("job_hopping_score", 0.5),
                    "avg_tenure": meta.get("avg_tenure_years", 2.0),
                    "position_count": meta.get("position_count", 0),
                    "seniority": meta.get("seniority_level", ""),
                }
            
            # Collect skills
            skills_str = meta.get("skills", "")
            if skills_str:
                for skill in skills_str.split(","):
                    skill = skill.strip()
                    if skill:
                        candidates[cv_id]["skills"].add(skill)
        
        return candidates
    
    def _calculate_scores(
        self,
        candidate_data: Dict,
        criteria: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate score for each criterion."""
        scores = {}
        
        for criterion in criteria:
            name = criterion.get("name", "")
            name_lower = name.lower()
            
            if "experience" in name_lower:
                # Score based on years of experience
                years = candidate_data.get("experience_years", 0)
                scores[name] = min(100, years * 10)  # 10 years = 100%
                
            elif "skill" in name_lower or "technical" in name_lower:
                # Score based on skill count
                skill_count = len(candidate_data.get("skills", set()))
                scores[name] = min(100, skill_count * 12)  # ~8 skills = 100%
                
            elif "stability" in name_lower:
                # Score based on job hopping (lower is better)
                hop_score = candidate_data.get("job_hopping_score", 0.5)
                scores[name] = max(0, 100 - hop_score * 100)
                
            elif "tenure" in name_lower:
                # Score based on average tenure
                tenure = candidate_data.get("avg_tenure", 2.0)
                scores[name] = min(100, tenure * 25)  # 4 years = 100%
                
            elif "seniority" in name_lower or "level" in name_lower:
                # Score based on seniority level
                seniority = candidate_data.get("seniority", "").lower()
                seniority_scores = {
                    "senior": 90, "lead": 95, "principal": 100,
                    "mid": 60, "junior": 30, "entry": 20
                }
                scores[name] = seniority_scores.get(seniority, 50)
                
            elif "fit" in name_lower or "role" in name_lower:
                # General fit score based on multiple factors
                exp_factor = min(1, candidate_data.get("experience_years", 0) / 5)
                skill_factor = min(1, len(candidate_data.get("skills", set())) / 5)
                scores[name] = (exp_factor * 50 + skill_factor * 50)
                
            elif "career" in name_lower or "trajectory" in name_lower:
                # Score based on career progression
                positions = candidate_data.get("position_count", 1)
                years = candidate_data.get("experience_years", 1)
                if years > 0:
                    progression = positions / years
                    scores[name] = min(100, max(30, 100 - abs(progression - 0.4) * 100))
                else:
                    scores[name] = 50
            else:
                # Default score
                scores[name] = 50
        
        return scores
    
    def _identify_strengths(self, scores: Dict[str, float]) -> List[str]:
        """Identify top scoring areas."""
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [name for name, score in sorted_scores[:2] if score >= 70]
    
    def _identify_weaknesses(self, scores: Dict[str, float]) -> List[str]:
        """Identify low scoring areas."""
        sorted_scores = sorted(scores.items(), key=lambda x: x[1])
        return [name for name, score in sorted_scores[:2] if score < 50]
    
    def format(self, data: RankingTableData) -> str:
        """
        Format ranking data into markdown table.
        
        Args:
            data: RankingTableData to format
            
        Returns:
            Formatted markdown string
        """
        if not data or not data.ranked:
            return ""
        
        # Build header
        lines = ["### 🏆 Candidate Ranking", ""]
        
        # Determine which criteria to show (max 4)
        criteria_to_show = data.criteria_names[:4]
        
        header = "| Rank | Candidate | Overall |"
        separator = "|:----:|:----------|:-------:|"
        
        for crit in criteria_to_show:
            short_name = crit[:8] if len(crit) > 8 else crit
            header += f" {short_name} |"
            separator += ":------:|"
        
        lines.append(header)
        lines.append(separator)
        
        # Rank emojis
        rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}
        
        for r in data.ranked:
            emoji = rank_emoji.get(r.rank, "")
            row = f"| {emoji} {r.rank} | [📄](cv:{r.cv_id}) **{r.candidate_name}** | {r.overall_score:.0f}% |"
            
            for crit in criteria_to_show:
                score = r.criterion_scores.get(crit, 0)
                row += f" {score:.0f}% |"
            
            lines.append(row)
        
        return "\n".join(lines)
