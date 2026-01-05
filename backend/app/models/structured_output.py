"""
Structured output models for modular LLM response processing.

This module defines the data structures for processed LLM outputs,
ensuring consistent and type-safe handling of output components.

VISUAL OUTPUT STRUCTURE:
1. Thinking Process (collapsible, purple)
2. Direct Answer (yellow/gold border)
3. Analysis (cyan border)
4. Candidate Table (with colored match scores)
5. Conclusion (green border)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CVReference:
    """A candidate reference in the output."""
    cv_id: str
    name: str
    context: str = ""


@dataclass
class TableRow:
    """A single row in the candidate comparison table."""
    candidate_name: str
    cv_id: str
    columns: Dict[str, str]  # {"Experience": "5 years", "Skills": "Python, Django"}
    match_score: int  # 0-100 for coloring (green >=90, yellow 70-89, gray <70)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_name": self.candidate_name,
            "cv_id": self.cv_id,
            "columns": self.columns,
            "match_score": self.match_score
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TableRow":
        return cls(
            candidate_name=data.get("candidate_name", ""),
            cv_id=data.get("cv_id", ""),
            columns=data.get("columns", {}),
            match_score=data.get("match_score", 0)
        )


@dataclass
class TableData:
    """Parsed table structure with match scores."""
    title: str = "Candidate Comparison Table"
    headers: List[str] = field(default_factory=list)
    rows: List[TableRow] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "headers": self.headers,
            "rows": [row.to_dict() for row in self.rows]
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TableData":
        """Create from dictionary."""
        rows = [TableRow.from_dict(r) for r in data.get("rows", [])]
        return cls(
            title=data.get("title", "Candidate Comparison Table"),
            headers=data.get("headers", []),
            rows=rows
        )


@dataclass
class StructuredOutput:
    """
    Complete structured output from LLM processing.
    
    This structure guarantees that the frontend always receives
    consistent data, regardless of LLM output quality.
    
    Components (v5.1):
    - Core: direct_answer, thinking, analysis, table_data, conclusion
    - Enhanced: gap_analysis, red_flags, timeline
    """
    # Core components (always present)
    direct_answer: str
    raw_content: str
    
    # Optional core components (null if not found/parsed)
    thinking: Optional[str] = None
    analysis: Optional[str] = None
    table_data: Optional[TableData] = None
    conclusion: Optional[str] = None
    
    # Enhanced components (v5.1)
    gap_analysis: Optional[Dict[str, Any]] = None  # GapAnalysisData.to_dict()
    red_flags: Optional[Dict[str, Any]] = None     # RedFlagsData.to_dict()
    timeline: Optional[Dict[str, Any]] = None      # TimelineData.to_dict()
    
    # Metadata
    cv_references: List[CVReference] = field(default_factory=list)
    parsing_warnings: List[str] = field(default_factory=list)
    fallback_used: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "direct_answer": self.direct_answer,
            "raw_content": self.raw_content,
            "thinking": self.thinking,
            "analysis": self.analysis,
            "table_data": self.table_data.to_dict() if self.table_data else None,
            "conclusion": self.conclusion,
            # Enhanced components (v5.1)
            "gap_analysis": self.gap_analysis,
            "red_flags": self.red_flags,
            "timeline": self.timeline,
            # Metadata
            "cv_references": [
                {"cv_id": ref.cv_id, "name": ref.name, "context": ref.context}
                for ref in self.cv_references
            ],
            "parsing_warnings": self.parsing_warnings,
            "fallback_used": self.fallback_used
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StructuredOutput":
        """Create from dictionary."""
        table_data = None
        if data.get("table_data"):
            table_data = TableData.from_dict(data["table_data"])
        
        cv_refs = [
            CVReference(cv_id=ref["cv_id"], name=ref["name"], context=ref.get("context", ""))
            for ref in data.get("cv_references", [])
        ]
        
        return cls(
            direct_answer=data["direct_answer"],
            raw_content=data["raw_content"],
            thinking=data.get("thinking"),
            analysis=data.get("analysis"),
            table_data=table_data,
            conclusion=data.get("conclusion"),
            # Enhanced components
            gap_analysis=data.get("gap_analysis"),
            red_flags=data.get("red_flags"),
            timeline=data.get("timeline"),
            # Metadata
            cv_references=cv_refs,
            parsing_warnings=data.get("parsing_warnings", []),
            fallback_used=data.get("fallback_used", False)
        )
