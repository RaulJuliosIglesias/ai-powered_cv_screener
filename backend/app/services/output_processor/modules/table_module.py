"""
Table Module - IMMUTABLE - FINAL FORMAT

Extracts and formats markdown tables.
DO NOT MODIFY without explicit user request.

CRITICAL FORMAT:
- Candidate names: **[Name](cv:cv_xxx)** (NO spaces before **)
- Relevance: ⭐ stars based on score
"""

import re
import logging
from typing import Optional, List
from app.models.structured_output import TableData

logger = logging.getLogger(__name__)


class TableModule:
    """
    Handles table extraction and formatting.
    
    FINAL FORMAT - DO NOT CHANGE:
    | Candidate | Key Skills | Relevance |
    |-----------|------------|-----------|
    | **[Name](cv:cv_xxx)** | Skills | ⭐⭐⭐ |
    """
    
    def extract(self, llm_output: str, chunks: List[dict] = None) -> Optional[TableData]:
        """
        Extract table from LLM output or generate fallback.
        
        Args:
            llm_output: Raw LLM response
            chunks: CV chunks for fallback generation
            
        Returns:
            TableData or None
        """
        if not llm_output:
            return self._generate_fallback_table(chunks) if chunks else None
        
        # Try to parse existing table
        table_data = self._parse_markdown_table(llm_output)
        if table_data:
            logger.info(f"[TABLE] Parsed from LLM: {len(table_data.rows)} rows")
            return table_data
        
        # Fallback: generate from chunks
        if chunks:
            logger.info("[TABLE] No table in LLM output, generating fallback")
            return self._generate_fallback_table(chunks)
        
        logger.debug("[TABLE] No table data available")
        return None
    
    def format(self, table_data: TableData) -> str:
        """
        Format table as markdown.
        
        CRITICAL: Cells are used AS-IS from extract() - no modifications.
        
        Args:
            table_data: TableData object
            
        Returns:
            Markdown table string
        """
        if not table_data or not table_data.headers or not table_data.rows:
            return ""
        
        lines = []
        
        # Header
        lines.append("| " + " | ".join(table_data.headers) + " |")
        
        # Separator
        lines.append("|" + "|".join(["---"] * len(table_data.headers)) + "|")
        
        # Rows - EXACTLY as provided
        for row in table_data.rows:
            lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
        
        return "\n".join(lines)
    
    def _parse_markdown_table(self, text: str) -> Optional[TableData]:
        """Parse markdown table from text."""
        # Find table region
        lines = text.split('\n')
        table_lines = []
        in_table = False
        
        for line in lines:
            stripped = line.strip()
            if '|' in stripped:
                if not in_table:
                    in_table = True
                table_lines.append(line)
            elif in_table and stripped == '':
                continue  # Allow empty lines
            elif in_table:
                break  # End of table
        
        if len(table_lines) < 2:
            return None
        
        # Parse header
        header_line = table_lines[0]
        headers = [cell.strip() for cell in header_line.split('|') if cell.strip()]
        
        if not headers:
            return None
        
        # Find separator
        separator_idx = None
        for i, line in enumerate(table_lines[1:3], start=1):
            if re.match(r'^\|?\s*[-:]+\s*\|', line):
                separator_idx = i
                break
        
        if separator_idx is None:
            separator_idx = 1
        
        # Parse rows
        rows = []
        for line in table_lines[separator_idx + 1:]:
            if not line or '|' not in line:
                continue
            
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if not any(cells):
                continue
            
            # Ensure row matches header length
            while len(cells) < len(headers):
                cells.append("")
            cells = cells[:len(headers)]
            
            rows.append(cells)
        
        if not rows:
            return None
        
        return TableData(headers=headers, rows=rows)
    
    def _generate_fallback_table(self, chunks: List[dict]) -> Optional[TableData]:
        """
        Generate fallback table from chunks.
        
        CRITICAL FORMAT:
        - Names: **[Name](cv:cv_xxx)** (NO spaces)
        - Relevance: ⭐ stars
        """
        if not chunks:
            return None
        
        logger.info("[TABLE] Generating fallback from chunks")
        
        # Extract unique candidates
        candidates = {}
        for chunk in chunks[:10]:
            metadata = chunk.get('metadata', {})
            cv_id = metadata.get('cv_id')
            if not cv_id or cv_id in candidates:
                continue
            
            name = metadata.get('candidate_name', 'Unknown')
            content = chunk.get('content', '')
            skills = self._extract_skills(content)
            
            candidates[cv_id] = {
                'name': name,
                'cv_id': cv_id,
                'skills': skills[:3] if skills else ['N/A'],
                'score': chunk.get('score', 0.0)
            }
        
        if not candidates:
            return None
        
        # Build table with FINAL FORMAT
        headers = ['Candidate', 'Key Skills', 'Relevance']
        rows = []
        
        for cv_id, info in candidates.items():
            # CRITICAL: **[Name](cv:cv_xxx)** - NO spaces before **
            name_cell = f"**[{info['name']}](cv:cv_{cv_id})**"
            
            skills_cell = ', '.join(info['skills'])
            
            # Relevance: stars based on score
            num_stars = min(5, max(1, int(info['score'] * 5)))
            relevance_cell = '⭐' * num_stars
            
            rows.append([name_cell, skills_cell, relevance_cell])
        
        logger.info(f"[TABLE] Generated {len(rows)} rows")
        return TableData(headers=headers, rows=rows)
    
    def _extract_skills(self, content: str) -> List[str]:
        """Extract skills from content."""
        if not content:
            return []
        
        skill_patterns = [
            r'\b(Python|Java|JavaScript|TypeScript|C\+\+|C#|Ruby|Go|Rust|PHP)\b',
            r'\b(React|Angular|Vue|Node\.js|Django|Flask|Spring|Express)\b',
            r'\b(AWS|Azure|GCP|Docker|Kubernetes|Terraform|Jenkins)\b',
            r'\b(SQL|MongoDB|PostgreSQL|MySQL|Redis|Elasticsearch)\b',
            r'\b(Machine Learning|AI|Data Science|Deep Learning)\b',
        ]
        
        skills = []
        for pattern in skill_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            skills.extend(matches)
        
        # Remove duplicates
        seen = set()
        unique = []
        for skill in skills:
            lower = skill.lower()
            if lower not in seen:
                seen.add(lower)
                unique.append(skill)
        
        return unique[:5]
