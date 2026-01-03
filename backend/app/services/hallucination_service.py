"""
Hallucination Detection Service for CV Screener.

This module provides post-LLM verification to detect potential hallucinations
by checking if the LLM's response contains information that can be verified
against the actual CV data.
"""
import re
import logging
from typing import Dict, List, Any, Set, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class HallucinationCheckResult:
    """Result of hallucination check."""
    is_valid: bool
    confidence_score: float
    verified_cv_ids: List[str] = field(default_factory=list)
    unverified_cv_ids: List[str] = field(default_factory=list)
    mentioned_names: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class HallucinationService:
    """
    Post-LLM verification service to detect potential hallucinations.
    
    Checks:
    1. CV IDs mentioned in response exist in the provided context
    2. Candidate names match those in the CVs
    3. Claims about skills/experience can be traced to CV content
    """
    
    # Regex to extract CV IDs from LLM response
    CV_ID_PATTERN = re.compile(r'\[CV:(cv_[a-f0-9]+)\]', re.IGNORECASE)
    
    # Regex to extract potential names (2-3 capitalized words)
    NAME_PATTERN = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b')
    
    def __init__(self):
        """Initialize the hallucination service."""
        logger.info("HallucinationService initialized")
    
    def verify_response(
        self,
        llm_response: str,
        context_chunks: List[Dict[str, Any]],
        cv_metadata: List[Dict[str, Any]]
    ) -> HallucinationCheckResult:
        """
        Verify LLM response against the provided CV context.
        
        Args:
            llm_response: The generated response from the LLM
            context_chunks: List of chunks used as context (with content and metadata)
            cv_metadata: List of CV metadata dicts with cv_id and filename
            
        Returns:
            HallucinationCheckResult with verification details
        """
        warnings = []
        details = {}
        
        # Extract real CV IDs from metadata
        real_cv_ids = {meta.get("cv_id", "") for meta in cv_metadata if meta.get("cv_id")}
        details["real_cv_ids"] = list(real_cv_ids)
        
        # Extract real names from filenames
        real_names = set()
        for meta in cv_metadata:
            name = self._extract_name_from_filename(meta.get("filename", ""))
            if name:
                real_names.add(name.lower())
        details["real_names"] = list(real_names)
        
        # 1. Check CV IDs mentioned in response
        mentioned_cv_ids = set(self.CV_ID_PATTERN.findall(llm_response))
        verified_cv_ids = mentioned_cv_ids & real_cv_ids
        unverified_cv_ids = mentioned_cv_ids - real_cv_ids
        
        if unverified_cv_ids:
            warnings.append(f"Unverified CV IDs mentioned: {list(unverified_cv_ids)}")
            logger.warning(f"Hallucination check: Unverified CV IDs: {unverified_cv_ids}")
        
        # 2. Check names mentioned in response
        mentioned_names = self._extract_names(llm_response)
        details["mentioned_names"] = list(mentioned_names)
        
        # Check if mentioned names roughly match real names
        unverified_names = []
        for name in mentioned_names:
            name_lower = name.lower()
            # Check if any part of the name matches
            if not any(
                part in real_name or real_name in part
                for real_name in real_names
                for part in name_lower.split()
            ):
                # Name doesn't match any known candidate
                if not self._is_common_word(name):
                    unverified_names.append(name)
        
        if unverified_names:
            warnings.append(f"Potentially unverified names: {unverified_names}")
            logger.debug(f"Hallucination check: Unverified names: {unverified_names}")
        
        # 3. Calculate confidence score
        confidence_score = self._calculate_confidence(
            mentioned_cv_ids=mentioned_cv_ids,
            verified_cv_ids=verified_cv_ids,
            mentioned_names=mentioned_names,
            unverified_names=unverified_names,
            context_chunks=context_chunks,
            llm_response=llm_response
        )
        
        # 4. Determine overall validity
        is_valid = len(unverified_cv_ids) == 0 and confidence_score >= 0.5
        
        result = HallucinationCheckResult(
            is_valid=is_valid,
            confidence_score=confidence_score,
            verified_cv_ids=list(verified_cv_ids),
            unverified_cv_ids=list(unverified_cv_ids),
            mentioned_names=list(mentioned_names),
            warnings=warnings,
            details=details
        )
        
        logger.info(f"Hallucination check: confidence={confidence_score:.2f}, valid={is_valid}")
        return result
    
    def _extract_names(self, text: str) -> Set[str]:
        """Extract potential candidate names from text."""
        # Find all potential names
        names = set(self.NAME_PATTERN.findall(text))
        
        # Filter out common non-name phrases
        filtered_names = set()
        for name in names:
            if not self._is_common_word(name):
                filtered_names.add(name)
        
        return filtered_names
    
    def _extract_name_from_filename(self, filename: str) -> str:
        """
        Extract candidate name from filename.
        
        Expected formats:
        - hash_FirstName_LastName_JobTitle.pdf
        - FirstName_LastName.pdf
        """
        if not filename:
            return ""
        
        # Remove extension
        name = filename.replace('.pdf', '').replace('.PDF', '')
        
        # Split by underscore
        parts = name.split('_')
        
        if len(parts) >= 3:
            # Skip first part if it looks like a hash (8 hex chars)
            if len(parts[0]) == 8 and all(c in '0123456789abcdef' for c in parts[0].lower()):
                # Take next 2-3 parts as name
                name_parts = []
                for part in parts[1:4]:
                    # Stop at job title words
                    if part.lower() in {'senior', 'junior', 'lead', 'head', 'manager', 'engineer', 'developer', 'analyst', 'designer', 'director', 'specialist'}:
                        break
                    name_parts.append(part)
                return ' '.join(name_parts[:3])
            else:
                return ' '.join(parts[:2])
        elif len(parts) >= 2:
            return ' '.join(parts[:2])
        
        return name[:30]  # Fallback: first 30 chars
    
    def _is_common_word(self, text: str) -> bool:
        """Check if text is a common non-name phrase."""
        common_phrases = {
            # Section headers
            'Understanding Your', 'Your Request', 'Analysis', 'Conclusion',
            'Key Skills', 'Technical Skills', 'Work Experience', 'Education',
            'Summary', 'Overview', 'Recommendation', 'Final Answer',
            # Common phrases in responses
            'Based On', 'According To', 'In Terms', 'Years Experience',
            'Best Candidate', 'Top Candidates', 'No Candidates',
            'Python Developer', 'Senior Developer', 'Lead Engineer',
            # CV-related terms that look like names
            'Project Manager', 'Data Analyst', 'Software Engineer',
            'Machine Learning', 'Deep Learning', 'Full Stack',
        }
        return text in common_phrases or text.lower() in {p.lower() for p in common_phrases}
    
    def _calculate_confidence(
        self,
        mentioned_cv_ids: Set[str],
        verified_cv_ids: Set[str],
        mentioned_names: Set[str],
        unverified_names: List[str],
        context_chunks: List[Dict[str, Any]],
        llm_response: str
    ) -> float:
        """
        Calculate confidence score for the response.
        
        Factors:
        - CV ID verification ratio
        - Name verification
        - Response references context
        - Response length vs context
        """
        scores = []
        weights = []
        
        # Factor 1: CV ID verification (weight: 0.4)
        if mentioned_cv_ids:
            cv_score = len(verified_cv_ids) / len(mentioned_cv_ids)
            scores.append(cv_score)
            weights.append(0.4)
        else:
            # No CV IDs mentioned - neutral
            scores.append(0.5)
            weights.append(0.2)
        
        # Factor 2: Name verification (weight: 0.2)
        if mentioned_names:
            verified_name_count = len(mentioned_names) - len(unverified_names)
            name_score = verified_name_count / len(mentioned_names) if mentioned_names else 0.5
            scores.append(max(0.3, name_score))  # Floor at 0.3 since name matching is imperfect
            weights.append(0.2)
        
        # Factor 3: Context reference (weight: 0.3)
        # Check if response contains terms from context
        if context_chunks:
            context_text = ' '.join(chunk.get('content', '') for chunk in context_chunks).lower()
            response_words = set(re.findall(r'\w+', llm_response.lower()))
            context_words = set(re.findall(r'\w+', context_text))
            
            # Calculate overlap (excluding common words)
            common_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                          'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                          'should', 'may', 'might', 'must', 'shall', 'can', 'and', 'or', 'but',
                          'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as',
                          'this', 'that', 'these', 'those', 'it', 'its', 'they', 'their'}
            
            response_meaningful = response_words - common_words
            context_meaningful = context_words - common_words
            
            if response_meaningful and context_meaningful:
                overlap = len(response_meaningful & context_meaningful)
                context_score = min(1.0, overlap / (len(response_meaningful) * 0.3))
                scores.append(context_score)
                weights.append(0.3)
        
        # Factor 4: Response appropriateness (weight: 0.1)
        # Check for clear "no match" responses which are valid
        no_match_indicators = [
            'no candidate', 'none of the candidate', 'no suitable',
            'not found', 'no match', 'ningún candidato', 'ninguno de los'
        ]
        if any(indicator in llm_response.lower() for indicator in no_match_indicators):
            # "No match" responses are valid and honest
            scores.append(0.9)
            weights.append(0.1)
        else:
            scores.append(0.7)
            weights.append(0.1)
        
        # Calculate weighted average
        if not weights:
            return 0.5
        
        total_weight = sum(weights)
        confidence = sum(s * w for s, w in zip(scores, weights)) / total_weight
        
        return round(confidence, 3)


# Singleton instance
_hallucination_service: Optional[HallucinationService] = None


def get_hallucination_service() -> HallucinationService:
    """Get singleton instance of HallucinationService."""
    global _hallucination_service
    if _hallucination_service is None:
        _hallucination_service = HallucinationService()
    return _hallucination_service
