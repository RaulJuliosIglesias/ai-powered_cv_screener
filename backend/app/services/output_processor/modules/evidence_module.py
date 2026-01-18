"""
EVIDENCE MODULE

Finds evidence in CV chunks for claims.
Used by: VerificationStructure
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Evidence:
    """Evidence for a claim."""
    source: str  # chunk/section reference
    excerpt: str  # relevant text
    relevance: float  # 0-1 how relevant
    cv_id: str = ""


@dataclass
class EvidenceData:
    """Container for evidence."""
    evidence: List[Evidence] = field(default_factory=list)
    total_found: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "evidence": [
                {
                    "source": e.source,
                    "excerpt": e.excerpt,
                    "relevance": e.relevance,
                    "cv_id": e.cv_id
                }
                for e in self.evidence
            ],
            "total_found": self.total_found
        }


class EvidenceModule:
    """Module for finding evidence in CV chunks."""
    
    def find(
        self,
        claim: Dict[str, Any],
        chunks: List[Dict[str, Any]],
        llm_output: str = ""
    ) -> Optional[EvidenceData]:
        """Find evidence for a claim in chunks."""
        if not claim or not chunks:
            return None
        
        subject = claim.get("subject", "").lower()
        claim_type = claim.get("claim_type", "")
        claim_value = claim.get("claim_value", "").lower()
        
        evidence_list = []
        
        # Search chunks for evidence
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            content = chunk.get("content", "")
            cv_id = chunk.get("cv_id", "") or meta.get("cv_id", "")
            candidate_name = (chunk.get("candidate_name", "") or meta.get("candidate_name", "")).lower()
            
            # Check if this chunk is for the right candidate
            if subject and subject not in candidate_name and candidate_name not in subject:
                continue
            
            # Search for claim-related evidence
            relevance, excerpts = self._search_evidence(
                content=content,
                meta=meta,
                claim_type=claim_type,
                claim_value=claim_value
            )
            
            if relevance > 0:
                for excerpt in excerpts:
                    evidence_list.append(Evidence(
                        source=meta.get("section_type", "CV"),
                        excerpt=excerpt[:200],
                        relevance=relevance,
                        cv_id=cv_id
                    ))
        
        # Also extract from LLM output
        if llm_output:
            llm_evidence = self._extract_from_llm(llm_output, claim_value)
            evidence_list.extend(llm_evidence)
        
        # Sort by relevance
        evidence_list.sort(key=lambda x: x.relevance, reverse=True)
        
        # Limit to top 5
        evidence_list = evidence_list[:5]
        
        logger.info(f"[EVIDENCE_MODULE] Found {len(evidence_list)} evidence items")
        
        return EvidenceData(
            evidence=evidence_list,
            total_found=len(evidence_list)
        )
    
    def _search_evidence(
        self,
        content: str,
        meta: Dict,
        claim_type: str,
        claim_value: str
    ) -> tuple[float, List[str]]:
        """Search for evidence in content."""
        content_lower = content.lower()
        excerpts = []
        relevance = 0.0
        
        # Check metadata for quick matches
        if claim_type == "certification":
            certs = meta.get("certifications", "").lower()
            if claim_value in certs:
                relevance = 0.9
                excerpts.append(f"Certifications: {meta.get('certifications', '')}")
        
        elif claim_type == "skill":
            skills = meta.get("skills", "").lower()
            if claim_value in skills:
                relevance = 0.8
                excerpts.append(f"Skills: {meta.get('skills', '')}")
        
        elif claim_type == "education":
            edu = meta.get("education_level", "").lower()
            edu_inst = meta.get("education_institution", "").lower()
            if claim_value in edu or claim_value in edu_inst:
                relevance = 0.9
                excerpts.append(f"Education: {meta.get('education_level', '')} at {meta.get('education_institution', '')}")
        
        # Search in content
        if claim_value in content_lower:
            relevance = max(relevance, 0.7)
            # Extract surrounding context
            idx = content_lower.find(claim_value)
            start = max(0, idx - 50)
            end = min(len(content), idx + len(claim_value) + 100)
            excerpt = content[start:end].strip()
            if excerpt:
                excerpts.append(f"...{excerpt}...")
        
        return relevance, excerpts
    
    def _extract_from_llm(
        self,
        llm_output: str,
        claim_value: str
    ) -> List[Evidence]:
        """Extract evidence citations from LLM output."""
        evidence = []
        
        patterns = [
            r'(?:evidence|proof|found|confirmed)[:\s]*([^.\n]+)',
            r'(?:CV\s+shows?|resume\s+indicates?)[:\s]*([^.\n]+)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, llm_output, re.IGNORECASE):
                excerpt = match.group(1).strip()
                if len(excerpt) > 20:
                    evidence.append(Evidence(
                        source="LLM Analysis",
                        excerpt=excerpt[:200],
                        relevance=0.6,
                        cv_id=""
                    ))
        
        return evidence[:2]
    
    def format(self, data: EvidenceData) -> str:
        """Format evidence for display."""
        if not data or not data.evidence:
            return "No evidence found."
        
        lines = ["### 📋 Evidence Found", ""]
        
        for i, e in enumerate(data.evidence, 1):
            relevance_bar = "🟢" if e.relevance >= 0.7 else "🟡" if e.relevance >= 0.4 else "🔴"
            lines.append(f"**{i}. {e.source}** {relevance_bar}")
            lines.append(f"> {e.excerpt}")
            lines.append("")
        
        return "\n".join(lines)
