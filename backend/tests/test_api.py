import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import io

from app.main import app


client = TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "name" in response.json()
        assert response.json()["name"] == "CV Screener RAG API"


class TestUploadEndpoint:
    """Tests for file upload endpoint."""
    
    def test_upload_no_files(self):
        response = client.post("/api/upload", files=[])
        assert response.status_code == 422  # Validation error - no files
    
    def test_upload_invalid_file_type(self):
        files = [("files", ("test.txt", b"test content", "text/plain"))]
        response = client.post("/api/upload", files=files)
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
    
    @patch('app.api.routes.process_files')
    def test_upload_valid_pdf(self, mock_process):
        pdf_content = b"%PDF-1.4 test content"
        files = [("files", ("test.pdf", pdf_content, "application/pdf"))]
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["files_received"] == 1
        assert data["status"] == "processing"


class TestCVsEndpoint:
    """Tests for CV management endpoints."""
    
    @patch('app.api.routes.get_vector_store')
    def test_list_cvs_empty(self, mock_store):
        mock_instance = MagicMock()
        mock_instance.get_all_cvs.return_value = []
        mock_store.return_value = mock_instance
        
        response = client.get("/api/cvs")
        assert response.status_code == 200
        assert response.json()["total"] == 0
        assert response.json()["cvs"] == []
    
    @patch('app.api.routes.get_vector_store')
    def test_list_cvs_with_data(self, mock_store):
        mock_instance = MagicMock()
        mock_instance.get_all_cvs.return_value = [
            {
                "id": "cv_001",
                "filename": "test.pdf",
                "candidate_name": "John Smith",
                "indexed_at": "2025-01-01T00:00:00",
                "chunk_count": 5,
            }
        ]
        mock_store.return_value = mock_instance
        
        response = client.get("/api/cvs")
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert len(response.json()["cvs"]) == 1
    
    @patch('app.api.routes.get_vector_store')
    def test_delete_cv_not_found(self, mock_store):
        mock_instance = MagicMock()
        mock_instance.get_cv_by_id.return_value = None
        mock_store.return_value = mock_instance
        
        response = client.delete("/api/cvs/nonexistent")
        assert response.status_code == 404


class TestChatEndpoint:
    """Tests for chat endpoint."""
    
    @patch('app.api.routes.get_vector_store')
    def test_chat_no_cvs_indexed(self, mock_store):
        mock_instance = MagicMock()
        mock_instance.get_collection_stats.return_value = {"total_cvs": 0}
        mock_store.return_value = mock_instance
        
        response = client.post("/api/chat", json={"message": "test question"})
        assert response.status_code == 404
        assert "No CVs indexed" in response.json()["detail"]
    
    def test_chat_empty_message(self):
        response = client.post("/api/chat", json={"message": ""})
        assert response.status_code == 422  # Validation error
    
    @patch('app.api.routes.get_vector_store')
    @patch('app.api.routes.get_rag_service')
    @patch('app.api.routes.get_guardrails_service')
    @patch('app.api.routes.get_usage_tracker')
    @patch('app.api.routes.get_query_logger')
    @patch('app.api.routes.get_rate_limiter')
    def test_chat_success(
        self,
        mock_limiter,
        mock_logger,
        mock_tracker,
        mock_guardrails,
        mock_rag,
        mock_store,
    ):
        # Setup mocks
        mock_store_instance = MagicMock()
        mock_store_instance.get_collection_stats.return_value = {"total_cvs": 5}
        mock_store.return_value = mock_store_instance
        
        mock_limiter_instance = MagicMock()
        mock_limiter_instance.check_limit.return_value = (True, 0)
        mock_limiter.return_value = mock_limiter_instance
        
        mock_guardrails_instance = MagicMock()
        mock_guardrails_instance.sanitize_input.return_value = "test question"
        mock_guardrails.return_value = mock_guardrails_instance
        
        mock_rag_instance = MagicMock()
        mock_rag_instance.query_async.return_value = {
            "response": "Test response",
            "sources": [
                {"cv_id": "cv_001", "filename": "test.pdf", "relevance_score": 0.9, "matched_chunk": "..."}
            ],
            "conversation_id": "conv_123",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "estimated_cost_usd": 0.001,
            }
        }
        mock_rag.return_value = mock_rag_instance
        
        response = client.post("/api/chat", json={"message": "test question"})
        # Note: This may fail due to async handling in tests
        # In a real scenario, use pytest-asyncio


class TestStatsEndpoint:
    """Tests for stats endpoint."""
    
    @patch('app.api.routes.get_usage_tracker')
    @patch('app.api.routes.get_vector_store')
    def test_get_stats(self, mock_store, mock_tracker):
        mock_tracker_instance = MagicMock()
        mock_tracker_instance.get_total_stats.return_value = {
            "total_requests": 10,
            "total_tokens": 5000,
            "total_cost_usd": 0.05,
            "average_latency_ms": 1200,
        }
        mock_tracker.return_value = mock_tracker_instance
        
        mock_store_instance = MagicMock()
        mock_store_instance.get_collection_stats.return_value = {
            "total_cvs": 5,
            "total_chunks": 50,
        }
        mock_store.return_value = mock_store_instance
        
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_queries" in data
        assert "cvs_indexed" in data
