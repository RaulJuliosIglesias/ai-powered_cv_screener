"""
STRUCTURES - Complete output assemblers that combine MODULES.

ARCHITECTURE:
- MODULES: Individual reusable components (tables, sections, blocks)
  Location: ../modules/
  
- STRUCTURES: Complete output formats that combine multiple modules
  Location: ./  (this folder)

AVAILABLE STRUCTURES:
1. SingleCandidateStructure - Full candidate profile
2. RiskAssessmentStructure - Risk-focused analysis
3. ComparisonStructure - Multi-candidate comparison
4. SearchStructure - Search results with match scores
5. RankingStructure - Ranked candidates for a role
6. JobMatchStructure - Match candidates to job requirements
7. TeamBuildStructure - Compose teams from candidates
8. VerificationStructure - Verify claims about candidates
9. SummaryStructure - Talent pool overview

Each structure uses modules from ../modules/ to build its output.
The same module (e.g., RiskTableModule) can be used by multiple structures.
"""

from .single_candidate_structure import SingleCandidateStructure
from .risk_assessment_structure import RiskAssessmentStructure
from .comparison_structure import ComparisonStructure
from .search_structure import SearchStructure
from .ranking_structure import RankingStructure
from .job_match_structure import JobMatchStructure
from .team_build_structure import TeamBuildStructure
from .verification_structure import VerificationStructure
from .summary_structure import SummaryStructure
from .adaptive_structure import AdaptiveStructure

__all__ = [
    "SingleCandidateStructure",
    "RiskAssessmentStructure", 
    "ComparisonStructure",
    "SearchStructure",
    "RankingStructure",
    "JobMatchStructure",
    "TeamBuildStructure",
    "VerificationStructure",
    "SummaryStructure",
    "AdaptiveStructure",
]
