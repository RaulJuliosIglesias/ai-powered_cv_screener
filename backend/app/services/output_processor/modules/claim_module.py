"""
CLAIM MODULE

Parses claims to verify from queries.
Used by: VerificationStructure
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class Claim:
    """Claim to be verified."""
    subject: str  # candidate name
    claim_type: str  # "experience", "certification", "education", "skill", "employment"
    claim_value: str  # what to verify
    raw_query: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "subject": self.subject,
            "claim_type": self.claim_type,
            "claim_value": self.claim_value,
            "raw_query": self.raw_query
        }


class ClaimModule:
    """Module for parsing verification claims."""
    
    CLAIM_PATTERNS = {
        "certification": [
            r'(?:verify|confirm|check)\s+(?:if\s+)?(\w+(?:\s+\w+)?)\s+(?:has|holds?|obtained?)\s+([^,.\n]+(?:certification|certificate|certified))',
            r'(?:does|did)\s+(\w+(?:\s+\w+)?)\s+(?:have|hold|get)\s+([^,.\n]+(?:certification|certificate))',
        ],
        "experience": [
            r'(?:verify|confirm|check)\s+(?:if\s+)?(\w+(?:\s+\w+)?)\s+(?:worked|has\s+experience)\s+(?:at|with|in)\s+([^,.\n]+)',
            r'(?:did|does)\s+(\w+(?:\s+\w+)?)\s+(?:work|have\s+experience)\s+(?:at|with|in)\s+([^,.\n]+)',
            # PHASE 4.3 FIX: Handle "X has Y years experience" patterns
            r'(?:verify|confirm|check|is\s+it\s+true)\s+(?:that\s+)?(?:the\s+)?(\w+(?:\s+\w+)?(?:\s+candidate)?)\s+has\s+(\d+\s*(?:\+\s*)?years?\s*(?:of\s+)?experience)',
            r'(?:does|did)\s+(?:the\s+)?(\w+(?:\s+\w+)?)\s+(?:have|has)\s+(\d+\s*(?:\+\s*)?years)',
        ],
        "education": [
            r'(?:verify|confirm|check)\s+(?:if\s+)?(\w+(?:\s+\w+)?)\s+(?:studied|graduated|has\s+degree)\s+(?:at|from|in)\s+([^,.\n]+)',
            r'(?:did|does)\s+(\w+(?:\s+\w+)?)\s+(?:study|graduate|have\s+degree)\s+(?:at|from|in)\s+([^,.\n]+)',
        ],
        "skill": [
            r'(?:verify|confirm|check)\s+(?:if\s+)?(\w+(?:\s+\w+)?)\s+(?:knows?|has|can\s+use)\s+([^,.\n]+)',
            r'(?:does|can)\s+(\w+(?:\s+\w+)?)\s+(?:know|use|work\s+with)\s+([^,.\n]+)',
        ],
        "employment": [
            r'(?:verify|confirm|check)\s+(?:if\s+)?(\w+(?:\s+\w+)?)\s+(?:is|was)\s+(?:a\s+)?([^,.\n]+)\s+at\s+([^,.\n]+)',
            r'(?:did|does)\s+(\w+(?:\s+\w+)?)\s+(?:work\s+as|hold\s+position)\s+([^,.\n]+)',
        ],
    }
    
    def parse(self, query: str) -> Optional[Claim]:
        """Parse claim from verification query."""
        if not query:
            return None
        
        query.lower()
        
        # Try each claim type pattern
        for claim_type, patterns in self.CLAIM_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    subject = groups[0].strip() if groups[0] else ""
                    claim_value = groups[1].strip() if len(groups) > 1 else ""
                    
                    if len(groups) > 2:
                        claim_value += f" at {groups[2].strip()}"
                    
                    logger.info(f"[CLAIM_MODULE] Parsed claim: {claim_type} for {subject}")
                    
                    return Claim(
                        subject=subject,
                        claim_type=claim_type,
                        claim_value=claim_value,
                        raw_query=query
                    )
        
        # Fallback: try to extract subject and claim from general query
        subject = self._extract_subject(query)
        claim_value = self._extract_claim_value(query)
        claim_type = self._infer_claim_type(query)
        
        if subject or claim_value:
            return Claim(
                subject=subject,
                claim_type=claim_type,
                claim_value=claim_value,
                raw_query=query
            )
        
        return None
    
    def _extract_subject(self, query: str) -> str:
        """Extract candidate name from query."""
        patterns = [
            r'(?:about|for|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:has|have|did|does|is|was)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_claim_value(self, query: str) -> str:
        """Extract claim value from query."""
        patterns = [
            r'(?:has|have|holds?|obtained?|knows?)\s+([^,.\n]+)',
            r'(?:worked|experience)\s+(?:at|with|in)\s+([^,.\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _infer_claim_type(self, query: str) -> str:
        """Infer claim type from query keywords."""
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in ['certif', 'license', 'accredit']):
            return "certification"
        elif any(kw in query_lower for kw in ['degree', 'university', 'graduate', 'study']):
            return "education"
        elif any(kw in query_lower for kw in ['work', 'employ', 'position', 'role']):
            return "employment"
        elif any(kw in query_lower for kw in ['experience', 'years']):
            return "experience"
        else:
            return "skill"
    
    def format(self, claim: Claim) -> str:
        """Format claim for display."""
        if not claim:
            return ""
        
        return f"**Verifying:** {claim.subject} — {claim.claim_type.title()}: {claim.claim_value}"
