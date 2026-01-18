"""Supabase Storage for PDFs in cloud mode."""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy client initialization
_supabase_client = None


def get_supabase_client():
    """Get Supabase client lazily."""
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client

        from app.config import settings
        
        if not settings.supabase_url or not settings.supabase_service_key:
            raise RuntimeError("Supabase credentials not configured")
        
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )
        logger.info("Supabase PDF storage client initialized")
    return _supabase_client


class SupabasePDFStorage:
    """Manages PDF storage in Supabase Storage."""
    
    def __init__(self, bucket_name: str = "cv-pdfs"):
        self.bucket_name = bucket_name
    
    @property
    def client(self):
        return get_supabase_client()
    
    def _ensure_bucket(self):
        """Ensure the storage bucket exists."""
        try:
            # Check if bucket exists
            buckets = self.client.storage.list_buckets()
            bucket_exists = any(b.name == self.bucket_name for b in buckets)
            
            if bucket_exists:
                logger.debug(f"Bucket already exists: {self.bucket_name}")
                return
            
            # Create bucket
            self.client.storage.create_bucket(
                self.bucket_name,
                options={"public": True, "fileSizeLimit": 52428800, "allowedMimeTypes": ["application/pdf"]}
            )
            logger.info(f"✅ Created storage bucket: {self.bucket_name}")
            
        except Exception as e:
            # Bucket might already exist or we might not have permission to list
            # Try to use it anyway
            logger.warning(f"Bucket check/create failed (might already exist): {e}")
    
    async def upload_pdf(self, cv_id: str, pdf_path: Path) -> str:
        """
        Upload PDF to Supabase Storage.
        
        Args:
            cv_id: Unique CV identifier
            pdf_path: Path to PDF file on disk
            
        Returns:
            Public URL of uploaded PDF
        """
        try:
            self._ensure_bucket()
            
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
            file_path = f"{cv_id}.pdf"
            
            # Upload to storage
            self.client.storage.from_(self.bucket_name).upload(
                file_path,
                pdf_bytes,
                file_options={"content-type": "application/pdf", "upsert": "true"}
            )
            
            # Get public URL
            url = self.client.storage.from_(self.bucket_name).get_public_url(file_path)
            logger.info(f"Uploaded PDF to Supabase: {cv_id} -> {url}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to upload PDF {cv_id}: {e}")
            # Don't fail the entire upload if storage fails
            return ""
    
    async def get_pdf_url(self, cv_id: str) -> Optional[str]:
        """
        Get public URL for a PDF.
        
        Args:
            cv_id: CV identifier
            
        Returns:
            Public URL or None if not found
        """
        try:
            file_path = f"{cv_id}.pdf"
            url = self.client.storage.from_(self.bucket_name).get_public_url(file_path)
            return url
        except Exception as e:
            logger.error(f"Failed to get PDF URL {cv_id}: {e}")
            return None
    
    async def delete_pdf(self, cv_id: str) -> bool:
        """
        Delete PDF from storage.
        
        Args:
            cv_id: CV identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = f"{cv_id}.pdf"
            self.client.storage.from_(self.bucket_name).remove([file_path])
            logger.info(f"Deleted PDF from Supabase: {cv_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete PDF {cv_id}: {e}")
            return False


# Singleton instance
pdf_storage = SupabasePDFStorage()
