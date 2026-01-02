import re
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of response validation."""
    is_valid: bool
    original_response: str
    issues: List[str]
    confidence_score: float
    corrected_response: str = None


class HallucinationGuard:
    """Validates that LLM responses only contain information from retrieved context."""
    
    def __init__(self, retrieved_chunks: List[Dict[str, Any]]):
        self.chunks = retrieved_chunks
        self.context = self._build_context()
        self.known_names = self._extract_names()
        self.known_companies = self._extract_companies()
        self.known_numbers = self._extract_numbers()
    
    def _build_context(self) -> str:
        """Build searchable context from chunks."""
        parts = []
        for chunk in self.chunks:
            content = chunk.get("content", "")
            metadata = chunk.get("metadata", {})
            candidate = metadata.get("candidate_name", "")
            parts.append(f"{candidate} {content}")
        return " ".join(parts).lower()
    
    def _extract_names(self) -> set:
        """Extract candidate names from chunks."""
        names = set()
        for chunk in self.chunks:
            metadata = chunk.get("metadata", {})
            name = metadata.get("candidate_name", "")
            if name:
                names.add(name.lower())
                # Also add parts of the name
                for part in name.split():
                    if len(part) > 2:
                        names.add(part.lower())
        return names
    
    def _extract_companies(self) -> set:
        """Extract company names from context using common patterns."""
        companies = set()
        
        # Common company indicators
        patterns = [
            r"(?:at|@|en)\s+([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?)",
            r"([A-Z][A-Za-z0-9]+(?:\s+(?:Inc|LLC|Ltd|Corp|Company|Technologies|Solutions|Labs))?)",
        ]
        
        for chunk in self.chunks:
            content = chunk.get("content", "")
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if len(match) > 2:
                        companies.add(match.lower())
        
        return companies
    
    def _extract_numbers(self) -> set:
        """Extract significant numbers from context."""
        numbers = set()
        
        for chunk in self.chunks:
            content = chunk.get("content", "")
            # Find years
            years = re.findall(r"\b(19|20)\d{2}\b", content)
            numbers.update(years)
            # Find experience years
            exp_years = re.findall(r"(\d+)\s*(?:years?|años?)", content, re.I)
            numbers.update(exp_years)
        
        return numbers
    
    def validate(self, response: str) -> Tuple[bool, List[str]]:
        """Validate response against known context."""
        issues = []
        response_lower = response.lower()
        
        # Check for names that might be hallucinated
        # Extract potential names from response (capitalized words)
        response_names = set(re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", response))
        
        for name in response_names:
            name_lower = name.lower()
            # Check if any part of the name is in our known names
            name_parts = name_lower.split()
            if not any(part in self.known_names for part in name_parts):
                # Could be a hallucinated name, but be lenient
                # Only flag if it looks like a person's name
                if len(name_parts) >= 2 and all(len(p) > 2 for p in name_parts):
                    if name_lower not in self.context:
                        issues.append(f"Potentially unknown name: {name}")
        
        # Check for out-of-scope indicators (this is GOOD)
        out_of_scope_phrases = [
            "i don't have information",
            "not mentioned in the cvs",
            "cannot find",
            "no information about",
            "not in the cvs",
            "no candidates",
        ]
        
        is_honest_decline = any(phrase in response_lower for phrase in out_of_scope_phrases)
        
        # If it's an honest decline, that's valid
        if is_honest_decline:
            return True, []
        
        return len(issues) == 0, issues


class GuardrailsService:
    """Service for validating and guarding LLM outputs."""
    
    def __init__(self):
        self.min_response_length = 20
        self.max_response_length = 5000
    
    def validate_response(
        self,
        response: str,
        retrieved_chunks: List[Dict[str, Any]],
        question: str,
    ) -> ValidationResult:
        """Multi-stage validation of LLM response."""
        issues = []
        confidence_score = 1.0
        
        # Stage 1: Basic validation
        if not response or len(response.strip()) < self.min_response_length:
            issues.append("Response too short")
            confidence_score -= 0.3
        
        if len(response) > self.max_response_length:
            issues.append("Response too long")
            confidence_score -= 0.1
        
        # Stage 2: Hallucination check
        if retrieved_chunks:
            guard = HallucinationGuard(retrieved_chunks)
            is_grounded, hallucination_issues = guard.validate(response)
            
            if not is_grounded:
                issues.extend(hallucination_issues)
                confidence_score -= 0.2 * len(hallucination_issues)
        
        # Stage 3: Source citation check
        if retrieved_chunks:
            has_source_mention = False
            for chunk in retrieved_chunks:
                metadata = chunk.get("metadata", {})
                filename = metadata.get("filename", "")
                candidate = metadata.get("candidate_name", "")
                
                if filename and filename.lower().replace(".pdf", "") in response.lower():
                    has_source_mention = True
                    break
                if candidate and candidate.lower() in response.lower():
                    has_source_mention = True
                    break
            
            if not has_source_mention and len(retrieved_chunks) > 0:
                issues.append("No sources or candidates mentioned")
                confidence_score -= 0.1
        
        # Stage 4: Check for honest "I don't know"
        out_of_scope_phrases = [
            "i don't have information",
            "not in the cvs",
            "cannot find",
        ]
        if any(phrase in response.lower() for phrase in out_of_scope_phrases):
            # This is actually good - model is being honest
            confidence_score = max(confidence_score, 0.9)
        
        # Ensure confidence is within bounds
        confidence_score = max(0.0, min(1.0, confidence_score))
        
        return ValidationResult(
            is_valid=confidence_score >= 0.5 and len([i for i in issues if "unknown name" not in i.lower()]) == 0,
            original_response=response,
            issues=issues,
            confidence_score=confidence_score,
        )
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize user input to prevent prompt injection."""
        # Remove potential prompt injection patterns
        dangerous_patterns = [
            r"ignore\s+(?:all\s+)?(?:previous\s+)?instructions",
            r"disregard\s+(?:all\s+)?(?:previous\s+)?instructions",
            r"forget\s+(?:all\s+)?(?:previous\s+)?instructions",
            r"new\s+instructions?\s*:",
            r"system\s*:",
            r"assistant\s*:",
        ]
        
        sanitized = text
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
