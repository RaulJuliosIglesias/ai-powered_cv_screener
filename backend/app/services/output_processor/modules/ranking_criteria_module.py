"""
RANKING CRITERIA MODULE

Extracts and formats ranking criteria from query and LLM output.
Used by: RankingStructure

Output format:
| Criterion | Weight | Description |
|-----------|--------|-------------|
| Experience | 40% | Years in similar roles |
"""

import logging
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RankingCriterion:
    """Single ranking criterion."""
    name: str
    weight: float  # 0.0 to 1.0
    description: str = ""
    category: str = "general"  # "required", "preferred", "bonus"


@dataclass
class RankingCriteriaData:
    """Container for ranking criteria."""
    criteria: List[RankingCriterion] = field(default_factory=list)
    role_context: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "criteria": [
                {
                    "name": c.name,
                    "weight": c.weight,
                    "description": c.description,
                    "category": c.category
                }
                for c in self.criteria
            ],
            "role_context": self.role_context
        }


class RankingCriteriaModule:
    """
    Module for extracting and formatting ranking criteria.
    
    Extracts criteria from query context and LLM analysis.
    """
    
    # Default criteria with weights
    DEFAULT_CRITERIA = [
        ("Experience", 0.30, "Years of relevant experience"),
        ("Technical Skills", 0.25, "Match with required technologies"),
        ("Role Fit", 0.20, "Alignment with job requirements"),
        ("Career Trajectory", 0.15, "Growth and progression pattern"),
        ("Stability", 0.10, "Employment history consistency"),
    ]
    
    def extract(
        self,
        query: str,
        llm_output: str = "",
        job_context: str = ""
    ) -> Optional[RankingCriteriaData]:
        """
        Extract ranking criteria from query and context.
        
        Args:
            query: Original ranking query
            llm_output: LLM response for additional context
            job_context: Optional job description context
            
        Returns:
            RankingCriteriaData with extracted criteria
        """
        criteria = []
        role_context = self._extract_role_context(query)
        
        # Try to extract criteria from LLM output first
        if llm_output:
            extracted = self._extract_from_llm(llm_output)
            if extracted:
                criteria = extracted
        
        # Fall back to query-based extraction
        if not criteria:
            criteria = self._extract_from_query(query)
        
        # Use defaults if nothing extracted
        if not criteria:
            criteria = [
                RankingCriterion(
                    name=name,
                    weight=weight,
                    description=desc
                )
                for name, weight, desc in self.DEFAULT_CRITERIA
            ]
        
        # Normalize weights
        criteria = self._normalize_weights(criteria)
        
        logger.info(f"[RANKING_CRITERIA_MODULE] Extracted {len(criteria)} criteria")
        
        return RankingCriteriaData(
            criteria=criteria,
            role_context=role_context
        )
    
    def _extract_role_context(self, query: str) -> str:
        """Extract role/position context from query."""
        patterns = [
            r'(?:for|as)\s+(?:a\s+)?([^,.\n]+?)(?:\s+position|\s+role)?(?:\s|$)',
            r'(?:top|best|rank)\s+\d*\s*(?:for|as)\s+([^,.\n]+)',
            r'(?:backend|frontend|fullstack|senior|junior|lead)\s+\w+',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).strip() if match.lastindex else match.group(0).strip()
        
        return ""
    
    def _extract_from_llm(self, llm_output: str) -> List[RankingCriterion]:
        """Extract criteria mentioned in LLM output."""
        criteria = []
        
        # Look for criteria section
        section_match = re.search(
            r'(?:criteria|factors|evaluation)[:\s]*([\s\S]*?)(?=###|:::|\Z)',
            llm_output,
            re.IGNORECASE
        )
        
        if not section_match:
            return criteria
        
        section = section_match.group(1)
        
        # Parse criteria items
        patterns = [
            r'\*\*([^*]+)\*\*[:\s]*([^|\n]+)',
            r'[-•]\s*([^:]+):\s*([^\n]+)',
            r'\d+\.\s*([^:]+):\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, section):
                name = match.group(1).strip()
                desc = match.group(2).strip() if match.lastindex > 1 else ""
                
                if name and len(name) > 2:
                    # FILTER: Skip if name looks like a candidate name (2+ capitalized words)
                    # Valid criteria: "Leadership", "Experience", "Technical Skills"
                    # Invalid: "Isabel Mendoza", "Rajiv Kapoor"
                    words = name.split()
                    if len(words) >= 2 and all(w[0].isupper() for w in words if len(w) > 2):
                        # Likely a person's name, skip
                        logger.debug(f"[RANKING_CRITERIA] Skipping likely person name: {name}")
                        continue
                    
                    # Also skip common non-criteria patterns
                    skip_words = {'was', 'is', 'are', 'were', 'has', 'have', 'the', 'and', 'for'}
                    if name.lower() in skip_words:
                        continue
                    
                    criteria.append(RankingCriterion(
                        name=name,
                        weight=0.2,  # Default weight, will be normalized
                        description=desc
                    ))
            
            if criteria:
                break
        
        return criteria[:6]  # Limit to 6 criteria
    
    def _extract_from_query(self, query: str) -> List[RankingCriterion]:
        """Extract implicit criteria from query keywords."""
        criteria = []
        
        keyword_criteria = {
            'python': ('Python Skills', 'Proficiency in Python'),
            'java': ('Java Skills', 'Proficiency in Java'),
            'react': ('React Skills', 'Frontend React experience'),
            'backend': ('Backend Experience', 'Server-side development'),
            'frontend': ('Frontend Experience', 'Client-side development'),
            'senior': ('Seniority', 'Senior-level experience'),
            'lead': ('Leadership', 'Team leadership experience'),
            'aws': ('AWS', 'Cloud infrastructure experience'),
            'devops': ('DevOps', 'CI/CD and infrastructure'),
        }
        
        query_lower = query.lower()
        for keyword, (name, desc) in keyword_criteria.items():
            if keyword in query_lower:
                criteria.append(RankingCriterion(
                    name=name,
                    weight=0.25,
                    description=desc,
                    category="required"
                ))
        
        return criteria
    
    def _normalize_weights(
        self,
        criteria: List[RankingCriterion]
    ) -> List[RankingCriterion]:
        """Normalize criteria weights to sum to 1.0."""
        if not criteria:
            return criteria
        
        total = sum(c.weight for c in criteria)
        if total > 0:
            for c in criteria:
                c.weight = c.weight / total
        
        return criteria
    
    def format(self, data: RankingCriteriaData) -> str:
        """
        Format criteria data into markdown table.
        
        Args:
            data: RankingCriteriaData to format
            
        Returns:
            Formatted markdown string
        """
        if not data or not data.criteria:
            return ""
        
        lines = ["### 📋 Ranking Criteria", ""]
        
        if data.role_context:
            lines.append(f"*Evaluating candidates for: {data.role_context}*")
            lines.append("")
        
        lines.extend([
            "| Criterion | Weight | Description |",
            "|:----------|:------:|:------------|",
        ])
        
        for c in data.criteria:
            weight_pct = f"{c.weight * 100:.0f}%"
            lines.append(f"| **{c.name}** | {weight_pct} | {c.description} |")
        
        return "\n".join(lines)
