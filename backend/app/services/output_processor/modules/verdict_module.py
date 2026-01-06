"""
VERDICT MODULE

Issues verification verdicts with confidence levels.
Used by: VerificationStructure
"""

import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Verdict:
    """Verification verdict."""
    status: str  # "CONFIRMED", "PARTIAL", "NOT_FOUND", "CONTRADICTED"
    confidence: float  # 0-1
    explanation: str
    
    def to_dict(self) -> Dict:
        return {
            "status": self.status,
            "confidence": self.confidence,
            "explanation": self.explanation
        }


class VerdictModule:
    """Module for issuing verification verdicts."""
    
    def evaluate(
        self,
        claim: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        llm_output: str = ""
    ) -> Optional[Verdict]:
        """Evaluate claim against evidence."""
        if not claim:
            return None
        
        claim_value = claim.get("claim_value", "")
        claim_type = claim.get("claim_type", "")
        
        if not evidence:
            return Verdict(
                status="NOT_FOUND",
                confidence=0.3,
                explanation=f"No evidence found in CV to verify: {claim_value}"
            )
        
        # Calculate confidence based on evidence quality
        total_relevance = sum(e.get("relevance", 0) for e in evidence)
        avg_relevance = total_relevance / len(evidence) if evidence else 0
        
        # Determine status
        if avg_relevance >= 0.7:
            status = "CONFIRMED"
            confidence = min(0.95, avg_relevance)
            explanation = self._generate_confirmation(claim, evidence)
        elif avg_relevance >= 0.4:
            status = "PARTIAL"
            confidence = avg_relevance
            explanation = self._generate_partial(claim, evidence)
        else:
            status = "NOT_FOUND"
            confidence = 0.3
            explanation = f"Insufficient evidence to confirm: {claim_value}"
        
        # Check LLM output for contradictions
        if self._check_contradiction(llm_output, claim_value):
            status = "CONTRADICTED"
            confidence = 0.6
            explanation = f"Evidence suggests the claim may be inaccurate: {claim_value}"
        
        logger.info(f"[VERDICT_MODULE] Verdict: {status} ({confidence:.0%})")
        
        return Verdict(
            status=status,
            confidence=round(confidence, 2),
            explanation=explanation
        )
    
    def _generate_confirmation(
        self,
        claim: Dict[str, Any],
        evidence: List[Dict[str, Any]]
    ) -> str:
        """Generate confirmation explanation."""
        claim_value = claim.get("claim_value", "")
        subject = claim.get("subject", "The candidate")
        
        best_evidence = evidence[0] if evidence else {}
        source = best_evidence.get("source", "CV")
        
        return f"{subject}'s {claim_value} is confirmed based on {source} evidence."
    
    def _generate_partial(
        self,
        claim: Dict[str, Any],
        evidence: List[Dict[str, Any]]
    ) -> str:
        """Generate partial match explanation."""
        claim_value = claim.get("claim_value", "")
        
        return f"Partial evidence found for {claim_value}. Some aspects could not be fully verified."
    
    def _check_contradiction(self, llm_output: str, claim_value: str) -> bool:
        """Check if LLM output contradicts the claim."""
        contradiction_patterns = [
            r'(?:no\s+evidence|not\s+found|cannot\s+confirm|does\s+not\s+have)',
            r'(?:contrary|contradicts|inconsistent)',
        ]
        
        for pattern in contradiction_patterns:
            if claim_value.lower() in llm_output.lower():
                import re
                if re.search(pattern, llm_output, re.IGNORECASE):
                    return True
        
        return False
    
    def format(self, verdict: Verdict) -> str:
        """Format verdict for display."""
        if not verdict:
            return ""
        
        status_emoji = {
            "CONFIRMED": "✅",
            "PARTIAL": "🟡",
            "NOT_FOUND": "❓",
            "CONTRADICTED": "❌"
        }
        
        emoji = status_emoji.get(verdict.status, "❓")
        
        lines = [
            "### 📜 Verification Verdict",
            "",
            f"**Status:** {emoji} {verdict.status}",
            f"**Confidence:** {verdict.confidence:.0%}",
            "",
            verdict.explanation
        ]
        
        return "\n".join(lines)
