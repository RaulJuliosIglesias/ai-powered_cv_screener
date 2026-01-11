"""
ADAPTIVE STRUCTURE

Dynamic structure for queries that don't fit predefined structures.
Builds tables and analysis dynamically based on the query content.

Use cases:
- "What technologies do the candidates have?" → Table: Candidate | Technologies
- "What languages do they speak?" → Table: Candidate | Languages
- "Show me experience levels" → Table: Candidate | Years | Seniority
- Any attribute-based query about ALL candidates

Components:
- DirectAnswer: Brief summary answering the query
- DynamicTable: Table built from query + chunks (columns based on what was asked)
- Analysis: Insights derived from the data
- Conclusion: Summary with recommendations
"""

import logging
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from ..modules import ThinkingModule, DirectAnswerModule, ConclusionModule

logger = logging.getLogger(__name__)


@dataclass
class DynamicTableRow:
    """Row in dynamic table."""
    candidate_name: str
    cv_id: str
    values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DynamicTableData:
    """Dynamic table data."""
    columns: List[str]
    rows: List[DynamicTableRow]
    query_attribute: str
    
    def to_dict(self) -> Dict:
        return {
            "columns": self.columns,
            "rows": [
                {
                    "candidate_name": r.candidate_name,
                    "cv_id": r.cv_id,
                    "values": r.values
                }
                for r in self.rows
            ],
            "query_attribute": self.query_attribute
        }


class AdaptiveStructure:
    """
    Adaptive structure that builds dynamic tables based on query content.
    
    When user asks "What technologies do candidates have?", this structure:
    1. Detects the attribute being asked (technologies/skills)
    2. Extracts that attribute from ALL candidates in chunks
    3. Builds a table with Candidate | [Attribute]
    4. Generates analysis and conclusion
    """
    
    # Attribute detection patterns
    ATTRIBUTE_PATTERNS = {
        "technologies": {
            "patterns": [r"technolog", r"tech\s+stack", r"programming", r"frameworks?"],
            "metadata_keys": ["skills", "technologies"],
            "display_name": "Technologies"
        },
        "skills": {
            "patterns": [r"\bskills?\b", r"competenc", r"abilit"],
            "metadata_keys": ["skills"],
            "display_name": "Skills"
        },
        "languages": {
            "patterns": [r"\blanguages?\b", r"idiomas?", r"speaks?"],
            "metadata_keys": ["languages", "spoken_languages"],
            "display_name": "Languages"
        },
        "experience": {
            "patterns": [r"experience", r"experiencia", r"years?\s+(of\s+)?work"],
            "metadata_keys": ["total_experience_years", "experience"],
            "display_name": "Experience (Years)"
        },
        "education": {
            "patterns": [r"education", r"degree", r"universit", r"estudios"],
            "metadata_keys": ["education", "degree"],
            "display_name": "Education"
        },
        "certifications": {
            "patterns": [r"certific", r"credential"],
            "metadata_keys": ["certifications"],
            "display_name": "Certifications"
        },
        "location": {
            "patterns": [r"location", r"ubicaci", r"where.*from", r"based\s+in"],
            "metadata_keys": ["location"],
            "display_name": "Location"
        },
        "current_role": {
            "patterns": [r"current\s+(role|position|job)", r"puesto\s+actual", r"working\s+as"],
            "metadata_keys": ["current_role", "job_title"],
            "display_name": "Current Role"
        },
        "seniority": {
            "patterns": [r"seniority", r"level", r"junior|senior|mid"],
            "metadata_keys": ["seniority_level"],
            "display_name": "Seniority Level"
        }
    }
    
    def __init__(self):
        self.thinking_module = ThinkingModule()
        self.direct_answer_module = DirectAnswerModule()
        self.conclusion_module = ConclusionModule()
    
    def assemble(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        query: str = "",
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Assemble adaptive structure with dynamic table.
        
        Args:
            llm_output: Raw LLM response
            chunks: CV chunks with metadata
            query: Original query
            
        Returns:
            Dict with structure_type="adaptive" and dynamic components
        """
        logger.info(f"[ADAPTIVE_STRUCTURE] Building adaptive response for: {query[:60]}...")
        
        # 1. Detect what attribute(s) the user is asking about
        detected_attributes = self._detect_attributes(query)
        logger.info(f"[ADAPTIVE_STRUCTURE] Detected attributes: {detected_attributes}")
        
        # 2. Extract thinking from LLM output
        thinking = self.thinking_module.extract(llm_output)
        
        # 3. Build dynamic table from chunks
        dynamic_table = self._build_dynamic_table(chunks, detected_attributes, query)
        
        # 4. Generate direct answer (summary of findings)
        direct_answer = self._generate_direct_answer(
            llm_output, 
            dynamic_table, 
            detected_attributes,
            query
        )
        
        # 5. Generate analysis from table data
        analysis = self._generate_analysis(dynamic_table, detected_attributes, query)
        
        # 6. Extract or generate conclusion
        conclusion = self.conclusion_module.extract(llm_output)
        if not conclusion:
            conclusion = self._generate_conclusion(dynamic_table, detected_attributes)
        
        return {
            "structure_type": "adaptive",
            "query": query,
            "detected_attributes": detected_attributes,
            "thinking": thinking,
            "direct_answer": direct_answer,
            "dynamic_table": dynamic_table.to_dict() if dynamic_table else None,
            "analysis": analysis,
            "conclusion": conclusion,
            "total_candidates": len(dynamic_table.rows) if dynamic_table else 0,
            "raw_content": llm_output
        }
    
    def _detect_attributes(self, query: str) -> List[str]:
        """Detect which attributes the user is asking about."""
        q_lower = query.lower()
        detected = []
        
        for attr_name, config in self.ATTRIBUTE_PATTERNS.items():
            for pattern in config["patterns"]:
                if re.search(pattern, q_lower):
                    detected.append(attr_name)
                    break
        
        # Default to skills if nothing detected
        if not detected:
            detected = ["skills"]
        
        return detected
    
    def _build_dynamic_table(
        self, 
        chunks: List[Dict[str, Any]], 
        attributes: List[str],
        query: str
    ) -> Optional[DynamicTableData]:
        """Build dynamic table from chunks based on detected attributes."""
        if not chunks:
            return None
        
        # Group chunks by candidate
        candidates: Dict[str, Dict[str, Any]] = {}
        
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            cv_id = chunk.get("cv_id") or meta.get("cv_id", "")
            name = chunk.get("candidate_name") or meta.get("candidate_name", "Unknown")
            
            if cv_id not in candidates:
                candidates[cv_id] = {
                    "name": name,
                    "cv_id": cv_id,
                    "values": {},
                    "score": chunk.get("score", 0)
                }
            
            # Extract values for each attribute
            for attr in attributes:
                config = self.ATTRIBUTE_PATTERNS.get(attr, {})
                metadata_keys = config.get("metadata_keys", [attr])
                
                for key in metadata_keys:
                    value = meta.get(key)
                    if value:
                        # Merge values (for skills, combine lists)
                        existing = candidates[cv_id]["values"].get(attr, "")
                        if isinstance(value, list):
                            value = ", ".join(str(v) for v in value)
                        elif isinstance(value, (int, float)):
                            value = str(value)
                        
                        if existing and value not in existing:
                            candidates[cv_id]["values"][attr] = f"{existing}, {value}"
                        elif not existing:
                            candidates[cv_id]["values"][attr] = value
            
            # Also try to extract from chunk content if metadata is missing
            content = chunk.get("content", "")
            for attr in attributes:
                if attr not in candidates[cv_id]["values"] or not candidates[cv_id]["values"][attr]:
                    extracted = self._extract_from_content(content, attr)
                    if extracted:
                        candidates[cv_id]["values"][attr] = extracted
        
        # Build table rows
        rows = []
        sorted_candidates = sorted(candidates.values(), key=lambda x: x["score"], reverse=True)
        
        for cand in sorted_candidates:
            if any(cand["values"].get(attr) for attr in attributes):
                rows.append(DynamicTableRow(
                    candidate_name=cand["name"],
                    cv_id=cand["cv_id"],
                    values=cand["values"]
                ))
        
        # Build column names
        columns = ["Candidate"]
        for attr in attributes:
            display_name = self.ATTRIBUTE_PATTERNS.get(attr, {}).get("display_name", attr.title())
            columns.append(display_name)
        
        logger.info(f"[ADAPTIVE_STRUCTURE] Built table with {len(rows)} rows, columns: {columns}")
        
        return DynamicTableData(
            columns=columns,
            rows=rows,
            query_attribute=", ".join(attributes)
        )
    
    def _extract_from_content(self, content: str, attribute: str) -> str:
        """Try to extract attribute value from chunk content."""
        # Simple extraction patterns for common attributes
        if attribute in ["technologies", "skills"]:
            # Look for skill-like words (capitalized tech terms)
            tech_patterns = [
                r'\b(Python|Java|JavaScript|TypeScript|React|Angular|Vue|Node\.?js|AWS|Azure|Docker|Kubernetes|SQL|MongoDB|PostgreSQL|Redis|GraphQL|REST|API|Git|CI/CD|Agile|Scrum)\b'
            ]
            found = set()
            for pattern in tech_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                found.update(matches)
            if found:
                return ", ".join(sorted(found))
        
        return ""
    
    def _generate_direct_answer(
        self, 
        llm_output: str, 
        table: Optional[DynamicTableData],
        attributes: List[str],
        query: str
    ) -> str:
        """Generate direct answer summarizing the table data."""
        # First try to extract from LLM output
        extracted = self.direct_answer_module.extract(llm_output)
        if extracted and len(extracted) > 50:
            return extracted
        
        # Generate from table data
        if not table or not table.rows:
            return f"No data found for the requested attributes: {', '.join(attributes)}"
        
        attr_display = ", ".join(
            self.ATTRIBUTE_PATTERNS.get(a, {}).get("display_name", a.title()) 
            for a in attributes
        )
        
        # Count unique values
        all_values = set()
        for row in table.rows:
            for attr in attributes:
                vals = row.values.get(attr, "")
                if vals:
                    for v in vals.split(", "):
                        all_values.add(v.strip())
        
        return (
            f"Found {len(table.rows)} candidates with {attr_display} information. "
            f"Across all candidates, there are {len(all_values)} unique {attr_display.lower()} "
            f"represented in the talent pool."
        )
    
    def _generate_analysis(
        self, 
        table: Optional[DynamicTableData],
        attributes: List[str],
        query: str
    ) -> str:
        """Generate analysis from table data."""
        if not table or not table.rows:
            return ""
        
        analysis_parts = []
        
        for attr in attributes:
            display_name = self.ATTRIBUTE_PATTERNS.get(attr, {}).get("display_name", attr.title())
            
            # Count frequency of values
            value_counts: Dict[str, int] = {}
            for row in table.rows:
                vals = row.values.get(attr, "")
                if vals:
                    for v in vals.split(", "):
                        v = v.strip()
                        if v:
                            value_counts[v] = value_counts.get(v, 0) + 1
            
            if value_counts:
                # Sort by frequency
                sorted_values = sorted(value_counts.items(), key=lambda x: -x[1])
                top_5 = sorted_values[:5]
                
                analysis_parts.append(f"**{display_name} Distribution:**")
                for val, count in top_5:
                    pct = (count / len(table.rows)) * 100
                    analysis_parts.append(f"- {val}: {count} candidates ({pct:.0f}%)")
                
                if len(sorted_values) > 5:
                    analysis_parts.append(f"- ... and {len(sorted_values) - 5} more")
                
                analysis_parts.append("")
        
        return "\n".join(analysis_parts)
    
    def _generate_conclusion(
        self, 
        table: Optional[DynamicTableData],
        attributes: List[str]
    ) -> str:
        """Generate conclusion from table data."""
        if not table or not table.rows:
            return "No candidates found matching the query criteria."
        
        attr_display = ", ".join(
            self.ATTRIBUTE_PATTERNS.get(a, {}).get("display_name", a.title()) 
            for a in attributes
        )
        
        # Find candidates with most values
        candidates_by_richness = []
        for row in table.rows:
            total_values = 0
            for attr in attributes:
                vals = row.values.get(attr, "")
                if vals:
                    total_values += len(vals.split(", "))
            candidates_by_richness.append((row.candidate_name, total_values))
        
        candidates_by_richness.sort(key=lambda x: -x[1])
        top_3 = candidates_by_richness[:3]
        
        if top_3:
            top_names = ", ".join(c[0] for c in top_3)
            return (
                f"Based on the {attr_display.lower()} analysis, the candidates with the most "
                f"comprehensive profiles are: **{top_names}**. "
                f"The talent pool shows good diversity across {len(table.rows)} candidates."
            )
        
        return f"Found {len(table.rows)} candidates with {attr_display.lower()} data."
