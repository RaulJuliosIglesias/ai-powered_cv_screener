import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import pdfplumber

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
class EducationEntry:
    """FASE 1: Represents an education entry."""
    degree: str  # "Master of Business Administration", "Bachelor of Science"
    field: str  # "Business Analytics", "Computer Science"
    institution: str  # "Seoul National University"
    graduation_year: Optional[int] = None
    is_highest: bool = False
    
    def to_dict(self) -> dict:
        return {
            "degree": self.degree,
            "field": self.field,
            "institution": self.institution,
            "graduation_year": self.graduation_year,
            "is_highest": self.is_highest
        }


@dataclass
class LanguageEntry:
    """FASE 1: Represents a language skill."""
    language: str  # "English", "French"
    level: str  # "Native", "C2", "B1", "Fluent", "Professional"
    is_native: bool = False
    
    def to_dict(self) -> dict:
        return {
            "language": self.language,
            "level": self.level,
            "is_native": self.is_native
        }


@dataclass 
class CertificationEntry:
    """FASE 1: Represents a professional certification."""
    name: str  # "AWS Solutions Architect", "CBAP"
    issuer: str  # "Amazon", "IIBA"
    year_obtained: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "issuer": self.issuer,
            "year_obtained": self.year_obtained
        }


@dataclass
class SkillWithLevel:
    """FASE 1: Represents a skill with proficiency level."""
    name: str  # "Python", "SQL"
    level: Optional[int] = None  # 1-10 scale
    level_raw: str = ""  # "9/10", "Advanced", "⭐⭐⭐⭐"
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "level": self.level,
            "level_raw": self.level_raw
        }


@dataclass
class EnrichedMetadata:
    """Rich metadata extracted from CV for improved indexing and retrieval."""
    # Basic info
    skills: List[str] = field(default_factory=list)
    
    # FASE 1: Skills with proficiency levels
    skills_with_levels: List[SkillWithLevel] = field(default_factory=list)
    
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
    
    # FASE 1: Education (enhanced)
    highest_education: Optional[str] = None
    education_institutions: List[str] = field(default_factory=list)
    education_entries: List[EducationEntry] = field(default_factory=list)
    education_field: Optional[str] = None
    graduation_year: Optional[int] = None
    has_mba: bool = False
    has_phd: bool = False
    
    # FASE 1: Languages
    languages: List[LanguageEntry] = field(default_factory=list)
    primary_language: Optional[str] = None
    speaks_english: bool = False
    speaks_french: bool = False
    speaks_spanish: bool = False
    speaks_german: bool = False
    
    # FASE 1: Certifications
    certifications: List[CertificationEntry] = field(default_factory=list)
    has_aws_cert: bool = False
    has_azure_cert: bool = False
    has_gcp_cert: bool = False
    has_pmp: bool = False
    
    def to_dict(self) -> dict:
        return {
            "skills": self.skills,
            "skills_with_levels": [s.to_dict() for s in self.skills_with_levels],
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
            "education_institutions": self.education_institutions,
            "education_entries": [e.to_dict() for e in self.education_entries],
            "education_field": self.education_field,
            "graduation_year": self.graduation_year,
            "has_mba": self.has_mba,
            "has_phd": self.has_phd,
            "languages": [lang.to_dict() for lang in self.languages],
            "primary_language": self.primary_language,
            "speaks_english": self.speaks_english,
            "speaks_french": self.speaks_french,
            "speaks_spanish": self.speaks_spanish,
            "speaks_german": self.speaks_german,
            "certifications": [c.to_dict() for c in self.certifications],
            "has_aws_cert": self.has_aws_cert,
            "has_azure_cert": self.has_azure_cert,
            "has_gcp_cert": self.has_gcp_cert,
            "has_pmp": self.has_pmp
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
        
        # PHASE 3 FIX: Split text into experience blocks
        # Each block should include: Job Title lines + Date line + Description lines
        # We look for date patterns and include preceding non-empty lines as part of the block
        lines = text.split("\n")
        blocks = []
        i = 0
        
        while i < len(lines):
            line_stripped = lines[i].strip()
            has_date = any(re.search(p, line_stripped, re.IGNORECASE) for p in date_patterns)
            
            if has_date:
                # Found a date line - look backwards for job title lines
                block_lines = []
                
                # Include up to 3 preceding non-empty lines (job title + optional subtitle)
                look_back = min(3, i)
                start_idx = i - look_back
                for j in range(start_idx, i):
                    prev_line = lines[j].strip()
                    # Skip section headers and empty lines
                    if prev_line and not re.match(r'^[A-Z](\s+[A-Z]){3,}$', prev_line):
                        block_lines.append(prev_line)
                
                # Add the date line
                block_lines.append(line_stripped)
                
                # Add following description lines until next date or empty block
                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()
                    next_has_date = any(re.search(p, next_line, re.IGNORECASE) for p in date_patterns)
                    
                    # Stop if we hit another date line (next job entry)
                    if next_has_date:
                        break
                    
                    # Stop if we hit what looks like a new job title (capitalized line after empty)
                    if not next_line and i + 1 < len(lines):
                        following = lines[i + 1].strip() if i + 1 < len(lines) else ""
                        if following and following[0].isupper() and len(following) > 10:
                            # Check if following line leads to a date
                            for k in range(i + 1, min(i + 4, len(lines))):
                                if any(re.search(p, lines[k].strip(), re.IGNORECASE) for p in date_patterns):
                                    break
                            else:
                                block_lines.append(next_line)
                                i += 1
                                continue
                            break
                    
                    block_lines.append(next_line)
                    i += 1
                
                if block_lines:
                    blocks.append("\n".join(block_lines))
            else:
                i += 1
        
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
                        
                        # PHASE 3 FIX: Extract job title - look for title BEFORE the date line
                        # Format: "Job Title\n(Optional subtitle)\nYEAR - YEAR | Company"
                        job_title = self._extract_job_title_from_block(block)
                        
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
        # PHASE 3 FIX: First try to extract from "YEAR - Present | Company Name" format
        # This is a common CV format where company follows the date with a pipe separator
        pipe_pattern = r'\d{4}\s*[-–—]\s*(?:Present|Presente|Actual|Current|\d{4})\s*\|\s*([A-Z][A-Za-z0-9\s&,\.\(\)]+?)(?:\n|$)'
        pipe_match = re.search(pipe_pattern, block, re.IGNORECASE)
        if pipe_match:
            company = pipe_match.group(1).strip()[:80]
            validated = self._validate_company_name(company)
            if validated:
                return validated
        
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
    
    def _extract_job_title_from_block(self, block: str) -> str:
        """
        PHASE 3 FIX: Extract job title from experience block.
        
        Handles formats like:
        - "Lead Editorial & Visual Stylist\n(Contract/Freelance)\n2015 - Present | Company"
        - "Director, Business Analytics\n2023 - Present | Hanriver Consulting"
        
        The title is typically the first meaningful line BEFORE the date.
        """
        lines = block.strip().split('\n')
        
        # Find the line with the date pattern
        date_line_idx = -1
        for i, line in enumerate(lines):
            if re.search(r'\b(19|20)\d{2}\s*[-–—]\s*(?:(19|20)\d{2}|Present|Actual|Current)', line, re.IGNORECASE):
                date_line_idx = i
                break
        
        # Look at lines BEFORE the date line for the job title
        candidate_titles = []
        search_range = range(0, date_line_idx) if date_line_idx > 0 else range(0, min(3, len(lines)))
        
        for i in search_range:
            line = lines[i].strip()
            if not line:
                continue
            
            # Skip lines that look like subtitles in parentheses
            if line.startswith('(') and line.endswith(')'):
                continue
            
            # Skip lines that are just section headers
            if re.match(r'^[A-Z](\s+[A-Z]){3,}$', line):
                continue
            
            # Validate as potential title
            validated = self._validate_job_title(line)
            if validated:
                candidate_titles.append(validated)
        
        # Return the first valid title found, or "Unknown Role"
        if candidate_titles:
            return candidate_titles[0]
        
        # Fallback: try to extract from the date line itself (format: "Title | 2020 - Present")
        if date_line_idx >= 0:
            date_line = lines[date_line_idx]
            # Check if title is before the year
            before_year = re.split(r'\b(19|20)\d{2}', date_line)[0].strip()
            if before_year:
                # Remove trailing separators
                before_year = re.sub(r'[\|–—\-,]\s*$', '', before_year).strip()
                validated = self._validate_job_title(before_year)
                if validated:
                    return validated
        
        return "Unknown Role"
    
    def _validate_job_title(self, title: str) -> str:
        """
        Validate and clean job title.
        Returns empty string if title is invalid.
        
        PHASE 3 FIX: Enhanced validation to reject description sentences.
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
        
        # PHASE 3 FIX: Reject if it ends with a period (descriptions end with periods, titles don't)
        if title.endswith('.'):
            return ""
        
        # PHASE 3 FIX: Reject if it's too long (job titles are typically < 60 chars)
        if len(title) > 80:
            return ""
        
        # PHASE 3 FIX: Reject if it starts with past-tense action verbs (description sentences)
        description_verbs = [
            'directed', 'managed', 'led', 'developed', 'created', 'implemented',
            'achieved', 'increased', 'reduced', 'delivered', 'executed', 'built',
            'designed', 'launched', 'established', 'coordinated', 'organized',
            'spearheaded', 'drove', 'cultivated', 'trained', 'mentored',
            'supported', 'assisted', 'prepared', 'conducted', 'performed',
            'maintained', 'ensured', 'provided', 'collaborated', 'worked',
            'responsible', 'entry-level', 'foundational', 'gained'
        ]
        title_lower = title.lower()
        for verb in description_verbs:
            if title_lower.startswith(verb + ' ') or title_lower.startswith(verb + ','):
                return ""
        
        # Reject common section headers
        section_headers = ['experience', 'education', 'skills', 'summary', 'profile', 'languages']
        if title_lower.strip() in section_headers:
            return ""
        
        # Reject if it's just a language or city
        invalid_values = ['english', 'spanish', 'french', 'german', 'italian',
                         'milan', 'london', 'berlin', 'paris', 'madrid', 'italy', 'germany']
        if title_lower.strip() in invalid_values:
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
        
        # PHASE 3 FIX: Reject skill ratings like "10/10", "9/10", "SQL 10/10"
        if re.search(r'\b\d{1,2}/\d{1,2}\b', company):
            return ""
        
        # PHASE 3 FIX: Reject if it contains skill-like patterns
        # e.g., "Data Visualization (Tableau)" is a skill, not a company
        skill_indicators = [
            r'\(Tableau\)', r'\(Python\)', r'\(Excel\)', r'\(SQL\)', 
            r'\(Adobe', r'\(Advanced', r'\(High', r'Analysis \(',
            r'Modeling\b', r'Visualization\b', r'Methodologies\b'
        ]
        for pattern in skill_indicators:
            if re.search(pattern, company, re.IGNORECASE):
                return ""
        
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
    
    def _calculate_total_experience_from_span(self, experiences: List[ExperienceEntry]) -> float:
        """
        PHASE 3 FIX: Calculate total experience from career span.
        
        Uses the range from earliest start year to latest end year,
        which correctly handles overlapping positions and gives accurate
        total career duration.
        
        Example: 4 positions from 1995-2026 = 31 years (not sum of durations)
        """
        if not experiences:
            return 0.0
        
        current_year = datetime.now().year
        
        # Get all valid start and end years
        start_years = [e.start_year for e in experiences if e.start_year and e.start_year > 1970]
        end_years = []
        for e in experiences:
            if e.is_current or e.end_year is None:
                end_years.append(current_year)
            elif e.end_year and e.end_year > 1970:
                end_years.append(e.end_year)
        
        if not start_years:
            # Fallback: sum individual durations if no valid start years
            return sum(e.duration_years for e in experiences)
        
        earliest_start = min(start_years)
        latest_end = max(end_years) if end_years else current_year
        
        # Calculate span
        total_span = latest_end - earliest_start
        
        # Sanity check: cap at 50 years, minimum 0
        total_span = max(0, min(50, total_span))
        
        logger.debug(
            f"[EXPERIENCE] Career span: {earliest_start} - {latest_end} = {total_span} years "
            f"(from {len(experiences)} positions)"
        )
        
        return float(total_span)
    
    def detect_seniority_level(self, text: str, experiences: List[ExperienceEntry]) -> str:
        """Detect seniority level from CV text and experience."""
        # First check titles in text
        for level, pattern in self.SENIORITY_PATTERNS.items():
            if re.search(pattern, text):
                return level
        
        # PHASE 3 FIX: Use career span for seniority calculation
        total_years = self._calculate_total_experience_from_span(experiences)
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
        companies = list({e.company for e in experiences if e.company != "Unknown Company"})
        
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
    
    # =========================================================================
    # FASE 1: NEW EXTRACTION METHODS
    # =========================================================================
    
    def extract_education_entries(self, text: str) -> List[EducationEntry]:
        """
        FASE 1: Extract structured education entries from CV text.
        
        Handles formats:
        - "Master of Business Administration (MBA)\nSeoul National University\n2019"
        - "Bachelor of Science in Economics, Korea University, 2012"
        - "PhD in Computer Science from MIT (2018)"
        """
        entries = []
        
        # Institution pattern
        institution_pattern = r"([A-Z][A-Za-z\s]+(?:University|Universidad|College|Institute|School|Academy|Universität))"
        
        # Year pattern  
        year_pattern = r"\b(19[89]\d|20[0-2]\d)\b"
        
        # Split into education section if possible
        edu_section = text
        edu_match = re.search(r"(?i)(?:education|academic|qualification)s?\s*\n([\s\S]*?)(?:\n\s*(?:experience|skills|certification|language|professional)|$)", text)
        if edu_match:
            edu_section = edu_match.group(1)
        
        # Pattern 1: "Master of Business Administration (MBA)"
        mba_pattern = r"(?i)(Master\s+of\s+Business\s+Administration|MBA|M\.?B\.?A\.?)"
        if re.search(mba_pattern, edu_section):
            context = edu_section
            inst_match = re.search(institution_pattern, context)
            year_match = re.search(year_pattern, context)
            entries.append(EducationEntry(
                degree="Master of Business Administration",
                field="Business Administration",
                institution=inst_match.group(1).strip()[:60] if inst_match else "",
                graduation_year=int(year_match.group(1)) if year_match else None,
                is_highest=True
            ))
        
        # Pattern 2: "Bachelor of Science in X" or "B.S. in X"
        bs_pattern = r"(?i)(Bachelor(?:'s)?\s+of\s+(?:Science|Arts)|B\.?S\.?|B\.?A\.?)\s+(?:in\s+)?([A-Za-z\s&]+?)(?:\n|,|$)"
        for match in re.finditer(bs_pattern, edu_section):
            field = match.group(2).strip() if match.group(2) else ""
            field = re.sub(r"(?i)\s*(from|at)\s*$", "", field).strip()
            
            context = edu_section[max(0, match.start()-20):min(len(edu_section), match.end()+150)]
            inst_match = re.search(institution_pattern, context)
            year_match = re.search(year_pattern, context)
            
            # Avoid duplicate with MBA
            if "business administration" not in field.lower():
                entries.append(EducationEntry(
                    degree="Bachelor's Degree",
                    field=field[:50],
                    institution=inst_match.group(1).strip()[:60] if inst_match else "",
                    graduation_year=int(year_match.group(1)) if year_match else None,
                    is_highest=False
                ))
        
        # Pattern 3: PhD/Doctorate
        phd_pattern = r"(?i)(Ph\.?D\.?|Doctor(?:ate)?|D\.?Phil\.?)\s+(?:in\s+)?([A-Za-z\s&]+?)(?:\n|,|from|at|$)"
        for match in re.finditer(phd_pattern, edu_section):
            field = match.group(2).strip() if match.group(2) else ""
            field = re.sub(r"(?i)\s*(from|at)\s*$", "", field).strip()
            
            context = edu_section[max(0, match.start()-20):min(len(edu_section), match.end()+150)]
            inst_match = re.search(institution_pattern, context)
            year_match = re.search(year_pattern, context)
            
            entries.append(EducationEntry(
                degree="PhD",
                field=field[:50],
                institution=inst_match.group(1).strip()[:60] if inst_match else "",
                graduation_year=int(year_match.group(1)) if year_match else None,
                is_highest=True
            ))
        
        # Pattern 4: Master's (non-MBA)
        masters_pattern = r"(?i)(Master(?:'s)?\s+of\s+(?:Science|Arts)|M\.?S\.?|M\.?A\.?)\s+(?:in\s+)?([A-Za-z\s&]+?)(?:\n|,|$)"
        for match in re.finditer(masters_pattern, edu_section):
            field = match.group(2).strip() if match.group(2) else ""
            field = re.sub(r"(?i)\s*(from|at)\s*$", "", field).strip()
            
            # Skip if it's MBA (already captured)
            if "business" in field.lower():
                continue
            
            context = edu_section[max(0, match.start()-20):min(len(edu_section), match.end()+150)]
            inst_match = re.search(institution_pattern, context)
            year_match = re.search(year_pattern, context)
            
            entries.append(EducationEntry(
                degree="Master's Degree",
                field=field[:50],
                institution=inst_match.group(1).strip()[:60] if inst_match else "",
                graduation_year=int(year_match.group(1)) if year_match else None,
                is_highest=True
            ))
        
        # Pattern 5: Diploma
        diploma_pattern = r"(?i)(Diploma|Certificate)\s+(?:in\s+)?([A-Za-z\s&]+?)(?:\n|,|$)"
        for match in re.finditer(diploma_pattern, edu_section):
            field = match.group(2).strip() if match.group(2) else ""
            
            context = edu_section[max(0, match.start()-20):min(len(edu_section), match.end()+150)]
            inst_match = re.search(institution_pattern, context)
            year_match = re.search(year_pattern, context)
            
            entries.append(EducationEntry(
                degree=match.group(1).strip(),
                field=field[:50],
                institution=inst_match.group(1).strip()[:60] if inst_match else "",
                graduation_year=int(year_match.group(1)) if year_match else None,
                is_highest=False
            ))
        
        return entries[:5]  # Max 5 entries
    
    def extract_languages(self, text: str) -> List[LanguageEntry]:
        """
        FASE 1: Extract languages with proficiency levels.
        
        Handles formats:
        - "English (Native)", "French (Fluent)"
        - "English: C2", "French: B1"
        - "English - Native", "Spanish - Intermediate"
        - "Languages: English, French, German"
        """
        entries = []
        
        # Common languages
        languages = [
            "english", "spanish", "french", "german", "italian", "portuguese",
            "chinese", "mandarin", "japanese", "korean", "arabic", "russian",
            "dutch", "swedish", "norwegian", "danish", "finnish", "polish",
            "hindi", "bengali", "turkish", "vietnamese", "thai", "indonesian",
            "hebrew", "greek", "czech", "hungarian", "romanian", "ukrainian"
        ]
        
        # Level indicators
        level_patterns = {
            "native": ["native", "mother tongue", "first language", "nativo", "lengua materna"],
            "C2": ["c2", "proficient", "bilingual", "fluent", "near-native", "advanced"],
            "C1": ["c1", "advanced", "professional", "full professional"],
            "B2": ["b2", "upper intermediate", "upper-intermediate", "working proficiency"],
            "B1": ["b1", "intermediate", "conversational"],
            "A2": ["a2", "elementary", "basic", "pre-intermediate"],
            "A1": ["a1", "beginner", "limited"]
        }
        
        text_lower = text.lower()
        
        for lang in languages:
            # Check if language is mentioned
            if lang not in text_lower:
                continue
            
            # Find the context around the language mention
            pattern = rf"(?i)\b{lang}\b[:\s\-–—\(]*([A-Za-z0-9\s\-]+?)(?:[,\)\n]|$)"
            matches = re.finditer(pattern, text_lower)
            
            level = "Unknown"
            is_native = False
            
            for match in matches:
                level_context = match.group(1).lower() if match.group(1) else ""
                
                # Check for level indicators
                for lvl, indicators in level_patterns.items():
                    if any(ind in level_context for ind in indicators):
                        level = lvl
                        is_native = (lvl == "native")
                        break
            
            # If language found but no level, default to "Professional"
            if level == "Unknown":
                level = "Professional"
            
            entries.append(LanguageEntry(
                language=lang.capitalize(),
                level=level,
                is_native=is_native
            ))
        
        return entries
    
    def extract_certifications(self, text: str) -> List[CertificationEntry]:
        """
        FASE 1: Extract professional certifications with dates.
        
        Handles formats:
        - "AWS Solutions Architect - 2022"
        - "Certified Business Analysis Professional (CBAP), IIBA, 2020"
        - "PMP | Project Management Institute | 2019"
        """
        entries = []
        
        # Known certifications with their issuers
        cert_patterns = [
            # AWS
            (r"(?i)(AWS\s+(?:Solutions?\s+Architect|Developer|SysOps|DevOps|Cloud\s+Practitioner|Certified)[A-Za-z\s\-]*)", "Amazon Web Services", "aws"),
            # Azure
            (r"(?i)(Azure\s+(?:Administrator|Developer|Architect|Data|AI|Security)[A-Za-z\s\-]*)", "Microsoft", "azure"),
            (r"(?i)(AZ-\d{3}[A-Za-z\s\-]*)", "Microsoft", "azure"),
            # GCP
            (r"(?i)(Google\s+Cloud\s+(?:Professional|Associate)[A-Za-z\s\-]*)", "Google", "gcp"),
            (r"(?i)(GCP\s+[A-Za-z\s\-]+(?:Engineer|Architect|Developer))", "Google", "gcp"),
            # PMP
            (r"(?i)(PMP|Project\s+Management\s+Professional)", "PMI", "pmp"),
            # CBAP
            (r"(?i)(CBAP|Certified\s+Business\s+Analysis\s+Professional)", "IIBA", "cbap"),
            # Scrum/Agile
            (r"(?i)(CSM|Certified\s+Scrum\s+Master)", "Scrum Alliance", "scrum"),
            (r"(?i)(PSM\s*I{1,3}|Professional\s+Scrum\s+Master)", "Scrum.org", "scrum"),
            # Data
            (r"(?i)(Tableau\s+(?:Desktop|Server|Data|Certified)[A-Za-z\s\-]*)", "Tableau", "data"),
            # Six Sigma
            (r"(?i)(Six\s+Sigma\s+(?:Green|Black|Yellow)\s+Belt)", "Various", "sixsigma"),
            # Generic cert pattern
            (r"(?i)(Certified\s+[A-Z][A-Za-z\s]{5,40})", "Unknown", "other"),
        ]
        
        year_pattern = r"\b(20[0-2]\d|19[89]\d)\b"
        
        for cert_pattern, default_issuer, _cert_type in cert_patterns:
            matches = re.finditer(cert_pattern, text)
            for match in matches:
                cert_name = match.group(1).strip()
                
                # Clean up
                cert_name = re.sub(r"\s+", " ", cert_name)[:60]
                
                # Look for year near the match
                context = text[max(0, match.start()-20):min(len(text), match.end()+50)]
                year_match = re.search(year_pattern, context)
                year_obtained = int(year_match.group(1)) if year_match else None
                
                # Avoid duplicates
                if not any(e.name.lower() == cert_name.lower() for e in entries):
                    entries.append(CertificationEntry(
                        name=cert_name,
                        issuer=default_issuer,
                        year_obtained=year_obtained
                    ))
        
        return entries[:10]  # Max 10 certs
    
    def extract_skills_with_levels(self, text: str) -> List[SkillWithLevel]:
        """
        FASE 1: Extract skills with proficiency levels.
        
        Handles formats:
        - "Python 9/10", "SQL 10/10"
        - "Python ⭐⭐⭐⭐⭐"
        - "Python (Advanced)", "SQL (Expert)"
        - "Python: 90%", "SQL: Expert"
        """
        entries = []
        
        # Pattern for "Skill X/10" format
        rating_pattern = r"([A-Za-z][A-Za-z\s\+\#\.]{1,25}?)\s*[:\-]?\s*(\d{1,2})\s*/\s*10"
        
        matches = re.finditer(rating_pattern, text)
        for match in matches:
            skill_name = match.group(1).strip()
            level = int(match.group(2))
            
            # Validate skill name
            if len(skill_name) < 2 or len(skill_name) > 30:
                continue
            if skill_name.lower() in ["the", "and", "for", "with", "from"]:
                continue
            
            entries.append(SkillWithLevel(
                name=skill_name,
                level=level,
                level_raw=f"{level}/10"
            ))
        
        # Pattern for star ratings
        star_pattern = r"([A-Za-z][A-Za-z\s\+\#\.]{1,25}?)\s*[:\-]?\s*(⭐{1,5}|★{1,5}|☆{1,5})"
        
        matches = re.finditer(star_pattern, text)
        for match in matches:
            skill_name = match.group(1).strip()
            stars = match.group(2)
            level = len(stars) * 2  # Convert 5 stars to 10 scale
            
            if len(skill_name) >= 2 and len(skill_name) <= 30:
                # Avoid duplicates
                if not any(e.name.lower() == skill_name.lower() for e in entries):
                    entries.append(SkillWithLevel(
                        name=skill_name,
                        level=level,
                        level_raw=stars
                    ))
        
        # Pattern for "Skill (Level)" format
        level_words = {
            "expert": 10, "advanced": 8, "proficient": 7,
            "intermediate": 5, "basic": 3, "beginner": 2
        }
        
        level_pattern = r"([A-Za-z][A-Za-z\s\+\#\.]{1,25}?)\s*\(\s*(expert|advanced|proficient|intermediate|basic|beginner)\s*\)"
        
        matches = re.finditer(level_pattern, text, re.IGNORECASE)
        for match in matches:
            skill_name = match.group(1).strip()
            level_word = match.group(2).lower()
            level = level_words.get(level_word, 5)
            
            if len(skill_name) >= 2 and len(skill_name) <= 30:
                if not any(e.name.lower() == skill_name.lower() for e in entries):
                    entries.append(SkillWithLevel(
                        name=skill_name,
                        level=level,
                        level_raw=level_word.capitalize()
                    ))
        
        return entries[:30]  # Max 30 skills with levels
    
    def build_enriched_metadata(self, text: str, skills: List[str]) -> EnrichedMetadata:
        """Build complete enriched metadata from CV text."""
        # Extract experiences
        experiences = self.extract_experiences(text)
        
        # PHASE 3 FIX: Calculate total experience from career span (earliest to latest)
        # instead of summing individual durations (which can be wrong for overlapping roles)
        total_years = self._calculate_total_experience_from_span(experiences)
        
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
        
        # Detect education (legacy)
        highest_edu, institutions = self.detect_highest_education(text)
        
        # =========================================================================
        # FASE 1: Extract new structured data
        # =========================================================================
        
        # Education entries
        education_entries = self.extract_education_entries(text)
        education_field = None
        graduation_year = None
        has_mba = False
        has_phd = False
        
        if education_entries:
            # Get field from highest degree
            for entry in education_entries:
                if entry.is_highest and entry.field:
                    education_field = entry.field
                    graduation_year = entry.graduation_year
                    break
            if not education_field and education_entries[0].field:
                education_field = education_entries[0].field
                graduation_year = education_entries[0].graduation_year
            
            # Check for MBA/PhD
            text_lower = text.lower()
            has_mba = "mba" in text_lower or "master of business" in text_lower
            has_phd = "phd" in text_lower or "ph.d" in text_lower or "doctorate" in text_lower
        
        # Languages
        languages = self.extract_languages(text)
        primary_language = languages[0].language if languages else None
        speaks_english = any(lang.language.lower() == "english" for lang in languages)
        speaks_french = any(lang.language.lower() == "french" for lang in languages)
        speaks_spanish = any(lang.language.lower() == "spanish" for lang in languages)
        speaks_german = any(lang.language.lower() == "german" for lang in languages)
        
        # Certifications
        certifications = self.extract_certifications(text)
        has_aws_cert = any("aws" in c.name.lower() for c in certifications)
        has_azure_cert = any("azure" in c.name.lower() or c.name.startswith("AZ-") for c in certifications)
        has_gcp_cert = any("google cloud" in c.name.lower() or "gcp" in c.name.lower() for c in certifications)
        has_pmp = any("pmp" in c.name.lower() or "project management professional" in c.name.lower() for c in certifications)
        
        # Skills with levels
        skills_with_levels = self.extract_skills_with_levels(text)
        
        logger.info(
            f"[FASE1] Extracted: {len(education_entries)} education, {len(languages)} languages, "
            f"{len(certifications)} certs, {len(skills_with_levels)} skills with levels"
        )
        
        return EnrichedMetadata(
            skills=skills,
            skills_with_levels=skills_with_levels,
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
            education_institutions=institutions,
            education_entries=education_entries,
            education_field=education_field,
            graduation_year=graduation_year,
            has_mba=has_mba,
            has_phd=has_phd,
            languages=languages,
            primary_language=primary_language,
            speaks_english=speaks_english,
            speaks_french=speaks_french,
            speaks_spanish=speaks_spanish,
            speaks_german=speaks_german,
            certifications=certifications,
            has_aws_cert=has_aws_cert,
            has_azure_cert=has_azure_cert,
            has_gcp_cert=has_gcp_cert,
            has_pmp=has_pmp
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
                "sections": list({s[0] for s in sections}),
                "total_experience_years": enriched_metadata.total_experience_years,
                "seniority_level": enriched_metadata.seniority_level,
                "current_role": enriched_metadata.current_role,
                "has_faang": enriched_metadata.has_faang_experience,
                "job_hopping_score": enriched_metadata.job_hopping_score,
                "employment_gaps_count": len(enriched_metadata.employment_gaps),
            },
            enriched_metadata=enriched_metadata
        )
