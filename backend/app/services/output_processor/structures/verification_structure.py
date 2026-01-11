"""
VERIFICATION STRUCTURE

Structure for verifying specific claims about candidates.
Combines MODULES:
- ThinkingModule
- ClaimModule
- EvidenceModule
- VerdictModule
- ConclusionModule

This structure is used when user asks to verify claims:
- "verify if X has AWS certification"
- "confirm X worked at Google"
- "check if X has 5 years experience"
"""

import logging
from typing import Dict, Any, List, Optional

from ..modules import ThinkingModule, ConclusionModule
from ..modules.claim_module import ClaimModule
from ..modules.evidence_module import EvidenceModule
from ..modules.verdict_module import VerdictModule
from ...context_resolver import resolve_reference, has_reference_pattern

logger = logging.getLogger(__name__)


class VerificationStructure:
    """Assembles the Verification Structure using modules."""
    
    def __init__(self):
        self.thinking_module = ThinkingModule()
        self.claim_module = ClaimModule()
        self.evidence_module = EvidenceModule()
        self.verdict_module = VerdictModule()
        self.conclusion_module = ConclusionModule()
    
    def assemble(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        query: str = "",
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Assemble all components of Verification Structure."""
        logger.info("[VERIFICATION_STRUCTURE] Assembling verification analysis")
        
        # PHASE 1.2 FIX: Resolve "top candidate" references before processing
        # This ensures consistency with previous ranking results
        resolved_candidate = None
        if conversation_history:
            has_ref, ref_type = has_reference_pattern(query)
            if has_ref and ref_type in ("top_candidate", "this_candidate", "same_candidate"):
                resolution = resolve_reference(query, conversation_history)
                if resolution.resolved and resolution.candidate_name:
                    resolved_candidate = {
                        "name": resolution.candidate_name,
                        "cv_id": resolution.cv_id
                    }
                    logger.info(f"[VERIFICATION_STRUCTURE] Resolved 'top candidate' to: {resolved_candidate['name']}")
        
        # Extract thinking
        thinking = self.thinking_module.extract(llm_output)
        
        # Parse claim from query, but inject resolved candidate if available
        claim = self.claim_module.parse(query)
        
        # PHASE 1.2: If claim subject is generic and we resolved a candidate, use that
        if claim and resolved_candidate:
            if not claim.subject or claim.subject.lower() in ("the top candidate", "top candidate", "the candidate", "candidate"):
                claim.subject = resolved_candidate["name"]
                logger.info(f"[VERIFICATION_STRUCTURE] Updated claim subject to: {claim.subject}")
        claim_dict = claim.to_dict() if claim else None
        
        # Find evidence
        evidence_data = self.evidence_module.find(
            claim=claim_dict,
            chunks=chunks,
            llm_output=llm_output
        )
        evidence_list = evidence_data.to_dict()["evidence"] if evidence_data else []
        
        # Issue verdict
        verdict = self.verdict_module.evaluate(
            claim=claim_dict,
            evidence=evidence_list,
            llm_output=llm_output
        )
        
        # Extract conclusion
        conclusion = self.conclusion_module.extract(llm_output)
        
        # PHASE 1.6 FIX: Validate conclusion aligns with verdict
        # If verdict is NOT_FOUND but conclusion says "Yes", fix the conclusion
        if conclusion and verdict:
            conclusion = self._validate_and_fix_conclusion(
                conclusion=conclusion,
                verdict=verdict,
                claim=claim_dict,
                query=query
            )
        
        return {
            "structure_type": "verification",
            "query": query,
            "thinking": thinking,
            "claim": claim_dict,
            "evidence": evidence_data.to_dict() if evidence_data else None,
            "verdict": verdict.to_dict() if verdict else None,
            "conclusion": conclusion,
            "raw_content": llm_output
        }
    
    def _validate_and_fix_conclusion(
        self,
        conclusion: str,
        verdict,
        claim: dict,
        query: str
    ) -> str:
        """
        PHASE 1.6 FIX: Validate that conclusion aligns with verdict status.
        
        Prevents contradictions like:
        - Verdict: NOT_FOUND (30% confidence)
        - Conclusion: "Yes, the candidate has 10 years experience"
        
        Args:
            conclusion: LLM-generated conclusion text
            verdict: Verdict object with status and confidence
            claim: Claim being verified
            query: Original user query
            
        Returns:
            Validated/fixed conclusion text
        """
        if not conclusion or not verdict:
            return conclusion
        
        status = verdict.status
        confidence = verdict.confidence
        claim_value = claim.get("claim_value", query) if claim else query
        
        conclusion_lower = conclusion.lower()
        
        # Detect contradictions
        is_affirmative = any(word in conclusion_lower for word in [
            "yes,", "yes.", "confirmed", "verified", "true", "correct", 
            "has the", "does have", "is correct"
        ])
        is_negative = any(word in conclusion_lower for word in [
            "no,", "no.", "not found", "cannot verify", "unable to", 
            "no evidence", "does not have", "is not"
        ])
        
        # Check for contradiction
        contradiction_detected = False
        
        if status == "NOT_FOUND" and is_affirmative and not is_negative:
            # Verdict says NOT_FOUND but conclusion is affirmative
            contradiction_detected = True
            logger.warning(
                f"[VERIFICATION_STRUCTURE] Contradiction: verdict=NOT_FOUND but conclusion is affirmative. Fixing."
            )
        elif status == "CONFIRMED" and is_negative and not is_affirmative:
            # Verdict says CONFIRMED but conclusion is negative
            contradiction_detected = True
            logger.warning(
                f"[VERIFICATION_STRUCTURE] Contradiction: verdict=CONFIRMED but conclusion is negative. Fixing."
            )
        elif status == "CONTRADICTED" and is_affirmative and not is_negative:
            # Verdict says CONTRADICTED but conclusion is affirmative
            contradiction_detected = True
            logger.warning(
                f"[VERIFICATION_STRUCTURE] Contradiction: verdict=CONTRADICTED but conclusion is affirmative. Fixing."
            )
        
        if contradiction_detected:
            return self._generate_verdict_aligned_conclusion(verdict, claim_value)
        
        return conclusion
    
    def _generate_verdict_aligned_conclusion(self, verdict, claim_value: str) -> str:
        """
        Generate a conclusion that is properly aligned with the verdict.
        
        Uses confidence-based language:
        - 80-100%: Definitive statements
        - 50-79%: Hedged language ("likely", "appears to")
        - 30-49%: Uncertain language ("unable to confirm", "limited evidence")
        - <30%: Cannot verify
        """
        status = verdict.status
        confidence = verdict.confidence
        
        if status == "CONFIRMED":
            if confidence >= 0.8:
                return f"**Yes, confirmed.** The claim \"{claim_value}\" is verified based on CV evidence."
            elif confidence >= 0.5:
                return f"**Likely yes.** Evidence suggests \"{claim_value}\" is accurate, though not fully confirmed ({confidence:.0%} confidence)."
            else:
                return f"**Partial confirmation.** Some evidence supports \"{claim_value}\" but verification is incomplete ({confidence:.0%} confidence)."
        
        elif status == "NOT_FOUND":
            if confidence <= 0.3:
                return f"**Unable to verify.** No sufficient evidence was found in the CV to confirm \"{claim_value}\". This does not mean the claim is false, only that it could not be verified from the available data."
            else:
                return f"**Inconclusive.** Limited evidence was found regarding \"{claim_value}\". Recommend direct verification with the candidate."
        
        elif status == "CONTRADICTED":
            return f"**No, contradicted.** Evidence in the CV suggests \"{claim_value}\" may not be accurate. Recommend clarification with the candidate."
        
        elif status == "PARTIAL":
            return f"**Partially verified.** Some aspects of \"{claim_value}\" are supported by CV evidence, but full verification is not possible ({confidence:.0%} confidence)."
        
        else:
            return f"Verification result: {status} ({confidence:.0%} confidence). See evidence details above."
