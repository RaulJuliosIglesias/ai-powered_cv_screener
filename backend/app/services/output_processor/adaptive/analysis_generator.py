"""
ADAPTIVE ANALYSIS GENERATOR - Context-Aware Analysis Generation

Generates analysis text that adapts to:
1. The specific attributes being analyzed
2. The data distribution and patterns
3. The user's intent (list, compare, count, etc.)

Unlike static templates, this generates analysis from DATA.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import Counter

from .query_analyzer import QueryAnalysis, QueryIntent, DataFormat
from .data_extractor import ExtractionResult, ExtractedRow
from .table_generator import DynamicTable

logger = logging.getLogger(__name__)


@dataclass
class AnalysisSection:
    """A section of the analysis."""
    title: str
    content: str
    section_type: str                      # "summary", "distribution", "findings", "gaps"
    priority: int = 1                      # Higher = more important


@dataclass
class AdaptiveAnalysis:
    """Complete adaptive analysis."""
    direct_answer: str                     # Brief answer to the question
    sections: List[AnalysisSection]        # Analysis sections
    conclusion: str                        # Final conclusion
    key_findings: List[str]                # Bullet points
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "direct_answer": self.direct_answer,
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "section_type": s.section_type,
                    "priority": s.priority
                }
                for s in self.sections
            ],
            "conclusion": self.conclusion,
            "key_findings": self.key_findings,
            "metadata": self.metadata
        }
    
    def to_markdown(self) -> str:
        """Convert to markdown format."""
        lines = []
        
        # Direct answer
        if self.direct_answer:
            lines.append(self.direct_answer)
            lines.append("")
        
        # Sections
        for section in sorted(self.sections, key=lambda x: x.priority):
            lines.append(f"**{section.title}**")
            lines.append(section.content)
            lines.append("")
        
        # Key findings
        if self.key_findings:
            lines.append("**Key Findings:**")
            for finding in self.key_findings:
                lines.append(f"- {finding}")
            lines.append("")
        
        # Conclusion
        if self.conclusion:
            lines.append(f"**Conclusion:** {self.conclusion}")
        
        return "\n".join(lines)


class AdaptiveAnalysisGenerator:
    """
    Generates analysis that adapts to the specific query and data.
    
    Key features:
    - Data-driven summaries (not templates)
    - Distribution analysis for categorical data
    - Pattern detection (gaps, clusters, outliers)
    - Intent-aware conclusions
    """
    
    def generate(
        self,
        analysis: QueryAnalysis,
        extraction_result: ExtractionResult,
        table: DynamicTable,
        llm_output: str = ""
    ) -> AdaptiveAnalysis:
        """
        Generate adaptive analysis from extracted data.
        
        Args:
            analysis: Query analysis result
            extraction_result: Extracted data
            table: Generated table
            llm_output: Optional LLM output for additional context
            
        Returns:
            AdaptiveAnalysis with all components
        """
        logger.info(f"[ANALYSIS_GENERATOR] Generating analysis for intent: {analysis.intent.value}")
        
        # Generate direct answer
        direct_answer = self._generate_direct_answer(analysis, extraction_result, table)
        
        # Generate sections based on intent
        sections = []
        
        # Distribution section (if applicable)
        if analysis.intent in [QueryIntent.LIST_ATTRIBUTE, QueryIntent.DISTRIBUTION]:
            dist_section = self._generate_distribution_section(analysis, extraction_result)
            if dist_section:
                sections.append(dist_section)
        
        # Top findings section
        findings_section = self._generate_findings_section(analysis, extraction_result, table)
        if findings_section:
            sections.append(findings_section)
        
        # Coverage section (who has what)
        coverage_section = self._generate_coverage_section(analysis, extraction_result)
        if coverage_section:
            sections.append(coverage_section)
        
        # Generate key findings bullets
        key_findings = self._generate_key_findings(analysis, extraction_result, table)
        
        # Generate conclusion
        conclusion = self._generate_conclusion(analysis, extraction_result, table, key_findings)
        
        return AdaptiveAnalysis(
            direct_answer=direct_answer,
            sections=sections,
            conclusion=conclusion,
            key_findings=key_findings,
            metadata={
                "query_intent": analysis.intent.value,
                "data_format": analysis.suggested_format.value,
                "attributes_analyzed": [a.name for a in analysis.detected_attributes]
            }
        )
    
    def _generate_direct_answer(
        self,
        analysis: QueryAnalysis,
        extraction_result: ExtractionResult,
        table: DynamicTable
    ) -> str:
        """Generate a direct answer to the user's question."""
        rows = extraction_result.rows
        total = len(rows)
        attrs = [a.name for a in analysis.detected_attributes]
        attr_str = ", ".join(attrs) if attrs else "data"
        
        if analysis.intent == QueryIntent.LIST_ATTRIBUTE:
            if total == 0:
                return f"No candidates found with {attr_str} information."
            return f"Found **{total} candidates** with {attr_str} information in the talent pool."
        
        elif analysis.intent == QueryIntent.COUNT_ATTRIBUTE:
            return f"There are **{total}** unique {attr_str} values across all candidates."
        
        elif analysis.intent == QueryIntent.DISTRIBUTION:
            return f"Here's the distribution of {attr_str} across **{total}** entries."
        
        elif analysis.intent == QueryIntent.FIND_BY_ATTRIBUTE:
            if total == 0:
                return "No candidates match the specified criteria."
            return f"Found **{total} candidates** matching your criteria."
        
        # Default
        return f"Analysis of {attr_str} across {total} candidates."
    
    # Cloud computing related skills for filtering
    CLOUD_SKILLS = {
        'aws', 'azure', 'gcp', 'google cloud', 'cloud', 'cloud computing',
        'docker', 'kubernetes', 'k8s', 'terraform', 'ansible', 'jenkins',
        'ci/cd', 'devops', 'serverless', 'lambda', 'ec2', 's3', 'cloudformation',
        'eks', 'ecs', 'fargate', 'cloudwatch', 'iam', 'vpc', 'route53',
        'azure devops', 'azure functions', 'blob storage', 'cosmos db',
        'google cloud platform', 'bigquery', 'cloud run', 'cloud functions',
        'microservices', 'containers', 'orchestration', 'infrastructure'
    }
    
    def _generate_distribution_section(
        self,
        analysis: QueryAnalysis,
        extraction_result: ExtractionResult
    ) -> Optional[AnalysisSection]:
        """Generate distribution analysis section."""
        if extraction_result.schema.row_entity == "attribute":
            # Already in attribute format, use directly
            rows = extraction_result.rows
            if not rows:
                return None
            
            # Top items by frequency
            top_items = rows[:5]
            lines = []
            for row in top_items:
                val = row.values.get("attribute_value", row.identifier)
                count = row.values.get("count", 0)
                freq = row.values.get("frequency", 0)
                lines.append(f"- **{val}**: {count} candidates ({freq}%)")
            
            if len(rows) > 5:
                lines.append(f"- ... and {len(rows) - 5} more")
            
            return AnalysisSection(
                title="Distribution",
                content="\n".join(lines),
                section_type="distribution",
                priority=1
            )
        
        # Candidate-centric: need to aggregate
        attr_name = analysis.detected_attributes[0].name if analysis.detected_attributes else "skills"
        
        # Check if we need to filter by specific skills (e.g., "cloud computing")
        must_have_filter = analysis.filter_conditions.get("must_have", "").lower()
        filter_cloud = "cloud" in must_have_filter or "computing" in must_have_filter
        
        # Count attribute values across all candidates (using sets to avoid duplicates per candidate)
        value_counts: Counter = Counter()
        candidates_with_skill: Dict[str, set] = {}  # skill -> set of candidate ids
        
        for row in extraction_result.rows:
            candidate_id = row.identifier_key or row.identifier
            candidate_skills = set()  # Track unique skills per candidate
            
            for col_key, col_value in row.values.items():
                if col_key in ["skills", "technologies", "languages", attr_name]:
                    if isinstance(col_value, str):
                        for item in col_value.split(","):
                            item = item.strip()
                            if item:
                                # Filter by cloud skills if requested
                                if filter_cloud:
                                    if item.lower() in self.CLOUD_SKILLS or any(cs in item.lower() for cs in self.CLOUD_SKILLS):
                                        candidate_skills.add(item)
                                else:
                                    candidate_skills.add(item)
                    elif isinstance(col_value, list):
                        for item in col_value:
                            if item:
                                item_str = str(item).strip()
                                if filter_cloud:
                                    if item_str.lower() in self.CLOUD_SKILLS or any(cs in item_str.lower() for cs in self.CLOUD_SKILLS):
                                        candidate_skills.add(item_str)
                                else:
                                    candidate_skills.add(item_str)
            
            # Count each skill only once per candidate
            for skill in candidate_skills:
                value_counts[skill] += 1
                if skill not in candidates_with_skill:
                    candidates_with_skill[skill] = set()
                candidates_with_skill[skill].add(candidate_id)
        
        if not value_counts:
            return None
        
        total_candidates = len(extraction_result.rows)
        top_5 = value_counts.most_common(5)
        
        lines = []
        for val, count in top_5:
            # Calculate percentage correctly (candidates with skill / total candidates)
            pct = min(100, round(count / total_candidates * 100, 0))
            lines.append(f"- **{val}**: {count} candidates ({pct:.0f}%)")
        
        if len(value_counts) > 5:
            lines.append(f"- ... and {len(value_counts) - 5} more")
        
        return AnalysisSection(
            title=f"{attr_name.title()} Distribution",
            content="\n".join(lines),
            section_type="distribution",
            priority=1
        )
    
    def _generate_findings_section(
        self,
        analysis: QueryAnalysis,
        extraction_result: ExtractionResult,
        table: DynamicTable
    ) -> Optional[AnalysisSection]:
        """Generate top findings section."""
        rows = extraction_result.rows
        if not rows:
            return None
        
        # Get top 3 candidates
        top_3 = rows[:3]
        attr_name = analysis.detected_attributes[0].name if analysis.detected_attributes else "skills"
        
        lines = []
        for i, row in enumerate(top_3, 1):
            name = row.identifier
            cv_id = row.values.get("cv_id", row.identifier_key)
            
            # Find the primary attribute value
            attr_value = None
            for key in [attr_name, "skills", "technologies", "certifications"]:
                if key in row.values and row.values[key]:
                    attr_value = row.values[key]
                    break
            
            # Format candidate name with CV reference
            candidate_ref = f"**[{name}](cv:{cv_id})**" if cv_id else f"**{name}**"
            
            if attr_value:
                # Truncate if too long
                if isinstance(attr_value, str) and len(attr_value) > 60:
                    attr_value = attr_value[:60] + "..."
                # Keep link and content on same line to preserve markdown parsing
                lines.append(f"{i}. {candidate_ref}: {attr_value}")
            else:
                lines.append(f"{i}. {candidate_ref}")
        
        return AnalysisSection(
            title="Top Candidates",
            content="\n".join(lines),
            section_type="findings",
            priority=2
        )
    
    def _generate_coverage_section(
        self,
        analysis: QueryAnalysis,
        extraction_result: ExtractionResult
    ) -> Optional[AnalysisSection]:
        """Generate coverage analysis (who has what, gaps, etc.)."""
        rows = extraction_result.rows
        if not rows:
            return None
        
        # Calculate coverage statistics
        total = len(rows)
        
        # Count how many have the primary attribute
        attr_name = analysis.detected_attributes[0].name if analysis.detected_attributes else "skills"
        with_attr = 0
        
        for row in rows:
            for key in [attr_name, "skills", "technologies"]:
                if key in row.values and row.values[key]:
                    with_attr += 1
                    break
        
        coverage_pct = round(with_attr / total * 100, 0) if total > 0 else 0
        
        lines = [
            f"- **{with_attr}** of {total} candidates ({coverage_pct:.0f}%) have {attr_name} data",
        ]
        
        if coverage_pct < 100:
            missing = total - with_attr
            lines.append(f"- **{missing}** candidates have no {attr_name} information")
        
        return AnalysisSection(
            title="Coverage",
            content="\n".join(lines),
            section_type="coverage",
            priority=3
        )
    
    def _generate_key_findings(
        self,
        analysis: QueryAnalysis,
        extraction_result: ExtractionResult,
        table: DynamicTable
    ) -> List[str]:
        """Generate key finding bullet points."""
        findings = []
        rows = extraction_result.rows
        
        if not rows:
            return ["No data available for analysis"]
        
        total = len(rows)
        attr_name = analysis.detected_attributes[0].name if analysis.detected_attributes else "skills"
        
        # Finding 1: Total count
        findings.append(f"{total} candidates analyzed for {attr_name}")
        
        # Finding 2: Top candidate with CV reference
        if rows:
            top = rows[0]
            cv_id = top.values.get("cv_id", top.identifier_key)
            if cv_id:
                findings.append(f"Top candidate: **[{top.identifier}](cv:{cv_id})**")
            else:
                findings.append(f"Top candidate: {top.identifier}")
        
        # Finding 3: Most common value (if distribution available)
        if extraction_result.schema.row_entity == "attribute" and rows:
            top_attr = rows[0].identifier
            count = rows[0].values.get("count", 0)
            findings.append(f"Most common: {top_attr} ({count} candidates)")
        
        return findings
    
    def _generate_conclusion(
        self,
        analysis: QueryAnalysis,
        extraction_result: ExtractionResult,
        table: DynamicTable,
        key_findings: List[str]
    ) -> str:
        """Generate a data-driven conclusion."""
        rows = extraction_result.rows
        if not rows:
            return "No data available to draw conclusions."
        
        total = len(rows)
        attr_name = analysis.detected_attributes[0].name if analysis.detected_attributes else "skills"
        
        # Get top candidates with CV references
        top_candidates = []
        for row in rows[:3]:
            name = row.identifier
            cv_id = row.values.get("cv_id", row.identifier_key)
            if cv_id:
                top_candidates.append(f"**[{name}](cv:{cv_id})**")
            else:
                top_candidates.append(f"**{name}**")
        
        top_names_str = ", ".join(top_candidates)
        
        if analysis.intent == QueryIntent.LIST_ATTRIBUTE:
            return (
                f"Based on the {attr_name} analysis, the candidates with the most comprehensive "
                f"profiles are {top_names_str}. The talent pool shows good diversity "
                f"across {total} candidates."
            )
        
        elif analysis.intent == QueryIntent.DISTRIBUTION:
            if extraction_result.schema.row_entity == "attribute":
                top_attr = rows[0].identifier if rows else "N/A"
                return (
                    f"The most common {attr_name} is **{top_attr}**. "
                    f"The distribution shows a diverse range of {attr_name} across the talent pool."
                )
        
        elif analysis.intent == QueryIntent.FIND_BY_ATTRIBUTE:
            return (
                f"Found {total} candidates matching your criteria. "
                f"Top matches are {top_names_str}."
            )
        
        # Default conclusion
        return (
            f"Analysis complete. Top candidates for {attr_name}: {top_names_str}."
        )
