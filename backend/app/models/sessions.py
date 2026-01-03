"""Session models for managing CV groups and chat history."""
import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

SESSIONS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sessions.json")


class ChatMessage(BaseModel):
    """A single chat message."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str  # 'user' or 'assistant'
    content: str
    sources: List[Dict] = Field(default_factory=list)
    pipeline_steps: List[Dict] = Field(default_factory=list)  # Pipeline execution steps for UI
    structured_output: Optional[Dict] = None  # Structured output from OutputProcessor
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class CVInfo(BaseModel):
    """CV information within a session."""
    id: str
    filename: str
    chunk_count: int = 0
    uploaded_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Session(BaseModel):
    """A session containing CVs and chat history."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    cvs: List[CVInfo] = Field(default_factory=list)
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class SessionManager:
    """Manages sessions with JSON persistence."""
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self._ensure_data_dir()
        self._load()
    
    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        data_dir = os.path.dirname(SESSIONS_FILE)
        os.makedirs(data_dir, exist_ok=True)
    
    def _load(self):
        """Load sessions from JSON file."""
        if os.path.exists(SESSIONS_FILE):
            try:
                with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for session_data in data.get('sessions', []):
                        session = Session(**session_data)
                        self.sessions[session.id] = session
                logger.info(f"Loaded {len(self.sessions)} sessions")
            except Exception as e:
                logger.error(f"Failed to load sessions: {e}")
                self.sessions = {}
    
    def _save(self):
        """Save sessions to JSON file."""
        try:
            data = {
                'sessions': [s.model_dump() for s in self.sessions.values()]
            }
            with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")
    
    def create_session(self, name: str, description: str = "") -> Session:
        """Create a new session."""
        session = Session(name=name, description=description)
        self.sessions[session.id] = session
        self._save()
        logger.info(f"Created session: {session.id} - {name}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return self.sessions.get(session_id)
    
    def list_sessions(self) -> List[Session]:
        """List all sessions."""
        return sorted(
            self.sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True
        )
    
    def update_session(self, session_id: str, name: str = None, description: str = None) -> Optional[Session]:
        """Update session metadata."""
        session = self.sessions.get(session_id)
        if session:
            if name is not None:
                session.name = name
            if description is not None:
                session.description = description
            session.updated_at = datetime.now().isoformat()
            self._save()
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save()
            logger.info(f"Deleted session: {session_id}")
            return True
        return False
    
    def add_cv_to_session(self, session_id: str, cv_id: str, filename: str, chunk_count: int = 0) -> Optional[Session]:
        """Add a CV to a session."""
        session = self.sessions.get(session_id)
        if session:
            cv_info = CVInfo(id=cv_id, filename=filename, chunk_count=chunk_count)
            session.cvs.append(cv_info)
            session.updated_at = datetime.now().isoformat()
            self._save()
            logger.info(f"Added CV {cv_id} to session {session_id}")
        return session
    
    def remove_cv_from_session(self, session_id: str, cv_id: str) -> Optional[Session]:
        """Remove a CV from a session."""
        session = self.sessions.get(session_id)
        if session:
            session.cvs = [cv for cv in session.cvs if cv.id != cv_id]
            session.updated_at = datetime.now().isoformat()
            self._save()
            logger.info(f"Removed CV {cv_id} from session {session_id}")
        return session
    
    def add_message(self, session_id: str, role: str, content: str, sources: List[Dict] = None, pipeline_steps: List[Dict] = None, structured_output: Optional[Dict] = None) -> Optional[ChatMessage]:
        """Add a chat message to a session."""
        session = self.sessions.get(session_id)
        if session:
            message = ChatMessage(
                role=role, 
                content=content, 
                sources=sources or [],
                pipeline_steps=pipeline_steps or [],
                structured_output=structured_output
            )
            session.messages.append(message)
            session.updated_at = datetime.now().isoformat()
            self._save()
            return message
        return None
    
    def get_cv_ids_for_session(self, session_id: str) -> List[str]:
        """Get list of CV IDs for a session."""
        session = self.sessions.get(session_id)
        if session:
            return [cv.id for cv in session.cvs]
        return []
    
    def clear_messages(self, session_id: str) -> bool:
        """Clear chat history for a session."""
        session = self.sessions.get(session_id)
        if session:
            session.messages = []
            session.updated_at = datetime.now().isoformat()
            self._save()
            return True
        return False
    
    def delete_message(self, session_id: str, message_index: int) -> bool:
        """Delete a specific message by index from a session."""
        session = self.sessions.get(session_id)
        if session and 0 <= message_index < len(session.messages):
            del session.messages[message_index]
            session.updated_at = datetime.now().isoformat()
            self._save()
            return True
        return False
    
    def delete_messages_from(self, session_id: str, from_index: int) -> int:
        """Delete all messages from a specific index onwards (inclusive)."""
        session = self.sessions.get(session_id)
        if session and 0 <= from_index < len(session.messages):
            count = len(session.messages) - from_index
            session.messages = session.messages[:from_index]
            session.updated_at = datetime.now().isoformat()
            self._save()
            return count
        return 0


# Global session manager instance
session_manager = SessionManager()
