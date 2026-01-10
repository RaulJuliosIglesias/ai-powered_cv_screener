import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.services.pdf_service import PDFService, CVChunk, ExtractedCV
from app.utils.exceptions import PDFExtractionError


class TestPDFService:
    """Tests for PDF extraction service."""
    
    def setup_method(self):
        self.service = PDFService()
    
    def test_clean_text_removes_multiple_spaces(self):
        text = "Hello    world   test"
        result = self.service._clean_text(text)
        assert "    " not in result
        assert "Hello world test" in result
    
    def test_clean_text_removes_multiple_newlines(self):
        text = "Hello\n\n\n\n\nWorld"
        result = self.service._clean_text(text)
        assert "\n\n\n" not in result
    
    def test_extract_candidate_name_from_first_line(self):
        text = "John Smith\njohn@email.com\nSoftware Developer"
        result = self.service.extract_candidate_name(text)
        assert result == "John Smith"
    
    def test_extract_candidate_name_with_middle_name(self):
        text = "María García López\nContact: maria@email.com"
        result = self.service.extract_candidate_name(text)
        assert result == "María García López"
    
    def test_extract_skills_finds_common_skills(self):
        text = """
        Skills:
        - Python programming
        - JavaScript and React
        - Docker containerization
        - AWS cloud services
        """
        result = self.service.extract_skills(text)
        assert "Python" in result
        assert "JavaScript" in result
        assert "React" in result
        assert "Docker" in result
        assert "AWS" in result
    
    def test_identify_section_experience(self):
        text = "Professional Experience\nWorked at Company X"
        result = self.service._identify_section(text)
        assert result == "experience"
    
    def test_identify_section_education(self):
        text = "Education\nUniversity of Test"
        result = self.service._identify_section(text)
        assert result == "education"
    
    def test_identify_section_skills(self):
        text = "Technical Skills\nPython, JavaScript"
        result = self.service._identify_section(text)
        assert result == "skills"
    
    def test_identify_section_general(self):
        text = "Some random content without section header"
        result = self.service._identify_section(text)
        assert result == "general"
    
    def test_chunk_text_short_text(self):
        text = "Short text that doesn't need chunking"
        result = self.service._chunk_text(text, "general", chunk_size=500, chunk_overlap=50)
        assert len(result) == 1
        assert result[0] == text
    
    def test_chunk_text_long_text(self):
        text = "A " * 300  # Create text longer than chunk_size
        result = self.service._chunk_text(text, "general", chunk_size=100, chunk_overlap=20)
        assert len(result) > 1
    
    def test_chunk_text_empty_text(self):
        text = "   "
        result = self.service._chunk_text(text, "general", chunk_size=500, chunk_overlap=50)
        assert len(result) == 0
    
    def test_split_into_sections(self):
        text = """John Smith
        
Experience
Worked at Company A for 5 years

Education
Bachelor's in Computer Science

Skills
Python, JavaScript, Docker
"""
        result = self.service._split_into_sections(text)
        section_types = [s[0] for s in result]
        assert "experience" in section_types
        assert "education" in section_types
        assert "skills" in section_types
    
    @patch('pdfplumber.open')
    def test_extract_text_from_pdf(self, mock_open):
        # Mock PDF pages
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Test PDF content"
        
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)
        
        mock_open.return_value = mock_pdf
        
        with patch.object(Path, 'exists', return_value=True):
            result = self.service.extract_text_from_pdf("test.pdf")
        
        assert "Test PDF content" in result
    
    def test_extract_text_file_not_found(self):
        with pytest.raises(PDFExtractionError) as exc_info:
            self.service.extract_text_from_pdf("/nonexistent/path.pdf")
        assert "not found" in str(exc_info.value).lower()


class TestCVChunk:
    """Tests for CVChunk dataclass."""
    
    def test_cv_chunk_creation(self):
        chunk = CVChunk(
            content="Test content",
            section_type="experience",
            chunk_index=0,
            cv_id="cv_001",
            filename="test.pdf",
            candidate_name="John Smith",
        )
        
        assert chunk.content == "Test content"
        assert chunk.section_type == "experience"
        assert chunk.cv_id == "cv_001"
        assert chunk.candidate_name == "John Smith"


class TestValidation:
    """Tests for validation functions that filter garbage data."""
    
    def setup_method(self):
        self.service = PDFService()
    
    def test_validate_job_title_rejects_year(self):
        """Years should be rejected as job titles."""
        assert self.service._validate_job_title("2005") == ""
        assert self.service._validate_job_title("2020") == ""
    
    def test_validate_job_title_rejects_date_range(self):
        """Date ranges should be rejected."""
        assert self.service._validate_job_title("2005 - 2010") == ""
        assert self.service._validate_job_title("2018–Present") == ""
    
    def test_validate_job_title_rejects_stars(self):
        """Ratings with stars should be rejected."""
        assert self.service._validate_job_title("English ⭐⭐⭐⭐") == ""
    
    def test_validate_job_title_rejects_spaced_headers(self):
        """Spaced-out section headers should be rejected."""
        assert self.service._validate_job_title("E X P E R I E N C E") == ""
        assert self.service._validate_job_title("S K I L L S") == ""
    
    def test_validate_job_title_rejects_section_headers(self):
        """Common section headers should be rejected."""
        assert self.service._validate_job_title("Experience") == ""
        assert self.service._validate_job_title("education") == ""
        assert self.service._validate_job_title("SKILLS") == ""
    
    def test_validate_job_title_rejects_locations(self):
        """City/country names should be rejected."""
        assert self.service._validate_job_title("Milan") == ""
        assert self.service._validate_job_title("Italy") == ""
        assert self.service._validate_job_title("London") == ""
    
    def test_validate_job_title_rejects_languages(self):
        """Language names should be rejected."""
        assert self.service._validate_job_title("English") == ""
        assert self.service._validate_job_title("Spanish") == ""
    
    def test_validate_job_title_rejects_description_fragments(self):
        """Description fragments starting with prepositions should be rejected."""
        assert self.service._validate_job_title("to culinary excellence") == ""
        assert self.service._validate_job_title("across finance and healthcare") == ""
    
    def test_validate_job_title_accepts_valid_titles(self):
        """Valid job titles should be accepted."""
        assert self.service._validate_job_title("Software Engineer") == "Software Engineer"
        assert self.service._validate_job_title("Senior Product Manager") == "Senior Product Manager"
        assert self.service._validate_job_title("Data Scientist") == "Data Scientist"
        assert self.service._validate_job_title("Business Analyst") == "Business Analyst"
    
    def test_validate_company_rejects_year(self):
        """Years should be rejected as company names."""
        assert self.service._validate_company_name("2010") == ""
    
    def test_validate_company_cleans_year_prefix(self):
        """Leading year patterns should be removed from company names."""
        result = self.service._validate_company_name("2010 | Banking Innovations PLC")
        assert result == "Banking Innovations PLC"
    
    def test_validate_company_rejects_countries(self):
        """Country names should be rejected."""
        assert self.service._validate_company_name("Italy") == ""
        assert self.service._validate_company_name("Germany") == ""
        assert self.service._validate_company_name("United States") == ""
    
    def test_validate_company_rejects_spaced_headers(self):
        """Spaced-out headers should be rejected."""
        assert self.service._validate_company_name("S K I L L S") == ""
    
    def test_validate_company_accepts_valid_companies(self):
        """Valid company names should be accepted."""
        assert self.service._validate_company_name("Google") == "Google"
        assert self.service._validate_company_name("Tech Innovations Ltd") == "Tech Innovations Ltd"
        assert self.service._validate_company_name("Banking Corp") == "Banking Corp"
