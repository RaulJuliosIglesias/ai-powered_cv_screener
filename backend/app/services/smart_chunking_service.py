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
    
    # Patterns for extracting dates
    YEAR_PATTERNS = [
        # "2020 - Present", "2020 - Presente", "2020 - Actual"
        r'(\d{4})\s*[-–—]\s*(Present|Presente|Actual|Current|Now|Oggi|Heute|Hoy)',
        # "2018 - 2023", "2018-2023"
        r'(\d{4})\s*[-–—]\s*(\d{4})',
        # "Jan 2020 - Dec 2023"
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*(\d{4})\s*[-–—]\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*(\d{4})',
        # "01/2020 - 12/2023"
        r'(?:\d{1,2}/)?(\d{4})\s*[-–—]\s*(?:\d{1,2}/)?(\d{4})',
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
            role = parts[-1].replace('-', ' ').replace('_', ' ')
            name_parts = parts[1:-1]
            candidate_name = ' '.join(name_parts)
            return {"file_id": file_id, "candidate_name": candidate_name, "role": role}
        elif len(parts) == 2:
            return {"file_id": parts[0], "candidate_name": parts[1], "role": ""}
        return {"file_id": "", "candidate_name": name, "role": ""}
    
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
            return title, company
        
        # Pattern: "Title | Company" or "Title - Company" or "Title, Company"
        for separator in ['|', '–', '—', '-', ',']:
            if separator in first_line:
                parts = first_line.split(separator, 1)
                if len(parts) == 2:
                    # Remove date patterns from parts
                    part1 = re.sub(r'\d{4}\s*[-–—]\s*(?:\d{4}|Present|Actual|Presente)', '', parts[0], flags=re.IGNORECASE).strip()
                    part2 = re.sub(r'\d{4}\s*[-–—]\s*(?:\d{4}|Present|Actual|Presente)', '', parts[1], flags=re.IGNORECASE).strip()
                    if part1 and part2 and len(part1) > 2 and len(part2) > 2:
                        title = part1
                        company = part2
                        return title, company
        
        # Fallback: first line is title
        title = re.sub(r'\d{4}\s*[-–—]\s*(?:\d{4}|Present|Actual|Presente)', '', first_line, flags=re.IGNORECASE).strip()
        
        # Look for company in subsequent lines
        for line in lines[1:4]:
            line = line.strip()
            if line and not re.match(r'^[\d\-/•\*]', line):
                if len(line) < 80 and not line.startswith(('•', '-', '*', '–')):
                    company = re.sub(r'\d{4}.*', '', line).strip()
                    break
        
        return title, company
    
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
            start_year, end_year, is_current = self._extract_years_from_text(job_text)
            title, company = self._extract_job_title_and_company(job_text)
            
            # Only add if we found meaningful data
            if (title or company) and len(job_text) > 30:
                position = JobPosition(
                    title=title or "Unknown Role",
                    company=company or "Unknown Company",
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
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from CV text."""
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
            if 2 < len(skill) < 50 and not re.match(self.SECTION_PATTERNS['skills'], skill, re.IGNORECASE):
                skills.append(skill)
        
        return skills[:30]
    
    def _calculate_total_experience(self, positions: List[JobPosition]) -> float:
        """Calculate total years of experience from all positions."""
        if not positions:
            return 0.0
        
        # From earliest start to latest end (accounts for career span)
        start_years = [p.start_year for p in positions if p.start_year]
        end_years = [p.end_year or self.current_year for p in positions if p.start_year]
        
        if start_years and end_years:
            total_from_range = max(end_years) - min(start_years)
            if 0 < total_from_range <= 50:
                return float(total_from_range)
        
        # Fallback: sum individual durations
        total_from_sum = sum(p.duration_years for p in positions)
        if 0 < total_from_sum <= 50:
            return total_from_sum
        
        return 0.0
    
    def extract_structured_data(self, text: str, filename: str) -> CVStructuredData:
        """Extract all structured data from CV text."""
        parsed = self._parse_filename(filename)
        candidate_name = parsed["candidate_name"]
        
        positions = self._extract_positions(text)
        
        # Determine current role
        current_role = None
        current_company = None
        for pos in positions:
            if pos.is_current:
                current_role = pos.title
                current_company = pos.company
                break
        
        # Fallback to first position
        if not current_role and positions:
            current_role = positions[0].title
            current_company = positions[0].company
        
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
        
        # ============================================================
        # CHUNK 0: SUMMARY CHUNK (most important for quick lookups)
        # ============================================================
        summary_content = self._build_summary_content(structured)
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
        """Build summary chunk content with key facts."""
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
