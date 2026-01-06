"""
MODULES - Reusable components for structured output.

ARCHITECTURE:
- MODULES (this folder): Individual reusable components
- STRUCTURES (../structures/): Complete output assemblers that combine modules

AVAILABLE MODULES:
1. Presentation modules: ThinkingModule, ConclusionModule, DirectAnswerModule
2. Content modules: RiskTableModule, TableModule, AnalysisModule
3. Profile modules: HighlightsModule, CareerModule, SkillsModule, CredentialsModule
4. Enhanced modules: GapAnalysisModule, RedFlagsModule, TimelineModule

Modules are called by STRUCTURES, not directly by orchestrator.
The same module can be used by multiple structures.
"""

from .thinking_module import ThinkingModule
from .direct_answer_module import DirectAnswerModule
from .analysis_module import AnalysisModule
from .table_module import TableModule
from .conclusion_module import ConclusionModule

# Content modules (reusable across structures)
from .risk_table_module import RiskTableModule, RiskAssessmentData, RiskFactor

# Profile modules (for SingleCandidateStructure)
from .highlights_module import HighlightsModule, HighlightsData, HighlightItem
from .career_module import CareerModule, CareerData, CareerEntry
from .skills_module import SkillsModule, SkillsData, SkillEntry
from .credentials_module import CredentialsModule, CredentialsData

# Search & Ranking modules
from .results_table_module import ResultsTableModule, ResultsTableData, SearchResult
from .ranking_criteria_module import RankingCriteriaModule, RankingCriteriaData, RankingCriterion
from .ranking_table_module import RankingTableModule, RankingTableData, RankedCandidate
from .top_pick_module import TopPickModule, TopPickData

# Job Match modules
from .requirements_module import RequirementsModule, RequirementsData, Requirement
from .match_score_module import MatchScoreModule, MatchScoreData, CandidateMatch

# Team Build modules
from .team_requirements_module import TeamRequirementsModule, TeamRequirementsData, TeamRole
from .team_composition_module import TeamCompositionModule, TeamCompositionData, TeamAssignment
from .skill_coverage_module import SkillCoverageModule, SkillCoverageData, SkillCoverage
from .team_risk_module import TeamRiskModule, TeamRiskData, TeamRisk

# Verification modules
from .claim_module import ClaimModule, Claim
from .evidence_module import EvidenceModule, EvidenceData, Evidence
from .verdict_module import VerdictModule, Verdict

# Summary modules
from .talent_pool_module import TalentPoolModule, PoolStats
from .skill_distribution_module import SkillDistributionModule, SkillDistributionData, SkillStats
from .experience_distribution_module import ExperienceDistributionModule, ExperienceDistributionData

# Enhanced modules
from .gap_analysis_module import GapAnalysisModule, GapAnalysisData, SkillGap
from .red_flags_module import RedFlagsModule, RedFlagsData, RedFlag
from .timeline_module import TimelineModule, TimelineData, CandidateTimeline

__all__ = [
    # Presentation modules
    "ThinkingModule",
    "DirectAnswerModule",
    "ConclusionModule",
    
    # Content modules (reusable)
    "AnalysisModule",
    "TableModule",
    "RiskTableModule",
    "RiskAssessmentData",
    "RiskFactor",
    
    # Profile modules
    "HighlightsModule",
    "HighlightsData",
    "HighlightItem",
    "CareerModule",
    "CareerData",
    "CareerEntry",
    "SkillsModule",
    "SkillsData",
    "SkillEntry",
    "CredentialsModule",
    "CredentialsData",
    
    # Search & Ranking modules
    "ResultsTableModule",
    "ResultsTableData",
    "SearchResult",
    "RankingCriteriaModule",
    "RankingCriteriaData",
    "RankingCriterion",
    "RankingTableModule",
    "RankingTableData",
    "RankedCandidate",
    "TopPickModule",
    "TopPickData",
    
    # Job Match modules
    "RequirementsModule",
    "RequirementsData",
    "Requirement",
    "MatchScoreModule",
    "MatchScoreData",
    "CandidateMatch",
    
    # Team Build modules
    "TeamRequirementsModule",
    "TeamRequirementsData",
    "TeamRole",
    "TeamCompositionModule",
    "TeamCompositionData",
    "TeamAssignment",
    "SkillCoverageModule",
    "SkillCoverageData",
    "SkillCoverage",
    "TeamRiskModule",
    "TeamRiskData",
    "TeamRisk",
    
    # Verification modules
    "ClaimModule",
    "Claim",
    "EvidenceModule",
    "EvidenceData",
    "Evidence",
    "VerdictModule",
    "Verdict",
    
    # Summary modules
    "TalentPoolModule",
    "PoolStats",
    "SkillDistributionModule",
    "SkillDistributionData",
    "SkillStats",
    "ExperienceDistributionModule",
    "ExperienceDistributionData",
    
    # Enhanced modules
    "GapAnalysisModule",
    "GapAnalysisData",
    "SkillGap",
    "RedFlagsModule",
    "RedFlagsData",
    "RedFlag",
    "TimelineModule",
    "TimelineData",
    "CandidateTimeline",
]
