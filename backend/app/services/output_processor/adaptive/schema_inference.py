"""
SCHEMA INFERENCE ENGINE - Dynamic Schema Detection

Infers the table schema (columns, types, formats) at runtime based on:
1. Query analysis results
2. Available data in chunks
3. Data characteristics (cardinality, distribution)

This is the BRAIN of the adaptive table system - it decides WHAT columns
to show and HOW to organize them.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .query_analyzer import QueryAnalysis, DataFormat, DetectedAttribute

logger = logging.getLogger(__name__)


class ColumnType(Enum):
    """Types of columns that can be generated."""
    TEXT = "text"                    # Free text (name, description)
    LIST = "list"                    # List of items (skills, languages)
    NUMERIC = "numeric"              # Numbers (years, score)
    PERCENTAGE = "percentage"        # Percentage values
    CATEGORY = "category"            # Categorical (seniority level)
    LINK = "link"                    # Clickable reference


class ColumnRole(Enum):
    """Role of the column in the table."""
    IDENTIFIER = "identifier"        # Primary identifier (candidate name)
    PRIMARY_DATA = "primary_data"    # Main data being asked about
    SECONDARY_DATA = "secondary"     # Supporting data
    METRIC = "metric"                # Calculated metric (score, count)
    AGGREGATION = "aggregation"      # Aggregated value


@dataclass
class ColumnDefinition:
    """Definition of a dynamically generated column."""
    name: str                        # Display name
    key: str                         # Data key to extract
    column_type: ColumnType
    role: ColumnRole
    width_hint: str = "auto"         # "narrow", "medium", "wide", "auto"
    sortable: bool = True
    format_template: Optional[str] = None  # e.g., "{value}%" or "{value} years"
    extract_from: str = "metadata"   # "metadata", "content", "computed"
    extraction_patterns: List[str] = field(default_factory=list)
    aggregation_method: Optional[str] = None  # "count", "join", "first"


@dataclass
class TableSchema:
    """Complete schema for a dynamic table."""
    columns: List[ColumnDefinition]
    row_entity: str                  # "candidate" or "attribute"
    sort_column: Optional[str] = None
    sort_descending: bool = True
    group_by: Optional[str] = None
    max_rows: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None


class SchemaInferenceEngine:
    """
    Dynamically infers table schema based on query and available data.
    
    This engine:
    1. Analyzes what columns make sense for the query
    2. Checks what data is actually available in chunks
    3. Determines column types and formats
    4. Decides row organization (candidates vs attributes as rows)
    """
    
    # Standard column templates
    COLUMN_TEMPLATES = {
        "candidate_name": ColumnDefinition(
            name="Candidate",
            key="candidate_name",
            column_type=ColumnType.LINK,
            role=ColumnRole.IDENTIFIER,
            width_hint="medium",
            extract_from="metadata"
        ),
        "cv_id": ColumnDefinition(
            name="CV ID",
            key="cv_id",
            column_type=ColumnType.TEXT,
            role=ColumnRole.IDENTIFIER,
            width_hint="narrow",
            extract_from="metadata"
        ),
        "skills": ColumnDefinition(
            name="Skills",
            key="skills",
            column_type=ColumnType.LIST,
            role=ColumnRole.PRIMARY_DATA,
            width_hint="wide",
            extract_from="metadata",
            aggregation_method="join"
        ),
        "technologies": ColumnDefinition(
            name="Technologies",
            key="skills",  # Often same as skills
            column_type=ColumnType.LIST,
            role=ColumnRole.PRIMARY_DATA,
            width_hint="wide",
            extract_from="metadata",
            aggregation_method="join"
        ),
        "languages": ColumnDefinition(
            name="Languages",
            key="languages",
            column_type=ColumnType.LIST,
            role=ColumnRole.PRIMARY_DATA,
            width_hint="medium",
            extract_from="metadata",
            aggregation_method="join"
        ),
        "experience": ColumnDefinition(
            name="Experience",
            key="total_experience_years",
            column_type=ColumnType.NUMERIC,
            role=ColumnRole.SECONDARY_DATA,
            width_hint="narrow",
            format_template="{value} yrs",
            extract_from="metadata"
        ),
        "current_role": ColumnDefinition(
            name="Current Role",
            key="current_role",
            column_type=ColumnType.TEXT,
            role=ColumnRole.SECONDARY_DATA,
            width_hint="medium",
            extract_from="metadata"
        ),
        "seniority": ColumnDefinition(
            name="Level",
            key="seniority_level",
            column_type=ColumnType.CATEGORY,
            role=ColumnRole.SECONDARY_DATA,
            width_hint="narrow",
            extract_from="metadata"
        ),
        "location": ColumnDefinition(
            name="Location",
            key="location",
            column_type=ColumnType.TEXT,
            role=ColumnRole.SECONDARY_DATA,
            width_hint="medium",
            extract_from="metadata"
        ),
        "score": ColumnDefinition(
            name="Match",
            key="score",
            column_type=ColumnType.PERCENTAGE,
            role=ColumnRole.METRIC,
            width_hint="narrow",
            format_template="{value}%",
            extract_from="computed"
        ),
        "count": ColumnDefinition(
            name="Count",
            key="count",
            column_type=ColumnType.NUMERIC,
            role=ColumnRole.METRIC,
            width_hint="narrow",
            extract_from="computed"
        ),
        "frequency": ColumnDefinition(
            name="Frequency",
            key="frequency",
            column_type=ColumnType.PERCENTAGE,
            role=ColumnRole.METRIC,
            width_hint="narrow",
            format_template="{value}%",
            extract_from="computed"
        ),
    }
    
    def infer_schema(
        self, 
        analysis: QueryAnalysis,
        chunks: List[Dict[str, Any]]
    ) -> TableSchema:
        """
        Infer the complete table schema based on query analysis and data.
        
        Args:
            analysis: Result from QueryAnalyzer
            chunks: Available data chunks
            
        Returns:
            TableSchema with all column definitions
        """
        logger.info(f"[SCHEMA_INFERENCE] Inferring schema for format: {analysis.suggested_format.value}")
        
        # Get available metadata keys from chunks
        available_keys = self._get_available_keys(chunks)
        logger.info(f"[SCHEMA_INFERENCE] Available metadata keys: {available_keys}")
        
        # Determine row entity based on format
        if analysis.suggested_format == DataFormat.ATTRIBUTE_ROWS:
            row_entity = "attribute"
            columns = self._build_attribute_centric_columns(analysis, available_keys)
        elif analysis.suggested_format == DataFormat.MATRIX:
            row_entity = "candidate"
            columns = self._build_matrix_columns(analysis, available_keys)
        else:
            row_entity = "candidate"
            columns = self._build_candidate_centric_columns(analysis, available_keys)
        
        # Determine sort column
        sort_column = self._determine_sort_column(columns, analysis)
        
        # Generate title
        title = self._generate_title(analysis)
        
        return TableSchema(
            columns=columns,
            row_entity=row_entity,
            sort_column=sort_column,
            sort_descending=True,
            max_rows=analysis.limit_hint or 20,
            title=title,
            description=f"Dynamic table for: {analysis.original_query}"
        )
    
    def _get_available_keys(self, chunks: List[Dict[str, Any]]) -> Set[str]:
        """Get all unique keys available in chunk metadata."""
        keys = set()
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            keys.update(meta.keys())
            # Also check top-level keys
            for key in ["cv_id", "candidate_name", "score", "content"]:
                if key in chunk:
                    keys.add(key)
        return keys
    
    def _build_candidate_centric_columns(
        self, 
        analysis: QueryAnalysis,
        available_keys: Set[str]
    ) -> List[ColumnDefinition]:
        """Build columns with candidates as rows."""
        columns = []
        added_keys = set()
        
        # Always start with candidate name
        columns.append(self._get_or_create_column("candidate_name"))
        added_keys.add("candidate_name")
        
        # Add columns for each detected attribute
        for attr in analysis.detected_attributes:
            col = self._create_column_for_attribute(attr, available_keys)
            if col and col.key not in added_keys:
                columns.append(col)
                added_keys.add(col.key)
        
        # SMART FALLBACK: For generic queries, always include skills/technologies
        # This ensures we show relevant data even when attribute detection is vague
        attr_names = [a.name for a in analysis.detected_attributes]
        has_skill_col = any(k in added_keys for k in ["skills", "technologies"])
        
        if not has_skill_col:
            # Add skills column - extracted from content if not in metadata
            skills_col = ColumnDefinition(
                name="Skills/Keywords",
                key="skills",
                column_type=ColumnType.LIST,
                role=ColumnRole.PRIMARY_DATA,
                width_hint="wide",
                extract_from="content",  # Extract from content as fallback
                aggregation_method="join"
            )
            columns.append(skills_col)
            added_keys.add("skills")
        
        # Add score column if relevant
        if "score" not in added_keys:
            columns.append(self._get_or_create_column("score"))
            added_keys.add("score")
        
        # Add experience column for context
        if "total_experience_years" in available_keys and "total_experience_years" not in added_keys:
            columns.append(self._get_or_create_column("experience"))
            added_keys.add("total_experience_years")
        
        return columns
    
    def _build_attribute_centric_columns(
        self, 
        analysis: QueryAnalysis,
        available_keys: Set[str]
    ) -> List[ColumnDefinition]:
        """Build columns with attributes as rows (for distribution views)."""
        columns = []
        
        # Primary attribute column
        attr_name = analysis.detected_attributes[0].name if analysis.detected_attributes else "Attribute"
        columns.append(ColumnDefinition(
            name=attr_name.title(),
            key="attribute_value",
            column_type=ColumnType.TEXT,
            role=ColumnRole.IDENTIFIER,
            width_hint="medium",
            extract_from="computed"
        ))
        
        # Candidates who have this attribute
        columns.append(ColumnDefinition(
            name="Candidates",
            key="candidates",
            column_type=ColumnType.LIST,
            role=ColumnRole.PRIMARY_DATA,
            width_hint="wide",
            extract_from="computed",
            aggregation_method="join"
        ))
        
        # Count column
        columns.append(self._get_or_create_column("count"))
        
        # Frequency percentage
        columns.append(self._get_or_create_column("frequency"))
        
        return columns
    
    def _build_matrix_columns(
        self, 
        analysis: QueryAnalysis,
        available_keys: Set[str]
    ) -> List[ColumnDefinition]:
        """Build columns for matrix view (candidate × multiple attributes)."""
        columns = []
        
        # Candidate identifier
        columns.append(self._get_or_create_column("candidate_name"))
        
        # Column for each detected attribute
        for attr in analysis.detected_attributes:
            col = self._create_column_for_attribute(attr, available_keys)
            if col:
                columns.append(col)
        
        # Score
        columns.append(self._get_or_create_column("score"))
        
        return columns
    
    def _create_column_for_attribute(
        self, 
        attr: DetectedAttribute,
        available_keys: Set[str]
    ) -> Optional[ColumnDefinition]:
        """Create a column definition for a detected attribute."""
        # Check if we have a template
        if attr.name in self.COLUMN_TEMPLATES:
            template = self.COLUMN_TEMPLATES[attr.name]
            # Verify data is available
            if template.key in available_keys or template.extract_from == "content":
                return ColumnDefinition(
                    name=template.name,
                    key=template.key,
                    column_type=template.column_type,
                    role=ColumnRole.PRIMARY_DATA,
                    width_hint=template.width_hint,
                    format_template=template.format_template,
                    extract_from=template.extract_from,
                    extraction_patterns=attr.content_patterns,
                    aggregation_method=template.aggregation_method
                )
        
        # Try to find a matching key in available data
        for key in attr.metadata_keys:
            if key in available_keys:
                return ColumnDefinition(
                    name=attr.name.replace("_", " ").title(),
                    key=key,
                    column_type=ColumnType.TEXT,
                    role=ColumnRole.PRIMARY_DATA,
                    width_hint="medium",
                    extract_from="metadata"
                )
        
        # Create a content-extracted column
        if attr.content_patterns:
            return ColumnDefinition(
                name=attr.name.replace("_", " ").title(),
                key=attr.name,
                column_type=ColumnType.LIST,
                role=ColumnRole.PRIMARY_DATA,
                width_hint="wide",
                extract_from="content",
                extraction_patterns=attr.content_patterns,
                aggregation_method="join"
            )
        
        return None
    
    def _get_or_create_column(self, name: str) -> ColumnDefinition:
        """Get a column from templates or create a basic one."""
        if name in self.COLUMN_TEMPLATES:
            return self.COLUMN_TEMPLATES[name]
        
        return ColumnDefinition(
            name=name.replace("_", " ").title(),
            key=name,
            column_type=ColumnType.TEXT,
            role=ColumnRole.SECONDARY_DATA,
            width_hint="medium",
            extract_from="metadata"
        )
    
    def _determine_sort_column(
        self, 
        columns: List[ColumnDefinition],
        analysis: QueryAnalysis
    ) -> Optional[str]:
        """Determine which column to sort by."""
        # Use preference from analysis
        if analysis.sort_preference:
            pref_map = {
                "score": "score",
                "frequency": "frequency",
                "count": "count",
                "experience": "total_experience_years",
                "alphabetical": "candidate_name"
            }
            if analysis.sort_preference in pref_map:
                target_key = pref_map[analysis.sort_preference]
                for col in columns:
                    if col.key == target_key:
                        return col.key
        
        # Default: sort by metric columns
        for col in columns:
            if col.role == ColumnRole.METRIC:
                return col.key
        
        return None
    
    def _generate_title(self, analysis: QueryAnalysis) -> str:
        """Generate a descriptive title for the table."""
        attrs = [a.name.replace("_", " ").title() for a in analysis.detected_attributes]
        
        if analysis.suggested_format == DataFormat.ATTRIBUTE_ROWS:
            if attrs:
                return f"{attrs[0]} Distribution"
            return "Attribute Distribution"
        elif analysis.suggested_format == DataFormat.CANDIDATE_ROWS:
            if attrs:
                return f"Candidates by {', '.join(attrs)}"
            return "Candidate Overview"
        elif analysis.suggested_format == DataFormat.MATRIX:
            return "Candidate Comparison Matrix"
        
        return "Query Results"
