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

Each structure uses modules from ../modules/ to build its output.
The same module (e.g., RiskTableModule) can be used by multiple structures.
"""

from .single_candidate_structure import SingleCandidateStructure
from .risk_assessment_structure import RiskAssessmentStructure
from .comparison_structure import ComparisonStructure

__all__ = [
    "SingleCandidateStructure",
    "RiskAssessmentStructure", 
    "ComparisonStructure",
]
