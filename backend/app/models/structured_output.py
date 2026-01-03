"""
Structured output models for modular LLM response processing.

This module defines the data structures for processed LLM outputs,
ensuring consistent and type-safe handling of output components.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class CVReference:
    """A candidate reference in the output."""
    cv_id: str
    name: str
    context: str = ""  # Where it was mentioned
    

@dataclass
class TableData:
    """Parsed table structure."""
    headers: List[str]
    rows: List[List[str]]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "headers": self.headers,
            "rows": self.rows
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TableData":
        """Create from dictionary."""
        return cls(
            headers=data.get("headers", []),
            rows=data.get("rows", [])
        )


@dataclass
class StructuredOutput:
    """
    Complete structured output from LLM processing.
    
    This structure guarantees that the frontend always receives
    consistent data, regardless of LLM output quality.
    """
    # Core components (always present)
    direct_answer: str
    raw_content: str
    
    # Optional components (null if not found/parsed)
    thinking: Optional[str] = None
    table_data: Optional[TableData] = None
    conclusion: Optional[str] = None
    
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
            "table_data": self.table_data.to_dict() if self.table_data else None,
            "conclusion": self.conclusion,
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
            table_data=table_data,
            conclusion=data.get("conclusion"),
            cv_references=cv_refs,
            parsing_warnings=data.get("parsing_warnings", []),
            fallback_used=data.get("fallback_used", False)
        )
