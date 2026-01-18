"""
Output validators to catch hallucinations and prohibited content.

This module validates LLM output AFTER generation to catch:
- External URLs/websites (prohibited)
- Malformed candidate references
- Duplicated sections
"""

import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)


class OutputValidator:
    """Validates LLM output for prohibited content and hallucinations."""
    
    # Patterns for prohibited external URLs
    URL_PATTERNS = [
        r'https?://[^\s]+',           # http:// or https://
        r'www\.[^\s]+\.[a-z]{2,}',    # www.example.com
        r'[a-z0-9-]+\.(com|net|org|io|dev|ai|co|me|xyz)',  # domain.com
        r'github\.com',
        r'linkedin\.com',
        r'[a-z0-9]+\.[a-z]{2,}/[^\s]*',  # any domain with path
    ]
    
    def validate(self, output: str, chunks: List[dict] = None) -> Tuple[bool, List[str]]:
        """
        Validate output for prohibited content.
        
        Args:
            output: LLM generated output
            chunks: CV chunks for cross-validation
            
        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        violations = []
        
        # Check 1: External URLs
        url_violations = self._check_external_urls(output)
        if url_violations:
            violations.extend(url_violations)
        
        # Check 2: Duplicate sections (same content appearing twice)
        if self._check_duplicates(output):
            violations.append("Duplicate content sections detected")
        
        # Check 3: Malformed candidate references
        malformed = self._check_malformed_references(output)
        if malformed:
            violations.extend(malformed)
        
        is_valid = len(violations) == 0
        
        if not is_valid:
            logger.warning(f"[VALIDATOR] Output validation failed: {violations}")
        else:
            logger.info("[VALIDATOR] Output validation passed")
        
        return is_valid, violations
    
    def _check_external_urls(self, text: str) -> List[str]:
        """Check for prohibited external URLs."""
        violations = []
        
        for pattern in self.URL_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches:
                    # Ignore cv: references
                    if not match.startswith('cv:'):
                        violations.append(f"External URL detected: {match}")
                        logger.warning(f"[VALIDATOR] Prohibited URL found: {match}")
        
        return violations
    
    def _check_duplicates(self, text: str) -> bool:
        """Check for duplicated sections (same content appearing twice)."""
        # Simple check: if "Direct Answer:" appears more than once
        direct_answer_count = len(re.findall(r'\*\*Direct Answer:\*\*', text))
        analysis_count = len(re.findall(r'\*\*Analysis:\*\*', text))
        
        if direct_answer_count > 1 or analysis_count > 1:
            logger.warning(
                f"[VALIDATOR] Duplicate sections: "
                f"DirectAnswer={direct_answer_count}, Analysis={analysis_count}"
            )
            return True
        
        return False
    
    def _check_malformed_references(self, text: str) -> List[str]:
        """Check for malformed candidate references."""
        violations = []
        
        # Find all cv: references
        cv_refs = re.findall(r'\[([^\]]+)\]\(cv:([^\)]+)\)', text)
        
        for name, cv_id in cv_refs:
            # Check if cv_id looks valid (should start with cv_)
            if not cv_id.startswith('cv_'):
                violations.append(f"Malformed CV ID: {cv_id} for {name}")
        
        return violations
    
    def sanitize_output(self, output: str) -> str:
        """
        Remove prohibited content from output.
        
        Args:
            output: Raw output
            
        Returns:
            Sanitized output with URLs removed
        """
        sanitized = output
        
        # Remove external URLs
        for pattern in self.URL_PATTERNS:
            sanitized = re.sub(pattern, '[URL removed]', sanitized, flags=re.IGNORECASE)
        
        logger.info("[VALIDATOR] Output sanitized")
        return sanitized


# Singleton instance
_validator_instance = None


def get_validator() -> OutputValidator:
    """Get singleton validator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = OutputValidator()
    return _validator_instance
