"""
Robust markdown table parser.

Parses markdown tables and generates fallback tables if parsing fails.
"""

import re
import logging
from typing import Optional, List, Any
from app.models.structured_output import TableData

logger = logging.getLogger(__name__)


class TableParser:
    """Parses markdown tables robustly with fallback generation."""
    
    def parse(self, text: str, chunks: List[dict] = None) -> Optional[TableData]:
        """
        Parse markdown table from text.
        
        Args:
            text: Text containing potential markdown table
            chunks: Fallback data if table parsing fails
            
        Returns:
            TableData or None if no table found and no chunks for fallback
        """
        if not text:
            logger.debug("Empty text, cannot parse table")
            return self._generate_fallback_table(chunks) if chunks else None
        
        # Try to extract table region
        table_text = self._extract_table_region(text)
        if not table_text:
            logger.debug("No table region found")
            return self._generate_fallback_table(chunks) if chunks else None
        
        # Try to parse the table
        try:
            table_data = self._parse_markdown_table(table_text)
            if table_data and table_data.headers and table_data.rows:
                logger.info(f"Successfully parsed table: {len(table_data.rows)} rows")
                return table_data
        except Exception as e:
            logger.warning(f"Table parsing failed: {e}")
        
        # Fallback if parsing failed
        return self._generate_fallback_table(chunks) if chunks else None
    
    def _extract_table_region(self, text: str) -> Optional[str]:
        """
        Find the markdown table region in text.
        
        Returns:
            Table text or None
        """
        # Look for markdown table pattern (lines with |)
        lines = text.split('\n')
        table_lines = []
        in_table = False
        
        for line in lines:
            stripped = line.strip()
            
            # Start of table (has pipes and looks like header or separator)
            if '|' in stripped and not in_table:
                in_table = True
                table_lines.append(line)
            elif in_table:
                # Continue if line has pipes
                if '|' in stripped:
                    table_lines.append(line)
                # Stop if we hit a line without pipes
                elif stripped == '':
                    continue  # Allow empty lines within table
                else:
                    break  # End of table
        
        if len(table_lines) >= 2:  # Minimum: header + separator
            return '\n'.join(table_lines)
        
        return None
    
    def _parse_markdown_table(self, table_text: str) -> Optional[TableData]:
        """
        Parse markdown table structure.
        
        Args:
            table_text: Text containing markdown table
            
        Returns:
            TableData or None if parsing fails
        """
        lines = [line.strip() for line in table_text.split('\n') if line.strip()]
        
        if len(lines) < 2:
            return None
        
        # Parse header
        header_line = lines[0]
        headers = [cell.strip() for cell in header_line.split('|') if cell.strip()]
        
        if not headers:
            return None
        
        # Find separator line (with dashes)
        separator_idx = None
        for i, line in enumerate(lines[1:3], start=1):  # Check first 2 lines after header
            if re.match(r'^\|?\s*[-:]+\s*\|', line):
                separator_idx = i
                break
        
        if separator_idx is None:
            logger.warning("No separator line found, treating line 1 as separator")
            separator_idx = 1
        
        # Parse data rows
        rows = []
        for line in lines[separator_idx + 1:]:
            if not line or not '|' in line:
                continue
            
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            
            # Skip empty rows
            if not any(cells):
                continue
            
            # Pad row if it has fewer cells than headers
            while len(cells) < len(headers):
                cells.append("")
            
            # Truncate row if it has more cells than headers
            cells = cells[:len(headers)]
            
            rows.append(cells)
        
        if not rows:
            logger.warning("No data rows found in table")
            return None
        
        return TableData(headers=headers, rows=rows)
    
    def _generate_fallback_table(self, chunks: List[dict]) -> Optional[TableData]:
        """
        Generate a basic table from chunks if LLM didn't provide one.
        
        Args:
            chunks: Retrieved CV chunks
            
        Returns:
            TableData with basic candidate info
        """
        if not chunks:
            return None
        
        logger.info("Generating fallback table from chunks")
        
        # Extract unique candidates
        candidates = {}
        for chunk in chunks[:10]:  # Limit to top 10
            metadata = chunk.get('metadata', {})
            cv_id = metadata.get('cv_id')
            if not cv_id or cv_id in candidates:
                continue
            
            name = metadata.get('candidate_name', 'Unknown')
            # Extract some skills from content
            content = chunk.get('content', '')
            skills = self._extract_skills_from_content(content)
            
            candidates[cv_id] = {
                'name': name,
                'cv_id': cv_id,
                'skills': skills[:3] if skills else ['N/A'],  # Top 3 skills
                'score': chunk.get('score', 0.0)
            }
        
        if not candidates:
            return None
        
        # Build table
        headers = ['Candidate', 'Key Skills', 'Relevance']
        rows = []
        
        for cv_id, info in candidates.items():
            name_link = f"**[{info['name']}](cv:cv_{cv_id})**"
            skills_str = ', '.join(info['skills'])
            score_stars = '⭐' * min(5, max(1, int(info['score'] * 5)))
            
            rows.append([name_link, skills_str, score_stars])
        
        logger.info(f"Generated fallback table with {len(rows)} candidates")
        return TableData(headers=headers, rows=rows)
    
    def _extract_skills_from_content(self, content: str) -> List[str]:
        """
        Extract potential skills from content text.
        
        Returns:
            List of skill keywords found
        """
        if not content:
            return []
        
        # Common skill keywords to look for
        skill_patterns = [
            r'\b(Python|Java|JavaScript|TypeScript|C\+\+|C#|Ruby|Go|Rust|PHP)\b',
            r'\b(React|Angular|Vue|Node\.js|Django|Flask|Spring|Express)\b',
            r'\b(AWS|Azure|GCP|Docker|Kubernetes|Terraform|Jenkins)\b',
            r'\b(SQL|MongoDB|PostgreSQL|MySQL|Redis|Elasticsearch)\b',
            r'\b(Machine Learning|AI|Data Science|Deep Learning)\b',
            r'\b(Agile|Scrum|Leadership|Management|Strategy)\b',
        ]
        
        skills = []
        for pattern in skill_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            skills.extend(matches)
        
        # Remove duplicates, keep order
        seen = set()
        unique_skills = []
        for skill in skills:
            skill_lower = skill.lower()
            if skill_lower not in seen:
                seen.add(skill_lower)
                unique_skills.append(skill)
        
        return unique_skills[:5]  # Max 5 skills
