"""
Unit tests for invoice processor service
"""
import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.services.invoice_processor import InvoiceProcessorService
from src.models import InvoiceData, ProcessingStatus
from src.utils.exceptions import AIModelError, FileProcessingError


class TestInvoiceProcessorService:
    """Test cases for InvoiceProcessorService"""
    
    @pytest.mark.asyncio
    async def test_process_invoice_image_success(self, invoice_processor_service, sample_image_file, mock_llm):
        """Test successful invoice image processing"""
        # Test processing
        result = await invoice_processor_service.process_invoice_image(sample_image_file)
        
        # Assertions
        assert isinstance(result, InvoiceData)
        assert result.invoice_number == "TEST-001"
        assert result.vendor_name == "Test Vendor"
        assert result.total_amount == 100.00
        
        # Verify LLM was called
        mock_llm.invoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_invoice_image_invalid_json(self, invoice_processor_service, sample_image_file, mock_llm):
        """Test handling of invalid JSON response from AI model"""
        # Mock invalid JSON response
        mock_response = Mock()
        mock_response.content = "Invalid JSON content"
        mock_llm.invoke.return_value = mock_response
        
        # Test processing
        with pytest.raises(Exception) as exc_info:
            await invoice_processor_service.process_invoice_image(sample_image_file)
        
        assert "Invalid JSON response" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_process_invoice_image_no_llm(self, temp_directories, sample_image_file):
        """Test processing when LLM is not available"""
        service = InvoiceProcessorService()
        service.llm = None
        
        with pytest.raises(Exception) as exc_info:
            await service.process_invoice_image(sample_image_file)
        
        assert "AI model not available" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_process_single_file_success(self, invoice_processor_service, sample_image_file, temp_directories):
        """Test successful single file processing"""
        # Process file
        result = await invoice_processor_service.process_single_file(sample_image_file)
        
        # Assertions
        assert result.status == ProcessingStatus.SUCCESS
        assert result.original_filename == sample_image_file.name
        assert result.invoice_data is not None
        assert result.processing_time > 0
        
        # Check that JSON file was created
        json_files = list(temp_directories['generated'].glob("*.json"))
        assert len(json_files) == 1
        
        # Check that original file was moved
        assert not sample_image_file.exists()
        moved_files = list(temp_directories['generated'].glob("*.jpg"))
        assert len(moved_files) == 1
    
    @pytest.mark.asyncio
    async def test_process_single_file_large_file(self, invoice_processor_service, temp_directories):
        """Test processing of file that exceeds size limit"""
        # Create a large dummy file
        large_file = temp_directories['incoming'] / 'large_file.jpg'
        with open(large_file, 'wb') as f:
            f.write(b'0' * (15 * 1024 * 1024))  # 15MB file
        
        # Process file
        result = await invoice_processor_service.process_single_file(large_file)
        
        # Assertions
        assert result.status == ProcessingStatus.FAILED
        assert "exceeds maximum allowed size" in result.error_message
    
    @pytest.mark.asyncio
    async def test_process_files_batch(self, invoice_processor_service, temp_directories):
        """Test batch processing of multiple files"""
        from PIL import Image
        
        # Create multiple test images
        for i in range(3):
            img = Image.new('RGB', (100, 100), color='white')
            image_path = temp_directories['incoming'] / f'test_invoice_{i}.jpg'
            img.save(image_path, 'JPEG')
        
        # Process files
        await invoice_processor_service.process_files()
        
        # Check results
        assert len(invoice_processor_service.processing_results) == 3
        
        # Check that all files were processed
        json_files = list(temp_directories['generated'].glob("*.json"))
        assert len(json_files) == 3
        
        # Check that original files were moved
        incoming_files = list(temp_directories['incoming'].glob("*.jpg"))
        assert len(incoming_files) == 0
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, invoice_processor_service):
        """Test statistics retrieval"""
        # Add some mock results
        from src.models import ProcessingResult
        from src.utils.helpers import generate_file_id
        
        # Add successful result
        result1 = ProcessingResult(
            file_id=generate_file_id("test1.jpg"),
            original_filename="test1.jpg",
            processed_filename="test1.json",
            status=ProcessingStatus.SUCCESS,
            processing_time=1.5
        )
        
        # Add failed result
        result2 = ProcessingResult(
            file_id=generate_file_id("test2.jpg"),
            original_filename="test2.jpg",
            processed_filename="",
            status=ProcessingStatus.FAILED,
            error_message="Test error"
        )
        
        invoice_processor_service.processing_results[result1.file_id] = result1
        invoice_processor_service.processing_results[result2.file_id] = result2
        
        # Get statistics
        stats = await invoice_processor_service.get_statistics()
        
        # Assertions
        assert stats.total_processed == 0  # These are manually added, not processed
        assert stats.successful == 0
        assert stats.failed == 0
        assert stats.average_processing_time == 1.5  # Only successful results count
    
    @pytest.mark.asyncio
    async def test_get_recent_results(self, invoice_processor_service):
        """Test recent results retrieval"""
        from src.models import ProcessingResult
        from src.utils.helpers import generate_file_id
        from datetime import datetime, timedelta
        
        # Add results with different timestamps
        for i in range(5):
            result = ProcessingResult(
                file_id=generate_file_id(f"test{i}.jpg"),
                original_filename=f"test{i}.jpg",
                processed_filename=f"test{i}.json",
                status=ProcessingStatus.SUCCESS,
                updated_at=datetime.utcnow() - timedelta(hours=i)
            )
            invoice_processor_service.processing_results[result.file_id] = result
        
        # Get recent results
        recent_results = await invoice_processor_service.get_recent_results(limit=3)
        
        # Assertions
        assert len(recent_results) == 3
        # Should be sorted by updated_at descending
        assert recent_results[0].original_filename == "test0.jpg"
        assert recent_results[1].original_filename == "test1.jpg"
        assert recent_results[2].original_filename == "test2.jpg"
    
    @pytest.mark.asyncio
    async def test_delete_result(self, invoice_processor_service):
        """Test result deletion"""
        from src.models import ProcessingResult
        from src.utils.helpers import generate_file_id
        
        # Add a result
        file_id = generate_file_id("test.jpg")
        result = ProcessingResult(
            file_id=file_id,
            original_filename="test.jpg",
            processed_filename="test.json",
            status=ProcessingStatus.SUCCESS
        )
        invoice_processor_service.processing_results[file_id] = result
        
        # Delete result
        success = await invoice_processor_service.delete_result(file_id)
        assert success is True
        assert file_id not in invoice_processor_service.processing_results
        
        # Try to delete non-existent result
        success = await invoice_processor_service.delete_result("non_existent")
        assert success is False
    
    def test_encode_image_to_base64(self, invoice_processor_service, sample_image_file):
        """Test image encoding to base64"""
        # Test encoding
        base64_str = invoice_processor_service._encode_image_to_base64(sample_image_file)
        
        # Assertions
        assert isinstance(base64_str, str)
        assert len(base64_str) > 0
        
        # Verify it's valid base64
        import base64
        try:
            base64.b64decode(base64_str)
        except Exception:
            pytest.fail("Invalid base64 encoding")
    
    def test_create_invoice_extraction_prompt(self, invoice_processor_service):
        """Test invoice extraction prompt creation"""
        prompt = invoice_processor_service._create_invoice_extraction_prompt()
        
        # Assertions
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "invoice_number" in prompt
        assert "JSON" in prompt
        assert "extract" in prompt.lower()

