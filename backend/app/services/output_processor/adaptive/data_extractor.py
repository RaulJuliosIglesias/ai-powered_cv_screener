"""
SMART DATA EXTRACTOR - Dynamic Data Extraction from Chunks

Extracts data from chunks based on the inferred schema.
Handles multiple extraction strategies:
1. Metadata extraction (direct key access)
2. Content extraction (regex patterns)
3. Computed values (aggregations, calculations)

Adapts to whatever data structure is available.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

from .schema_inference import TableSchema, ColumnDefinition, ColumnType

logger = logging.getLogger(__name__)


@dataclass
class ExtractedRow:
    """A single row of extracted data."""
    identifier: str                        # Primary identifier (candidate name or attribute)
    identifier_key: str                    # Key used (cv_id, attribute_value)
    values: Dict[str, Any] = field(default_factory=dict)
    raw_score: float = 0.0


@dataclass 
class ExtractionResult:
    """Complete extraction result."""
    rows: List[ExtractedRow]
    schema: TableSchema
    extraction_stats: Dict[str, Any] = field(default_factory=dict)


class SmartDataExtractor:
    """
    Extracts data dynamically based on schema and available chunks.
    
    Key features:
    - Multi-source extraction (metadata, content, computed)
    - Automatic deduplication by candidate
    - Value aggregation across multiple chunks
    - Pattern-based content extraction
    """
    
    def extract(
        self,
        schema: TableSchema,
        chunks: List[Dict[str, Any]]
    ) -> ExtractionResult:
        """
        Extract data from chunks according to schema.
        
        Args:
            schema: Inferred table schema
            chunks: Raw data chunks
            
        Returns:
            ExtractionResult with all rows and stats
        """
        logger.info(f"[DATA_EXTRACTOR] Extracting data for {len(schema.columns)} columns from {len(chunks)} chunks")
        
        if schema.row_entity == "candidate":
            rows = self._extract_candidate_rows(schema, chunks)
        else:
            rows = self._extract_attribute_rows(schema, chunks)
        
        # Sort rows
        if schema.sort_column:
            rows = self._sort_rows(rows, schema.sort_column, schema.sort_descending)
        
        # Limit rows
        if schema.max_rows:
            rows = rows[:schema.max_rows]
        
        # Calculate stats
        stats = self._calculate_stats(rows, schema)
        
        logger.info(f"[DATA_EXTRACTOR] Extracted {len(rows)} rows")
        
        return ExtractionResult(
            rows=rows,
            schema=schema,
            extraction_stats=stats
        )
    
    def _extract_candidate_rows(
        self,
        schema: TableSchema,
        chunks: List[Dict[str, Any]]
    ) -> List[ExtractedRow]:
        """Extract rows where each row is a candidate."""
        # Group chunks by candidate
        candidates: Dict[str, Dict[str, Any]] = {}
        
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            cv_id = chunk.get("cv_id") or meta.get("cv_id", "")
            name = chunk.get("candidate_name") or meta.get("candidate_name", "Unknown")
            
            if not cv_id:
                continue
            
            if cv_id not in candidates:
                candidates[cv_id] = {
                    "name": name,
                    "cv_id": cv_id,
                    "chunks": [],
                    "metadata_merged": {},
                    "content_merged": "",
                    "max_score": 0.0
                }
            
            candidates[cv_id]["chunks"].append(chunk)
            candidates[cv_id]["content_merged"] += " " + chunk.get("content", "")
            candidates[cv_id]["max_score"] = max(
                candidates[cv_id]["max_score"],
                chunk.get("score", 0.0)
            )
            
            # Merge metadata
            for key, value in meta.items():
                if key not in candidates[cv_id]["metadata_merged"]:
                    candidates[cv_id]["metadata_merged"][key] = value
                elif isinstance(value, str) and value not in str(candidates[cv_id]["metadata_merged"][key]):
                    existing = candidates[cv_id]["metadata_merged"][key]
                    if isinstance(existing, str):
                        candidates[cv_id]["metadata_merged"][key] = f"{existing}, {value}"
        
        # Extract values for each candidate
        rows = []
        for cv_id, data in candidates.items():
            row = ExtractedRow(
                identifier=data["name"],
                identifier_key=cv_id,
                raw_score=data["max_score"]
            )
            
            for col in schema.columns:
                value = self._extract_column_value(
                    col,
                    data["metadata_merged"],
                    data["content_merged"],
                    data["max_score"]
                )
                row.values[col.key] = value
            
            # Ensure we have the identifier
            row.values["candidate_name"] = data["name"]
            row.values["cv_id"] = cv_id
            
            rows.append(row)
        
        return rows
    
    def _extract_attribute_rows(
        self,
        schema: TableSchema,
        chunks: List[Dict[str, Any]]
    ) -> List[ExtractedRow]:
        """Extract rows where each row is an attribute value."""
        # Find the primary data column (the attribute we're analyzing)
        primary_col = None
        for col in schema.columns:
            if col.key == "attribute_value":
                continue
            if col.column_type == ColumnType.LIST:
                primary_col = col
                break
        
        if not primary_col:
            # Fallback to skills
            primary_col = schema.columns[0]
        
        # Extract all values of this attribute from all candidates
        attribute_candidates: Dict[str, List[str]] = defaultdict(list)
        total_candidates = set()
        
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            cv_id = chunk.get("cv_id") or meta.get("cv_id", "")
            name = chunk.get("candidate_name") or meta.get("candidate_name", "Unknown")
            
            if not cv_id:
                continue
            
            total_candidates.add(cv_id)
            
            # Extract attribute values
            values = self._extract_column_value(
                primary_col,
                meta,
                chunk.get("content", ""),
                0.0
            )
            
            if values:
                # Split if it's a comma-separated string
                if isinstance(values, str):
                    for val in values.split(","):
                        val = val.strip()
                        if val and name not in attribute_candidates[val]:
                            attribute_candidates[val].append(name)
                elif isinstance(values, list):
                    for val in values:
                        if val and name not in attribute_candidates[val]:
                            attribute_candidates[val].append(name)
        
        # Build rows
        rows = []
        total = len(total_candidates)
        
        for attr_value, candidates in attribute_candidates.items():
            count = len(set(candidates))  # Unique candidates
            frequency = (count / total * 100) if total > 0 else 0
            
            row = ExtractedRow(
                identifier=attr_value,
                identifier_key=attr_value,
                raw_score=count  # Use count for sorting
            )
            row.values = {
                "attribute_value": attr_value,
                "candidates": ", ".join(sorted(set(candidates))),
                "count": count,
                "frequency": round(frequency, 1)
            }
            rows.append(row)
        
        return rows
    
    def _extract_column_value(
        self,
        col: ColumnDefinition,
        metadata: Dict[str, Any],
        content: str,
        score: float
    ) -> Any:
        """Extract value for a single column."""
        if col.extract_from == "metadata":
            return self._extract_from_metadata(col, metadata)
        elif col.extract_from == "content":
            return self._extract_from_content(col, content)
        elif col.extract_from == "computed":
            return self._compute_value(col, metadata, score)
        
        # Try all sources
        value = self._extract_from_metadata(col, metadata)
        if not value:
            value = self._extract_from_content(col, content)
        if not value:
            value = self._compute_value(col, metadata, score)
        
        return value
    
    def _extract_from_metadata(
        self,
        col: ColumnDefinition,
        metadata: Dict[str, Any]
    ) -> Any:
        """Extract value from metadata."""
        value = metadata.get(col.key)
        
        if value is None:
            # Try alternative keys
            alt_keys = {
                "skills": ["technologies", "tech_stack", "skills"],
                "total_experience_years": ["experience_years", "years_experience"],
                "candidate_name": ["name"],
                "current_role": ["job_title", "position", "role"],
            }
            for alt in alt_keys.get(col.key, []):
                if alt in metadata:
                    value = metadata[alt]
                    break
        
        return value
    
    def _extract_from_content(
        self,
        col: ColumnDefinition,
        content: str
    ) -> Any:
        """Extract value from content using patterns."""
        if not col.extraction_patterns:
            return None
        
        found = set()
        for pattern in col.extraction_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if match:
                    found.add(match.strip())
        
        if found:
            return ", ".join(sorted(found))
        
        return None
    
    def _compute_value(
        self,
        col: ColumnDefinition,
        metadata: Dict[str, Any],
        score: float
    ) -> Any:
        """Compute a derived value."""
        if col.key == "score":
            # Normalize score to percentage
            if score > 1.5:
                return min(100, round(score / 2 * 100))
            elif score > 1.0:
                return min(100, round(score * 50))
            else:
                return min(100, round(score * 100))
        
        return None
    
    def _sort_rows(
        self,
        rows: List[ExtractedRow],
        sort_column: str,
        descending: bool
    ) -> List[ExtractedRow]:
        """Sort rows by a column."""
        def get_sort_key(row: ExtractedRow):
            value = row.values.get(sort_column, row.raw_score)
            if value is None:
                return 0
            if isinstance(value, str):
                try:
                    return float(value.replace("%", "").replace(",", ""))
                except:
                    return 0
            return value
        
        return sorted(rows, key=get_sort_key, reverse=descending)
    
    def _calculate_stats(
        self,
        rows: List[ExtractedRow],
        schema: TableSchema
    ) -> Dict[str, Any]:
        """Calculate extraction statistics."""
        return {
            "total_rows": len(rows),
            "columns_extracted": len(schema.columns),
            "row_entity": schema.row_entity,
            "sort_column": schema.sort_column
        }
