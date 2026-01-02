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
    
    def chunk_cv(
        self,
        text: str,
        cv_id: str,
        filename: str
    ) -> List[Dict[str, Any]]:
        """Chunk CV text into meaningful sections."""
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
                            "section_type": section_type
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
                "section_type": "full_cv"
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
