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
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

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
        cv_id: str = ""
    ) -> RiskAssessmentData:
        """
        Extract risk assessment from chunk metadata.
        
        Args:
            chunks: CV chunks with enriched metadata
            candidate_name: Name of the candidate
            cv_id: CV identifier
            
        Returns:
            RiskAssessmentData with factors, table, and analysis
        """
        data = RiskAssessmentData(
            candidate_name=candidate_name,
            cv_id=cv_id
        )
        
        if not chunks:
            logger.warning(f"[RISK_ASSESSMENT] No chunks provided for {candidate_name}")
            return data
        
        # Find chunk with enriched metadata
        enriched_meta = self._find_enriched_metadata(chunks)
        
        if not enriched_meta:
            logger.warning(f"[RISK_ASSESSMENT] No enriched metadata found for {candidate_name}")
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
        data.has_issues = data.job_hopping_score > self.JOB_HOPPING_MODERATE or \
                         data.avg_tenure_years < self.TENURE_CONCERN or \
                         data.employment_gaps_count > 0
        
        if data.job_hopping_score > self.JOB_HOPPING_MODERATE:
            data.overall_risk = "high"
        elif data.job_hopping_score > self.JOB_HOPPING_LOW or data.avg_tenure_years < self.TENURE_CONCERN:
            data.overall_risk = "moderate"
        else:
            data.overall_risk = "low"
        
        # Generate analysis text
        data.analysis_text = self._generate_analysis(data)
        
        return data
    
    def _find_enriched_metadata(self, chunks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find chunk with actual enriched metadata."""
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            # Require has_enriched_metadata flag OR actual job_hopping_score
            if meta.get("has_enriched_metadata") or meta.get("job_hopping_score") is not None:
                return meta
        return None
    
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
        
        # 1. Red Flags summary
        has_flags = score > self.JOB_HOPPING_MODERATE or tenure < self.TENURE_CONCERN or gaps > 0
        if has_flags:
            rf_icon, rf_status = "⚠️", "Issues Found"
            rf_details = "High mobility or gaps" if score > self.JOB_HOPPING_MODERATE else "Moderate concerns"
        else:
            rf_icon, rf_status = "✅", "None Detected"
            rf_details = "Clean profile"
        
        factors.append(RiskFactor(
            factor="🚩 Red Flags",
            status=f"{rf_icon} {rf_status}",
            details=rf_details,
            status_icon=rf_icon,
            status_text=rf_status
        ))
        
        # 2. Job Hopping
        if score < self.JOB_HOPPING_LOW:
            jh_icon, jh_status = "✅", "Low"
        elif score < self.JOB_HOPPING_MODERATE:
            jh_icon, jh_status = "⚡", "Moderate"
        else:
            jh_icon, jh_status = "⚠️", "High"
        
        factors.append(RiskFactor(
            factor="🔄 Job Hopping",
            status=f"{jh_icon} {jh_status}",
            details=f"Score: {score:.0%}, Avg tenure: {tenure:.1f} yrs",
            status_icon=jh_icon,
            status_text=jh_status
        ))
        
        # 3. Employment Gaps
        if gaps == 0:
            gaps_icon, gaps_status = "✅", "None"
            gaps_details = "Continuous history"
        else:
            gaps_icon, gaps_status = "⚠️", f"{gaps} detected"
            gaps_details = "Verify in interview"
        
        factors.append(RiskFactor(
            factor="⏸️ Employment Gaps",
            status=f"{gaps_icon} {gaps_status}",
            details=gaps_details,
            status_icon=gaps_icon,
            status_text=gaps_status
        ))
        
        # 4. Stability
        if score < self.JOB_HOPPING_LOW:
            stab_icon, stab_status = "✅", "Stable"
        elif score < 0.6:
            stab_icon, stab_status = "⚡", "Moderate"
        else:
            stab_icon, stab_status = "⚠️", "Unstable"
        
        factors.append(RiskFactor(
            factor="📊 Stability",
            status=f"{stab_icon} {stab_status}",
            details=f"{positions or 'N/A'} positions over {exp:.0f} years",
            status_icon=stab_icon,
            status_text=stab_status
        ))
        
        # 5. Experience Level
        if exp < 3:
            exp_level = "Entry"
        elif exp < 7:
            exp_level = "Mid"
        elif exp < 15:
            exp_level = "Senior"
        else:
            exp_level = "Executive"
        
        factors.append(RiskFactor(
            factor="🎯 Experience",
            status=exp_level,
            details=f"{current_role} @ {current_company}",
            status_icon="",
            status_text=exp_level
        ))
        
        return factors
    
    def _generate_analysis(self, data: RiskAssessmentData) -> str:
        """Generate human-readable analysis text based on the metrics."""
        name = data.candidate_name
        score = data.job_hopping_score
        tenure = data.avg_tenure_years
        exp = data.total_experience_years
        gaps = data.employment_gaps_count
        positions = data.position_count or "multiple"
        
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
