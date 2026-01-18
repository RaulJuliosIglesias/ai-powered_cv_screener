"""Supabase session manager for cloud mode."""
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Lazy import to avoid startup errors
_supabase_client = None


def get_supabase_client():
    """Get or create Supabase client lazily."""
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client

        from app.config import settings
        
        if not settings.supabase_url or not settings.supabase_service_key:
            raise RuntimeError("Supabase credentials not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
        
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )
        logger.info("Supabase client initialized")
    return _supabase_client


class SupabaseSessionManager:
    """Manages sessions using Supabase."""
    
    @property
    def client(self):
        """Get Supabase client lazily."""
        return get_supabase_client()
    
    def _ensure_client(self):
        """Ensure client is available."""
        return self.client  # Will raise if not configured
    
    def create_session(self, name: str, description: str = "") -> Dict:
        """Create a new session."""
        try:
            self._ensure_client()
            session_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            data = {
                "id": session_id,
                "name": name,
                "description": description,
                "created_at": now,
                "updated_at": now
            }
            
            self.client.table("sessions").insert(data).execute()
            logger.info(f"Created Supabase session: {session_id} - {name}")
            
            return {
                **data,
                "cvs": [],
                "messages": []
            }
        except Exception as e:
            logger.error(f"Failed to create session in Supabase: {e}")
            raise RuntimeError(f"Supabase error: {e}")
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get a session by ID with its CVs and messages."""
        self._ensure_client()
        
        # Get session
        result = self.client.table("sessions").select("*").eq("id", session_id).execute()
        if not result.data:
            return None
        
        session = result.data[0]
        
        # Get CVs for this session
        cvs_result = self.client.table("session_cvs").select("*").eq("session_id", session_id).execute()
        session["cvs"] = [
            {
                "id": cv["cv_id"],
                "filename": cv["filename"],
                "chunk_count": cv.get("chunk_count", 0),
                "uploaded_at": cv.get("uploaded_at", session["created_at"])
            }
            for cv in cvs_result.data
        ]
        
        # Get messages for this session
        msgs_result = self.client.table("session_messages").select("*").eq("session_id", session_id).order("timestamp").execute()
        session["messages"] = [
            {
                "id": msg["id"],
                "role": msg["role"],
                "content": msg["content"],
                "sources": msg.get("sources", []),
                "pipeline_steps": msg.get("pipeline_steps", []),
                "structured_output": msg.get("structured_output"),
                "timestamp": msg["timestamp"]
            }
            for msg in msgs_result.data
        ]
        
        return session
    
    def list_sessions(self) -> List[Dict]:
        """List all sessions."""
        try:
            self._ensure_client()
            
            result = self.client.table("sessions").select("*").order("updated_at", desc=True).execute()
            
            sessions = []
            for s in result.data:
                # Get CV count
                cvs = self.client.table("session_cvs").select("id", count="exact").eq("session_id", s["id"]).execute()
                # Get message count
                msgs = self.client.table("session_messages").select("id", count="exact").eq("session_id", s["id"]).execute()
                
                sessions.append({
                    **s,
                    "cv_count": cvs.count or 0,
                    "message_count": msgs.count or 0
                })
            
            return sessions
        except Exception as e:
            logger.error(f"Failed to list sessions from Supabase: {e}")
            return []
    
    def update_session(self, session_id: str, name: str = None, description: str = None) -> Optional[Dict]:
        """Update session metadata."""
        self._ensure_client()
        
        updates = {"updated_at": datetime.now().isoformat()}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        
        result = self.client.table("sessions").update(updates).eq("id", session_id).execute()
        
        if result.data:
            return self.get_session(session_id)
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its data."""
        self._ensure_client()
        
        try:
            # Delete messages
            self.client.table("session_messages").delete().eq("session_id", session_id).execute()
            # Delete CV associations
            self.client.table("session_cvs").delete().eq("session_id", session_id).execute()
            # Delete session
            self.client.table("sessions").delete().eq("id", session_id).execute()
            
            logger.info(f"Deleted Supabase session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    def add_cv_to_session(self, session_id: str, cv_id: str, filename: str, chunk_count: int = 0, content_hash: str = "") -> Optional[Dict]:
        """Add a CV to a session."""
        self._ensure_client()
        
        data = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "cv_id": cv_id,
            "filename": filename,
            "chunk_count": chunk_count,
            "content_hash": content_hash,
            "uploaded_at": datetime.now().isoformat()
        }
        
        self.client.table("session_cvs").insert(data).execute()
        
        # Update session timestamp
        self.client.table("sessions").update({"updated_at": datetime.now().isoformat()}).eq("id", session_id).execute()
        
        logger.info(f"Added CV {cv_id} to Supabase session {session_id}")
        return self.get_session(session_id)
    
    def remove_cv_from_session(self, session_id: str, cv_id: str) -> Optional[Dict]:
        """Remove a CV from a session."""
        self._ensure_client()
        
        self.client.table("session_cvs").delete().eq("session_id", session_id).eq("cv_id", cv_id).execute()
        
        # Update session timestamp
        self.client.table("sessions").update({"updated_at": datetime.now().isoformat()}).eq("id", session_id).execute()
        
        logger.info(f"Removed CV {cv_id} from Supabase session {session_id}")
        return self.get_session(session_id)
    
    def add_message(self, session_id: str, role: str, content: str, sources: List[Dict] = None, pipeline_steps: List[Dict] = None, structured_output: Optional[Dict] = None) -> Optional[Dict]:
        """Add a chat message to a session."""
        self._ensure_client()
        
        message_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        data = {
            "id": message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "sources": sources or [],
            "pipeline_steps": pipeline_steps or [],
            "structured_output": structured_output,
            "timestamp": now
        }
        
        self.client.table("session_messages").insert(data).execute()
        
        # Update session timestamp
        self.client.table("sessions").update({"updated_at": now}).eq("id", session_id).execute()
        
        logger.info(f"Added {role} message to session {session_id}")
        
        return {
            "id": message_id,
            "role": role,
            "content": content,
            "sources": sources or [],
            "pipeline_steps": pipeline_steps or [],
            "structured_output": structured_output,
            "timestamp": now
        }
    
    def get_cv_ids_for_session(self, session_id: str) -> List[str]:
        """Get list of CV IDs for a session."""
        self._ensure_client()
        
        result = self.client.table("session_cvs").select("cv_id").eq("session_id", session_id).execute()
        return [row["cv_id"] for row in result.data]
    
    def clear_messages(self, session_id: str) -> bool:
        """Clear chat history for a session."""
        self._ensure_client()
        
        try:
            self.client.table("session_messages").delete().eq("session_id", session_id).execute()
            self.client.table("sessions").update({"updated_at": datetime.now().isoformat()}).eq("id", session_id).execute()
            return True
        except Exception:
            return False
    
    def delete_message(self, session_id: str, message_index: int) -> bool:
        """Delete a specific message by index from a session."""
        self._ensure_client()
        
        try:
            # Get all messages for the session
            msgs_result = self.client.table("session_messages").select("*").eq("session_id", session_id).order("timestamp").execute()
            
            if 0 <= message_index < len(msgs_result.data):
                message_to_delete = msgs_result.data[message_index]
                self.client.table("session_messages").delete().eq("id", message_to_delete["id"]).execute()
                self.client.table("sessions").update({"updated_at": datetime.now().isoformat()}).eq("id", session_id).execute()
                logger.info(f"Deleted message {message_index} from session {session_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete message {message_index} from session {session_id}: {e}")
            return False
    
    def delete_messages_from(self, session_id: str, from_index: int) -> int:
        """Delete all messages from a specific index onwards (inclusive)."""
        self._ensure_client()
        
        try:
            # Get all messages for the session
            msgs_result = self.client.table("session_messages").select("*").eq("session_id", session_id).order("timestamp").execute()
            
            if from_index < 0 or from_index >= len(msgs_result.data):
                return 0
            
            # Delete messages from index onwards
            deleted_count = 0
            for msg in msgs_result.data[from_index:]:
                self.client.table("session_messages").delete().eq("id", msg["id"]).execute()
                deleted_count += 1
            
            self.client.table("sessions").update({"updated_at": datetime.now().isoformat()}).eq("id", session_id).execute()
            logger.info(f"Deleted {deleted_count} messages from session {session_id} starting at index {from_index}")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete messages from session {session_id}: {e}")
            return 0
    
    def get_conversation_history(self, session_id: str, limit: int = 6) -> List[Dict]:
        """
        Get recent conversation history for context.
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to retrieve (default 6 = 3 turns)
        
        Returns:
            List of recent messages ordered from oldest to newest
        """
        self._ensure_client()
        
        try:
            # Get all messages ordered by timestamp
            result = self.client.table("session_messages").select("*").eq("session_id", session_id).order("timestamp").execute()
            
            if not result.data:
                return []
            
            # Get last N messages
            recent_messages = result.data[-limit:] if len(result.data) > limit else result.data
            
            return [
                {
                    "id": msg["id"],
                    "role": msg["role"],
                    "content": msg["content"],
                    "sources": msg.get("sources", []),
                    "pipeline_steps": msg.get("pipeline_steps", []),
                    "structured_output": msg.get("structured_output"),
                    "timestamp": msg["timestamp"]
                }
                for msg in recent_messages
            ]
        except Exception as e:
            logger.error(f"Failed to get conversation history for session {session_id}: {e}")
            return []


# Global instance
supabase_session_manager = SupabaseSessionManager()
