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

from .analysis_module import AnalysisModule
from .career_module import CareerData, CareerEntry, CareerModule

# Verification modules
from .claim_module import Claim, ClaimModule
from .conclusion_module import ConclusionModule
from .credentials_module import CredentialsData, CredentialsModule
from .direct_answer_module import DirectAnswerModule
from .evidence_module import Evidence, EvidenceData, EvidenceModule
from .experience_distribution_module import ExperienceDistributionData, ExperienceDistributionModule

# Enhanced modules
from .gap_analysis_module import GapAnalysisData, GapAnalysisModule, SkillGap

# Profile modules (for SingleCandidateStructure)
from .highlights_module import HighlightItem, HighlightsData, HighlightsModule
from .match_score_module import CandidateMatch, MatchScoreData, MatchScoreModule
from .ranking_criteria_module import RankingCriteriaData, RankingCriteriaModule, RankingCriterion
from .ranking_table_module import RankedCandidate, RankingTableData, RankingTableModule
from .red_flags_module import RedFlag, RedFlagsData, RedFlagsModule

# Job Match modules
from .requirements_module import Requirement, RequirementsData, RequirementsModule

# Search & Ranking modules
from .results_table_module import ResultsTableData, ResultsTableModule, SearchResult

# Content modules (reusable across structures)
from .risk_table_module import RiskAssessmentData, RiskFactor, RiskTableModule
from .skill_coverage_module import SkillCoverage, SkillCoverageData, SkillCoverageModule
from .skill_distribution_module import SkillDistributionData, SkillDistributionModule, SkillStats
from .skills_module import SkillEntry, SkillsData, SkillsModule
from .table_module import TableModule

# Summary modules
from .talent_pool_module import PoolStats, TalentPoolModule
from .team_composition_module import TeamAssignment, TeamCompositionData, TeamCompositionModule

# Team Build modules
from .team_requirements_module import TeamRequirementsData, TeamRequirementsModule, TeamRole
from .team_risk_module import TeamRisk, TeamRiskData, TeamRiskModule
from .thinking_module import ThinkingModule
from .timeline_module import CandidateTimeline, TimelineData, TimelineModule
from .top_pick_module import TopPickData, TopPickModule
from .verdict_module import Verdict, VerdictModule

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
