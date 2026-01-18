"""
Risk Table Module - REUSABLE TABLE COMPONENT

This is a MÓDULO (not a structure) that generates the 5-factor Risk Assessment TABLE.

ARCHITECTURE:
- This MODULE is used by multiple STRUCTURES:
  1. SingleCandidateStructure (embedded in full profile)
  2. RiskAssessmentStructure (standalone risk query)

The module ONLY generates the table. The structures combine this with other modules.

DO NOT duplicate this functionality. Import and use this module.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RiskFactor:
    """Single risk factor in the assessment."""
    factor: str       # e.g., "🚩 Red Flags", "🔄 Job Hopping"
    status: str       # e.g., "✅ Low", "⚠️ High", "⚡ Moderate"
    details: str      # e.g., "Score: 50%, Avg tenure: 1.3 yrs"
    status_icon: str  # "✅", "⚠️", "⚡"
    status_text: str  # "Low", "High", "Moderate", "None", etc.


@dataclass
class RiskAssessmentData:
    """Complete risk assessment for a candidate."""
    candidate_name: str
    cv_id: str
    factors: List[RiskFactor] = field(default_factory=list)
    has_issues: bool = False
    overall_risk: str = "low"  # "low", "moderate", "high"
    analysis_text: str = ""    # Generated analysis paragraph
    
    # Raw metrics for reference
    job_hopping_score: float = 0.0
    avg_tenure_years: float = 0.0
    total_experience_years: float = 0.0
    employment_gaps_count: int = 0
    position_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_name": self.candidate_name,
            "cv_id": self.cv_id,
            "factors": [
                {
                    "factor": f.factor,
                    "status": f.status,
                    "details": f.details,
                    "status_icon": f.status_icon,
                    "status_text": f.status_text
                }
                for f in self.factors
            ],
            "has_issues": self.has_issues,
            "overall_risk": self.overall_risk,
            "analysis_text": self.analysis_text,
            "metrics": {
                "job_hopping_score": self.job_hopping_score,
                "avg_tenure_years": self.avg_tenure_years,
                "total_experience_years": self.total_experience_years,
                "employment_gaps_count": self.employment_gaps_count,
                "position_count": self.position_count
            }
        }
    
    def to_markdown_table(self) -> str:
        """Generate the markdown table for LLM output."""
        if not self.factors:
            return "| Factor | Status | Details |\n|--------|--------|---------|\n| ℹ️ Data | Pending | Risk metrics not yet calculated |"
        
        lines = [
            "| Factor | Status | Details |",
            "|:-------|:------:|:--------|"
        ]
        for f in self.factors:
            lines.append(f"| **{f.factor}** | {f.status} | {f.details} |")
        
        return "\n".join(lines)


class RiskTableModule:
    """
    REUSABLE Risk Table Module - Generates the 5-factor risk assessment TABLE.
    
    This is a MODULE, not a STRUCTURE. It generates:
    1. Risk Assessment table (5 factors)
    2. Analysis text describing the risk profile
    3. Overall risk classification
    
    Used by STRUCTURES:
    - SingleCandidateStructure (embedded)
    - RiskAssessmentStructure (standalone)
    
    Usage:
        module = RiskTableModule()
        data = module.extract(chunks, candidate_name, cv_id)
        table_md = data.to_markdown_table()
        analysis = data.analysis_text
    """
    
    # Thresholds for classification
    JOB_HOPPING_LOW = 0.3      # < 30% = Low
    JOB_HOPPING_MODERATE = 0.5  # 30-50% = Moderate, > 50% = High
    
    TENURE_CONCERN = 1.5  # avg tenure < 1.5 years triggers concern
    
    def extract(
        self,
        chunks: List[Dict[str, Any]],
        candidate_name: str = "Unknown",
        cv_id: str = "",
        llm_output: str = ""
    ) -> RiskAssessmentData:
        """
        Extract risk assessment from chunk metadata OR LLM output.
        
        Priority:
        1. Try to extract from chunk enriched metadata (pre-calculated)
        2. Fallback: Parse from LLM output (LLM-generated table)
        
        Args:
            chunks: CV chunks with enriched metadata
            candidate_name: Name of the candidate
            cv_id: CV identifier
            llm_output: Raw LLM response (optional, for fallback parsing)
            
        Returns:
            RiskAssessmentData with factors, table, and analysis
        """
        data = RiskAssessmentData(
            candidate_name=self._clean_candidate_name(candidate_name),
            cv_id=cv_id
        )
        
        if not chunks:
            logger.warning(f"[RISK_ASSESSMENT] No chunks provided for {candidate_name}")
            # Try LLM output fallback
            if llm_output:
                return self._extract_from_llm_output(llm_output, candidate_name, cv_id)
            return data
        
        # Find chunk with enriched metadata
        enriched_meta = self._find_enriched_metadata(chunks)
        
        if not enriched_meta:
            logger.warning(f"[RISK_ASSESSMENT] No enriched metadata found for {candidate_name}")
            # FALLBACK: Try to parse from LLM output
            if llm_output:
                logger.info("[RISK_ASSESSMENT] Attempting fallback: parsing from LLM output")
                return self._extract_from_llm_output(llm_output, candidate_name, cv_id)
            data.analysis_text = f"Risk metrics have not been calculated for {candidate_name}. Please re-index the CV to generate risk assessment data."
            return data
        
        # Extract raw metrics
        data.job_hopping_score = float(enriched_meta.get("job_hopping_score", 0))
        data.avg_tenure_years = float(enriched_meta.get("avg_tenure_years", 0))
        data.total_experience_years = float(enriched_meta.get("total_experience_years", 0))
        data.employment_gaps_count = int(enriched_meta.get("employment_gaps_count", 0))
        data.position_count = int(enriched_meta.get("position_count", 0) or 0)
        current_role = enriched_meta.get("current_role", "N/A")
        current_company = enriched_meta.get("current_company", "N/A")
        
        logger.info(f"[RISK_ASSESSMENT] Metrics for {candidate_name}: "
                   f"job_hopping={data.job_hopping_score:.0%}, "
                   f"tenure={data.avg_tenure_years:.1f}yrs, "
                   f"exp={data.total_experience_years:.1f}yrs")
        
        # Generate the 5 risk factors
        data.factors = self._generate_factors(data, current_role, current_company)
        
        # Determine overall risk level
        # NOTE: tenure=0 means NO DATA, not short tenure - only consider if tenure > 0
        tenure_is_short = data.avg_tenure_years > 0 and data.avg_tenure_years < self.TENURE_CONCERN and data.position_count >= 2
        
        # PHASE 1.3 FIX: Zero/missing experience is a risk factor
        # Candidates with 0 years experience should NOT be "low risk"
        has_no_experience = data.total_experience_years == 0 and data.position_count == 0
        has_minimal_experience = data.total_experience_years == 0 and data.position_count > 0  # Has positions but no years calculated
        
        data.has_issues = data.job_hopping_score > self.JOB_HOPPING_MODERATE or \
                         tenure_is_short or \
                         data.employment_gaps_count > 0 or \
                         has_no_experience  # NEW: Zero experience is an issue
        
        if data.job_hopping_score > self.JOB_HOPPING_MODERATE:
            data.overall_risk = "high"
        elif has_no_experience:
            # PHASE 1.3: Zero experience = at least moderate risk (data quality concern)
            data.overall_risk = "moderate"
            logger.info(f"[RISK_ASSESSMENT] Zero experience detected for {candidate_name} - marking as moderate risk")
        elif data.job_hopping_score > self.JOB_HOPPING_LOW or tenure_is_short:
            data.overall_risk = "moderate"
        elif has_minimal_experience:
            # Has positions but couldn't calculate years - caution
            data.overall_risk = "moderate"
        else:
            data.overall_risk = "low"
        
        # Generate analysis text
        data.analysis_text = self._generate_analysis(data)
        
        return data
    
    def _find_enriched_metadata(self, chunks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find chunk with actual enriched metadata.
        
        PHASE 6.3 FIX: Search ALL chunks thoroughly, prioritizing those with
        actual data (total_experience_years > 0, position_count > 0).
        """
        best_meta = None
        best_score = -1
        
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            
            # Skip if no metadata at all
            if not meta:
                continue
            
            # Calculate a "quality score" for this metadata
            score = 0
            if meta.get("has_enriched_metadata"):
                score += 10
            if meta.get("total_experience_years", 0) > 0:
                score += 5
            if meta.get("position_count", 0) > 0:
                score += 3
            if meta.get("avg_tenure_years", 0) > 0:
                score += 2
            if meta.get("job_hopping_score") is not None:
                score += 1
            
            # Keep the best metadata found
            if score > best_score:
                best_score = score
                best_meta = meta
        
        # Only return if we found meaningful metadata
        if best_score > 0:
            logger.info(f"[RISK_ASSESSMENT] Found enriched metadata with quality score {best_score}")
            return best_meta
        
        return None
    
    def _extract_from_llm_output(
        self,
        llm_output: str,
        candidate_name: str,
        cv_id: str
    ) -> RiskAssessmentData:
        """
        FALLBACK: Parse risk assessment table from LLM markdown output.
        
        This is used when:
        1. CV metadata doesn't have enriched risk metrics
        2. LLM generated a risk assessment in its response
        
        Parses markdown tables with format:
        | Factor | Status | Details |
        |--------|--------|---------|
        | 🚩 Red Flags | ✅ None | ... |
        """
        data = RiskAssessmentData(
            candidate_name=self._clean_candidate_name(candidate_name),
            cv_id=cv_id
        )
        
        if not llm_output:
            return data
        
        logger.info("[RISK_TABLE] Parsing LLM output for risk assessment table")
        
        # Find Risk Assessment section
        risk_section_patterns = [
            r'(?:###?\s*)?(?:⚠️\s*)?Risk Assessment.*?(?=\n#{1,3}\s|\n\*\*[A-Z]|\Z)',
            r'(?:###?\s*)?Risk (?:Analysis|Evaluation).*?(?=\n#{1,3}\s|\n\*\*[A-Z]|\Z)',
        ]
        
        risk_section = ""
        for pattern in risk_section_patterns:
            match = re.search(pattern, llm_output, re.IGNORECASE | re.DOTALL)
            if match:
                risk_section = match.group(0)
                break
        
        if not risk_section:
            # Try to find any table with risk-related content
            risk_section = llm_output
        
        # Parse markdown table rows
        # Pattern: | Factor | Status | Details |
        table_row_pattern = r'\|\s*\*?\*?([^|]+)\*?\*?\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|'
        
        rows = re.findall(table_row_pattern, risk_section)
        
        factors = []
        for row in rows:
            factor = row[0].strip()
            status = row[1].strip()
            details = row[2].strip()
            
            # Skip header rows
            if factor.lower() in ('factor', '-----', ':---', '---'):
                continue
            if 'factor' in factor.lower() and 'status' in status.lower():
                continue
            
            # Determine status icon
            status_icon = ""
            status_text = status
            if "✅" in status:
                status_icon = "✅"
                status_text = status.replace("✅", "").strip()
            elif "⚠️" in status:
                status_icon = "⚠️"
                status_text = status.replace("⚠️", "").strip()
            elif "⚡" in status:
                status_icon = "⚡"
                status_text = status.replace("⚡", "").strip()
            
            factors.append(RiskFactor(
                factor=factor,
                status=status,
                details=details,
                status_icon=status_icon,
                status_text=status_text
            ))
        
        if factors:
            logger.info(f"[RISK_TABLE] Parsed {len(factors)} factors from LLM output")
            data.factors = factors
            data.has_issues = any("⚠️" in f.status or "High" in f.status for f in factors)
            
            # Extract analysis text (paragraph before or after the table)
            analysis_patterns = [
                r'\*\*[^*]+\*\*\s+(?:presents?|shows?|exhibits?|has)\s+[^.]+(?:risk|profile)[^.]*\.',
                r'(?:Based on|According to|The analysis shows)[^.]+\.',
            ]
            for pattern in analysis_patterns:
                match = re.search(pattern, llm_output, re.IGNORECASE)
                if match:
                    data.analysis_text = match.group(0)
                    break
            
            if not data.analysis_text:
                data.analysis_text = f"Risk assessment for {candidate_name} based on available data."
        else:
            # FALLBACK: No table found - try to extract from text analysis
            logger.info("[RISK_TABLE] No table found, attempting text extraction")
            data = self._extract_from_text_analysis(llm_output, candidate_name, cv_id)
        
        return data
    
    def _extract_from_text_analysis(
        self,
        llm_output: str,
        candidate_name: str,
        cv_id: str
    ) -> RiskAssessmentData:
        """
        FALLBACK 2: Extract risk data from LLM text analysis (no table format).
        
        Parses text like:
        - "low job hopping" / "high job mobility"
        - "three positions in four years"
        - "no employment gaps"
        """
        data = RiskAssessmentData(
            candidate_name=candidate_name,
            cv_id=cv_id
        )
        
        text_lower = llm_output.lower()
        factors = []
        has_issues = False
        
        # 1. RED FLAGS
        if "no significant red flag" in text_lower or "no red flag" in text_lower or "no major concern" in text_lower:
            factors.append(RiskFactor(
                factor="🚩 Red Flags",
                status="✅ None Detected",
                details="Clean profile based on analysis",
                status_icon="✅",
                status_text="None Detected"
            ))
        elif "red flag" in text_lower or "concern" in text_lower or "issue" in text_lower:
            factors.append(RiskFactor(
                factor="🚩 Red Flags",
                status="⚠️ Issues Found",
                details="See analysis for details",
                status_icon="⚠️",
                status_text="Issues Found"
            ))
            has_issues = True
        
        # 2. JOB HOPPING
        if "low job hopping" in text_lower or "low job-hopping" in text_lower:
            factors.append(RiskFactor(
                factor="🔄 Job Hopping",
                status="✅ Low",
                details="Stable employment history",
                status_icon="✅",
                status_text="Low"
            ))
        elif "moderate job" in text_lower or "some job" in text_lower:
            factors.append(RiskFactor(
                factor="🔄 Job Hopping",
                status="⚡ Moderate",
                details="Some position changes",
                status_icon="⚡",
                status_text="Moderate"
            ))
        elif "high job" in text_lower or "frequent job" in text_lower or "high mobility" in text_lower:
            factors.append(RiskFactor(
                factor="🔄 Job Hopping",
                status="⚠️ High",
                details="Frequent position changes",
                status_icon="⚠️",
                status_text="High"
            ))
            has_issues = True
        
        # 3. EMPLOYMENT GAPS
        if "no employment gap" in text_lower or "no gap" in text_lower or "continuous" in text_lower:
            factors.append(RiskFactor(
                factor="⏸️ Employment Gaps",
                status="✅ None",
                details="Continuous employment history",
                status_icon="✅",
                status_text="None"
            ))
        elif "gap" in text_lower:
            factors.append(RiskFactor(
                factor="⏸️ Employment Gaps",
                status="⚠️ Detected",
                details="Employment gaps found",
                status_icon="⚠️",
                status_text="Detected"
            ))
            has_issues = True
        
        # 4. STABILITY - extract positions/years
        positions_match = re.search(r'(\d+)\s*positions?\s*(?:in|over)\s*(\d+)\s*years?', text_lower)
        if positions_match:
            positions = positions_match.group(1)
            years = positions_match.group(2)
            factors.append(RiskFactor(
                factor="📊 Stability",
                status="✅ Stable" if int(positions) <= int(years) else "⚡ Moderate",
                details=f"{positions} positions over {years} years",
                status_icon="✅" if int(positions) <= int(years) else "⚡",
                status_text="Stable" if int(positions) <= int(years) else "Moderate"
            ))
        
        # 5. EXPERIENCE LEVEL
        if "entry" in text_lower or "junior" in text_lower:
            factors.append(RiskFactor(
                factor="🎯 Experience",
                status="Entry",
                details="Entry-level position",
                status_icon="",
                status_text="Entry"
            ))
        elif "mid" in text_lower or "intermediate" in text_lower:
            factors.append(RiskFactor(
                factor="🎯 Experience",
                status="Mid",
                details="Mid-level experience",
                status_icon="",
                status_text="Mid"
            ))
        elif "senior" in text_lower or "lead" in text_lower:
            factors.append(RiskFactor(
                factor="🎯 Experience",
                status="Senior",
                details="Senior-level experience",
                status_icon="",
                status_text="Senior"
            ))
        
        if factors:
            logger.info(f"[RISK_TABLE] Extracted {len(factors)} factors from text analysis")
            data.factors = factors
            data.has_issues = has_issues
            
            # Use conclusion or assessment text as analysis
            conclusion_match = re.search(r':::conclusion\s*(.*?):::', llm_output, re.DOTALL | re.IGNORECASE)
            if conclusion_match:
                data.analysis_text = conclusion_match.group(1).strip()
            else:
                # Look for Assessment: text
                assessment_match = re.search(r'\*?\*?Assessment:?\*?\*?\s*(.+?)(?:\n\n|\Z)', llm_output, re.DOTALL | re.IGNORECASE)
                if assessment_match:
                    data.analysis_text = assessment_match.group(1).strip()
                else:
                    data.analysis_text = f"Risk assessment for {candidate_name} extracted from analysis."
        else:
            logger.warning("[RISK_TABLE] Could not extract risk factors from text")
            data.analysis_text = f"Risk assessment for {candidate_name} - see details above."
        
        return data
    
    def _generate_factors(
        self, 
        data: RiskAssessmentData,
        current_role: str,
        current_company: str
    ) -> List[RiskFactor]:
        """Generate the 5 risk factors for the table."""
        factors = []
        
        score = data.job_hopping_score
        tenure = data.avg_tenure_years
        exp = data.total_experience_years
        gaps = data.employment_gaps_count
        positions = data.position_count
        
        # 1. Red Flags summary with detailed explanation
        # NOTE: tenure=0 means NO DATA, not short tenure - only flag if tenure > 0 AND < threshold
        tenure_is_short = tenure > 0 and tenure < self.TENURE_CONCERN and positions >= 2
        has_flags = score > self.JOB_HOPPING_MODERATE or tenure_is_short or gaps > 0
        
        # PHASE 4.1 FIX: Also flag when data is insufficient for proper assessment
        has_insufficient_data = (exp == 0 and positions == 0) or (positions > 0 and tenure == 0 and exp == 0)
        
        if has_insufficient_data:
            rf_icon, rf_status = "⚡", "Insufficient Data"
            rf_details = "Unable to fully assess - CV data incomplete or missing dates"
        elif has_flags:
            rf_icon, rf_status = "⚠️", "Issues Found"
            # Build detailed explanation of WHY there are flags
            flag_reasons = []
            if score > self.JOB_HOPPING_MODERATE:
                flag_reasons.append(f"high job mobility ({score:.0%} score)")
            if tenure_is_short:
                flag_reasons.append(f"short avg tenure ({tenure:.1f} yrs)")
            if gaps > 0:
                flag_reasons.append(f"{gaps} employment gap(s)")
            rf_details = "Issues: " + ", ".join(flag_reasons) if flag_reasons else "Minor concerns detected"
        else:
            rf_icon, rf_status = "✅", "None Detected"
            rf_details = f"Clean profile: {positions} positions, {tenure:.1f} yrs avg tenure, no gaps"
        
        factors.append(RiskFactor(
            factor="🚩 Red Flags",
            status=f"{rf_icon} {rf_status}",
            details=rf_details,
            status_icon=rf_icon,
            status_text=rf_status
        ))
        
        # 2. Job Hopping with explanation of what the score means
        if score < self.JOB_HOPPING_LOW:
            jh_icon, jh_status = "✅", "Low"
            jh_explanation = f"Stable career: {positions} positions over {exp:.0f} yrs, avg {tenure:.1f} yrs/position"
        elif score < self.JOB_HOPPING_MODERATE:
            jh_icon, jh_status = "⚡", "Moderate"
            jh_explanation = f"Some mobility: {positions} positions over {exp:.0f} yrs, avg {tenure:.1f} yrs/position"
        else:
            jh_icon, jh_status = "⚠️", "High"
            jh_explanation = f"Frequent changes: {positions} positions over {exp:.0f} yrs, avg {tenure:.1f} yrs/position"
        
        factors.append(RiskFactor(
            factor="🔄 Job Hopping",
            status=f"{jh_icon} {jh_status}",
            details=jh_explanation,
            status_icon=jh_icon,
            status_text=jh_status
        ))
        
        # 3. Employment Gaps with WHY explanation
        if gaps == 0:
            gaps_icon, gaps_status = "✅", "None"
            gaps_details = f"Continuous employment history across {positions} positions"
        else:
            gaps_icon, gaps_status = "⚠️", f"{gaps} detected"
            gaps_details = f"{gaps} gap(s) detected between positions - recommend verifying reasons in interview"
        
        factors.append(RiskFactor(
            factor="⏸️ Employment Gaps",
            status=f"{gaps_icon} {gaps_status}",
            details=gaps_details,
            status_icon=gaps_icon,
            status_text=gaps_status
        ))
        
        # 4. Stability with WHY explanation
        if score < self.JOB_HOPPING_LOW:
            stab_icon, stab_status = "✅", "Stable"
            stab_explanation = f"Good stability: {positions} positions over {exp:.0f} yrs indicates commitment"
        elif score < 0.6:
            stab_icon, stab_status = "⚡", "Moderate"
            stab_explanation = f"Moderate stability: {positions} positions over {exp:.0f} yrs, some movement"
        else:
            stab_icon, stab_status = "⚠️", "Unstable"
            stab_explanation = f"Unstable pattern: {positions} positions over {exp:.0f} yrs raises retention concerns"
        
        factors.append(RiskFactor(
            factor="📊 Stability",
            status=f"{stab_icon} {stab_status}",
            details=stab_explanation,
            status_icon=stab_icon,
            status_text=stab_status
        ))
        
        # 5. Experience Level with WHY explanation
        # PHASE 1.3 FIX: Zero experience should show as a concern, not just "Entry"
        if exp == 0 and positions == 0:
            # No experience data at all - this is a data quality concern
            exp_level = "⚠️ Unverified"
            exp_icon = "⚠️"
            exp_reason = "No verifiable experience data"
            role_details = "Experience could not be determined from CV"
        elif exp == 0 and positions > 0:
            # Has positions but no years calculated
            exp_level = "⚡ Incomplete"
            exp_icon = "⚡"
            exp_reason = f"{positions} positions but years not calculated"
            role_details = "Dates may be missing from CV"
        elif exp < 3:
            exp_level = "Entry"
            exp_icon = ""
            exp_reason = "<3 years experience"
            role_details = f"{current_role} @ {current_company}" if current_role != "N/A" else f"{exp:.0f} yrs total"
        elif exp < 7:
            exp_level = "Mid"
            exp_icon = ""
            exp_reason = "3-7 years experience"
            role_details = f"{current_role} @ {current_company}" if current_role != "N/A" else f"{exp:.0f} yrs total"
        elif exp < 15:
            exp_level = "Senior"
            exp_icon = ""
            exp_reason = "7-15 years experience"
            role_details = f"{current_role} @ {current_company}" if current_role != "N/A" else f"{exp:.0f} yrs total"
        else:
            exp_level = "Executive"
            exp_icon = ""
            exp_reason = "15+ years experience"
            role_details = f"{current_role} @ {current_company}" if current_role != "N/A" else f"{exp:.0f} yrs total"
        
        factors.append(RiskFactor(
            factor="🎯 Experience",
            status=f"{exp_icon} {exp_level}".strip(),
            details=f"{exp_reason}: {role_details}",
            status_icon=exp_icon,
            status_text=exp_level
        ))
        
        return factors
    
    def _clean_candidate_name(self, name: str) -> str:
        """Clean candidate name by removing markdown asterisks, extra spaces, and suffixes."""
        if not name:
            return name
        
        # Remove markdown asterisks
        name = name.strip('*').strip()
        
        # Remove common suffixes like "Career", "Profile", etc.
        suffixes_to_remove = ['Career', 'Profile', 'CV', 'Resume']
        for suffix in suffixes_to_remove:
            if name.endswith(suffix):
                name = name[:-len(suffix)].strip()
        
        # Remove extra spaces between words
        words = name.split()
        name = ' '.join(words)
        
        return name
    
    def _generate_analysis(self, data: RiskAssessmentData) -> str:
        """Generate human-readable analysis text based on the metrics."""
        # Clean candidate name
        name = self._clean_candidate_name(data.candidate_name)
        score = data.job_hopping_score
        tenure = data.avg_tenure_years
        exp = data.total_experience_years
        gaps = data.employment_gaps_count
        positions = data.position_count or 0
        
        # PHASE 1.3 FIX: Handle zero experience case explicitly
        if exp == 0 and positions == 0:
            # No experience data - this is a data quality concern
            analysis = (
                f"**{name}** presents an **incomplete profile**. "
                f"No verifiable work experience data was found in the CV. "
                f"This could indicate a fresh graduate, career changer, or incomplete CV data. "
                f"**Recommend verifying experience details directly with the candidate.**"
            )
            return analysis
        
        if exp == 0 and positions > 0:
            # Has positions but no years calculated
            analysis = (
                f"**{name}** shows **{positions} position(s)** but experience years could not be calculated. "
                f"This may indicate missing date information in the CV. "
                f"**Recommend requesting updated CV with employment dates.**"
            )
            return analysis
        
        # Build analysis based on actual data
        if data.overall_risk == "low":
            analysis = (
                f"**{name}** presents a **low-risk profile**. "
                f"With {exp:.0f} years of experience and an average tenure of {tenure:.1f} years per position, "
                f"the candidate demonstrates good job stability. "
            )
            if gaps == 0:
                analysis += "No employment gaps were detected, indicating continuous professional engagement."
            else:
                analysis += f"However, {gaps} employment gap(s) were identified that may warrant discussion."
        
        elif data.overall_risk == "moderate":
            analysis = (
                f"**{name}** shows a **moderate risk profile**. "
                f"The job hopping score of {score:.0%} with an average tenure of {tenure:.1f} years "
                f"suggests some mobility in their career. "
                f"With {positions} positions over {exp:.0f} years, "
            )
            if score >= self.JOB_HOPPING_LOW:
                analysis += "there may be concerns about long-term retention that should be explored in interviews."
            else:
                analysis += "the pattern is within acceptable ranges but should be discussed."
        
        else:  # high risk
            analysis = (
                f"**{name}** exhibits a **higher risk profile**. "
                f"The job hopping score of {score:.0%} and average tenure of only {tenure:.1f} years "
                f"indicate frequent job changes. "
                f"With {positions} positions in {exp:.0f} years, "
                f"retention may be a significant concern. "
            )
            if gaps > 0:
                analysis += f"Additionally, {gaps} employment gap(s) were detected."
            analysis += " Recommend thorough discussion of career motivations during interview."
        
        return analysis
    
    def format(self, data: RiskAssessmentData) -> str:
        """
        Format complete Risk Assessment section for output.
        
        Returns markdown string with:
        - Analysis paragraph
        - Risk Assessment table
        """
        if not data or not data.factors:
            return ""
        
        parts = []
        
        # Analysis paragraph
        if data.analysis_text:
            parts.append(data.analysis_text)
            parts.append("")
        
        # Table
        parts.append("### ⚠️ Risk Assessment")
        parts.append("")
        parts.append(data.to_markdown_table())
        
        return "\n".join(parts)
