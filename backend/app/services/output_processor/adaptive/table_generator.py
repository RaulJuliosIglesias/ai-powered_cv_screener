"""
DYNAMIC TABLE GENERATOR - Creates Tables with Variable Structure

Generates tables dynamically based on:
1. Schema (columns defined at runtime)
2. Extracted data
3. Format preferences

The table structure is NEVER fixed - columns, rows, formatting
all adapt to the specific query and available data.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .schema_inference import TableSchema, ColumnDefinition, ColumnType, ColumnRole
from .data_extractor import ExtractionResult, ExtractedRow

logger = logging.getLogger(__name__)


@dataclass
class TableCell:
    """A single cell in the dynamic table."""
    value: Any                             # Raw value
    display_value: str                     # Formatted for display
    column_key: str                        # Which column this belongs to
    column_type: ColumnType                # Type for rendering hints
    is_link: bool = False                  # Should render as link
    link_target: Optional[str] = None      # Link destination


@dataclass
class TableRow:
    """A single row in the dynamic table."""
    identifier: str                        # Row identifier
    identifier_key: str                    # Key (cv_id or attribute)
    cells: List[TableCell] = field(default_factory=list)
    highlight: bool = False                # Should highlight this row


@dataclass
class DynamicTable:
    """Complete dynamic table ready for rendering."""
    title: str
    description: Optional[str]
    columns: List[Dict[str, Any]]          # Column definitions for header
    rows: List[TableRow]                   # Data rows
    total_rows: int                        # Before any limiting
    row_entity: str                        # "candidate" or "attribute"
    sort_info: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "description": self.description,
            "columns": self.columns,
            "rows": [
                {
                    "identifier": row.identifier,
                    "identifier_key": row.identifier_key,
                    "cells": [
                        {
                            "value": cell.value,
                            "display_value": cell.display_value,
                            "column_key": cell.column_key,
                            "column_type": cell.column_type.value,
                            "is_link": cell.is_link,
                            "link_target": cell.link_target
                        }
                        for cell in row.cells
                    ],
                    "highlight": row.highlight
                }
                for row in self.rows
            ],
            "total_rows": self.total_rows,
            "row_entity": self.row_entity,
            "sort_info": self.sort_info,
            "metadata": self.metadata
        }


class DynamicTableGenerator:
    """
    Generates dynamic tables that adapt to query and data.
    
    Key features:
    - Variable number of columns
    - Adaptive formatting per column type
    - Smart value truncation
    - Link generation for candidates
    - Highlighting of top results
    """
    
    def generate(
        self,
        extraction_result: ExtractionResult,
        highlight_top: int = 3
    ) -> DynamicTable:
        """
        Generate a dynamic table from extracted data.
        
        Args:
            extraction_result: Data extraction result with schema
            highlight_top: Number of top rows to highlight
            
        Returns:
            DynamicTable ready for rendering
        """
        schema = extraction_result.schema
        rows_data = extraction_result.rows
        
        logger.info(f"[TABLE_GENERATOR] Generating table with {len(schema.columns)} columns, {len(rows_data)} rows")
        
        # Build column definitions for header
        columns = self._build_column_headers(schema.columns)
        
        # Build data rows
        rows = []
        for i, row_data in enumerate(rows_data):
            row = self._build_row(
                row_data,
                schema.columns,
                highlight=(i < highlight_top)
            )
            rows.append(row)
        
        # Build sort info
        sort_info = None
        if schema.sort_column:
            sort_info = {
                "column": schema.sort_column,
                "descending": schema.sort_descending
            }
        
        return DynamicTable(
            title=schema.title or "Results",
            description=schema.description,
            columns=columns,
            rows=rows,
            total_rows=len(rows_data),
            row_entity=schema.row_entity,
            sort_info=sort_info,
            metadata={
                "generated_dynamically": True,
                "columns_count": len(columns),
                "rows_displayed": len(rows)
            }
        )
    
    def _build_column_headers(
        self,
        columns: List[ColumnDefinition]
    ) -> List[Dict[str, Any]]:
        """Build column header definitions."""
        headers = []
        
        for col in columns:
            headers.append({
                "key": col.key,
                "name": col.name,
                "type": col.column_type.value,
                "role": col.role.value,
                "sortable": col.sortable,
                "width_hint": col.width_hint
            })
        
        return headers
    
    def _build_row(
        self,
        row_data: ExtractedRow,
        columns: List[ColumnDefinition],
        highlight: bool = False
    ) -> TableRow:
        """Build a single table row."""
        cells = []
        
        for col in columns:
            value = row_data.values.get(col.key)
            cell = self._build_cell(col, value, row_data)
            cells.append(cell)
        
        return TableRow(
            identifier=row_data.identifier,
            identifier_key=row_data.identifier_key,
            cells=cells,
            highlight=highlight
        )
    
    def _build_cell(
        self,
        col: ColumnDefinition,
        value: Any,
        row_data: ExtractedRow
    ) -> TableCell:
        """Build a single table cell with proper formatting."""
        # Handle None/empty values
        if value is None or value == "":
            return TableCell(
                value=None,
                display_value="-",
                column_key=col.key,
                column_type=col.column_type
            )
        
        # Format based on column type
        display_value = self._format_value(value, col)
        
        # Check if it should be a link
        is_link = col.column_type == ColumnType.LINK
        link_target = None
        
        if is_link and col.key == "candidate_name":
            cv_id = row_data.values.get("cv_id", row_data.identifier_key)
            link_target = f"cv:{cv_id}"
        
        return TableCell(
            value=value,
            display_value=display_value,
            column_key=col.key,
            column_type=col.column_type,
            is_link=is_link,
            link_target=link_target
        )
    
    def _format_value(
        self,
        value: Any,
        col: ColumnDefinition
    ) -> str:
        """Format value for display based on column type."""
        if value is None:
            return "-"
        
        # Apply format template if specified
        if col.format_template:
            try:
                return col.format_template.format(value=value)
            except:
                pass
        
        # Format by type
        if col.column_type == ColumnType.PERCENTAGE:
            if isinstance(value, (int, float)):
                return f"{value:.0f}%"
            return f"{value}%"
        
        elif col.column_type == ColumnType.NUMERIC:
            if isinstance(value, float):
                if value == int(value):
                    return str(int(value))
                return f"{value:.1f}"
            return str(value)
        
        elif col.column_type == ColumnType.LIST:
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            # Truncate long lists
            if isinstance(value, str) and len(value) > 100:
                items = value.split(", ")
                if len(items) > 5:
                    return ", ".join(items[:5]) + f" +{len(items)-5} more"
            return str(value)
        
        elif col.column_type == ColumnType.CATEGORY:
            # Capitalize category values
            return str(value).upper()
        
        # Default: convert to string
        return str(value)
    
    def to_markdown(self, table: DynamicTable) -> str:
        """Convert dynamic table to markdown format."""
        if not table.rows:
            return "*No data available*"
        
        lines = []
        
        # Title
        if table.title:
            lines.append(f"### {table.title}")
            lines.append("")
        
        # Header row
        header_cells = [col["name"] for col in table.columns]
        lines.append("| " + " | ".join(header_cells) + " |")
        
        # Separator
        separators = ["-" * max(3, len(name)) for name in header_cells]
        lines.append("| " + " | ".join(separators) + " |")
        
        # Data rows
        for row in table.rows:
            cells = []
            for cell in row.cells:
                display = cell.display_value
                if cell.is_link and cell.link_target:
                    display = f"[{display}]({cell.link_target})"
                cells.append(display)
            
            prefix = "**" if row.highlight else ""
            suffix = "**" if row.highlight else ""
            
            if row.highlight:
                cells[0] = f"**{cells[0]}**"
            
            lines.append("| " + " | ".join(cells) + " |")
        
        return "\n".join(lines)
