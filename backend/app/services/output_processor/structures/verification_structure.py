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
        
        # Extract thinking
        thinking = self.thinking_module.extract(llm_output)
        
        # Parse claim from query
        claim = self.claim_module.parse(query)
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
