"""
TEAM RISK MODULE

Identifies team composition risks.
Used by: TeamBuildStructure
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TeamRisk:
    """Single team risk."""
    risk_type: str  # "skill_gap", "single_point_of_failure", "seniority_imbalance"
    severity: str  # "high", "medium", "low"
    description: str
    mitigation: str = ""


@dataclass
class TeamRiskData:
    """Container for team risk analysis."""
    risks: List[TeamRisk] = field(default_factory=list)
    overall_risk_level: str = "low"
    
    def to_dict(self) -> Dict:
        return {
            "risks": [
                {
                    "risk_type": r.risk_type,
                    "severity": r.severity,
                    "description": r.description,
                    "mitigation": r.mitigation
                }
                for r in self.risks
            ],
            "overall_risk_level": self.overall_risk_level
        }


class TeamRiskModule:
    """Module for identifying team composition risks."""
    
    def analyze(
        self,
        assignments: List[Dict[str, Any]],
        skill_coverage: Dict[str, Any] = None
    ) -> Optional[TeamRiskData]:
        """Analyze team composition for risks."""
        if not assignments:
            return None
        
        risks = []
        
        # Check for skill gaps
        if skill_coverage:
            gaps = skill_coverage.get("gaps", [])
            if gaps:
                risks.append(TeamRisk(
                    risk_type="skill_gap",
                    severity="high" if len(gaps) > 2 else "medium",
                    description=f"Missing coverage for: {', '.join(gaps[:3])}",
                    mitigation="Consider hiring or training for these skills"
                ))
        
        # Check for single points of failure
        spof_skills = []
        if skill_coverage:
            for cov in skill_coverage.get("coverages", []):
                if cov.get("coverage_level") == "moderate":
                    spof_skills.append(cov.get("skill", ""))
        
        if spof_skills:
            risks.append(TeamRisk(
                risk_type="single_point_of_failure",
                severity="medium",
                description=f"Only one person covers: {', '.join(spof_skills[:3])}",
                mitigation="Consider cross-training or adding redundancy"
            ))
        
        # Check seniority balance
        seniority_count = {"senior": 0, "mid": 0, "junior": 0}
        for a in assignments:
            role = a.get("role_name", "").lower()
            if "senior" in role or "lead" in role:
                seniority_count["senior"] += 1
            elif "junior" in role:
                seniority_count["junior"] += 1
            else:
                seniority_count["mid"] += 1
        
        total = len(assignments)
        if total > 2:
            if seniority_count["senior"] == 0:
                risks.append(TeamRisk(
                    risk_type="seniority_imbalance",
                    severity="medium",
                    description="No senior-level team members identified",
                    mitigation="Consider adding technical leadership"
                ))
            elif seniority_count["junior"] > seniority_count["senior"] + seniority_count["mid"]:
                risks.append(TeamRisk(
                    risk_type="seniority_imbalance",
                    severity="low",
                    description="Team skews toward junior members",
                    mitigation="Ensure adequate mentorship capacity"
                ))
        
        # Check team size
        if total < 2:
            risks.append(TeamRisk(
                risk_type="team_size",
                severity="high",
                description="Team may be too small for project needs",
                mitigation="Consider adding more team members"
            ))
        
        # Determine overall risk level
        high_risks = sum(1 for r in risks if r.severity == "high")
        medium_risks = sum(1 for r in risks if r.severity == "medium")
        
        if high_risks >= 2:
            overall = "high"
        elif high_risks >= 1 or medium_risks >= 2:
            overall = "medium"
        else:
            overall = "low"
        
        logger.info(f"[TEAM_RISK_MODULE] Found {len(risks)} risks, overall: {overall}")
        
        return TeamRiskData(
            risks=risks,
            overall_risk_level=overall
        )
    
    def format(self, data: TeamRiskData) -> str:
        """Format team risks into markdown."""
        if not data:
            return ""
        
        severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        
        lines = [
            "### ⚠️ Team Risk Analysis",
            "",
            f"**Overall Risk Level:** {severity_emoji.get(data.overall_risk_level, '⚪')} {data.overall_risk_level.title()}",
            "",
        ]
        
        if data.risks:
            lines.extend([
                "| Risk | Severity | Description | Mitigation |",
                "|:-----|:--------:|:------------|:-----------|",
            ])
            
            for r in data.risks:
                emoji = severity_emoji.get(r.severity, "⚪")
                lines.append(
                    f"| {r.risk_type.replace('_', ' ').title()} | {emoji} | "
                    f"{r.description} | {r.mitigation} |"
                )
        else:
            lines.append("✅ No significant risks identified.")
        
        return "\n".join(lines)
