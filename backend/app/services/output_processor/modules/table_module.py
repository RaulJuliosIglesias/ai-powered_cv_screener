"""
Table Module - Visual Structured Output

Extracts candidate comparison tables with match scores.
Returns TableData with TableRow objects containing numeric match_score for coloring.

MATCH SCORE COLORS:
- Green (>=90%): Strong match
- Yellow (70-89%): Partial match  
- Gray (<70%): Weak match
"""

import re
import logging
from typing import Optional, List, Dict
from app.models.structured_output import TableData, TableRow

logger = logging.getLogger(__name__)


class TableModule:
    """
    Extracts and structures candidate comparison tables.
    
    Output: TableData with TableRow objects containing:
    - candidate_name: str
    - cv_id: str
    - columns: Dict[str, str] (column_name -> value)
    - match_score: int (0-100 for coloring)
    """
    
    def extract(self, llm_output: str, chunks: List[dict] = None) -> Optional[TableData]:
        """
        Extract table from LLM output with match scores.
        
        Args:
            llm_output: Raw LLM response
            chunks: CV chunks for fallback generation
            
        Returns:
            TableData with TableRow objects
        """
        if not llm_output:
            return self._generate_fallback_table(chunks) if chunks else None
        
        # Pre-process: extract tables from code blocks
        text = self._extract_tables_from_code_blocks(llm_output)
        
        # Try to parse existing table
        table_data = self._parse_markdown_table(text)
        if table_data and table_data.rows:
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
        Format table - NOT USED for visual output.
        The frontend renders TableData directly as JSON.
        This is kept for backward compatibility.
        """
        if not table_data or not table_data.rows:
            return ""
        
        # For backward compatibility only
        lines = [f"| {' | '.join(table_data.headers)} |"]
        lines.append("|" + "|".join(["---"] * len(table_data.headers)) + "|")
        
        for row in table_data.rows:
            cols = [row.candidate_name] + list(row.columns.values()) + [f"{row.match_score}%"]
            lines.append("| " + " | ".join(cols) + " |")
        
        return "\n".join(lines)
    
    def _parse_markdown_table(self, text: str) -> Optional[TableData]:
        """Parse markdown table and extract TableRow objects with match scores."""
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
                continue
            elif in_table:
                break
        
        if len(table_lines) < 2:
            return None
        
        # Parse header
        header_line = table_lines[0]
        raw_headers = [cell.strip() for cell in header_line.split('|') if cell.strip()]
        
        if not raw_headers:
            return None
        
        # Find separator
        separator_idx = None
        for i, line in enumerate(table_lines[1:3], start=1):
            if re.match(r'^\|?\s*[-:]+\s*\|', line):
                separator_idx = i
                break
        
        if separator_idx is None:
            separator_idx = 1
        
        # Parse rows into TableRow objects
        table_rows: List[TableRow] = []
        
        for line in table_lines[separator_idx + 1:]:
            if not line or '|' not in line:
                continue
            
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if not any(cells):
                continue
            
            # Fix bold formatting
            cells = [self._fix_bold_formatting(cell) for cell in cells]
            
            # Extract candidate info from first cell
            candidate_name, cv_id = self._extract_candidate_info(cells[0] if cells else "")
            
            # Extract match score - search all cells for percentage/score
            match_score = self._extract_match_score(cells[-1] if cells else "", all_cells=cells)
            
            # Build columns dict (excluding first and last columns)
            columns: Dict[str, str] = {}
            for i, header in enumerate(raw_headers[1:-1], start=1):
                if i < len(cells) - 1:
                    columns[header] = cells[i]
                else:
                    columns[header] = ""
            
            # If no middle columns, use all except first as columns
            if not columns and len(cells) > 1:
                for i, header in enumerate(raw_headers[1:], start=1):
                    if i < len(cells):
                        columns[header] = cells[i]
            
            table_rows.append(TableRow(
                candidate_name=candidate_name,
                cv_id=cv_id,
                columns=columns,
                match_score=match_score
            ))
        
        if not table_rows:
            return None
        
        # Deduplicate rows by cv_id (keep first occurrence with highest score)
        table_rows = self._deduplicate_rows(table_rows)
        
        # Headers without Candidate and Match Score columns
        display_headers = ["Candidate"] + raw_headers[1:-1] + ["Match Score"]
        if len(raw_headers) <= 2:
            display_headers = raw_headers + ["Match Score"]
        
        return TableData(
            title="Candidate Comparison Table",
            headers=display_headers,
            rows=table_rows
        )
    
    def _extract_candidate_info(self, cell: str) -> tuple:
        """Extract candidate name and cv_id from cell."""
        # Pattern: **[Name](cv:cv_xxx)** or **Name** cv_xxx or just Name cv_xxx
        
        # Try **[Name](cv:cv_xxx)** format
        match = re.search(r'\*?\*?\[([^\]]+)\]\(cv:?(cv_[a-z0-9_-]+)\)\*?\*?', cell, re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2)
        
        # Try **Name** cv_xxx format
        match = re.search(r'\*\*([^*]+)\*\*\s*(cv_[a-z0-9_-]+)?', cell, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            cv_id = match.group(2) if match.group(2) else ""
            return name, cv_id
        
        # Try Name cv_xxx format
        match = re.search(r'([^*\[\]]+?)\s*(cv_[a-z0-9_-]+)', cell, re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2)
        
        # Just return cleaned cell as name
        clean_name = re.sub(r'\*+|\[|\]|\(.*?\)', '', cell).strip()
        cv_match = re.search(r'(cv_[a-z0-9_-]+)', cell, re.IGNORECASE)
        cv_id = cv_match.group(1) if cv_match else ""
        
        return clean_name or "Unknown", cv_id
    
    def _extract_match_score(self, cell: str, all_cells: List[str] = None) -> int:
        """Extract numeric match score from cell (0-100).
        
        Search strategy:
        1. First try to find explicit percentage in any cell
        2. Then try stars (but scale appropriately)
        3. Look for text indicators
        4. Default based on context
        """
        # Search all cells if provided
        cells_to_search = [cell]
        if all_cells:
            cells_to_search = all_cells
        
        for search_cell in cells_to_search:
            if not search_cell:
                continue
            
            # Try percentage: "95%" or "(95)"
            match = re.search(r'(\d{1,3})\s*%', search_cell)
            if match:
                score = int(match.group(1))
                if 0 <= score <= 100:
                    return score
        
        # Check for stars in the specific cell
        if cell:
            stars = cell.count('⭐')
            if stars > 0:
                # Scale stars: 5 stars = 100%, 1 star = 20%
                # But if context shows "no match", lower the score
                base_score = min(100, stars * 20)
                cell_lower = cell.lower()
                if 'no match' in cell_lower or 'no 2d' in cell_lower or 'not' in cell_lower:
                    return max(15, base_score - 50)  # Reduce significantly for non-matches
                return base_score
            
            # Try text indicators
            cell_lower = cell.lower()
            if 'excellent' in cell_lower or 'strong' in cell_lower or 'perfect' in cell_lower:
                return 95
            if 'good' in cell_lower or 'partial' in cell_lower:
                return 75
            if 'weak' in cell_lower or 'low' in cell_lower or 'no match' in cell_lower:
                return 25
            if 'none' in cell_lower or 'n/a' in cell_lower:
                return 15
        
        return 50  # Default when no indicator found
    
    def _deduplicate_rows(self, rows: List[TableRow]) -> List[TableRow]:
        """
        Deduplicate table rows by candidate NAME with ROBUST prioritization.
        
        PRIORITY ORDER (highest to lowest):
        1. Most recent upload (indexed_at timestamp) - CV actualizado gana
        2. Higher match_score - más relevante para la query
        3. First occurrence - fallback
        
        Args:
            rows: List of TableRow objects (may contain duplicates)
            
        Returns:
            Deduplicated list of TableRow objects
        """
        if not rows:
            return rows
        
        # Primary deduplication by normalized candidate name
        seen_names: Dict[str, TableRow] = {}
        
        for row in rows:
            normalized_name = row.candidate_name.lower().strip()
            
            if normalized_name not in seen_names:
                seen_names[normalized_name] = row
            else:
                existing = seen_names[normalized_name]
                # Priority 1: Most recent upload wins (if timestamps available)
                existing_time = existing.columns.get("_indexed_at", "")
                new_time = row.columns.get("_indexed_at", "")
                
                if new_time and existing_time and new_time > existing_time:
                    logger.info(f"[TABLE] Dedup: keeping NEWER {row.candidate_name} ({row.cv_id}, {new_time}) over ({existing.cv_id}, {existing_time})")
                    seen_names[normalized_name] = row
                # Priority 2: Higher match_score wins (more relevant to query)
                elif row.match_score > existing.match_score:
                    logger.info(f"[TABLE] Dedup: keeping HIGHER SCORE {row.candidate_name} ({row.cv_id}, {row.match_score}%) over ({existing.cv_id}, {existing.match_score}%)")
                    seen_names[normalized_name] = row
        
        result = list(seen_names.values())
        
        # Sort by match_score descending to maintain ranking
        result.sort(key=lambda r: r.match_score, reverse=True)
        
        if len(result) < len(rows):
            logger.info(f"[TABLE] Deduplicated: {len(rows)} -> {len(result)} rows")
        
        return result
    
    def _generate_fallback_table(self, chunks: List[dict]) -> Optional[TableData]:
        """Generate fallback table from chunks using TableRow structure.
        
        ROBUST DEDUPLICATION:
        - Same name = same person (even with different cv_ids)
        - Priority: Most recent upload (indexed_at) > Higher similarity score
        """
        if not chunks:
            return None
        
        logger.info("[TABLE] Generating fallback from chunks")
        
        # Group chunks by candidate name, keeping the BEST one per candidate
        # Best = most recent (indexed_at) or highest score
        candidates_by_name: Dict[str, dict] = {}
        
        for chunk in chunks[:30]:  # Check more chunks for better coverage
            metadata = chunk.get('metadata', {})
            cv_id = metadata.get('cv_id')
            if not cv_id:
                continue
            
            name = metadata.get('candidate_name', 'Unknown')
            name_lower = name.lower().strip()
            content = chunk.get('content', '')
            score = chunk.get('score', 0.5)
            indexed_at = metadata.get('indexed_at', '')
            
            skills = self._extract_skills(content)
            
            candidate_data = {
                'name': name,
                'cv_id': cv_id,
                'skills': skills[:3] if skills else ['N/A'],
                'score': score,
                'indexed_at': indexed_at,
            }
            
            if name_lower not in candidates_by_name:
                candidates_by_name[name_lower] = candidate_data
            else:
                existing = candidates_by_name[name_lower]
                # Priority 1: Most recent indexed_at wins
                if indexed_at and existing['indexed_at'] and indexed_at > existing['indexed_at']:
                    logger.info(f"[TABLE] Fallback dedup: keeping NEWER {name} ({cv_id}) over ({existing['cv_id']})")
                    candidates_by_name[name_lower] = candidate_data
                # Priority 2: Higher similarity score wins
                elif score > existing['score']:
                    logger.info(f"[TABLE] Fallback dedup: keeping HIGHER SCORE {name} ({cv_id}, {score:.2f}) over ({existing['cv_id']}, {existing['score']:.2f})")
                    candidates_by_name[name_lower] = candidate_data
        
        if not candidates_by_name:
            return None
        
        # Limit to top 10 candidates by score
        sorted_candidates = sorted(candidates_by_name.values(), key=lambda x: x['score'], reverse=True)[:10]
        
        # Build TableRow objects
        table_rows: List[TableRow] = []
        
        for info in sorted_candidates:
            # Convert similarity score (0-1) to match percentage (0-100)
            match_score = int(min(100, max(0, info['score'] * 100)))
            
            table_rows.append(TableRow(
                candidate_name=info['name'],
                cv_id=info['cv_id'],
                columns={
                    "Key Skills": ', '.join(info['skills']),
                    "_indexed_at": info.get('indexed_at', ''),  # Hidden field for dedup
                },
                match_score=match_score
            ))
        
        logger.info(f"[TABLE] Generated {len(table_rows)} rows (deduplicated by name)")
        return TableData(
            title="Candidate Comparison Table",
            headers=["Candidate", "Key Skills", "Match Score"],
            rows=table_rows
        )
    
    def _fix_bold_formatting(self, text: str) -> str:
        """
        Fix malformed bold markdown formatting from LLM.
        
        LLM generates multiple formats:
        1. **[Name](cv:id)** - link inside bold (PRESERVE THIS)
        2. ** Name** cv_id - name in bold with spaces, link separate (FIX THIS)
        3. ** Name Role** cv_id - name+role in bold with spaces (FIX THIS)
        
        Args:
            text: Cell text that may have malformed bold
            
        Returns:
            Text with corrected bold formatting
        """
        if not text or '*' not in text:
            return text
        
        original = text
        
        # Case 1: If text contains **[...](...)**  format, preserve it exactly
        # This is the CORRECT format where link is inside bold
        if re.search(r'\*\*\[.+?\]\(.+?\)\*\*', text):
            # Don't touch this format at all
            return text
        
        # Case 2: Fix "** text**" pattern - space AFTER opening **
        # This is the main issue: "** Layla Hassan NFT** cv_xxx"
        # Use a more aggressive pattern that captures any whitespace
        text = re.sub(r'\*\*\s+', '**', text)  # Remove space after **
        text = re.sub(r'\s+\*\*', '**', text)  # Remove space before **
        
        # Case 3: Fix double asterisks with space in between like "* * Name"
        text = re.sub(r'\*\s+\*', '**', text)
        
        # Case 4: Remove bold entirely if malformed (orphan ** without matching pair)
        # Count asterisks - if odd number of **, remove them all
        double_asterisk_count = len(re.findall(r'\*\*', text))
        if double_asterisk_count == 1:
            # Single ** without pair - remove it
            text = text.replace('**', '')
        
        # Case 5: Ensure proper spacing between bold name and cv_id
        # Pattern: **Name** cv_xxx (ensure space before cv_)
        text = re.sub(r'\*\*([^*]+)\*\*(cv_)', r'**\1** \2', text)
        
        if original != text:
            logger.info(f"[TABLE] Fixed bold formatting: '{original[:60]}' -> '{text[:60]}'")
        
        return text
    
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
    
    def _extract_tables_from_code_blocks(self, text: str) -> str:
        """
        Extract tables from inside code blocks.
        
        Handles cases where LLM wraps tables in:
        - ```markdown ... ```
        - ``` ... ```
        - ```code ... ```
        - code Copy code blocks
        
        Args:
            text: Raw text that may contain code blocks
            
        Returns:
            Text with code block wrappers removed, tables exposed
        """
        if not text:
            return text
        
        # Pattern 1: ```language ... ``` blocks containing tables
        # Extract content from code blocks that contain table markers (|)
        code_block_pattern = r'```(?:markdown|code|text|)?\s*\n?([\s\S]*?)\n?```'
        
        def replace_code_block(match):
            content = match.group(1)
            # If the content contains a table (has | characters), extract it
            if '|' in content and '---' in content:
                logger.debug("[TABLE] Extracted table from code block")
                return content
            # Otherwise keep the original (non-table code blocks)
            return match.group(0)
        
        result = re.sub(code_block_pattern, replace_code_block, text, flags=re.IGNORECASE)
        
        # Pattern 2: Clean up "code Copy code" artifacts
        result = re.sub(r'code\s*Copy\s*code\s*', '', result, flags=re.IGNORECASE)
        
        # Pattern 3: Remove standalone "Copy code" text
        result = re.sub(r'\bCopy\s+code\b', '', result, flags=re.IGNORECASE)
        
        return result
