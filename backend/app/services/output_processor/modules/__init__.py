"""
MODULES - Reusable components for structured output.

ARCHITECTURE:
- MODULES (this folder): Individual reusable components
- STRUCTURES (../structures/): Complete output assemblers that combine modules

AVAILABLE MODULES:
1. Presentation modules: ThinkingModule, ConclusionModule, DirectAnswerModule
2. Content modules: RiskTableModule, TableModule, AnalysisModule
3. Enhanced modules: GapAnalysisModule, RedFlagsModule, TimelineModule

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
