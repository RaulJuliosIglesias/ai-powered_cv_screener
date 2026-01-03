import re
from typing import List, Dict, Any


class ChunkingService:
    """Service for chunking CV text into meaningful sections."""
    
    # Common CV section headers
    SECTION_PATTERNS = [
        (r"(?i)(professional\s+)?summary", "summary"),
        (r"(?i)(work\s+)?experience", "experience"),
        (r"(?i)education", "education"),
        (r"(?i)skills", "skills"),
        (r"(?i)certifications?", "certifications"),
        (r"(?i)languages?", "languages"),
        (r"(?i)projects?", "projects"),
        (r"(?i)contact(\s+info(rmation)?)?", "contact"),
    ]
    
    def _parse_filename(self, filename: str) -> Dict[str, str]:
        """Parse filename to extract candidate info.
        
        Expected format: ID_FirstName_LastName_Role.pdf
        Example: 1ef4e451_Dirk_van_der_Meer_Therapist.pdf
        """
        # Remove .pdf extension
        name = filename.replace('.pdf', '').replace('.PDF', '')
        
        # Split by underscore
        parts = name.split('_')
        
        if len(parts) >= 3:
            # First part is ID
            file_id = parts[0]
            # Last part is role
            role = parts[-1].replace('-', ' ').replace('_', ' ')
            # Middle parts are the name
            name_parts = parts[1:-1]
            candidate_name = ' '.join(name_parts)
            
            return {
                "file_id": file_id,
                "candidate_name": candidate_name,
                "role": role
            }
        elif len(parts) == 2:
            return {
                "file_id": parts[0],
                "candidate_name": parts[1],
                "role": ""
            }
        else:
            return {
                "file_id": "",
                "candidate_name": name,
                "role": ""
            }
    
    def chunk_cv(
        self,
        text: str,
        cv_id: str,
        filename: str
    ) -> List[Dict[str, Any]]:
        """Chunk CV text into meaningful sections."""
        # Parse filename to extract candidate info
        parsed = self._parse_filename(filename)
        candidate_name = parsed["candidate_name"]
        role = parsed["role"]
        
        # Try section-based chunking first
        sections = self._extract_sections(text)
        
        if sections:
            chunks = []
            for i, (section_type, content) in enumerate(sections):
                if content.strip():
                    chunks.append({
                        "id": f"{cv_id}_chunk_{i}",
                        "cv_id": cv_id,
                        "filename": filename,
                        "chunk_index": i,
                        "content": content.strip(),
                        "metadata": {
                            "section_type": section_type,
                            "candidate_name": candidate_name,
                            "role": role
                        }
                    })
            return chunks
        
        # Fallback: chunk the entire CV as one piece
        # (CVs are usually small enough)
        return [{
            "id": f"{cv_id}_chunk_0",
            "cv_id": cv_id,
            "filename": filename,
            "chunk_index": 0,
            "content": text.strip(),
            "metadata": {
                "section_type": "full_cv",
                "candidate_name": candidate_name,
                "role": role
            }
        }]
    
    def _extract_sections(self, text: str) -> List[tuple]:
        """Extract sections from CV text."""
        # Find all section headers and their positions
        section_positions = []
        
        for pattern, section_type in self.SECTION_PATTERNS:
            for match in re.finditer(pattern, text):
                section_positions.append((match.start(), section_type, match.group()))
        
        if not section_positions:
            return []
        
        # Sort by position
        section_positions.sort(key=lambda x: x[0])
        
        # Extract content between sections
        sections = []
        
        # Add header/contact info (content before first section)
        first_pos = section_positions[0][0]
        if first_pos > 50:  # Has substantial content before first section
            sections.append(("header", text[:first_pos]))
        
        # Extract each section's content
        for i, (pos, section_type, header) in enumerate(section_positions):
            # Find end of this section (start of next, or end of text)
            if i + 1 < len(section_positions):
                end_pos = section_positions[i + 1][0]
            else:
                end_pos = len(text)
            
            content = text[pos:end_pos]
            sections.append((section_type, content))
        
        return sections
