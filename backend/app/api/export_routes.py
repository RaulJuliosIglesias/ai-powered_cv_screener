"""
Export Routes - API endpoints for PDF/CSV export functionality.

V8 Feature: Download candidate analysis reports in various formats.
"""

import io
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.config import Mode, settings
from app.models.sessions import session_manager
from app.providers.cloud.sessions import supabase_session_manager
from app.services.export_service import get_export_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/export", tags=["export"])


def get_session_manager(mode: Mode):
    """Get the appropriate session manager based on mode."""
    if mode == Mode.CLOUD:
        return supabase_session_manager
    return session_manager


@router.get("/{session_id}/csv")
async def export_session_csv(
    session_id: str,
    query: Optional[str] = None,
    mode: Mode = Query(default=settings.default_mode)
):
    """
    Export session analysis results as CSV.
    
    Args:
        session_id: Session ID to export
        query: Optional specific query to export (defaults to last analysis)
        mode: Operating mode (local/cloud)
    
    Returns:
        CSV file download
    """
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get ALL messages from the session (not just recent ones)
    # For export, we need the complete conversation history
    all_messages = session.messages if hasattr(session, 'messages') else session.get('messages', [])
    logger.info(f"[EXPORT] Exporting {len(all_messages)} messages from session {session_id}")
    
    messages_list = [
        {
            "role": msg.role if hasattr(msg, 'role') else msg.get('role'),
            "content": msg.content if hasattr(msg, 'content') else msg.get('content'),
            "structured_output": msg.structured_output if hasattr(msg, 'structured_output') else msg.get('structured_output')
        }
        for msg in all_messages
    ]
    
    # Convert session to dict if needed
    session_dict = session if isinstance(session, dict) else {
        "id": session.id,
        "name": session.name,
        "cvs": [{"id": cv.id, "filename": cv.filename} for cv in session.cvs]
    }
    
    # Generate report
    export_service = get_export_service()
    report = export_service.create_report_from_session(
        session=session_dict,
        messages=messages_list,
        query=query
    )
    
    # Generate CSV
    csv_content = export_service.generate_csv(report)
    
    # Create filename
    safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in report.session_name)
    filename = f"cv_analysis_{safe_name}_{report.generated_at.strftime('%Y%m%d')}.csv"
    
    return StreamingResponse(
        io.BytesIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8-sig"
        }
    )


@router.get("/{session_id}/pdf")
async def export_session_pdf(
    session_id: str,
    query: Optional[str] = None,
    mode: Mode = Query(default=settings.default_mode)
):
    """
    Export session analysis results as PDF.
    
    Args:
        session_id: Session ID to export
        query: Optional specific query to export (defaults to last analysis)
        mode: Operating mode (local/cloud)
    
    Returns:
        PDF file download
    """
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get ALL messages from the session (not just recent ones)
    # For export, we need the complete conversation history
    all_messages = session.messages if hasattr(session, 'messages') else session.get('messages', [])
    logger.info(f"[EXPORT PDF] Exporting {len(all_messages)} messages from session {session_id}")
    
    messages_list = [
        {
            "role": msg.role if hasattr(msg, 'role') else msg.get('role'),
            "content": msg.content if hasattr(msg, 'content') else msg.get('content'),
            "structured_output": msg.structured_output if hasattr(msg, 'structured_output') else msg.get('structured_output')
        }
        for msg in all_messages
    ]
    
    # Convert session to dict if needed
    session_dict = session if isinstance(session, dict) else {
        "id": session.id,
        "name": session.name,
        "cvs": [{"id": cv.id, "filename": cv.filename} for cv in session.cvs]
    }
    
    # Generate report
    export_service = get_export_service()
    report = export_service.create_report_from_session(
        session=session_dict,
        messages=messages_list,
        query=query
    )
    
    try:
        # Generate PDF
        pdf_content = export_service.generate_pdf(report)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    
    # Create filename
    safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in report.session_name)
    filename = f"cv_analysis_{safe_name}_{report.generated_at.strftime('%Y%m%d')}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_content),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/pdf"
        }
    )


@router.get("/{session_id}/formats")
async def get_available_formats(
    session_id: str,
    mode: Mode = Query(default=settings.default_mode)
):
    """
    Get available export formats for a session.
    
    Returns information about what can be exported.
    """
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    export_service = get_export_service()
    
    # Check what's available
    cv_count = len(session.get("cvs", [])) if isinstance(session, dict) else len(session.cvs)
    messages = mgr.get_conversation_history(session_id, limit=10)
    has_analysis = any(
        (msg.structured_output if hasattr(msg, 'structured_output') else msg.get('structured_output'))
        for msg in messages
    )
    
    return {
        "session_id": session_id,
        "formats": [
            {
                "format": "csv",
                "available": True,
                "description": "Spreadsheet-compatible format for Excel/Google Sheets"
            },
            {
                "format": "pdf",
                "available": export_service._pdf_available,
                "description": "Professional PDF report"
            }
        ],
        "has_analysis": has_analysis,
        "cv_count": cv_count
    }
