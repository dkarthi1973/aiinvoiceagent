"""
Integration tests for FastAPI endpoints
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json
import io
from PIL import Image

from src.api.main import app
from src.models import ProcessingStatus


class TestAPIEndpoints:
    """Test cases for API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_services(self):
        """Mock the global services"""
        with patch('src.api.main.invoice_processor') as mock_processor, \
             patch('src.api.main.file_monitor') as mock_monitor:
            
            # Setup mock processor
            mock_processor.get_statistics.return_value = AsyncMock(return_value=Mock(
                total_processed=10,
                successful=8,
                failed=2,
                pending=0,
                processing=0,
                average_processing_time=2.5,
                uptime="1 day"
            ))
            
            mock_processor.get_recent_results.return_value = AsyncMock(return_value=[])
            mock_processor.process_files.return_value = AsyncMock()
            mock_processor.delete_result.return_value = AsyncMock(return_value=True)
            
            # Setup mock monitor
            mock_monitor.is_running = True
            
            yield mock_processor, mock_monitor
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
        assert "services" in data
    
    def test_get_system_status(self, client, mock_services):
        """Test system status endpoint"""
        mock_processor, mock_monitor = mock_services
        
        response = client.get("/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "uptime" in data["data"]
        assert "stats" in data["data"]
        assert "settings" in data["data"]
    
    def test_get_processing_stats(self, client, mock_services):
        """Test processing statistics endpoint"""
        mock_processor, mock_monitor = mock_services
        
        response = client.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_processed" in data
        assert "successful" in data
        assert "failed" in data
        assert "average_processing_time" in data
    
    def test_get_processing_stats_service_unavailable(self, client):
        """Test processing stats when service is unavailable"""
        with patch('src.api.main.invoice_processor', None):
            response = client.get("/stats")
            assert response.status_code == 503
    
    def test_trigger_processing(self, client, mock_services):
        """Test manual processing trigger"""
        mock_processor, mock_monitor = mock_services
        
        request_data = {
            "file_path": None,
            "force_reprocess": False
        }
        
        response = client.post("/process", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Processing triggered successfully" in data["message"]
    
    def test_trigger_processing_service_unavailable(self, client):
        """Test processing trigger when service is unavailable"""
        with patch('src.api.main.invoice_processor', None):
            response = client.post("/process", json={})
            assert response.status_code == 503
    
    def test_upload_invoice_success(self, client, temp_directories):
        """Test successful invoice upload"""
        # Create test image
        img = Image.new('RGB', (100, 100), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        with patch('config.settings.settings') as mock_settings:
            mock_settings.incoming_path = temp_directories['incoming']
            mock_settings.supported_formats_list = ['jpg', 'jpeg', 'png']
            
            files = {"file": ("test_invoice.jpg", img_bytes, "image/jpeg")}
            response = client.post("/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "uploaded successfully" in data["message"]
        assert "filename" in data["data"]
        assert "size" in data["data"]
    
    def test_upload_invoice_unsupported_format(self, client):
        """Test upload with unsupported file format"""
        # Create test text file
        text_content = io.BytesIO(b"This is a text file")
        
        with patch('config.settings.settings') as mock_settings:
            mock_settings.supported_formats_list = ['jpg', 'jpeg', 'png']
            
            files = {"file": ("test.txt", text_content, "text/plain")}
            response = client.post("/upload", files=files)
        
        assert response.status_code == 400
        assert "Unsupported file format" in response.json()["detail"]
    
    def test_upload_invoice_no_filename(self, client):
        """Test upload without filename"""
        files = {"file": ("", io.BytesIO(b"content"), "image/jpeg")}
        response = client.post("/upload", files=files)
        
        assert response.status_code == 400
        assert "No filename provided" in response.json()["detail"]
    
    def test_get_processing_results(self, client, mock_services):
        """Test getting processing results"""
        mock_processor, mock_monitor = mock_services
        
        # Mock results
        mock_results = [
            {
                "file_id": "test123",
                "original_filename": "test.jpg",
                "status": "success",
                "processing_time": 2.5,
                "created_at": "2024-01-01T12:00:00Z"
            }
        ]
        mock_processor.get_recent_results.return_value = AsyncMock(return_value=mock_results)
        
        response = client.get("/results")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["file_id"] == "test123"
    
    def test_get_processing_results_with_limit(self, client, mock_services):
        """Test getting processing results with limit"""
        mock_processor, mock_monitor = mock_services
        
        response = client.get("/results?limit=10")
        
        assert response.status_code == 200
        # Verify limit parameter was passed
        mock_processor.get_recent_results.assert_called_with(10)
    
    def test_get_processing_results_service_unavailable(self, client):
        """Test getting results when service is unavailable"""
        with patch('src.api.main.invoice_processor', None):
            response = client.get("/results")
            assert response.status_code == 503
    
    def test_delete_processing_result_success(self, client, mock_services):
        """Test successful result deletion"""
        mock_processor, mock_monitor = mock_services
        
        file_id = "test123"
        response = client.delete(f"/results/{file_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted successfully" in data["message"]
        assert data["data"]["file_id"] == file_id
        
        # Verify delete was called
        mock_processor.delete_result.assert_called_with(file_id)
    
    def test_delete_processing_result_not_found(self, client, mock_services):
        """Test deleting non-existent result"""
        mock_processor, mock_monitor = mock_services
        mock_processor.delete_result.return_value = AsyncMock(return_value=False)
        
        file_id = "nonexistent"
        response = client.delete(f"/results/{file_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_delete_processing_result_service_unavailable(self, client):
        """Test deleting result when service is unavailable"""
        with patch('src.api.main.invoice_processor', None):
            response = client.delete("/results/test123")
            assert response.status_code == 503
    
    def test_get_recent_logs(self, client):
        """Test getting recent logs"""
        response = client.get("/logs")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Currently returns empty list as placeholder
        assert len(data) == 0
    
    def test_get_recent_logs_with_limit(self, client):
        """Test getting recent logs with limit"""
        response = client.get("/logs?limit=50")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.options("/")
        
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "*"
    
    def test_api_error_handling(self, client, mock_services):
        """Test API error handling"""
        mock_processor, mock_monitor = mock_services
        
        # Mock an exception
        mock_processor.get_statistics.side_effect = Exception("Test error")
        
        response = client.get("/stats")
        
        assert response.status_code == 500
        assert "Test error" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_background_task_execution(self, client, mock_services):
        """Test that background tasks are executed"""
        mock_processor, mock_monitor = mock_services
        
        request_data = {
            "file_path": "test.jpg",
            "force_reprocess": True
        }
        
        response = client.post("/process", json=request_data)
        
        assert response.status_code == 200
        
        # Wait a bit for background task
        await asyncio.sleep(0.1)
        
        # Background task should have been executed
        # Note: This is difficult to test directly with TestClient
        # In a real scenario, you might use a different approach

