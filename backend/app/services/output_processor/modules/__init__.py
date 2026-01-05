"""
Modular output components - IMMUTABLE unless user requests changes.

Each module is responsible for ONE component of the structured output:
- thinking_module: :::thinking::: block (collapsible reasoning)
- direct_answer_module: Direct answer extraction and formatting
- analysis_module: Additional analysis content
- table_module: Table parsing and formatting
- conclusion_module: :::conclusion::: block

DO NOT create parallel functions outside these modules.
DO NOT modify these modules without explicit user request.
"""

from .thinking_module import ThinkingModule
from .direct_answer_module import DirectAnswerModule
from .analysis_module import AnalysisModule
from .table_module import TableModule
from .conclusion_module import ConclusionModule
from .gap_analysis_module import GapAnalysisModule, GapAnalysisData, SkillGap
from .red_flags_module import RedFlagsModule, RedFlagsData, RedFlag
from .timeline_module import TimelineModule, TimelineData, CandidateTimeline

__all__ = [
    # Core modules
    "ThinkingModule",
    "DirectAnswerModule",
    "AnalysisModule",
    "TableModule",
    "ConclusionModule",
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
