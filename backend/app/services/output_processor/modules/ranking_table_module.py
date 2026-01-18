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
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RankedCandidate:
    """Candidate with ranking scores and enriched metadata."""
    rank: int
    candidate_name: str
    cv_id: str
    overall_score: float
    criterion_scores: Dict[str, float] = field(default_factory=dict)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    # Enriched metadata for concrete justifications
    experience_years: float = 0.0
    avg_tenure: float = 0.0
    job_hopping_score: float = 0.5
    seniority: str = ""


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
                    "weaknesses": r.weaknesses,
                    # Include enriched metadata for TopPickModule
                    "experience_years": r.experience_years,
                    "avg_tenure": r.avg_tenure,
                    "job_hopping_score": r.job_hopping_score,
                    "seniority": r.seniority
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
        
        PRIORITY: Extract ranking from LLM output first (it analyzed actual CV content).
        FALLBACK: Calculate from metadata if LLM extraction fails.
        
        Args:
            chunks: Retrieved CV chunks with metadata
            criteria: List of ranking criteria with weights
            llm_output: LLM response for additional context
            
        Returns:
            RankingTableData with ranked candidates
        """
        if not chunks:
            return None
        
        # Group chunks by candidate for name/cv_id lookup
        candidates = self._group_by_candidate(chunks)
        criteria_names = [c.get("name", f"C{i}") for i, c in enumerate(criteria)]
        
        # PRIORITY 1: Try to extract ranking from LLM output
        # The LLM has actually analyzed the CV content and knows who is best
        if llm_output:
            llm_ranking = self._extract_ranking_from_llm(llm_output, candidates)
            if llm_ranking and len(llm_ranking) >= 3:
                logger.info(f"[RANKING_TABLE_MODULE] Using LLM-extracted ranking ({len(llm_ranking)} candidates)")
                return RankingTableData(
                    ranked=llm_ranking,
                    criteria_names=criteria_names
                )
        
        # FALLBACK: Calculate scores from metadata
        logger.info("[RANKING_TABLE_MODULE] Using metadata-based ranking (LLM extraction failed)")
        ranked_candidates = []
        
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
                weaknesses=self._identify_weaknesses(scores),
                # Include enriched metadata for concrete justifications
                experience_years=data.get("experience_years", 0),
                avg_tenure=data.get("avg_tenure", 0),
                job_hopping_score=data.get("job_hopping_score", 0.5),
                seniority=data.get("seniority", "")
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
    
    def _extract_ranking_from_llm(
        self,
        llm_output: str,
        candidates: Dict[str, Dict]
    ) -> List[RankedCandidate]:
        """
        Extract candidate ranking from LLM output.
        
        The LLM analyzes actual CV content and identifies best candidates.
        This is more accurate than metadata-based scoring for subjective criteria
        like "leadership" or "strategic thinking".
        
        Args:
            llm_output: LLM response text
            candidates: Dict of cv_id -> candidate data for lookup
            
        Returns:
            List of RankedCandidate extracted from LLM, or empty list if extraction fails
        """
        ranked = []
        
        # Build name to cv_id mapping
        name_to_cvid = {}
        for cv_id, data in candidates.items():
            name = data.get("name", "")
            if name:
                name_to_cvid[name.lower()] = cv_id
                # Also map partial names (first name, last name)
                parts = name.split()
                for part in parts:
                    if len(part) > 3:
                        name_to_cvid[part.lower()] = cv_id
        
        # Patterns to extract ranked candidates from LLM output
        # Look for: "1. **Name**", "**Name** is the most suitable", etc.
        
        found_names = []
        found_set = set()
        
        # First pattern: numbered list (gives explicit order)
        numbered_pattern = r'(?:^|\n)\s*(\d+)[.)\]]\s*\*?\*?\[?([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,3})'
        for match in re.finditer(numbered_pattern, llm_output, re.MULTILINE):
            rank_num = int(match.group(1))
            name = match.group(2).strip()
            name_lower = name.lower()
            
            # Find cv_id for this name
            cv_id = None
            for known_name, cid in name_to_cvid.items():
                if known_name in name_lower or name_lower in known_name:
                    cv_id = cid
                    break
            
            if cv_id and name_lower not in found_set:
                found_names.append((rank_num, name, cv_id))
                found_set.add(name_lower)
        
        # Sort by rank number and create candidates
        found_names.sort(key=lambda x: x[0])
        
        if found_names:
            for i, (_, name, cv_id) in enumerate(found_names[:10]):  # Limit to top 10
                # Get enriched metadata from candidates dict
                cand_data = candidates.get(cv_id, {})
                ranked.append(RankedCandidate(
                    rank=i + 1,
                    candidate_name=name,
                    cv_id=cv_id,
                    overall_score=max(20, 100 - i * 10),  # 100, 90, 80, ...
                    criterion_scores={},
                    strengths=[],
                    weaknesses=[],
                    experience_years=cand_data.get("experience_years", 0),
                    avg_tenure=cand_data.get("avg_tenure", 0),
                    job_hopping_score=cand_data.get("job_hopping_score", 0.5),
                    seniority=cand_data.get("seniority", "")
                ))
            return ranked
        
        # Second approach: Extract from conclusion/analysis
        # Look for "Name is the most suitable" patterns
        conclusion_patterns = [
            r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,3})\s+is\s+the\s+most\s+suitable',
            r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,3})\s+is\s+(?:also\s+)?highly\s+suitable',
            r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,3})\s+demonstrates\s+leadership',
        ]
        
        for pattern in conclusion_patterns:
            for match in re.finditer(pattern, llm_output, re.IGNORECASE):
                name = match.group(1).strip()
                name_lower = name.lower()
                
                # Skip common words
                if name_lower in {'the', 'this', 'that', 'they', 'their', 'candidate'}:
                    continue
                
                cv_id = None
                for known_name, cid in name_to_cvid.items():
                    if known_name in name_lower or name_lower in known_name:
                        cv_id = cid
                        break
                
                if cv_id and name_lower not in found_set:
                    found_names.append((len(found_names), name, cv_id))
                    found_set.add(name_lower)
        
        # Create ranked candidates from found names
        for i, (_, name, cv_id) in enumerate(found_names[:10]):
            # Get enriched metadata from candidates dict
            cand_data = candidates.get(cv_id, {})
            ranked.append(RankedCandidate(
                rank=i + 1,
                candidate_name=name,
                cv_id=cv_id,
                overall_score=max(20, 100 - i * 10),
                criterion_scores={},
                strengths=[],
                weaknesses=[],
                experience_years=cand_data.get("experience_years", 0),
                avg_tenure=cand_data.get("avg_tenure", 0),
                job_hopping_score=cand_data.get("job_hopping_score", 0.5),
                seniority=cand_data.get("seniority", "")
            ))
        
        return ranked
    
    def _group_by_candidate(
        self,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Dict]:
        """Group chunks by candidate and preserve ALL enriched metadata."""
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
            else:
                # Update with max values if this chunk has better data
                if meta.get("total_experience_years", 0) > candidates[cv_id]["experience_years"]:
                    candidates[cv_id]["experience_years"] = meta.get("total_experience_years", 0)
                if meta.get("avg_tenure_years", 0) > candidates[cv_id]["avg_tenure"]:
                    candidates[cv_id]["avg_tenure"] = meta.get("avg_tenure_years", 0)
                if meta.get("job_hopping_score") is not None:
                    # Lower is better for job hopping, so take min
                    candidates[cv_id]["job_hopping_score"] = min(
                        candidates[cv_id]["job_hopping_score"],
                        meta.get("job_hopping_score", 0.5)
                    )
                if not candidates[cv_id]["seniority"] and meta.get("seniority_level"):
                    candidates[cv_id]["seniority"] = meta.get("seniority_level", "")
            
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
        """Calculate score for each criterion based on candidate metadata."""
        scores = {}
        
        # Pre-calculate base factors from candidate data
        years = candidate_data.get("experience_years", 0)
        skill_count = len(candidate_data.get("skills", set()))
        hop_score = candidate_data.get("job_hopping_score", 0.5)
        tenure = candidate_data.get("avg_tenure", 2.0)
        positions = candidate_data.get("position_count", 1)
        seniority = candidate_data.get("seniority", "").lower()
        
        # Seniority mapping
        seniority_score = {
            "principal": 100, "director": 100, "lead": 95, "senior": 90,
            "staff": 85, "mid": 60, "junior": 30, "entry": 20, "intern": 10
        }.get(seniority, 50)
        
        for criterion in criteria:
            name = criterion.get("name", "")
            name_lower = name.lower()
            
            # EXPERIENCE-based criteria
            if any(kw in name_lower for kw in ["experience", "years", "exp"]):
                scores[name] = min(100, years * 10)  # 10 years = 100%
                
            # SKILL-based criteria
            elif any(kw in name_lower for kw in ["skill", "technical", "competenc"]):
                scores[name] = min(100, skill_count * 12)  # ~8 skills = 100%
                
            # STABILITY criteria
            elif any(kw in name_lower for kw in ["stability", "reliable", "consistent"]):
                scores[name] = max(0, 100 - hop_score * 100)
                
            # TENURE criteria
            elif "tenure" in name_lower:
                scores[name] = min(100, tenure * 25)  # 4 years = 100%
                
            # SENIORITY/LEVEL criteria
            elif any(kw in name_lower for kw in ["seniority", "level", "rank"]):
                scores[name] = seniority_score
                
            # LEADERSHIP criteria - KEY ADDITION
            elif any(kw in name_lower for kw in ["leadership", "leader", "lead", "management", "managing", "team"]):
                # Score based on seniority + experience + positions held
                leadership_score = (
                    seniority_score * 0.5 +  # 50% from seniority
                    min(100, years * 8) * 0.3 +  # 30% from experience
                    min(100, positions * 20) * 0.2  # 20% from positions held
                )
                scores[name] = min(100, leadership_score)
                
            # FIT/ROLE criteria
            elif any(kw in name_lower for kw in ["fit", "role", "match", "suitable"]):
                exp_factor = min(1, years / 5)
                skill_factor = min(1, skill_count / 5)
                scores[name] = (exp_factor * 50 + skill_factor * 50)
                
            # CAREER/TRAJECTORY criteria
            elif any(kw in name_lower for kw in ["career", "trajectory", "progress", "growth"]):
                if years > 0:
                    progression = positions / years
                    scores[name] = min(100, max(30, 100 - abs(progression - 0.4) * 100))
                else:
                    scores[name] = 50
                    
            # COMMUNICATION criteria
            elif any(kw in name_lower for kw in ["communication", "interpersonal", "soft skill"]):
                # Approximate from seniority (senior = better communication assumed)
                scores[name] = seniority_score
                
            # STRATEGIC criteria
            elif any(kw in name_lower for kw in ["strategic", "vision", "planning"]):
                # Higher seniority + more experience = more strategic
                scores[name] = min(100, seniority_score * 0.6 + min(100, years * 8) * 0.4)
                
            else:
                # DEFAULT: Use composite score instead of flat 50
                # This ensures some differentiation even for unknown criteria
                composite = (
                    min(100, years * 8) * 0.4 +  # Experience weight
                    seniority_score * 0.3 +  # Seniority weight
                    min(100, skill_count * 10) * 0.3  # Skills weight
                )
                scores[name] = max(20, min(100, composite))
                logger.debug(f"[RANKING] Unknown criterion '{name}' - using composite score: {scores[name]:.1f}")
        
        return scores
    
    def _identify_strengths(self, scores: Dict[str, float]) -> List[str]:
        """Identify top scoring areas."""
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [name for name, score in sorted_scores[:2] if score >= 70]
    
    def _identify_weaknesses(self, scores: Dict[str, float]) -> List[str]:
        """Identify low scoring areas."""
        sorted_scores = sorted(scores.items(), key=lambda x: x[1])
        return [name for name, score in sorted_scores[:2] if score < 50]
    
    def format(self, data: RankingTableData, show_experience_instead_of_score: bool = False) -> str:
        """
        Format ranking data into markdown table.
        
        Args:
            data: RankingTableData to format
            show_experience_instead_of_score: If True, show experience years instead of overall score
            
        Returns:
            Formatted markdown string
        """
        if not data or not data.ranked:
            return ""
        
        # Build header
        lines = ["### 🏆 Candidate Ranking", ""]
        
        # Determine which criteria to show (max 4)
        criteria_to_show = data.criteria_names[:4]
        
        if show_experience_instead_of_score:
            header = "| Rank | Candidate | Experience |"
            separator = "|:----:|:----------|:----------:|"
        else:
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
            
            if show_experience_instead_of_score:
                # Show actual experience years instead of score
                exp_years = r.experience_years
                if exp_years > 0:
                    exp_display = f"{exp_years:.1f} yrs"
                else:
                    exp_display = "N/A"
                row = f"| {emoji} {r.rank} | [📄](cv:{r.cv_id}) **{r.candidate_name}** | {exp_display} |"
            else:
                # Show overall score
                overall = max(0, min(100, r.overall_score))
                row = f"| {emoji} {r.rank} | [📄](cv:{r.cv_id}) **{r.candidate_name}** | {overall:.0f}% |"
            
            for crit in criteria_to_show:
                score = r.criterion_scores.get(crit, 0)
                # PHASE 3.1 FIX: Ensure criterion score is never negative
                score = max(0, min(100, score))
                row += f" {score:.0f}% |"
            
            lines.append(row)
        
        return "\n".join(lines)
