import pdfplumber
import re
import logging
from typing import Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

from app.utils.exceptions import PDFExtractionError

logger = logging.getLogger(__name__)


@dataclass
class ExperienceEntry:
    """Represents a single work experience entry."""
    job_title: str
    company: str
    start_year: Optional[int] = None
    end_year: Optional[int] = None  # None means "Present"
    duration_years: float = 0.0
    is_current: bool = False
    description: str = ""
    
    def to_dict(self) -> dict:
        return {
            "job_title": self.job_title,
            "company": self.company,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "duration_years": self.duration_years,
            "is_current": self.is_current,
            "description": self.description
        }


@dataclass
class EnrichedMetadata:
    """Rich metadata extracted from CV for improved indexing and retrieval."""
    # Basic info
    skills: List[str] = field(default_factory=list)
    
    # Experience analysis
    total_experience_years: float = 0.0
    experiences: List[ExperienceEntry] = field(default_factory=list)
    current_role: Optional[str] = None
    current_company: Optional[str] = None
    
    # Seniority detection
    seniority_level: str = "unknown"  # junior, mid, senior, lead, executive
    
    # Companies
    companies_worked: List[str] = field(default_factory=list)
    has_faang_experience: bool = False
    
    # Red flags detection
    employment_gaps: List[Tuple[int, int]] = field(default_factory=list)  # (start_year, end_year)
    job_hopping_score: float = 0.0  # 0-1, higher = more job changes
    avg_tenure_years: float = 0.0
    
    # Education
    highest_education: Optional[str] = None
    education_institutions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "skills": self.skills,
            "total_experience_years": self.total_experience_years,
            "experiences": [e.to_dict() for e in self.experiences],
            "current_role": self.current_role,
            "current_company": self.current_company,
            "seniority_level": self.seniority_level,
            "companies_worked": self.companies_worked,
            "has_faang_experience": self.has_faang_experience,
            "employment_gaps": self.employment_gaps,
            "job_hopping_score": self.job_hopping_score,
            "avg_tenure_years": self.avg_tenure_years,
            "highest_education": self.highest_education,
            "education_institutions": self.education_institutions
        }


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
    is_summary_chunk: bool = False  # Special flag for summary chunks


@dataclass
class ExtractedCV:
    """Represents a fully extracted CV."""
    cv_id: str
    filename: str
    raw_text: str
    candidate_name: Optional[str]
    chunks: List[CVChunk]
    metadata: dict
    enriched_metadata: Optional[EnrichedMetadata] = None


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
    
    def extract_skills(self, text: str) -> List[str]:
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
    
    # =========================================================================
    # ENRICHED METADATA EXTRACTION
    # =========================================================================
    
    FAANG_COMPANIES = {
        "google", "alphabet", "meta", "facebook", "amazon", "apple", "netflix",
        "microsoft", "openai", "deepmind", "nvidia", "tesla", "uber", "airbnb",
        "spotify", "stripe", "salesforce", "oracle", "ibm", "intel", "adobe"
    }
    
    SENIORITY_PATTERNS = {
        "executive": r"(?i)\b(cto|ceo|cfo|coo|vp|vice president|director|head of|chief)\b",
        "lead": r"(?i)\b(lead|principal|staff|architect|manager|team lead)\b",
        "senior": r"(?i)\b(senior|sr\.?|ssr)\b",
        "mid": r"(?i)\b(mid[- ]?level|intermediate|regular)\b",
        "junior": r"(?i)\b(junior|jr\.?|entry[- ]?level|trainee|intern|graduate)\b",
    }
    
    EDUCATION_LEVELS = {
        "phd": r"(?i)\b(ph\.?d|doctor|doctorate)\b",
        "masters": r"(?i)\b(master|m\.?s\.?|m\.?a\.?|mba|m\.?sc)\b",
        "bachelors": r"(?i)\b(bachelor|b\.?s\.?|b\.?a\.?|b\.?sc|degree|licenciatura|grado)\b",
        "associate": r"(?i)\b(associate|diploma|certificate)\b",
    }
    
    def extract_experiences(self, text: str) -> List[ExperienceEntry]:
        """Extract work experience entries from CV text."""
        experiences = []
        current_year = datetime.now().year
        
        # Pattern for date ranges: "2020 - 2023", "2020 - Present", "Jan 2020 - Dec 2023"
        date_patterns = [
            # Year - Year or Present
            r"(?P<start>\d{4})\s*[-–—to]+\s*(?P<end>(?:\d{4}|present|current|actual|now|actualidad))",
            # Month Year - Month Year
            r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|enero|febrero|marzo|abril|mayo|junio|julio|agosto|sept|octubre|noviembre|diciembre)[a-z]*\.?\s*(?P<start2>\d{4})\s*[-–—to]+\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|enero|febrero|marzo|abril|mayo|junio|julio|agosto|sept|octubre|noviembre|diciembre)?[a-z]*\.?\s*(?P<end2>(?:\d{4}|present|current|actual|now|actualidad))",
        ]
        
        # Split text into potential experience blocks
        lines = text.split("\n")
        current_block = []
        blocks = []
        
        for line in lines:
            line_stripped = line.strip()
            # New block starts with a date pattern or job title indicators
            has_date = any(re.search(p, line_stripped, re.IGNORECASE) for p in date_patterns)
            if has_date and current_block:
                blocks.append("\n".join(current_block))
                current_block = [line_stripped]
            else:
                current_block.append(line_stripped)
        
        if current_block:
            blocks.append("\n".join(current_block))
        
        # Parse each block
        for block in blocks:
            for pattern in date_patterns:
                match = re.search(pattern, block, re.IGNORECASE)
                if match:
                    groups = match.groupdict()
                    start_year = int(groups.get("start") or groups.get("start2") or 0)
                    end_str = (groups.get("end") or groups.get("end2") or "").lower()
                    
                    is_current = end_str in ("present", "current", "actual", "now", "actualidad", "")
                    end_year = current_year if is_current else int(end_str) if end_str.isdigit() else None
                    
                    if start_year and start_year > 1970:
                        duration = (end_year or current_year) - start_year
                        
                        # Extract job title (usually first meaningful line)
                        title_match = re.search(
                            r"(?:^|\n)([A-Z][^|\n]{5,60})(?:\s*[|@at]\s*|\s+at\s+|\s+-\s+)?",
                            block
                        )
                        raw_title = title_match.group(1).strip() if title_match else ""
                        job_title = self._validate_job_title(raw_title) or "Unknown Role"
                        
                        # Extract company name
                        company = self._extract_company_from_block(block)
                        
                        experiences.append(ExperienceEntry(
                            job_title=job_title[:100],
                            company=company,
                            start_year=start_year,
                            end_year=end_year if not is_current else None,
                            duration_years=max(0, duration),
                            is_current=is_current,
                            description=block[:500]
                        ))
                    break
        
        # Sort by start year descending (most recent first)
        experiences.sort(key=lambda x: x.start_year or 0, reverse=True)
        return experiences
    
    def _extract_company_from_block(self, block: str) -> str:
        """Extract company name from experience block."""
        # Common patterns: "at Company", "@ Company", "Company Inc.", etc.
        patterns = [
            r"(?:at|@|en)\s+([A-Z][A-Za-z0-9\s&,\.]+?)(?:\s*[|\n]|$)",
            r"([A-Z][A-Za-z0-9\s&]+(?:Inc|LLC|Ltd|Corp|Company|GmbH|S\.?A\.?|S\.?L\.?)\.?)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, block)
            if match:
                company = match.group(1).strip()[:80]
                # Validate the extracted company
                validated = self._validate_company_name(company)
                if validated:
                    return validated
        
        return "Unknown Company"
    
    def _validate_job_title(self, title: str) -> str:
        """
        Validate and clean job title.
        Returns empty string if title is invalid.
        """
        if not title:
            return ""
        
        title = title.strip()
        
        # Reject if it's just a year
        if re.match(r'^\d{4}$', title):
            return ""
        
        # Reject if it's a date range
        if re.match(r'^\d{4}\s*[-–—]', title):
            return ""
        
        # Reject if it contains rating stars
        if '⭐' in title or '★' in title:
            return ""
        
        # Reject if it's a spaced-out header like "E X P E R I E N C E"
        if re.match(r'^[A-Z](\s+[A-Z]){3,}$', title):
            return ""
        
        # Reject common section headers
        section_headers = ['experience', 'education', 'skills', 'summary', 'profile', 'languages']
        if title.lower().strip() in section_headers:
            return ""
        
        # Reject if it's just a language or city
        invalid_values = ['english', 'spanish', 'french', 'german', 'italian',
                         'milan', 'london', 'berlin', 'paris', 'madrid', 'italy', 'germany']
        if title.lower().strip() in invalid_values:
            return ""
        
        # Reject very short titles
        if len(title) < 3:
            return ""
        
        # Reject if it starts with description words
        description_starters = ['to ', 'and ', 'with ', 'for ', 'the ', 'across ', 'in ']
        for starter in description_starters:
            if title.lower().startswith(starter):
                return ""
        
        return title
    
    def _validate_company_name(self, company: str) -> str:
        """
        Validate and clean company name.
        Returns empty string if company is invalid.
        """
        if not company:
            return ""
        
        company = company.strip()
        
        # Remove leading year and separator patterns
        company = re.sub(r'^\d{4}\s*[|\-–—]\s*', '', company).strip()
        
        # Reject if it's just a year or date range
        if re.match(r'^\d{4}$', company) or re.match(r'^\d{4}\s*[-–—]', company):
            return ""
        
        # Reject if it's a spaced-out header
        if re.match(r'^[A-Z](\s+[A-Z]){3,}$', company):
            return ""
        
        # Reject section headers and countries
        invalid_values = ['experience', 'education', 'skills', 'italy', 'germany', 
                         'france', 'spain', 'uk', 'usa', 'united states']
        if company.lower().strip() in invalid_values:
            return ""
        
        # Reject very short names
        if len(company) < 2:
            return ""
        
        # Reject if starts with description words
        description_starters = ['to ', 'and ', 'with ', 'for ', 'ensuring ', 'delivering ']
        for starter in description_starters:
            if company.lower().startswith(starter):
                return ""
        
        return company
    
    def detect_seniority_level(self, text: str, experiences: List[ExperienceEntry]) -> str:
        """Detect seniority level from CV text and experience."""
        # First check titles in text
        for level, pattern in self.SENIORITY_PATTERNS.items():
            if re.search(pattern, text):
                return level
        
        # Infer from total experience
        total_years = sum(e.duration_years for e in experiences)
        if total_years >= 15:
            return "lead"
        elif total_years >= 8:
            return "senior"
        elif total_years >= 3:
            return "mid"
        elif total_years > 0:
            return "junior"
        
        return "unknown"
    
    def detect_employment_gaps(self, experiences: List[ExperienceEntry]) -> List[Tuple[int, int]]:
        """Detect gaps in employment history."""
        gaps = []
        if len(experiences) < 2:
            return gaps
        
        # Sort by end year descending
        sorted_exp = sorted(experiences, key=lambda x: x.end_year or datetime.now().year, reverse=True)
        
        for i in range(len(sorted_exp) - 1):
            current = sorted_exp[i]
            previous = sorted_exp[i + 1]
            
            current_start = current.start_year or 0
            previous_end = previous.end_year or previous.start_year or 0
            
            if current_start and previous_end and current_start > previous_end + 1:
                gaps.append((previous_end, current_start))
        
        return gaps
    
    def calculate_job_hopping_score(self, experiences: List[ExperienceEntry]) -> Tuple[float, float]:
        """
        Calculate job-hopping score (0-1) and average tenure.
        
        Higher score = more job changes relative to career length.
        """
        if not experiences:
            return 0.0, 0.0
        
        durations = [e.duration_years for e in experiences if e.duration_years > 0]
        if not durations:
            return 0.0, 0.0
        
        avg_tenure = sum(durations) / len(durations)
        
        # Score based on average tenure
        # < 1 year avg = high job hopping (0.8-1.0)
        # 1-2 years avg = moderate (0.4-0.6)
        # > 3 years avg = stable (0.0-0.2)
        if avg_tenure < 1:
            score = 0.8 + (1 - avg_tenure) * 0.2
        elif avg_tenure < 2:
            score = 0.4 + (2 - avg_tenure) * 0.2
        elif avg_tenure < 3:
            score = 0.2 + (3 - avg_tenure) * 0.2
        else:
            score = max(0, 0.2 - (avg_tenure - 3) * 0.05)
        
        return min(1.0, max(0.0, score)), avg_tenure
    
    def extract_companies(self, experiences: List[ExperienceEntry]) -> Tuple[List[str], bool]:
        """Extract company list and check for FAANG experience."""
        companies = list(set(e.company for e in experiences if e.company != "Unknown Company"))
        
        has_faang = any(
            any(faang in company.lower() for faang in self.FAANG_COMPANIES)
            for company in companies
        )
        
        return companies, has_faang
    
    def detect_highest_education(self, text: str) -> Tuple[Optional[str], List[str]]:
        """Detect highest education level and institutions."""
        highest = None
        institutions = []
        
        # Check education level
        for level, pattern in self.EDUCATION_LEVELS.items():
            if re.search(pattern, text):
                highest = level
                break
        
        # Extract institution names
        institution_patterns = [
            r"(?i)(?:university|universidad|college|institute|school|academy)\s+(?:of\s+)?([A-Z][A-Za-z\s]+)",
            r"([A-Z][A-Za-z\s]+(?:University|Universidad|College|Institute|School|Academy))",
        ]
        
        for pattern in institution_patterns:
            matches = re.findall(pattern, text)
            institutions.extend([m.strip()[:60] for m in matches if len(m.strip()) > 3])
        
        return highest, list(set(institutions))[:5]
    
    def build_enriched_metadata(self, text: str, skills: List[str]) -> EnrichedMetadata:
        """Build complete enriched metadata from CV text."""
        # Extract experiences
        experiences = self.extract_experiences(text)
        
        # Calculate totals
        total_years = sum(e.duration_years for e in experiences)
        
        # Get current role
        current_role = None
        current_company = None
        for exp in experiences:
            if exp.is_current:
                current_role = exp.job_title
                current_company = exp.company
                break
        
        # Detect seniority
        seniority = self.detect_seniority_level(text, experiences)
        
        # Detect gaps
        gaps = self.detect_employment_gaps(experiences)
        
        # Calculate job hopping
        job_hopping_score, avg_tenure = self.calculate_job_hopping_score(experiences)
        
        # Extract companies
        companies, has_faang = self.extract_companies(experiences)
        
        # Detect education
        highest_edu, institutions = self.detect_highest_education(text)
        
        return EnrichedMetadata(
            skills=skills,
            total_experience_years=total_years,
            experiences=experiences,
            current_role=current_role,
            current_company=current_company,
            seniority_level=seniority,
            companies_worked=companies,
            has_faang_experience=has_faang,
            employment_gaps=gaps,
            job_hopping_score=job_hopping_score,
            avg_tenure_years=avg_tenure,
            highest_education=highest_edu,
            education_institutions=institutions
        )
    
    def create_summary_chunk(
        self,
        cv_id: str,
        filename: str,
        candidate_name: Optional[str],
        enriched: EnrichedMetadata
    ) -> CVChunk:
        """
        Create a special summary chunk with key CV information.
        
        This chunk is designed for high-level queries and ranking.
        """
        parts = []
        
        # Candidate header
        name = candidate_name or "Unknown Candidate"
        parts.append(f"CANDIDATE SUMMARY: {name}")
        parts.append(f"CV ID: {cv_id}")
        
        # Current position
        if enriched.current_role:
            parts.append(f"Current Role: {enriched.current_role}")
        if enriched.current_company:
            parts.append(f"Current Company: {enriched.current_company}")
        
        # Experience summary
        parts.append(f"Total Experience: {enriched.total_experience_years:.1f} years")
        parts.append(f"Seniority Level: {enriched.seniority_level.upper()}")
        parts.append(f"Number of Positions: {len(enriched.experiences)}")
        
        # Key skills
        if enriched.skills:
            parts.append(f"Key Skills: {', '.join(enriched.skills[:10])}")
        
        # Companies
        if enriched.companies_worked:
            parts.append(f"Companies: {', '.join(enriched.companies_worked[:5])}")
        if enriched.has_faang_experience:
            parts.append("Has FAANG/Big Tech Experience: Yes")
        
        # Education
        if enriched.highest_education:
            parts.append(f"Education Level: {enriched.highest_education.upper()}")
        
        # Red flags summary
        if enriched.employment_gaps:
            parts.append(f"Employment Gaps: {len(enriched.employment_gaps)} gap(s) detected")
        if enriched.job_hopping_score > 0.6:
            parts.append(f"Job Stability: Low (avg tenure {enriched.avg_tenure_years:.1f} years)")
        elif enriched.job_hopping_score < 0.3:
            parts.append(f"Job Stability: High (avg tenure {enriched.avg_tenure_years:.1f} years)")
        
        # Career trajectory
        if enriched.experiences:
            trajectory = " → ".join([
                f"{e.job_title} ({e.start_year or '?'})"
                for e in reversed(enriched.experiences[:5])
            ])
            parts.append(f"Career Path: {trajectory}")
        
        content = "\n".join(parts)
        
        return CVChunk(
            content=content,
            section_type="summary",
            chunk_index=0,  # Always first chunk
            cv_id=cv_id,
            filename=filename,
            candidate_name=candidate_name,
            metadata={
                "is_summary": True,
                "skills": enriched.skills,
                "total_experience_years": enriched.total_experience_years,
                "current_role": enriched.current_role,
                "current_company": enriched.current_company,
                "seniority_level": enriched.seniority_level,
                "has_faang": enriched.has_faang_experience,
                "job_hopping_score": enriched.job_hopping_score,
                "position_count": len(enriched.experiences),
            },
            is_summary_chunk=True
        )
    
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
        """Extract and chunk a CV from a PDF file with ADAPTIVE chunking and enriched metadata."""
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
        
        # Extract basic metadata
        candidate_name = self.extract_candidate_name(raw_text)
        skills = self.extract_skills(raw_text)
        
        # Build enriched metadata
        enriched_metadata = self.build_enriched_metadata(raw_text, skills)
        
        logger.info(
            f"Enriched metadata for {candidate_name or filename}: "
            f"{enriched_metadata.total_experience_years:.1f}y exp, "
            f"seniority={enriched_metadata.seniority_level}, "
            f"{len(enriched_metadata.experiences)} positions, "
            f"gaps={len(enriched_metadata.employment_gaps)}, "
            f"job_hopping={enriched_metadata.job_hopping_score:.2f}"
        )
        
        # Split into sections and chunk
        sections = self._split_into_sections(raw_text)
        
        chunks = []
        
        # FIRST: Create summary chunk (always index 0)
        summary_chunk = self.create_summary_chunk(
            cv_id=cv_id,
            filename=filename,
            candidate_name=candidate_name,
            enriched=enriched_metadata
        )
        chunks.append(summary_chunk)
        
        chunk_index = 1  # Start at 1 since summary is 0
        
        for section_type, section_content in sections:
            section_chunks = self._chunk_text(
                section_content, 
                section_type,
                chunk_size=optimal_chunk_size,
                chunk_overlap=optimal_overlap
            )
            
            for chunk_content in section_chunks:
                # Build enriched chunk metadata with ALL enriched fields
                chunk_metadata = {
                    "skills": skills,
                    "section": section_type,
                    "total_experience_years": enriched_metadata.total_experience_years,
                    "seniority_level": enriched_metadata.seniority_level,
                    "current_role": enriched_metadata.current_role,
                    "current_company": enriched_metadata.current_company,
                    "has_faang": enriched_metadata.has_faang_experience,
                    # Red flags metadata - CRITICAL for enhanced modules
                    "job_hopping_score": enriched_metadata.job_hopping_score,
                    "avg_tenure_years": enriched_metadata.avg_tenure_years,
                    "position_count": len(enriched_metadata.experiences),
                    "employment_gaps_count": len(enriched_metadata.employment_gaps),
                }
                
                # For experience sections, add position-specific metadata
                if section_type == "experience":
                    for exp in enriched_metadata.experiences:
                        if exp.job_title in chunk_content or exp.company in chunk_content:
                            chunk_metadata["job_title"] = exp.job_title
                            chunk_metadata["company"] = exp.company
                            chunk_metadata["start_year"] = exp.start_year
                            chunk_metadata["end_year"] = exp.end_year
                            chunk_metadata["is_current"] = exp.is_current
                            chunk_metadata["duration_years"] = exp.duration_years
                            break
                
                chunk = CVChunk(
                    content=chunk_content,
                    section_type=section_type,
                    chunk_index=chunk_index,
                    cv_id=cv_id,
                    filename=filename,
                    candidate_name=candidate_name,
                    metadata=chunk_metadata
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
                "total_experience_years": enriched_metadata.total_experience_years,
                "seniority_level": enriched_metadata.seniority_level,
                "current_role": enriched_metadata.current_role,
                "has_faang": enriched_metadata.has_faang_experience,
                "job_hopping_score": enriched_metadata.job_hopping_score,
                "employment_gaps_count": len(enriched_metadata.employment_gaps),
            },
            enriched_metadata=enriched_metadata
        )
