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
- "confirm the education credentials"
"""

import logging
import re
from typing import Any, Dict, List

from ...context_resolver import has_reference_pattern, resolve_reference
from ..modules import ConclusionModule, ThinkingModule
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
        
        # PHASE 8.1: Check if this is an education/credentials verification query
        query_lower = query.lower()
        is_education_query = any(kw in query_lower for kw in [
            'education', 'credential', 'degree', 'university', 'college',
            'certification', 'certificate', 'qualification', 'academic'
        ])
        
        if is_education_query:
            return self._assemble_education_verification(llm_output, chunks, query)
        
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
    
    def _assemble_education_verification(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """
        PHASE 8.1: Assemble education/credentials verification with real data table.
        
        Extracts actual education and certification data from CV chunks
        and presents it in a structured table format.
        """
        logger.info("[VERIFICATION_STRUCTURE] Assembling education verification with data table")
        
        # Extract thinking
        thinking = self.thinking_module.extract(llm_output)
        
        # Extract education data from chunks
        education_data = self._extract_education_from_chunks(chunks)
        
        # Build credentials table
        credentials_table = self._build_credentials_table(education_data)
        
        # Count statistics
        total_candidates = len(education_data)
        with_education = sum(1 for c in education_data if c.get("education"))
        with_certs = sum(1 for c in education_data if c.get("certifications"))
        
        # Generate analysis
        analysis = self._generate_education_analysis(education_data)
        
        # Generate conclusion with facts
        conclusion = self._generate_education_conclusion(education_data, total_candidates, with_education, with_certs)
        
        return {
            "structure_type": "verification",
            "query": query,
            "thinking": thinking,
            "claim": {"type": "education", "claim_value": "education credentials verification"},
            "evidence": {
                "evidence": [{"source": "CV metadata", "content": f"Analyzed {total_candidates} candidates"}],
                "total_found": total_candidates
            },
            "verdict": {
                "status": "CONFIRMED" if with_education > 0 else "PARTIAL",
                "confidence": with_education / max(total_candidates, 1),
                "reasoning": f"Found education data for {with_education}/{total_candidates} candidates"
            },
            "credentials_table": credentials_table,
            "education_data": education_data,
            "statistics": {
                "total_candidates": total_candidates,
                "with_education": with_education,
                "with_certifications": with_certs
            },
            "analysis": analysis,
            "conclusion": conclusion,
            "raw_content": llm_output
        }
    
    def _extract_education_from_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract education and certification data from CV chunks."""
        candidates = {}
        
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            cv_id = chunk.get("cv_id") or meta.get("cv_id", "")
            name = meta.get("candidate_name", "Unknown")
            
            if not cv_id or cv_id in candidates:
                continue
            
            # Extract education from metadata
            education = meta.get("education_level", "")
            certifications = meta.get("certifications", "")
            
            # Also try to extract from content
            content = chunk.get("content", "")
            extracted_edu = self._extract_education_from_content(content)
            extracted_certs = self._extract_certifications_from_content(content)
            
            candidates[cv_id] = {
                "cv_id": cv_id,
                "name": name,
                "education": education or extracted_edu or "Not specified",
                "certifications": certifications or extracted_certs or "None listed",
                "experience_years": meta.get("total_experience_years", 0)
            }
        
        return list(candidates.values())
    
    def _extract_education_from_content(self, content: str) -> str:
        """Extract education details from CV content."""
        if not content:
            return ""
        
        # Look for education patterns
        edu_patterns = [
            r'(?:Bachelor|Master|PhD|MBA|BSc|MSc|BA|MA|B\.S\.|M\.S\.)[^,\n]*(?:in|of)[^,\n]+',
            r'(?:University|College|Institute)[^,\n]+',
            r'(?:Degree|Diploma)[^,\n]+',
        ]
        
        for pattern in edu_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                edu = match.group(0).strip()
                if len(edu) > 10:
                    return edu[:100]  # Limit length
        
        return ""
    
    def _extract_certifications_from_content(self, content: str) -> str:
        """Extract certification details from CV content."""
        if not content:
            return ""
        
        # Look for certification patterns
        cert_patterns = [
            r'(?:AWS|Azure|GCP|PMP|CISSP|CCNA|CFA|CPA|CBAP|Scrum|Agile|ITIL)[^,\n]*(?:Certified|Certificate|Professional)?',
            r'Certified\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',
        ]
        
        certs = []
        for pattern in cert_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            certs.extend([m.strip() for m in matches if len(m.strip()) > 3])
        
        if certs:
            return ", ".join(certs[:3])  # Limit to 3 certs
        return ""
    
    def _build_credentials_table(self, education_data: List[Dict[str, Any]]) -> str:
        """Build markdown table with education credentials."""
        if not education_data:
            return "No education data found."
        
        lines = [
            "| Candidate | Education | Certifications | Experience |",
            "|-----------|-----------|----------------|------------|"
        ]
        
        for candidate in education_data:
            name = candidate.get("name", "Unknown")
            cv_id = candidate.get("cv_id", "")
            edu = candidate.get("education", "Not specified")[:50]
            certs = candidate.get("certifications", "None")[:40]
            exp = candidate.get("experience_years", 0)
            
            exp_str = f"{exp:.1f} yrs" if exp > 0 else "N/A"
            
            lines.append(f"| [📄](cv:{cv_id}) **{name}** | {edu} | {certs} | {exp_str} |")
        
        return "\n".join(lines)
    
    def _generate_education_analysis(self, education_data: List[Dict[str, Any]]) -> str:
        """Generate analysis of education credentials."""
        if not education_data:
            return "No candidates found for education analysis."
        
        # Count education levels
        with_degree = sum(1 for c in education_data if any(
            kw in c.get("education", "").lower() 
            for kw in ["bachelor", "master", "phd", "mba", "degree", "university"]
        ))
        with_certs = sum(1 for c in education_data if c.get("certifications", "") not in ["None listed", "None", ""])
        
        total = len(education_data)
        
        analysis_lines = [
            f"**Education Analysis** ({total} candidates reviewed)",
            "",
            f"- **{with_degree}/{total}** candidates have formal degree qualifications",
            f"- **{with_certs}/{total}** candidates have professional certifications",
        ]
        
        # Highlight notable credentials
        notable = []
        for c in education_data:
            edu = c.get("education", "").lower()
            if any(kw in edu for kw in ["phd", "master", "mba"]):
                notable.append(f"**{c['name']}**: {c['education'][:60]}")
        
        if notable:
            analysis_lines.append("")
            analysis_lines.append("**Notable Qualifications:**")
            for n in notable[:5]:
                analysis_lines.append(f"- {n}")
        
        return "\n".join(analysis_lines)
    
    def _generate_education_conclusion(
        self, 
        education_data: List[Dict[str, Any]], 
        total: int,
        with_edu: int,
        with_certs: int
    ) -> str:
        """Generate conclusion for education verification."""
        if not education_data:
            return "No education credentials could be verified from the available CVs."
        
        # Build candidate list with links
        candidate_links = []
        for c in education_data[:6]:
            if c.get("education") not in ["Not specified", ""]:
                candidate_links.append(f"**[{c['name']}](cv:{c['cv_id']})**")
        
        if candidate_links:
            names_str = ", ".join(candidate_links[:-1])
            if len(candidate_links) > 1:
                names_str += f", and {candidate_links[-1]}"
            else:
                names_str = candidate_links[0]
            
            return (
                f"**Verification Complete:** {with_edu}/{total} candidates have verifiable education credentials. "
                f"{names_str} have provided educational details in their CVs. "
                f"Additionally, {with_certs} candidates hold professional certifications."
            )
        
        return f"Education credentials reviewed for {total} candidates. See table above for details."
    
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
                "[VERIFICATION_STRUCTURE] Contradiction: verdict=NOT_FOUND but conclusion is affirmative. Fixing."
            )
        elif status == "CONFIRMED" and is_negative and not is_affirmative:
            # Verdict says CONFIRMED but conclusion is negative
            contradiction_detected = True
            logger.warning(
                "[VERIFICATION_STRUCTURE] Contradiction: verdict=CONFIRMED but conclusion is negative. Fixing."
            )
        elif status == "CONTRADICTED" and is_affirmative and not is_negative:
            # Verdict says CONTRADICTED but conclusion is affirmative
            contradiction_detected = True
            logger.warning(
                "[VERIFICATION_STRUCTURE] Contradiction: verdict=CONTRADICTED but conclusion is affirmative. Fixing."
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
