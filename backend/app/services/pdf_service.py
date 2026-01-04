import pdfplumber
import re
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field

from app.utils.exceptions import PDFExtractionError


@dataclass
class CVChunk:
    """Represents a chunk of CV content with metadata."""
    content: str
    section_type: str
    chunk_index: int
    cv_id: str
    filename: str
    candidate_name: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ExtractedCV:
    """Represents a fully extracted CV."""
    cv_id: str
    filename: str
    raw_text: str
    candidate_name: Optional[str]
    chunks: list[CVChunk]
    metadata: dict


class PDFService:
    """Service for extracting and processing PDF CVs."""
    
    SECTION_PATTERNS = {
        "contact_info": r"(?i)(contact|email|phone|address|linkedin|github)",
        "summary": r"(?i)(summary|objective|profile|about\s*me|professional\s*summary)",
        "experience": r"(?i)(experience|work\s*history|employment|professional\s*experience)",
        "education": r"(?i)(education|academic|degree|university|college|school)",
        "skills": r"(?i)(skills|technical\s*skills|competencies|technologies|expertise)",
        "certifications": r"(?i)(certification|certificate|accreditation|license)",
        "languages": r"(?i)(language|idioma|spoken\s*language)",
        "projects": r"(?i)(project|portfolio|work\s*sample)",
    }
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.default_chunk_size = chunk_size
        self.default_chunk_overlap = chunk_overlap
    
    def extract_text_from_pdf(self, pdf_path: str | Path) -> str:
        """Extract all text from a PDF file."""
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise PDFExtractionError(f"PDF file not found: {pdf_path}")
            
            text_parts = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            raw_text = "\n".join(text_parts)
            return self._clean_text(raw_text)
            
        except Exception as e:
            if isinstance(e, PDFExtractionError):
                raise
            raise PDFExtractionError(
                f"Failed to extract text from PDF: {str(e)}",
                details={"pdf_path": str(pdf_path)}
            )
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text by removing artifacts and normalizing whitespace."""
        # Remove multiple spaces
        text = re.sub(r" +", " ", text)
        # Remove multiple newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Fix common encoding issues
        text = text.replace("\x00", "")
        # Strip leading/trailing whitespace from lines
        lines = [line.strip() for line in text.split("\n")]
        return "\n".join(lines)
    
    def extract_candidate_name(self, text: str) -> Optional[str]:
        """Extract candidate name from CV text (usually first line or after name pattern)."""
        lines = text.strip().split("\n")
        
        # Try first non-empty line (most CVs start with name)
        for line in lines[:5]:
            line = line.strip()
            if line and len(line) < 60 and not re.search(r"@|http|www\.|resume|cv|curriculum", line, re.I):
                # Check if it looks like a name (2-4 words, mostly letters)
                words = line.split()
                if 1 <= len(words) <= 5 and all(re.match(r"^[A-Za-zÀ-ÿ\-'\.]+$", w) for w in words):
                    return line
        
        # Try pattern matching
        name_patterns = [
            r"(?i)name[:\s]+([A-Za-zÀ-ÿ\s\-'\.]+)",
            r"(?i)^([A-Za-zÀ-ÿ]+\s+[A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+)?)\s*$",
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text[:500], re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_skills(self, text: str) -> list[str]:
        """Extract skills from CV text."""
        skills = []
        
        # Common tech skills to look for
        common_skills = [
            "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
            "React", "Angular", "Vue", "Node.js", "Django", "FastAPI", "Flask",
            "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
            "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform",
            "Git", "Linux", "REST", "GraphQL", "CI/CD",
            "TensorFlow", "PyTorch", "Keras", "scikit-learn", "Pandas", "NumPy",
            "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
            "Agile", "Scrum", "JIRA", "Confluence",
        ]
        
        text_lower = text.lower()
        for skill in common_skills:
            if skill.lower() in text_lower:
                skills.append(skill)
        
        return skills
    
    def _identify_section(self, text: str) -> str:
        """Identify which section type a text block belongs to."""
        for section_type, pattern in self.SECTION_PATTERNS.items():
            if re.search(pattern, text[:100]):
                return section_type
        return "general"
    
    def _split_into_sections(self, text: str) -> list[tuple[str, str]]:
        """Split CV text into sections based on headers."""
        sections = []
        current_section = "header"
        current_content = []
        
        lines = text.split("\n")
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if this line is a section header
            section_found = None
            for section_type, pattern in self.SECTION_PATTERNS.items():
                if re.match(pattern, line_stripped) and len(line_stripped) < 50:
                    section_found = section_type
                    break
            
            if section_found:
                # Save current section if it has content
                if current_content:
                    content = "\n".join(current_content).strip()
                    if content:
                        sections.append((current_section, content))
                
                current_section = section_found
                current_content = [line_stripped]
            else:
                current_content.append(line)
        
        # Add last section
        if current_content:
            content = "\n".join(current_content).strip()
            if content:
                sections.append((current_section, content))
        
        return sections
    
    def _chunk_text(self, text: str, section_type: str, chunk_size: int, chunk_overlap: int) -> list[str]:
        """Split text into chunks using recursive character splitting with dynamic sizing."""
        if len(text) <= chunk_size:
            return [text] if text.strip() else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            if end < len(text):
                break_point = text.rfind("\n\n", start, end)
                if break_point == -1 or break_point <= start:
                    break_point = text.rfind(". ", start, end)
                if break_point == -1 or break_point <= start:
                    break_point = text.rfind(" ", start, end)
                if break_point > start:
                    end = break_point + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - chunk_overlap if end < len(text) else end
        
        return chunks
    
    def process_cv(self, pdf_path: str | Path, cv_id: str) -> ExtractedCV:
        """Extract and chunk a CV from a PDF file with ADAPTIVE chunking."""
        pdf_path = Path(pdf_path)
        filename = pdf_path.name
        
        # Extract text
        raw_text = self.extract_text_from_pdf(pdf_path)
        
        if not raw_text.strip():
            raise PDFExtractionError(
                "No text could be extracted from PDF",
                details={"filename": filename}
            )
        
        total_length = len(raw_text)
        
        target_chunks = 18
        optimal_chunk_size = max(300, min(800, total_length // target_chunks))
        optimal_overlap = max(30, int(optimal_chunk_size * 0.1))
        
        logger.info(f"Adaptive chunking for {filename}: {total_length} chars → "
                    f"{optimal_chunk_size} chunk size, {optimal_overlap} overlap")
        
        # Extract metadata
        candidate_name = self.extract_candidate_name(raw_text)
        skills = self.extract_skills(raw_text)
        
        # Split into sections and chunk
        sections = self._split_into_sections(raw_text)
        
        chunks = []
        chunk_index = 0
        
        for section_type, section_content in sections:
            section_chunks = self._chunk_text(
                section_content, 
                section_type,
                chunk_size=optimal_chunk_size,
                chunk_overlap=optimal_overlap
            )
            
            for chunk_content in section_chunks:
                chunk = CVChunk(
                    content=chunk_content,
                    section_type=section_type,
                    chunk_index=chunk_index,
                    cv_id=cv_id,
                    filename=filename,
                    candidate_name=candidate_name,
                    metadata={
                        "skills": skills,
                        "section": section_type,
                    }
                )
                chunks.append(chunk)
                chunk_index += 1
        
        return ExtractedCV(
            cv_id=cv_id,
            filename=filename,
            raw_text=raw_text,
            candidate_name=candidate_name,
            chunks=chunks,
            metadata={
                "skills": skills,
                "chunk_count": len(chunks),
                "sections": list(set(s[0] for s in sections)),
            }
        )
