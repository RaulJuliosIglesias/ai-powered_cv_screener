"""
Smart CV Chunking Service v2

This service extracts structured information from CVs and creates
enriched chunks with metadata that enables accurate responses to
questions like:
- What is the current role?
- How many years of experience?
- What is the career trajectory?

Key improvements over basic chunking:
1. Extracts dates and calculates experience years
2. Identifies current vs previous positions
3. Creates a "summary chunk" with pre-calculated totals
4. Creates individual chunks per job with rich metadata
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class JobPosition:
    """Represents a single job position extracted from CV."""
    title: str
    company: str
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    is_current: bool = False
    duration_years: float = 0.0
    description: str = ""
    raw_text: str = ""
    
    def calculate_duration(self) -> float:
        """Calculate duration in years."""
        if self.start_year is None:
            return 0.0
        
        current_year = datetime.now().year
        end = self.end_year if self.end_year else current_year
        duration = end - self.start_year
        return max(0, duration)


@dataclass
class CVStructuredData:
    """Structured data extracted from CV."""
    candidate_name: str
    current_role: Optional[str] = None
    current_company: Optional[str] = None
    total_experience_years: float = 0.0
    positions: List[JobPosition] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    raw_text: str = ""


class SmartChunkingService:
    """
    Intelligent CV chunking that extracts structured data and creates
    enriched chunks for better RAG retrieval.
    """
    
    # Patterns for extracting dates - EXTENDED to capture more formats
    YEAR_PATTERNS = [
        # "2020 - Present", "2020 - Presente", "2020 - Actual", "2020 - ongoing"
        r'(\d{4})\s*[-–—]\s*(Present|Presente|Actual|Current|Now|Oggi|Heute|Hoy|Ongoing|Today|Heden|Nuvarande)',
        # "2018 - 2023", "2018-2023", "2018 – 2023"
        r'(\d{4})\s*[-–—]\s*(\d{4})',
        # "Jan 2020 - Dec 2023", "January 2020 - December 2023"
        r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[a-z]*\.?\s*(\d{4})\s*[-–—]\s*(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[a-z]*\.?\s*(\d{4})',
        # "01/2020 - 12/2023", "1/2020 - 12/2023"
        r'(?:\d{1,2}/)?(\d{4})\s*[-–—]\s*(?:\d{1,2}/)?(\d{4})',
        # "(2020-2023)", "(2020 - Present)" - parenthesized dates
        r'\((\d{4})\s*[-–—]\s*(\d{4}|Present|Presente|Actual|Current)\)',
        # "Since 2020", "Desde 2020", "From 2020"
        r'(?:Since|Desde|From|Ab)\s+(\d{4})',
        # "2020 to 2023", "2020 until 2023"
        r'(\d{4})\s+(?:to|until|till|a|bis|jusqu)\s+(\d{4})',
        # "2020 to Present", "2020 to now"
        r'(\d{4})\s+(?:to|until|till)\s+(Present|Now|Current|Actual|Presente)',
        # European format: "2020/01 - 2023/12"
        r'(\d{4})/\d{1,2}\s*[-–—]\s*(\d{4})/\d{1,2}',
        # ISO-like: "2020.01 - 2023.12"
        r'(\d{4})\.\d{1,2}\s*[-–—]\s*(\d{4})\.\d{1,2}',
    ]
    
    # Patterns for current position indicators
    CURRENT_INDICATORS = [
        r'present', r'presente', r'actual', r'current', r'now', 
        r'oggi', r'heute', r'hoy', r'currently', r'actualidad'
    ]
    
    # Section header patterns
    SECTION_PATTERNS = {
        'experience': r'(?i)(work\s+)?experience|employment|career|professional\s+background|work\s+history|experiencia',
        'education': r'(?i)education|academic|studies|qualifications|educación|formación',
        'skills': r'(?i)skills|technical\s+skills|competencies|technologies|expertise|habilidades',
        'certifications': r'(?i)certification|certificate|accreditation|license|credential|certificación',
        'summary': r'(?i)summary|profile|objective|about\s*me|professional\s+summary|resumen|perfil',
    }
    
    def __init__(self):
        self.current_year = datetime.now().year
    
    def _parse_filename(self, filename: str) -> Dict[str, str]:
        """Parse filename to extract candidate info."""
        name = filename.replace('.pdf', '').replace('.PDF', '')
        parts = name.split('_')
        
        if len(parts) >= 3:
            file_id = parts[0]
            # Role is typically the last part
            role_raw = parts[-1].replace('-', ' ').replace('_', ' ')
            # Name parts are between file_id and role
            name_parts = parts[1:-1]
            candidate_name = ' '.join(name_parts)
            # Clean the candidate name - remove any trailing role/title that got attached
            candidate_name = self._clean_candidate_name(candidate_name)
            return {"file_id": file_id, "candidate_name": candidate_name, "role": role_raw}
        elif len(parts) == 2:
            candidate_name = self._clean_candidate_name(parts[1])
            return {"file_id": parts[0], "candidate_name": candidate_name, "role": ""}
        
        candidate_name = self._clean_candidate_name(name)
        return {"file_id": "", "candidate_name": candidate_name, "role": ""}
    
    def _clean_candidate_name(self, name: str) -> str:
        """
        Clean candidate name by removing common artifacts.
        
        PHASE 2.1 FIX: Also removes non-name words like food, objects, etc.
        
        Fixes issues like:
        - " Aisha Okafor  Business" -> "Aisha Okafor"
        - "Matteo Rossi  Associate" -> "Matteo Rossi"
        - "Aisha Tan Pizza" -> "Aisha Tan" (removes food words)
        """
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        # Common job title words that shouldn't be in names
        title_words = [
            'Business', 'Associate', 'Junior', 'Senior', 'Manager', 'Director',
            'Engineer', 'Developer', 'Analyst', 'Consultant', 'Specialist',
            'Coordinator', 'Administrator', 'Executive', 'Lead', 'Principal',
            'Architect', 'Designer', 'Pharmacy', 'Pharmacist', 'Chef', 'Sous',
            'Mix', 'Camera', 'Digital', 'Protocol', 'Growth', 'Brand', 'Crypto',
            'Creature', 'Celebrity', 'Restaurant', 'Graduate', 'Intern', 'Trainee',
            'Systems', 'Technical', 'Instructional', 'Swift', 'Game', 'Law',
            'Accessories', 'Group', 'Camera', 'Smart', 'Contract'
        ]
        
        # PHASE 2.1: Non-name words (food, objects, places that aren't surnames)
        non_name_words = [
            # Food words
            'Pizza', 'Burger', 'Sushi', 'Taco', 'Coffee', 'Pasta', 'Salad',
            'Sandwich', 'Cookie', 'Cake', 'Bread', 'Rice', 'Soup', 'Steak',
            # Objects
            'Table', 'Chair', 'Desk', 'Computer', 'Phone', 'Book', 'Car',
            'House', 'Building', 'Office', 'Room', 'Door', 'Window',
            # Common non-surname words that might get attached
            'Resume', 'CV', 'Profile', 'Career', 'Experience', 'Skills',
            'Education', 'Contact', 'Summary', 'Objective', 'Reference',
            # Numbers and codes
            'One', 'Two', 'Three', 'Four', 'Five', 'First', 'Second', 'Third',
        ]
        
        all_invalid_words = set(title_words + non_name_words)
        
        # Remove trailing invalid words
        words = name.split()
        clean_words = []
        
        for word in words:
            # Once we hit an invalid word, stop adding words
            if word in all_invalid_words:
                logger.debug(f"[SMART_CHUNKING] Removing invalid word from name: '{word}'")
                break
            clean_words.append(word)
        
        # If we removed everything, keep original (minus double spaces)
        if not clean_words:
            return name
        
        # PHASE 2.1: Validate final name has at least 2 words (first + last name)
        # and doesn't contain obviously invalid patterns
        result = ' '.join(clean_words)
        
        # Final validation: reject if result looks invalid
        if self._is_invalid_name(result):
            logger.warning(f"[SMART_CHUNKING] Name validation failed for: '{result}', keeping original")
            return name
        
        return result
    
    def _is_invalid_name(self, name: str) -> bool:
        """
        PHASE 2.1: Check if a name looks invalid.
        
        Returns True if the name should be rejected.
        """
        if not name:
            return True
        
        # Too short (less than 3 chars)
        if len(name) < 3:
            return True
        
        # Contains numbers
        if re.search(r'\d', name):
            return True
        
        # Contains special characters (except hyphen, apostrophe, space)
        if re.search(r'[^\w\s\'\-]', name):
            return True
        
        # All uppercase or all lowercase (likely not a proper name)
        if name.isupper() or name.islower():
            return True
        
        # Starts with lowercase
        if name[0].islower():
            return True
        
        return False
    
    def _extract_years_from_text(self, text: str) -> Tuple[Optional[int], Optional[int], bool]:
        """
        Extract start year, end year, and whether it's current position.
        Returns: (start_year, end_year, is_current)
        """
        is_current = False
        
        # Check for current position indicators
        for indicator in self.CURRENT_INDICATORS:
            if re.search(indicator, text, re.IGNORECASE):
                is_current = True
                break
        
        # Try each date pattern
        for pattern in self.YEAR_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                start_year = int(groups[0]) if groups[0].isdigit() else None
                
                # Check if second group is a year or "Present" indicator
                if len(groups) > 1:
                    if groups[1] and groups[1].isdigit():
                        end_year = int(groups[1])
                    else:
                        end_year = None
                        is_current = True
                else:
                    end_year = None
                
                return start_year, end_year, is_current
        
        # Fallback: find any 4-digit years
        years = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        if years:
            years = [int(y) for y in years]
            years.sort()
            if len(years) >= 2:
                return years[0], years[-1], is_current
            elif len(years) == 1:
                return years[0], None, is_current
        
        return None, None, is_current
    
    def _extract_job_title_and_company(self, text: str) -> Tuple[str, str]:
        """Extract job title and company from a job entry."""
        lines = text.strip().split('\n')
        title = ""
        company = ""
        
        if not lines:
            return title, company
        
        first_line = lines[0].strip()
        
        # Pattern: "Title at/@ Company"
        match = re.match(r'^(.+?)\s+(?:at|@|en)\s+(.+?)(?:\s*[\(\[]|$)', first_line, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            company = match.group(2).strip()
            # Clean date patterns from extracted values
            title = re.sub(r'\s*\d{4}\s*[-–—].*$', '', title).strip()
            company = re.sub(r'\s*\d{4}\s*[-–—].*$', '', company).strip()
            # Validate extracted values
            title = self._validate_job_title(title)
            company = self._validate_company_name(company)
            if title and company:
                return title, company
        
        # Pattern: "Title | Company" or "Title - Company" or "Title, Company"
        for separator in ['|', '–', '—', '-', ',']:
            if separator in first_line:
                parts = first_line.split(separator, 1)
                if len(parts) == 2:
                    # Remove date patterns from parts
                    part1 = re.sub(r'\d{4}\s*[-–—]\s*(?:\d{4}|Present|Actual|Presente)', '', parts[0], flags=re.IGNORECASE).strip()
                    part2 = re.sub(r'\d{4}\s*[-–—]\s*(?:\d{4}|Present|Actual|Presente)', '', parts[1], flags=re.IGNORECASE).strip()
                    
                    part1 = self._validate_job_title(part1)
                    part2 = self._validate_company_name(part2)
                    
                    if part1 and part2 and len(part1) > 2 and len(part2) > 2:
                        title = part1
                        company = part2
                        return title, company
        
        # Fallback: first line is title
        title = re.sub(r'\d{4}\s*[-–—]\s*(?:\d{4}|Present|Actual|Presente)', '', first_line, flags=re.IGNORECASE).strip()
        title = self._validate_job_title(title)
        
        # Look for company in subsequent lines
        for line in lines[1:4]:
            line = line.strip()
            if line and not re.match(r'^[\d\-/•\*]', line):
                if len(line) < 80 and not line.startswith(('•', '-', '*', '–')):
                    potential_company = re.sub(r'\d{4}.*', '', line).strip()
                    company = self._validate_company_name(potential_company)
                    if company:
                        break
        
        return title or "Unknown Role", company or "Unknown Company"
    
    def _validate_job_title(self, title: str) -> str:
        """
        Validate and clean job title.
        Returns empty string if title is invalid.
        
        Fixes issues like:
        - "2005" -> "" (just a year)
        - "E X P E R I E N C E" -> "" (section header)
        - "English ⭐⭐⭐⭐" -> "" (language rating)
        - "Milan" -> "" (city name only)
        """
        if not title:
            return ""
        
        title = title.strip()
        
        # Clean leading pipe or separator
        title = re.sub(r'^[|\-–—]\s*', '', title).strip()
        
        # Reject if it's just a year
        if re.match(r'^\d{4}$', title):
            return ""
        
        # Reject if it's a date range
        if re.match(r'^\d{4}\s*[-–—]', title):
            return ""
        
        # Reject if it's just numbers/symbols
        if re.match(r'^[\d\s\-–—/]+$', title):
            return ""
        
        # Reject if it contains rating stars
        if '⭐' in title or '★' in title:
            return ""
        
        # Reject if it's a spaced-out header like "E X P E R I E N C E"
        if re.match(r'^[A-Z](\s+[A-Z]){3,}$', title):
            return ""
        
        # Reject common section headers
        section_headers = [
            'experience', 'education', 'skills', 'summary', 'profile',
            'languages', 'certifications', 'references', 'hobbies',
            'interests', 'projects', 'publications', 'awards'
        ]
        if title.lower().strip() in section_headers:
            return ""
        
        # Reject common certifications that are not job titles
        certifications = [
            'cbap', 'pmp', 'cpa', 'cfa', 'mba', 'phd', 'md', 'jd',
            'cissp', 'aws', 'azure', 'gcp', 'scrum', 'agile', 'itil'
        ]
        if title.lower().strip() in certifications:
            return ""
        
        # Reject if it's just a language name
        languages = ['english', 'spanish', 'french', 'german', 'italian', 
                     'portuguese', 'chinese', 'japanese', 'korean', 'arabic']
        if title.lower().strip() in languages:
            return ""
        
        # Reject if it's a city/country or "City, Country" pattern
        locations = ['milan', 'italy', 'london', 'berlin', 'paris', 'madrid',
                    'barcelona', 'new york', 'los angeles', 'san francisco',
                    'singapore', 'tokyo', 'sydney', 'dubai', 'stockholm',
                    'rome', 'amsterdam', 'munich', 'frankfurt', 'zurich']
        title_lower = title.lower().strip()
        if title_lower in locations:
            return ""
        # Reject "City, Country" pattern
        if re.match(r'^[A-Za-z]+,\s*[A-Za-z]+$', title):
            parts = title.split(',')
            if parts[0].strip().lower() in locations or parts[1].strip().lower() in locations:
                return ""
        
        # Reject if it's a rating like "9/10"
        if re.match(r'^\d+/\d+$', title):
            return ""
        
        # Reject very short titles (likely fragments)
        if len(title) < 3:
            return ""
        
        # Reject if it starts with common description words (truncated descriptions)
        description_starters = [
            'to ', 'and ', 'with ', 'for ', 'the ', 'a ', 'an ',
            'across ', 'in ', 'at ', 'by ', 'from ', 'of '
        ]
        for starter in description_starters:
            if title.lower().startswith(starter):
                return ""
        
        return title
    
    def _validate_company_name(self, company: str) -> str:
        """
        Validate and clean company name.
        Returns empty string if company is invalid.
        
        Fixes issues like:
        - "2010 | Banking Innovations PLC" -> "Banking Innovations PLC"
        - "Italy" -> "" (just a country)
        - "S K I L L S" -> "" (spaced header)
        """
        if not company:
            return ""
        
        company = company.strip()
        
        # Remove leading pipe or separator
        company = re.sub(r'^[|\-–—]\s*', '', company).strip()
        
        # Remove leading year and separator patterns
        company = re.sub(r'^\d{4}\s*[|\-–—]\s*', '', company).strip()
        
        # Reject if it's just a year
        if re.match(r'^\d{4}$', company):
            return ""
        
        # Reject if it's a date range
        if re.match(r'^\d{4}\s*[-–—]', company):
            return ""
        
        # Reject if it's a spaced-out header
        if re.match(r'^[A-Z](\s+[A-Z]){3,}$', company):
            return ""
        
        # Reject common section headers
        section_headers = [
            'experience', 'education', 'skills', 'summary', 'profile',
            'languages', 'certifications', 'references'
        ]
        if company.lower().strip() in section_headers:
            return ""
        
        # Reject if it looks like a job title, not a company
        job_title_words = [
            'junior', 'senior', 'lead', 'manager', 'director', 'analyst',
            'engineer', 'developer', 'consultant', 'specialist', 'coordinator',
            'intern', 'trainee', 'associate', 'assistant', 'executive'
        ]
        company_lower = company.lower().strip()
        for title_word in job_title_words:
            if company_lower == title_word or company_lower.startswith(title_word + ' '):
                return ""
        
        # Reject if it's just a country name (likely location, not company)
        countries = ['italy', 'germany', 'france', 'spain', 'uk', 'usa',
                    'united states', 'united kingdom', 'canada', 'australia',
                    'japan', 'china', 'india', 'brazil', 'sweden', 'norway']
        if company_lower in countries:
            return ""
        
        # Reject very short names
        if len(company) < 2:
            return ""
        
        # Reject if it starts with description words
        description_starters = [
            'to ', 'and ', 'with ', 'for ', 'the ', 'a ', 'an ',
            'ensuring ', 'delivering ', 'managing ', 'leading '
        ]
        for starter in description_starters:
            if company_lower.startswith(starter):
                return ""
        
        return company
    
    def _split_experience_into_jobs(self, experience_text: str) -> List[str]:
        """Split experience section into individual job entries."""
        jobs = []
        lines = experience_text.split('\n')
        current_job = []
        
        for i, line in enumerate(lines):
            # Skip section header
            if i == 0 and re.match(self.SECTION_PATTERNS['experience'], line.strip()):
                continue
            
            # New job indicators
            is_job_start = False
            
            # Line with year range typically starts a new job
            if re.search(r'\b(19|20)\d{2}\s*[-–—]\s*(?:(19|20)\d{2}|Present|Actual|Presente)', line, re.IGNORECASE):
                is_job_start = True
            # Or a line that looks like a job title (starts with capital, contains "at" or company indicators)
            elif re.match(r'^[A-Z][A-Za-z\s]+(?:at|@|\||–|-|,)\s*[A-Z]', line.strip()):
                is_job_start = True
            # Or an empty line followed by a capitalized line could indicate new section
            elif line.strip() == '' and current_job:
                # Check if next non-empty line looks like a title
                for next_line in lines[i+1:i+3]:
                    if next_line.strip() and re.match(r'^[A-Z]', next_line.strip()):
                        is_job_start = True
                        break
            
            if is_job_start and current_job and len('\n'.join(current_job).strip()) > 50:
                job_text = '\n'.join(current_job).strip()
                if job_text:
                    jobs.append(job_text)
                current_job = []
            
            current_job.append(line)
        
        # Don't forget last job
        if current_job:
            job_text = '\n'.join(current_job).strip()
            if job_text and len(job_text) > 30:
                jobs.append(job_text)
        
        return jobs
    
    def _extract_positions(self, text: str) -> List[JobPosition]:
        """Extract all job positions from CV text."""
        positions = []
        
        # Find experience section
        experience_match = None
        for pattern in [self.SECTION_PATTERNS['experience']]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                experience_match = match
                break
        
        if not experience_match:
            # Try to find positions without explicit section header
            logger.debug("No experience section header found, scanning full text")
            experience_text = text
        else:
            # Find end of experience section
            experience_start = experience_match.start()
            experience_end = len(text)
            
            for section_name, pattern in self.SECTION_PATTERNS.items():
                if section_name == 'experience':
                    continue
                match = re.search(pattern, text[experience_start + 50:], re.IGNORECASE)
                if match:
                    potential_end = experience_start + 50 + match.start()
                    if potential_end < experience_end:
                        experience_end = potential_end
            
            experience_text = text[experience_start:experience_end]
        
        # Split into individual jobs
        job_texts = self._split_experience_into_jobs(experience_text)
        
        for job_text in job_texts:
            # Skip if this looks like education, not work experience
            if self._is_education_entry(job_text):
                logger.debug(f"Skipping education entry: {job_text[:50]}...")
                continue
            
            start_year, end_year, is_current = self._extract_years_from_text(job_text)
            title, company = self._extract_job_title_and_company(job_text)
            
            # Skip entries with invalid titles/companies
            if title == "Unknown Role" and company == "Unknown Company":
                continue
            
            # Only add if we found meaningful data
            if (title and title != "Unknown Role") or (company and company != "Unknown Company"):
                if len(job_text) > 30:
                    position = JobPosition(
                        title=title,
                        company=company,
                        start_year=start_year,
                        end_year=end_year,
                        is_current=is_current,
                        raw_text=job_text
                    )
                    position.duration_years = position.calculate_duration()
                    positions.append(position)
        
        # Sort by start year (most recent first)
        positions.sort(key=lambda p: (p.start_year or 0), reverse=True)
        
        # If no position is marked as current, mark the most recent one
        if positions and not any(p.is_current for p in positions):
            for p in positions:
                if p.end_year is None or p.end_year >= self.current_year - 1:
                    p.is_current = True
                    break
            # If still none, just mark the first (most recent by start year)
            if not any(p.is_current for p in positions):
                positions[0].is_current = True
        
        return positions
    
    def _is_education_entry(self, text: str) -> bool:
        """
        Determine if a text block is an education entry rather than work experience.
        
        This helps prevent education being confused with job positions.
        """
        text_lower = text.lower()
        
        # Strong education indicators
        education_keywords = [
            'bachelor', 'master', 'phd', 'ph.d', 'doctorate', 'degree',
            'university', 'college', 'institute', 'school of',
            'bsc', 'msc', 'mba', 'b.s.', 'm.s.', 'b.a.', 'm.a.',
            'licenciatura', 'grado', 'maestría', 'doctorado',
            'thesis', 'dissertation', 'gpa', 'cum laude', 'magna cum laude',
            'dean\'s list', 'honors', 'graduated', 'graduation',
            'major in', 'minor in', 'studied', 'coursework'
        ]
        
        # Count education keywords
        education_score = sum(1 for kw in education_keywords if kw in text_lower)
        
        # Work experience indicators
        work_keywords = [
            'managed', 'developed', 'led', 'created', 'implemented',
            'responsible for', 'collaborated', 'delivered', 'achieved',
            'increased', 'decreased', 'improved', 'reduced', 'launched',
            'team of', 'reported to', 'clients', 'stakeholders',
            'revenue', 'budget', 'kpi', 'metrics'
        ]
        
        # Count work keywords
        work_score = sum(1 for kw in work_keywords if kw in text_lower)
        
        # Check for degree patterns
        degree_pattern = re.search(
            r'\b(bachelor|master|phd|doctorate|bsc|msc|mba|b\.?s\.?|m\.?s\.?)\b.*\b(of|in|degree)\b',
            text_lower
        )
        if degree_pattern:
            education_score += 3
        
        # Check for university patterns
        university_pattern = re.search(
            r'\b(university|college|institute|school)\s+(of\s+)?[a-z]+',
            text_lower
        )
        if university_pattern:
            education_score += 2
        
        # If education score significantly higher, it's education
        return education_score > work_score and education_score >= 2
    
    def _extract_skills(self, text: str) -> List[str]:
        """
        Extract skills from CV text.
        
        PHASE 2.2 FIX: Validates skills to exclude:
        - Spaced-letter strings like "E D U C A T I O N"
        - Education items (degrees, universities)
        - Company names
        - Job titles
        """
        skills = []
        
        # Find skills section
        match = re.search(self.SECTION_PATTERNS['skills'], text, re.IGNORECASE)
        if not match:
            return skills
        
        skills_start = match.end()
        skills_end = len(text)
        
        for section_name, pattern in self.SECTION_PATTERNS.items():
            if section_name == 'skills':
                continue
            section_match = re.search(pattern, text[skills_start:], re.IGNORECASE)
            if section_match:
                potential_end = skills_start + section_match.start()
                if potential_end < skills_end:
                    skills_end = potential_end
        
        skills_text = text[skills_start:skills_end]
        
        # Extract skills
        skills_text = re.sub(r'[•\-\*\|]', ',', skills_text)
        skill_candidates = re.split(r'[,\n;]', skills_text)
        
        for skill in skill_candidates:
            skill = skill.strip()
            # Basic length check
            if len(skill) < 2 or len(skill) > 50:
                continue
            # Skip section headers
            if re.match(self.SECTION_PATTERNS['skills'], skill, re.IGNORECASE):
                continue
            # PHASE 2.2: Validate skill
            if self._is_valid_skill(skill):
                skills.append(skill)
        
        return skills[:30]
    
    def _is_valid_skill(self, skill: str) -> bool:
        """
        PHASE 2.2 FIX: Validate that a string is actually a skill.
        
        Rejects:
        - Spaced-letter strings: "E D U C A T I O N"
        - Education items: "Master of Arts in", "University of"
        - Company names: "Local Fashion House"
        - Job titles: "Analysis Styling Intern"
        - Section headers: "SKILLS", "EXPERIENCE"
        """
        if not skill:
            return False
        
        # 1. Reject spaced-letter strings (e.g., "E D U C A T I O N")
        if re.match(r'^[A-Z](\s+[A-Z])+$', skill):
            logger.debug(f"[SKILLS] Rejecting spaced-letters: '{skill}'")
            return False
        
        # Also reject if more than 30% of chars are spaces (indicator of spaced text)
        if skill.count(' ') > len(skill) * 0.3 and len(skill) > 10:
            words = skill.split()
            if all(len(w) <= 2 for w in words):
                logger.debug(f"[SKILLS] Rejecting high-space ratio: '{skill}'")
                return False
        
        # 2. Reject education items
        education_patterns = [
            r'\b(master|bachelor|phd|doctorate|degree|university|college)\b',
            r'\b(mba|msc|bsc|ba|ma|bs|ms)\b',
            r'\b(graduated|graduation|diploma|certificate of)\b',
            r'^master of', r'^bachelor of', r'^doctor of',
        ]
        skill_lower = skill.lower()
        for pattern in education_patterns:
            if re.search(pattern, skill_lower):
                logger.debug(f"[SKILLS] Rejecting education item: '{skill}'")
                return False
        
        # 3. Reject company name patterns
        company_patterns = [
            r'\b(inc|llc|ltd|corp|gmbh|plc|company|group|holdings)\b',
            r'\b(fashion house|consulting|solutions|services|agency)\b',
            r'^\w+\s+(early|late|\d{4})',  # "Company Name (Early 2020)"
        ]
        for pattern in company_patterns:
            if re.search(pattern, skill_lower):
                logger.debug(f"[SKILLS] Rejecting company pattern: '{skill}'")
                return False
        
        # 4. Reject job title patterns
        job_title_patterns = [
            r'\b(intern|trainee|assistant|coordinator|manager|director)\b',
            r'\b(analyst|specialist|consultant|engineer|developer)\b',
            r'^(senior|junior|lead|chief|head)\s+',
            r'&\s*analysis',  # "& Analysis Styling Intern"
        ]
        for pattern in job_title_patterns:
            if re.search(pattern, skill_lower):
                # Exception: keep if it's a technical skill with these words
                technical_exceptions = ['data analyst', 'business analyst', 'systems analyst']
                if skill_lower not in technical_exceptions:
                    logger.debug(f"[SKILLS] Rejecting job title pattern: '{skill}'")
                    return False
        
        # 5. Reject section headers
        section_headers = [
            'skills', 'experience', 'education', 'summary', 'profile',
            'languages', 'certifications', 'references', 'hobbies',
            'interests', 'projects', 'contact', 'objective'
        ]
        if skill_lower.strip() in section_headers:
            return False
        
        # 6. Reject if starts with common non-skill words
        non_skill_starters = [
            'local ', 'the ', 'a ', 'an ', 'my ', 'our ', 'their ',
            'responsible for', 'worked on', 'managed', 'developed',
        ]
        for starter in non_skill_starters:
            if skill_lower.startswith(starter):
                logger.debug(f"[SKILLS] Rejecting non-skill starter: '{skill}'")
                return False
        
        # 7. Reject if it's just numbers or very short
        if re.match(r'^[\d\s\-/\.]+$', skill):
            return False
        if len(skill.replace(' ', '')) < 2:
            return False
        
        return True
    
    def _calculate_total_experience(self, positions: List[JobPosition]) -> float:
        """
        Calculate total years of experience from all positions.
        
        PHASE 2.5 FIX: Better handling when dates are missing.
        Uses multiple strategies to estimate experience.
        """
        if not positions:
            return 0.0
        
        # Strategy 1: From earliest start to latest end (accounts for career span)
        start_years = [p.start_year for p in positions if p.start_year]
        end_years = [p.end_year or self.current_year for p in positions if p.start_year]
        
        if start_years and end_years:
            total_from_range = max(end_years) - min(start_years)
            if 0 < total_from_range <= 50:
                logger.debug(f"[EXPERIENCE] Calculated from date range: {total_from_range} years")
                return float(total_from_range)
        
        # Strategy 2: Sum individual durations
        total_from_sum = sum(p.duration_years for p in positions)
        if 0 < total_from_sum <= 50:
            logger.debug(f"[EXPERIENCE] Calculated from sum: {total_from_sum} years")
            return total_from_sum
        
        # PHASE 2.5 FIX: Strategy 3 - Estimate from position count when dates unavailable
        # If we have positions but couldn't calculate years, estimate based on typical tenure
        positions_without_dates = [p for p in positions if not p.start_year]
        positions_with_dates = [p for p in positions if p.start_year]
        
        if positions_without_dates:
            # Average tenure assumption: 2.5 years per position
            estimated_years = len(positions_without_dates) * 2.5
            
            # Add any calculated years from positions with dates
            calculated_years = sum(p.duration_years for p in positions_with_dates)
            
            total_estimated = estimated_years + calculated_years
            
            if total_estimated > 0:
                logger.info(
                    f"[EXPERIENCE] Estimated {total_estimated:.1f} years from "
                    f"{len(positions_without_dates)} undated + {len(positions_with_dates)} dated positions"
                )
                return min(total_estimated, 40.0)  # Cap at 40 years
        
        # PHASE 2.5 FIX: Strategy 4 - If we have positions, don't return 0
        # Having positions means SOME experience
        if len(positions) > 0:
            # Minimum estimate: 1 year per position, capped reasonably
            minimum_estimate = min(len(positions) * 1.5, 20.0)
            logger.warning(
                f"[EXPERIENCE] No dates available, using minimum estimate: "
                f"{minimum_estimate:.1f} years for {len(positions)} positions"
            )
            return minimum_estimate
        
        return 0.0
    
    def extract_structured_data(self, text: str, filename: str) -> CVStructuredData:
        """Extract all structured data from CV text."""
        parsed = self._parse_filename(filename)
        candidate_name = parsed["candidate_name"]
        
        positions = self._extract_positions(text)
        
        # Determine current role - validate it's not garbage
        current_role = None
        current_company = None
        for pos in positions:
            if pos.is_current:
                # Validate title is not "Unknown Role" or garbage
                if pos.title and pos.title != "Unknown Role":
                    validated_title = self._validate_job_title(pos.title)
                    if validated_title:
                        current_role = validated_title
                # Validate company is not "Unknown Company" or garbage
                if pos.company and pos.company != "Unknown Company":
                    validated_company = self._validate_company_name(pos.company)
                    if validated_company:
                        current_company = validated_company
                break
        
        # Fallback to first position with valid data
        if (not current_role or not current_company) and positions:
            for pos in positions:
                if not current_role and pos.title and pos.title != "Unknown Role":
                    validated_title = self._validate_job_title(pos.title)
                    if validated_title:
                        current_role = validated_title
                if not current_company and pos.company and pos.company != "Unknown Company":
                    validated_company = self._validate_company_name(pos.company)
                    if validated_company:
                        current_company = validated_company
                if current_role and current_company:
                    break
        
        total_experience = self._calculate_total_experience(positions)
        skills = self._extract_skills(text)
        
        return CVStructuredData(
            candidate_name=candidate_name,
            current_role=current_role,
            current_company=current_company,
            total_experience_years=total_experience,
            positions=positions,
            skills=skills,
            raw_text=text
        )
    
    def chunk_cv(
        self,
        text: str,
        cv_id: str,
        filename: str
    ) -> List[Dict[str, Any]]:
        """
        Create intelligent chunks from CV with rich metadata.
        
        ================================================================
        METADATA FLOW DOCUMENTATION (READ BEFORE MODIFYING)
        ================================================================
        
        This is the ENTRY POINT for all CV metadata. Metadata added here
        flows through the entire pipeline:
        
        1. SmartChunkingService.chunk_cv() ← YOU ARE HERE
           ↓ Creates chunks with metadata dict
        2. rag_service_v5.py:index_documents()
           ↓ Passes to vector store
        3. vector_store.add_documents()
           ↓ Stores in ChromaDB/local store
        4. vector_store.search()
           ↓ Returns SearchResult with full metadata
        5. rag_service_v5.py:_step_fusion_retrieval()
           ↓ Preserves ALL metadata (see CRITICAL comment there)
        6. templates.py:_extract_enriched_metadata()
           ↓ Extracts specific fields for LLM prompts
        7. LLM receives enriched context
        
        TO ADD A NEW METADATA FIELD:
        ─────────────────────────────
        1. Calculate the value in this method (like job_hopping_score below)
        2. Add it to the "metadata" dict of EACH chunk type below
        3. In templates.py:_extract_enriched_metadata(), extract and format it
        4. Test by checking logs: [ENRICHED_METADATA] should show your field
        
        CURRENT METADATA FIELDS:
        ─────────────────────────
        - total_experience_years: Total career experience in years
        - job_hopping_score: Career stability (0-1, higher = less stable)
        - avg_tenure_years: Average years per position
        - position_count: Number of positions held
        - employment_gaps_count: Number of gaps > 1 year
        - current_role: Current job title
        - current_company: Current employer
        - section_type: Type of CV section (summary, experience, skills, etc.)
        - candidate_name: Candidate's name
        
        ================================================================
        
        Creates:
        1. A "summary" chunk with pre-calculated totals
        2. Individual chunks for each job position
        3. Skills chunk
        4. Full CV chunk for comprehensive queries
        """
        structured = self.extract_structured_data(text, filename)
        chunks = []
        chunk_index = 0
        
        # ================================================================
        # ENRICHED METADATA CALCULATIONS
        # Add new calculations here, then add to metadata dicts below
        # ================================================================
        job_hopping_score, avg_tenure_years = self._calculate_job_hopping_metrics(structured.positions)
        employment_gaps_count = self._detect_employment_gaps(structured.positions)
        
        # Phase 2: Enhanced metadata extraction
        languages, language_primary = self._extract_languages(text)
        education = self._extract_education(text)
        certifications = self._extract_certifications(text)
        location = self._extract_location(text)
        urls = self._extract_urls(text)
        hobbies = self._extract_hobbies(text)
        seniority_level = self._infer_seniority_level(
            structured.total_experience_years,
            structured.current_role
        )
        skills_str = ",".join(structured.skills) if structured.skills else ""
        
        # ================================================================
        # FASE 1: Boolean flags for direct metadata queries
        # These enable queries like "who speaks French", "has AWS cert"
        # ================================================================
        text_lower = text.lower()
        languages_lower = languages.lower() if languages else ""
        certs_lower = certifications.lower() if certifications else ""
        
        # Language flags
        speaks_english = "english" in languages_lower
        speaks_french = "french" in languages_lower
        speaks_spanish = "spanish" in languages_lower
        speaks_german = "german" in languages_lower
        speaks_chinese = "chinese" in languages_lower or "mandarin" in languages_lower
        
        # Education flags
        has_mba = "mba" in text_lower or "master of business" in text_lower
        has_phd = "phd" in text_lower or "ph.d" in text_lower or "doctorate" in text_lower
        
        # Certification flags
        has_aws_cert = "aws" in certs_lower or "amazon web services" in text_lower
        has_azure_cert = "azure" in certs_lower or "az-" in text_lower
        has_gcp_cert = "gcp" in certs_lower or "google cloud" in text_lower
        has_pmp = "pmp" in certs_lower or "project management professional" in text_lower
        has_cbap = "cbap" in certs_lower or "business analysis professional" in text_lower
        has_scrum = "scrum" in certs_lower or "csm" in certs_lower or "psm" in certs_lower
        
        # ============================================================
        # CHUNK 0: SUMMARY CHUNK (most important for quick lookups)
        # FASE 2: Use enriched content for better semantic search
        # ============================================================
        summary_content = self._build_enriched_summary_content(
            structured, languages, education, certifications, location
        )
        chunks.append({
            "id": f"{cv_id}_chunk_{chunk_index}",
            "cv_id": cv_id,
            "filename": filename,
            "chunk_index": chunk_index,
            "content": summary_content,
            "metadata": {
                "section_type": "summary",
                "candidate_name": structured.candidate_name,
                "current_role": structured.current_role or "",
                "current_company": structured.current_company or "",
                "total_experience_years": structured.total_experience_years,
                "is_summary": True,
                "position_count": len(structured.positions),
                # Enhanced metadata for red flags analysis
                "job_hopping_score": job_hopping_score,
                "avg_tenure_years": avg_tenure_years,
                "employment_gaps_count": employment_gaps_count,
                # Phase 2: New metadata fields
                "skills": skills_str,
                "seniority_level": seniority_level,
                "languages": languages,
                "language_primary": language_primary,
                "education_level": education["level"],
                "education_field": education["field"],
                "education_institution": education["institution"],
                "graduation_year": education["graduation_year"],
                "certifications": certifications,
                "location": location,
                "linkedin_url": urls["linkedin"],
                "github_url": urls["github"],
                "portfolio_url": urls["portfolio"],
                "hobbies": hobbies,
                # FASE 1: Boolean flags for direct queries
                "speaks_english": speaks_english,
                "speaks_french": speaks_french,
                "speaks_spanish": speaks_spanish,
                "speaks_german": speaks_german,
                "speaks_chinese": speaks_chinese,
                "has_mba": has_mba,
                "has_phd": has_phd,
                "has_aws_cert": has_aws_cert,
                "has_azure_cert": has_azure_cert,
                "has_gcp_cert": has_gcp_cert,
                "has_pmp": has_pmp,
                "has_cbap": has_cbap,
                "has_scrum": has_scrum,
            }
        })
        chunk_index += 1
        
        # ============================================================
        # CHUNKS 1-N: INDIVIDUAL JOB POSITIONS
        # ============================================================
        for i, position in enumerate(structured.positions):
            position_content = self._build_position_content(position, i + 1, len(structured.positions))
            chunks.append({
                "id": f"{cv_id}_chunk_{chunk_index}",
                "cv_id": cv_id,
                "filename": filename,
                "chunk_index": chunk_index,
                "content": position_content,
                "metadata": {
                    "section_type": "experience",
                    "candidate_name": structured.candidate_name,
                    "job_title": position.title,
                    "company": position.company,
                    "start_year": position.start_year,
                    "end_year": position.end_year,
                    "is_current": position.is_current,
                    "duration_years": position.duration_years,
                    "position_order": i + 1,
                    # Enhanced metadata for red flags analysis
                    "total_experience_years": structured.total_experience_years,
                    "job_hopping_score": job_hopping_score,
                    "avg_tenure_years": avg_tenure_years,
                    "employment_gaps_count": employment_gaps_count,
                    "position_count": len(structured.positions),
                    # Phase 2: New metadata fields
                    "skills": skills_str,
                    "seniority_level": seniority_level,
                    "certifications": certifications,
                    "location": location,
                }
            })
            chunk_index += 1
        
        # ============================================================
        # SKILLS CHUNK
        # ============================================================
        if structured.skills:
            skills_content = f"SKILLS AND COMPETENCIES for {structured.candidate_name}:\n\n"
            skills_content += ", ".join(structured.skills)
            chunks.append({
                "id": f"{cv_id}_chunk_{chunk_index}",
                "cv_id": cv_id,
                "filename": filename,
                "chunk_index": chunk_index,
                "content": skills_content,
                "metadata": {
                    "section_type": "skills",
                    "candidate_name": structured.candidate_name,
                    "skill_count": len(structured.skills),
                    # Enhanced metadata for red flags analysis
                    "total_experience_years": structured.total_experience_years,
                    "job_hopping_score": job_hopping_score,
                    "avg_tenure_years": avg_tenure_years,
                    "employment_gaps_count": employment_gaps_count,
                    "position_count": len(structured.positions),
                    # Phase 2: New metadata fields
                    "skills": skills_str,
                    "seniority_level": seniority_level,
                    "certifications": certifications,
                }
            })
            chunk_index += 1
        
        # ============================================================
        # FULL CV CHUNK (for comprehensive queries)
        # ============================================================
        full_cv_content = f"COMPLETE CV for {structured.candidate_name}\n\n"
        full_cv_content += f"CURRENT ROLE: {structured.current_role or 'Not specified'}\n"
        full_cv_content += f"COMPANY: {structured.current_company or 'Not specified'}\n"
        full_cv_content += f"TOTAL EXPERIENCE: {structured.total_experience_years:.0f} years\n\n"
        full_cv_content += "--- FULL CV TEXT ---\n\n"
        full_cv_content += text[:4000]  # First 4000 chars
        
        chunks.append({
            "id": f"{cv_id}_chunk_{chunk_index}",
            "cv_id": cv_id,
            "filename": filename,
            "chunk_index": chunk_index,
            "content": full_cv_content,
            "metadata": {
                "section_type": "full_cv",
                "candidate_name": structured.candidate_name,
                "current_role": structured.current_role or "",
                "current_company": structured.current_company or "",
                "total_experience_years": structured.total_experience_years,
                # Enhanced metadata for red flags analysis
                "job_hopping_score": job_hopping_score,
                "avg_tenure_years": avg_tenure_years,
                "employment_gaps_count": employment_gaps_count,
                "position_count": len(structured.positions),
                # Phase 2: New metadata fields
                "skills": skills_str,
                "seniority_level": seniority_level,
                "languages": languages,
                "education_level": education["level"],
                "certifications": certifications,
                "location": location,
                "linkedin_url": urls["linkedin"],
                "github_url": urls["github"],
            }
        })
        
        logger.info(
            f"[SMART_CHUNKING] {structured.candidate_name}: "
            f"current='{structured.current_role}' @ '{structured.current_company}', "
            f"experience={structured.total_experience_years:.0f}y, "
            f"positions={len(structured.positions)}, "
            f"chunks={len(chunks)}"
        )
        
        return chunks
    
    def _build_summary_content(self, data: CVStructuredData) -> str:
        """
        Build summary chunk content with key facts.
        
        FASE 2: Enhanced with structured metadata for better semantic search.
        The content here gets embedded, so including structured info helps
        queries like "who speaks French" or "has AWS certification" match better.
        """
        lines = [
            f"===== CANDIDATE PROFILE: {data.candidate_name} =====",
            "",
            f"CURRENT POSITION: {data.current_role or 'Not specified'}",
            f"CURRENT COMPANY: {data.current_company or 'Not specified'}",
            f"TOTAL YEARS OF EXPERIENCE: {data.total_experience_years:.0f} years",
            f"NUMBER OF POSITIONS HELD: {len(data.positions)}",
            "",
            "CAREER HISTORY (chronological, most recent first):",
        ]
        
        for i, pos in enumerate(data.positions, 1):
            year_str = ""
            if pos.start_year:
                end = "Present" if pos.is_current else str(pos.end_year or "?")
                year_str = f" ({pos.start_year}-{end}, {pos.duration_years:.0f}y)"
            current_marker = " [CURRENT]" if pos.is_current else ""
            lines.append(f"  {i}. {pos.title} at {pos.company}{year_str}{current_marker}")
        
        if data.skills:
            lines.append("")
            lines.append(f"KEY SKILLS: {', '.join(data.skills[:15])}")
        
        return "\n".join(lines)
    
    def _build_enriched_summary_content(
        self, 
        data: CVStructuredData, 
        languages: str,
        education: dict,
        certifications: str,
        location: str
    ) -> str:
        """
        FASE 2: Build enriched summary content for better semantic search.
        
        This content will be embedded and used for vector search.
        Including structured metadata helps queries match correctly:
        - "who speaks French" → matches "LANGUAGES: French (Intermediate)"
        - "AWS certified" → matches "CERTIFICATIONS: AWS Solutions Architect"
        - "MBA candidates" → matches "EDUCATION: MBA, Master of Business Administration"
        """
        lines = [
            f"===== CANDIDATE PROFILE: {data.candidate_name} =====",
            "",
            "--- QUICK FACTS ---",
            f"CURRENT ROLE: {data.current_role or 'Not specified'}",
            f"CURRENT COMPANY: {data.current_company or 'Not specified'}",
            f"TOTAL EXPERIENCE: {data.total_experience_years:.0f} years",
            f"POSITIONS HELD: {len(data.positions)}",
        ]
        
        # Location
        if location:
            lines.append(f"LOCATION: {location}")
        
        # Languages (critical for queries like "who speaks French")
        if languages:
            lines.append(f"LANGUAGES: {languages}")
        
        # Education (critical for queries like "MBA candidates", "PhD holders")
        if education.get("level"):
            edu_str = education["level"]
            if education.get("field"):
                edu_str += f" in {education['field']}"
            if education.get("institution"):
                edu_str += f" from {education['institution']}"
            if education.get("graduation_year"):
                edu_str += f" ({education['graduation_year']})"
            lines.append(f"EDUCATION: {edu_str}")
        
        # Certifications (critical for queries like "AWS certified", "PMP holders")
        if certifications:
            lines.append(f"CERTIFICATIONS: {certifications}")
        
        # Skills
        if data.skills:
            lines.append(f"SKILLS: {', '.join(data.skills[:20])}")
        
        lines.append("")
        lines.append("--- CAREER HISTORY ---")
        
        for i, pos in enumerate(data.positions, 1):
            year_str = ""
            if pos.start_year:
                end = "Present" if pos.is_current else str(pos.end_year or "?")
                year_str = f" ({pos.start_year}-{end}, {pos.duration_years:.0f}y)"
            current_marker = " [CURRENT]" if pos.is_current else ""
            lines.append(f"  {i}. {pos.title} at {pos.company}{year_str}{current_marker}")
        
        return "\n".join(lines)
    
    def _build_position_content(self, pos: JobPosition, order: int, total: int) -> str:
        """Build content for a single position chunk."""
        year_str = "Unknown dates"
        if pos.start_year:
            end = "Present" if pos.is_current else str(pos.end_year or "?")
            year_str = f"{pos.start_year} - {end}"
        
        current_marker = " === CURRENT POSITION ===" if pos.is_current else ""
        
        lines = [
            f"JOB POSITION {order} of {total}{current_marker}",
            "",
            f"TITLE: {pos.title}",
            f"COMPANY: {pos.company}",
            f"PERIOD: {year_str}",
            f"DURATION: {pos.duration_years:.0f} years",
            "",
            "JOB DESCRIPTION AND RESPONSIBILITIES:",
            "",
            pos.raw_text[:1500] if pos.raw_text else "No description available"
        ]
        
        return "\n".join(lines)
    
    def _calculate_job_hopping_metrics(self, positions: List[JobPosition]) -> Tuple[float, float]:
        """Calculate job hopping score and average tenure."""
        if not positions:
            return 0.0, 0.0
        
        total_duration = sum(pos.duration_years for pos in positions)
        num_positions = len(positions)
        
        if total_duration > 0:
            avg_tenure = total_duration / num_positions
            # Job hopping score: higher = more frequent changes
            job_hopping_score = min((num_positions - 1) / total_duration, 1.0)
        else:
            avg_tenure = 0.0
            job_hopping_score = 0.0
        
        return job_hopping_score, avg_tenure
    
    def _detect_employment_gaps(self, positions: List[JobPosition]) -> int:
        """Count employment gaps > 1 year between positions."""
        if len(positions) < 2:
            return 0
        
        # Sort positions by start year
        sorted_positions = sorted(
            [p for p in positions if p.start_year and p.end_year],
            key=lambda p: p.start_year
        )
        
        gaps = 0
        for i in range(len(sorted_positions) - 1):
            current_end = sorted_positions[i].end_year
            next_start = sorted_positions[i + 1].start_year
            
            if current_end and next_start:
                gap_years = next_start - current_end
                if gap_years > 1:
                    gaps += 1
        
        return gaps
    
    # ================================================================
    # ENHANCED METADATA EXTRACTION (Phase 2)
    # ================================================================
    
    def _extract_languages(self, text: str) -> Tuple[str, str]:
        """
        Extract languages and primary language from CV.
        Returns: (comma-separated languages, primary language)
        """
        languages = []
        
        # Language patterns
        language_names = [
            'English', 'Spanish', 'French', 'German', 'Chinese', 'Mandarin',
            'Japanese', 'Portuguese', 'Italian', 'Russian', 'Arabic', 'Hindi',
            'Korean', 'Dutch', 'Swedish', 'Polish', 'Turkish', 'Vietnamese',
            'Thai', 'Indonesian', 'Malay', 'Hebrew', 'Greek', 'Czech',
            'Inglés', 'Español', 'Francés', 'Alemán', 'Italiano', 'Portugués'
        ]
        
        # Find languages section or scan full text
        lang_section = re.search(
            r'(?:languages?|idiomas?)[:\s]*([\s\S]{0,300}?)(?=\n\n|\n[A-Z]|$)',
            text, re.IGNORECASE
        )
        
        search_text = lang_section.group(1) if lang_section else text
        
        for lang in language_names:
            if re.search(rf'\b{lang}\b', search_text, re.IGNORECASE):
                languages.append(lang)
        
        # Determine primary (usually first or marked as native)
        primary = languages[0] if languages else ""
        for lang in languages:
            if re.search(rf'{lang}\s*[\(\[]?\s*(?:native|nativo|mother|materna)', 
                        search_text, re.IGNORECASE):
                primary = lang
                break
        
        return ",".join(languages[:5]), primary
    
    def _extract_education(self, text: str) -> Dict[str, str]:
        """Extract education details from CV."""
        education = {
            "level": "",
            "field": "",
            "institution": "",
            "graduation_year": ""
        }
        
        # Find education section
        edu_match = re.search(self.SECTION_PATTERNS['education'], text, re.IGNORECASE)
        if not edu_match:
            return education
        
        edu_start = edu_match.start()
        edu_end = len(text)
        
        for name, pattern in self.SECTION_PATTERNS.items():
            if name == 'education':
                continue
            match = re.search(pattern, text[edu_start + 50:], re.IGNORECASE)
            if match:
                potential_end = edu_start + 50 + match.start()
                if potential_end < edu_end:
                    edu_end = potential_end
        
        edu_text = text[edu_start:edu_end]
        
        # Extract degree level
        degree_patterns = [
            (r'\b(Ph\.?D|Doctorate|Doctorado)\b', 'PhD'),
            (r'\b(Master|Masters|MSc|MBA|M\.S\.|Maestría)\b', 'Master'),
            (r'\b(Bachelor|BSc|B\.S\.|BA|B\.A\.|Licenciatura|Grado)\b', 'Bachelor'),
            (r'\b(Associate|Técnico)\b', 'Associate'),
        ]
        
        for pattern, level in degree_patterns:
            if re.search(pattern, edu_text, re.IGNORECASE):
                education["level"] = level
                break
        
        # Extract field of study
        field_patterns = [
            r'(?:in|of|en)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})',
            r'(?:degree|grado)\s+(?:in|en)\s+([^\n,]+)',
        ]
        
        for pattern in field_patterns:
            match = re.search(pattern, edu_text)
            if match:
                education["field"] = match.group(1).strip()[:50]
                break
        
        # Extract institution
        uni_patterns = [
            r'(University\s+of\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'([A-Z][a-z]+\s+University)',
            r'(Universidad\s+[A-Za-z\s]+)',
            r'(MIT|Stanford|Harvard|Berkeley|Oxford|Cambridge)',
        ]
        
        for pattern in uni_patterns:
            match = re.search(pattern, edu_text)
            if match:
                education["institution"] = match.group(1).strip()[:60]
                break
        
        # Extract graduation year
        year_match = re.search(r'\b(19|20)\d{2}\b', edu_text)
        if year_match:
            education["graduation_year"] = year_match.group(0)
        
        return education
    
    def _extract_certifications(self, text: str) -> str:
        """Extract certifications from CV."""
        certs = []
        
        cert_patterns = [
            r'(AWS\s+(?:Solutions?\s+)?Architect|AWS\s+(?:Certified\s+)?[\w\s]+)',
            r'(Azure\s+[\w\s]+(?:Certified)?)',
            r'(GCP\s+[\w\s]+)',
            r'(PMP|Project\s+Management\s+Professional)',
            r'(CISSP|CISM|CEH)',
            r'(Scrum\s+Master|PSM|CSM)',
            r'(CCNA|CCNP|CCIE)',
            r'(CPA|CFA|FRM)',
            r'(Six\s+Sigma)',
            r'(Certified\s+[\w\s]+)',
        ]
        
        for pattern in cert_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            certs.extend(matches)
        
        # Clean and deduplicate
        clean_certs = []
        seen = set()
        for cert in certs:
            cert_clean = cert.strip()[:50]
            cert_lower = cert_clean.lower()
            if cert_lower not in seen and len(cert_clean) > 2:
                seen.add(cert_lower)
                clean_certs.append(cert_clean)
        
        return ",".join(clean_certs[:10])
    
    def _extract_location(self, text: str) -> str:
        """Extract location from CV."""
        # Common location patterns
        patterns = [
            r'(?:Location|Ubicación|City|Ciudad)[:\s]+([A-Z][a-z]+(?:[\s,]+[A-Z][a-z]+){0,2})',
            r'([A-Z][a-z]+,\s*(?:CA|NY|TX|FL|WA|MA|IL|PA|OH|GA|NC|MI|NJ|VA|AZ|CO|TN|MO|MD|WI|MN|IN|OR))',
            r'([A-Z][a-z]+,\s*(?:USA|UK|Spain|Germany|France|Italy|Canada|Australia))',
            r'(San\s+Francisco|New\s+York|Los\s+Angeles|Seattle|Boston|Chicago|Austin|Denver|Miami)',
            r'(London|Berlin|Paris|Madrid|Barcelona|Amsterdam|Dublin|Toronto|Sydney|Singapore)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()[:50]
        
        return ""
    
    def _extract_urls(self, text: str) -> Dict[str, str]:
        """Extract URLs (LinkedIn, GitHub, Portfolio) from CV."""
        urls = {
            "linkedin": "",
            "github": "",
            "portfolio": ""
        }
        
        # LinkedIn
        linkedin = re.search(r'((?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+)', text, re.IGNORECASE)
        if linkedin:
            urls["linkedin"] = linkedin.group(1)
        
        # GitHub
        github = re.search(r'((?:https?://)?(?:www\.)?github\.com/[\w\-]+)', text, re.IGNORECASE)
        if github:
            urls["github"] = github.group(1)
        
        # Portfolio (generic URL that's not LinkedIn/GitHub)
        portfolio = re.search(r'(?:portfolio|website|web)[:\s]*(https?://[^\s]+)', text, re.IGNORECASE)
        if portfolio:
            urls["portfolio"] = portfolio.group(1)[:100]
        
        return urls
    
    def _extract_hobbies(self, text: str) -> str:
        """Extract hobbies/interests from CV."""
        hobbies = []
        
        # Find hobbies section
        hobby_match = re.search(
            r'(?:hobbies?|interests?|activities|personal)[:\s]*([\s\S]{0,500}?)(?=\n\n|\n[A-Z][a-z]+:|\Z)',
            text, re.IGNORECASE
        )
        
        if hobby_match:
            hobby_text = hobby_match.group(1)
            # Split by common separators
            items = re.split(r'[,•\-\n;]', hobby_text)
            for item in items:
                item = item.strip()
                if 3 < len(item) < 30 and not re.match(r'^[A-Z][a-z]+:', item):
                    hobbies.append(item)
        
        return ",".join(hobbies[:8])
    
    def _infer_seniority_level(self, experience_years: float, current_role: str) -> str:
        """Infer seniority level from experience and role."""
        role_lower = (current_role or "").lower()
        
        # Check for explicit seniority in title
        if any(kw in role_lower for kw in ['principal', 'staff', 'distinguished', 'director']):
            return "principal"
        if any(kw in role_lower for kw in ['lead', 'head', 'manager', 'architect']):
            return "lead"
        if any(kw in role_lower for kw in ['senior', 'sr.', 'sr ']):
            return "senior"
        if any(kw in role_lower for kw in ['junior', 'jr.', 'jr ', 'entry', 'trainee', 'intern']):
            return "junior"
        
        # Infer from years of experience
        if experience_years >= 12:
            return "principal"
        elif experience_years >= 8:
            return "senior"
        elif experience_years >= 4:
            return "mid"
        elif experience_years >= 1:
            return "junior"
        else:
            return "entry"
