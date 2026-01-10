"""
Export Service - PDF and CSV generation for candidate analysis reports.

V8 Feature: Allow users to download analysis results in professional formats.

FIXED: Now extracts data from actual structured_output keys:
- ranking_table (not 'ranking')
- results_table (not 'candidate_profiles')
- table_data, direct_answer, thinking, conclusion, analysis
"""

import io
import csv
import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExportCandidate:
    """Candidate data for export."""
    name: str
    cv_id: str
    filename: str = ""
    score: Optional[float] = None
    rank: Optional[int] = None
    skills: List[str] = field(default_factory=list)
    experience_years: Optional[float] = None
    education: Optional[str] = None
    current_role: Optional[str] = None
    summary: Optional[str] = None
    seniority: Optional[str] = None
    avg_tenure: Optional[float] = None
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)


@dataclass
class ChatTurn:
    """A single question-answer turn in the conversation."""
    question: str
    answer: str
    thinking: Optional[str] = None
    analysis: Optional[str] = None
    conclusion: Optional[str] = None
    direct_answer: Optional[str] = None
    table_data: Optional[Dict] = None
    structure_type: Optional[str] = None


@dataclass
class ExportReport:
    """Complete report data for export."""
    title: str
    session_name: str
    generated_at: datetime
    candidates: List[ExportCandidate] = field(default_factory=list)
    conversation: List[ChatTurn] = field(default_factory=list)
    analysis_summary: Optional[str] = None
    total_cvs: int = 0
    
    @property
    def query(self) -> str:
        """Get the last query for backward compatibility."""
        if self.conversation:
            return self.conversation[-1].question
        return "General analysis"


class ExportService:
    """Service for generating PDF and CSV exports of candidate analysis."""
    
    def __init__(self):
        self._pdf_available = False
        try:
            from fpdf import FPDF
            self._pdf_available = True
        except ImportError:
            logger.warning("fpdf2 not installed. PDF export will be unavailable.")
    
    def generate_csv(self, report: ExportReport) -> bytes:
        """Generate CSV export of candidate ranking/analysis.
        
        UPDATED: Now includes full conversation history with all fields.
        
        Args:
            report: Export report data
            
        Returns:
            CSV file content as bytes
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header with metadata
        writer.writerow(['# CV Screener Export Report'])
        writer.writerow([f'# Session: {report.session_name}'])
        writer.writerow([f'# Generated: {report.generated_at.isoformat()}'])
        writer.writerow([f'# Total CVs: {report.total_cvs}'])
        writer.writerow([f'# Total Conversations: {len(report.conversation)}'])
        writer.writerow([])
        
        # ===== CONVERSATION HISTORY =====
        if report.conversation:
            writer.writerow(['# CONVERSATION HISTORY'])
            writer.writerow([])
            
            for i, turn in enumerate(report.conversation, 1):
                writer.writerow([f'--- Turn {i} ---'])
                writer.writerow(['Question:', turn.question])
                
                if turn.direct_answer:
                    writer.writerow(['Answer:', self._clean_csv_text(turn.direct_answer)])
                
                if turn.analysis:
                    writer.writerow(['Analysis:', self._clean_csv_text(turn.analysis)])
                
                if turn.conclusion:
                    writer.writerow(['Conclusion:', self._clean_csv_text(turn.conclusion)])
                
                if turn.thinking:
                    writer.writerow(['Thinking:', self._clean_csv_text(turn.thinking[:500])])
                
                writer.writerow([])
            
            writer.writerow([])
        
        # ===== CANDIDATE RANKING =====
        if report.candidates:
            writer.writerow(['# CANDIDATE RANKING'])
            writer.writerow([])
            
            # Column headers
            headers = ['Rank', 'Name', 'Score', 'Current Role', 'Experience (Years)', 
                       'Seniority', 'Skills', 'CV ID']
            writer.writerow(headers)
            
            # Candidate data
            for candidate in report.candidates:
                score_str = f'{candidate.score:.0f}%' if candidate.score else '-'
                exp_str = f'{candidate.experience_years:.1f}' if candidate.experience_years else '-'
                skills_str = ', '.join(candidate.skills[:5]) if candidate.skills else '-'
                
                writer.writerow([
                    candidate.rank or '-',
                    candidate.name,
                    score_str,
                    candidate.current_role or '-',
                    exp_str,
                    candidate.seniority or '-',
                    skills_str,
                    candidate.cv_id
                ])
            
            writer.writerow([])
        
        # ===== ANALYSIS SUMMARY =====
        if report.analysis_summary:
            writer.writerow(['# ANALYSIS SUMMARY'])
            writer.writerow([self._clean_csv_text(report.analysis_summary)])
        
        content = output.getvalue()
        return content.encode('utf-8-sig')  # BOM for Excel compatibility
    
    def _clean_csv_text(self, text: str) -> str:
        """Clean text for CSV output."""
        if not text:
            return ""
        # Remove markdown formatting
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r':::[\w]+', '', text)
        text = re.sub(r':::', '', text)
        # Replace newlines with spaces for CSV
        text = text.replace('\n', ' ').replace('\r', '')
        return text.strip()
    
    def generate_pdf(self, report: ExportReport) -> bytes:
        """Generate PDF export of candidate ranking/analysis.
        
        Args:
            report: Export report data
            
        Returns:
            PDF file content as bytes
        """
        if not self._pdf_available:
            raise RuntimeError("PDF export unavailable: fpdf2 not installed")
        
        from fpdf import FPDF
        
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # ===== HEADER =====
        pdf.set_fill_color(41, 128, 185)  # Professional blue
        pdf.rect(0, 0, 210, 35, 'F')
        
        pdf.set_font('Helvetica', 'B', 22)
        pdf.set_text_color(255, 255, 255)
        pdf.set_y(10)
        pdf.cell(0, 10, 'CV Screener Analysis Report', ln=True, align='C')
        
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 6, f'Session: {report.session_name}', ln=True, align='C')
        
        pdf.set_y(40)
        
        # ===== METADATA BOX =====
        pdf.set_fill_color(245, 245, 245)
        pdf.rect(10, 40, 190, 20, 'F')
        pdf.set_text_color(80, 80, 80)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_xy(15, 43)
        pdf.cell(60, 5, f'Generated: {report.generated_at.strftime("%Y-%m-%d %H:%M")}')
        pdf.cell(60, 5, f'Total CVs: {report.total_cvs}')
        pdf.cell(60, 5, f'Conversations: {len(report.conversation)}')
        pdf.ln(15)
        
        # ===== CONVERSATION HISTORY =====
        if report.conversation:
            pdf.set_y(65)
            pdf.set_font('Helvetica', 'B', 14)
            pdf.set_text_color(41, 128, 185)
            pdf.cell(0, 10, 'Conversation History', ln=True)
            pdf.set_draw_color(41, 128, 185)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
            for i, turn in enumerate(report.conversation, 1):
                # Check if we need a new page
                if pdf.get_y() > 250:
                    pdf.add_page()
                
                # Question box
                pdf.set_fill_color(232, 245, 233)  # Light green
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(33, 37, 41)
                pdf.cell(0, 7, f'Q{i}: {self._clean_text(turn.question[:100])}', ln=True, fill=True)
                
                # Direct Answer (most important)
                if turn.direct_answer:
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.set_text_color(25, 135, 84)  # Green
                    pdf.cell(0, 6, 'Answer:', ln=True)
                    pdf.set_font('Helvetica', '', 9)
                    pdf.set_text_color(33, 37, 41)
                    pdf.multi_cell(0, 5, self._clean_text(turn.direct_answer[:500]))
                    pdf.ln(2)
                
                # Analysis section
                if turn.analysis:
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.set_text_color(13, 110, 253)  # Blue
                    pdf.cell(0, 6, 'Analysis:', ln=True)
                    pdf.set_font('Helvetica', '', 8)
                    pdf.set_text_color(33, 37, 41)
                    pdf.multi_cell(0, 4, self._clean_text(turn.analysis[:800]))
                    pdf.ln(2)
                
                # Conclusion
                if turn.conclusion:
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.set_text_color(111, 66, 193)  # Purple
                    pdf.cell(0, 6, 'Conclusion:', ln=True)
                    pdf.set_font('Helvetica', '', 9)
                    pdf.set_text_color(33, 37, 41)
                    pdf.multi_cell(0, 5, self._clean_text(turn.conclusion[:500]))
                    pdf.ln(2)
                
                # Table data if present
                if turn.table_data:
                    self._add_table_to_pdf(pdf, turn.table_data, turn.structure_type)
                
                pdf.ln(5)
        
        # ===== CANDIDATE RANKING TABLE =====
        if report.candidates:
            if pdf.get_y() > 200:
                pdf.add_page()
            
            pdf.set_font('Helvetica', 'B', 14)
            pdf.set_text_color(41, 128, 185)
            pdf.cell(0, 10, 'Candidate Summary', ln=True)
            pdf.set_draw_color(41, 128, 185)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
            # Table header
            pdf.set_font('Helvetica', 'B', 8)
            pdf.set_fill_color(41, 128, 185)
            pdf.set_text_color(255, 255, 255)
            col_widths = [12, 45, 18, 45, 25, 45]
            headers = ['#', 'Name', 'Score', 'Role', 'Exp', 'Skills']
            
            for header, width in zip(headers, col_widths):
                pdf.cell(width, 7, header, border=1, fill=True, align='C')
            pdf.ln()
            
            # Table rows
            pdf.set_font('Helvetica', '', 7)
            pdf.set_text_color(33, 37, 41)
            
            for j, candidate in enumerate(report.candidates[:15]):
                # Alternate row colors
                if j % 2 == 0:
                    pdf.set_fill_color(249, 249, 249)
                else:
                    pdf.set_fill_color(255, 255, 255)
                
                rank_text = str(candidate.rank) if candidate.rank else str(j + 1)
                name = self._truncate(candidate.name, 20)
                score = f'{candidate.score:.0f}%' if candidate.score else '-'
                role = self._truncate(candidate.current_role or '-', 20)
                exp = f'{candidate.experience_years:.0f}y' if candidate.experience_years else '-'
                skills = self._truncate(', '.join(candidate.skills[:3]), 22) if candidate.skills else '-'
                
                pdf.cell(col_widths[0], 6, rank_text, border=1, fill=True, align='C')
                pdf.cell(col_widths[1], 6, name, border=1, fill=True)
                pdf.cell(col_widths[2], 6, score, border=1, fill=True, align='C')
                pdf.cell(col_widths[3], 6, role, border=1, fill=True)
                pdf.cell(col_widths[4], 6, exp, border=1, fill=True, align='C')
                pdf.cell(col_widths[5], 6, skills, border=1, fill=True)
                pdf.ln()
        
        # ===== ANALYSIS SUMMARY =====
        if report.analysis_summary:
            if pdf.get_y() > 230:
                pdf.add_page()
            
            pdf.ln(5)
            pdf.set_font('Helvetica', 'B', 12)
            pdf.set_text_color(41, 128, 185)
            pdf.cell(0, 8, 'Summary', ln=True)
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(33, 37, 41)
            pdf.multi_cell(0, 5, self._clean_text(report.analysis_summary[:1500]))
        
        # ===== FOOTER =====
        pdf.set_y(-20)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 5, 'Generated by AI-Powered CV Screener', ln=True, align='C')
        
        return bytes(pdf.output())
    
    def _add_table_to_pdf(self, pdf, table_data: Dict, structure_type: str):
        """Add structured table data to PDF."""
        if not table_data:
            return
        
        # Handle ranking_table
        if 'ranked' in table_data:
            ranked = table_data.get('ranked', [])
            if ranked:
                pdf.set_font('Helvetica', 'B', 8)
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(15, 6, 'Rank', border=1, fill=True, align='C')
                pdf.cell(50, 6, 'Candidate', border=1, fill=True)
                pdf.cell(25, 6, 'Score', border=1, fill=True, align='C')
                pdf.cell(25, 6, 'Exp', border=1, fill=True, align='C')
                pdf.ln()
                
                pdf.set_font('Helvetica', '', 7)
                for r in ranked[:10]:
                    pdf.cell(15, 5, str(r.get('rank', '-')), border=1, align='C')
                    pdf.cell(50, 5, self._truncate(r.get('candidate_name', ''), 25), border=1)
                    score = r.get('overall_score', 0)
                    pdf.cell(25, 5, f'{score:.0f}%' if score else '-', border=1, align='C')
                    exp = r.get('experience_years', 0)
                    pdf.cell(25, 5, f'{exp:.0f}y' if exp else '-', border=1, align='C')
                    pdf.ln()
        
        # Handle results_table
        elif 'results' in table_data:
            results = table_data.get('results', [])
            if results:
                pdf.set_font('Helvetica', 'B', 8)
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(50, 6, 'Candidate', border=1, fill=True)
                pdf.cell(50, 6, 'Role', border=1, fill=True)
                pdf.cell(25, 6, 'Match', border=1, fill=True, align='C')
                pdf.ln()
                
                pdf.set_font('Helvetica', '', 7)
                for r in results[:10]:
                    pdf.cell(50, 5, self._truncate(r.get('candidate_name', ''), 25), border=1)
                    pdf.cell(50, 5, self._truncate(r.get('current_role', '-'), 25), border=1)
                    match = r.get('match_level', '-')
                    pdf.cell(25, 5, match, border=1, align='C')
                    pdf.ln()
    
    def _clean_text(self, text: str) -> str:
        """Clean text for PDF output - remove markdown and special chars."""
        if not text:
            return ""
        # Remove markdown formatting
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Italic
        text = re.sub(r':::[\w]+', '', text)  # Custom markers
        text = re.sub(r':::', '', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Links
        text = re.sub(r'#{1,6}\s*', '', text)  # Headers
        text = re.sub(r'\|[^\n]+\|', '', text)  # Table rows
        # Remove emojis that might cause encoding issues
        text = text.encode('latin-1', 'ignore').decode('latin-1')
        return text.strip()
    
    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text to max length."""
        if not text:
            return "-"
        text = self._clean_text(text)
        if len(text) > max_len:
            return text[:max_len-2] + '..'
        return text
    
    def create_report_from_session(
        self,
        session: Dict[str, Any],
        messages: List[Dict[str, Any]],
        query: Optional[str] = None
    ) -> ExportReport:
        """Create export report from session data.
        
        FIXED: Now extracts data from actual structured_output keys:
        - ranking_table.ranked (not 'ranking')
        - results_table.results (not 'candidate_profiles')
        - direct_answer, thinking, conclusion, analysis
        
        Args:
            session: Session data with CVs
            messages: Chat messages with analysis results
            query: Optional specific query to export (defaults to last query)
            
        Returns:
            ExportReport ready for export
        """
        conversation = []
        candidates = []
        analysis_summary = None
        
        # Process ALL messages to build conversation history
        current_question = None
        
        for i, msg in enumerate(messages):
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            if role == 'user':
                current_question = content
            
            elif role == 'assistant' and current_question:
                structured = msg.get('structured_output', {}) or {}
                
                # Create ChatTurn with all available data
                turn = ChatTurn(
                    question=current_question,
                    answer=content[:1000] if content else '',
                    thinking=structured.get('thinking'),
                    analysis=structured.get('analysis'),
                    conclusion=structured.get('conclusion'),
                    direct_answer=structured.get('direct_answer'),
                    structure_type=structured.get('structure_type'),
                    table_data=self._extract_table_data(structured)
                )
                conversation.append(turn)
                
                # Extract candidates from this message's structured output
                msg_candidates = self._extract_candidates_from_structured(structured)
                if msg_candidates:
                    candidates = msg_candidates  # Use most recent ranking
                
                # Extract analysis summary from conclusion or direct answer
                if not analysis_summary:
                    analysis_summary = (
                        structured.get('conclusion') or 
                        structured.get('direct_answer') or
                        structured.get('analysis') or
                        content[:800]
                    )
                
                current_question = None
        
        # If no candidates from structured output, extract from CVs in session
        if not candidates and session.get('cvs'):
            for i, cv in enumerate(session['cvs'], 1):
                candidates.append(ExportCandidate(
                    name=self._extract_name_from_filename(cv.get('filename', '')),
                    cv_id=cv.get('id', ''),
                    filename=cv.get('filename', ''),
                    rank=i
                ))
        
        logger.info(f"[EXPORT] Created report with {len(conversation)} turns, {len(candidates)} candidates")
        
        return ExportReport(
            title='CV Analysis Report',
            session_name=session.get('name', 'Unnamed Session'),
            generated_at=datetime.utcnow(),
            candidates=candidates,
            conversation=conversation,
            analysis_summary=analysis_summary,
            total_cvs=len(session.get('cvs', []))
        )
    
    def _extract_table_data(self, structured: Dict) -> Optional[Dict]:
        """Extract table data from structured output."""
        # Check for various table types in order of priority
        if structured.get('ranking_table'):
            return structured['ranking_table']
        if structured.get('results_table'):
            return structured['results_table']
        if structured.get('table_data'):
            return structured['table_data']
        if structured.get('risk_table'):
            return structured['risk_table']
        if structured.get('team_overview'):
            return structured['team_overview']
        return None
    
    def _extract_candidates_from_structured(self, structured: Dict) -> List[ExportCandidate]:
        """Extract candidates from structured output.
        
        FIXED: Uses actual keys: ranking_table.ranked, results_table.results
        """
        candidates = []
        
        # Extract from ranking_table (most common for rankings)
        ranking_table = structured.get('ranking_table', {})
        if ranking_table and 'ranked' in ranking_table:
            for entry in ranking_table['ranked']:
                skills = []
                # Parse skills from string if needed
                skills_data = entry.get('skills', [])
                if isinstance(skills_data, str):
                    skills = [s.strip() for s in skills_data.split(',') if s.strip()]
                elif isinstance(skills_data, list):
                    skills = skills_data
                
                candidates.append(ExportCandidate(
                    name=entry.get('candidate_name', 'Unknown'),
                    cv_id=entry.get('cv_id', ''),
                    score=entry.get('overall_score'),
                    rank=entry.get('rank'),
                    skills=skills,
                    experience_years=entry.get('experience_years'),
                    current_role=entry.get('current_role', ''),
                    seniority=entry.get('seniority', ''),
                    avg_tenure=entry.get('avg_tenure'),
                    strengths=entry.get('strengths', []),
                    weaknesses=entry.get('weaknesses', [])
                ))
            return candidates
        
        # Extract from results_table (for search results)
        results_table = structured.get('results_table', {})
        if results_table and 'results' in results_table:
            for i, entry in enumerate(results_table['results'], 1):
                candidates.append(ExportCandidate(
                    name=entry.get('candidate_name', 'Unknown'),
                    cv_id=entry.get('cv_id', ''),
                    rank=i,
                    current_role=entry.get('current_role', ''),
                    experience_years=entry.get('experience_years'),
                    summary=entry.get('match_reason', '')
                ))
            return candidates
        
        # Extract from team_member_cards (for team building)
        team_cards = structured.get('team_member_cards', {})
        if team_cards and 'cards' in team_cards:
            for card in team_cards['cards']:
                skills = []
                skills_data = card.get('key_skills', [])
                if isinstance(skills_data, str):
                    skills = [s.strip() for s in skills_data.split(',') if s.strip()]
                elif isinstance(skills_data, list):
                    skills = skills_data
                
                candidates.append(ExportCandidate(
                    name=card.get('name', 'Unknown'),
                    cv_id=card.get('cv_id', ''),
                    rank=card.get('rank'),
                    current_role=card.get('role', ''),
                    skills=skills,
                    summary=card.get('contribution', '')
                ))
            return candidates
        
        # Extract from single_candidate_data (for single candidate analysis)
        single = structured.get('single_candidate_data', {})
        if single:
            candidates.append(ExportCandidate(
                name=single.get('candidate_name', 'Unknown'),
                cv_id=single.get('cv_id', ''),
                current_role=single.get('current_role', ''),
                experience_years=single.get('total_experience'),
                summary=single.get('summary', '')
            ))
            return candidates
        
        return candidates
    
    def _extract_name_from_filename(self, filename: str) -> str:
        """Extract candidate name from filename."""
        name = filename.replace('.pdf', '').replace('.PDF', '')
        parts = name.split('_')
        if len(parts) >= 3:
            return ' '.join(parts[1:-1])
        elif len(parts) == 2:
            return parts[1]
        return name


# Singleton instance
_export_service: Optional[ExportService] = None


def get_export_service() -> ExportService:
    """Get singleton export service instance."""
    global _export_service
    if _export_service is None:
        _export_service = ExportService()
    return _export_service
