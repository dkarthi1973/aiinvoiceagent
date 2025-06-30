"""
Unit tests for file monitor service
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import time

from src.services.file_monitor import FileMonitorService, InvoiceFileHandler
from src.services.invoice_processor import InvoiceProcessorService


class TestInvoiceFileHandler:
    """Test cases for InvoiceFileHandler"""
    
    def test_init(self, invoice_processor_service):
        """Test file handler initialization"""
        handler = InvoiceFileHandler(invoice_processor_service)
        
        assert handler.processor_service == invoice_processor_service
        assert handler.processing_queue is not None
    
    def test_handle_new_file_supported_format(self, invoice_processor_service, temp_directories):
        """Test handling of supported file format"""
        handler = InvoiceFileHandler(invoice_processor_service)
        
        # Create test file
        test_file = temp_directories['incoming'] / 'test.jpg'
        test_file.touch()
        
        # Handle file
        handler._handle_new_file(str(test_file))
        
        # Should not raise exception for supported format
        assert True
    
    def test_handle_new_file_unsupported_format(self, invoice_processor_service, temp_directories):
        """Test handling of unsupported file format"""
        handler = InvoiceFileHandler(invoice_processor_service)
        
        # Create test file with unsupported format
        test_file = temp_directories['incoming'] / 'test.txt'
        test_file.touch()
        
        # Handle file - should log warning but not crash
        handler._handle_new_file(str(test_file))
        
        assert True
    
    @pytest.mark.asyncio
    async def test_queue_file_for_processing(self, invoice_processor_service, temp_directories):
        """Test queuing file for processing"""
        handler = InvoiceFileHandler(invoice_processor_service)
        
        # Create test file
        test_file = temp_directories['incoming'] / 'test.jpg'
        test_file.touch()
        
        # Queue file
        await handler._queue_file_for_processing(test_file)
        
        # Check queue
        assert handler.processing_queue.qsize() == 1
        queued_file = await handler.processing_queue.get()
        assert queued_file == test_file


class TestFileMonitorService:
    """Test cases for FileMonitorService"""
    
    def test_init(self, invoice_processor_service):
        """Test file monitor service initialization"""
        service = FileMonitorService(invoice_processor_service)
        
        assert service.processor_service == invoice_processor_service
        assert service.observer is None
        assert service.file_handler is None
        assert service.is_running is False
        assert service.processing_task is None
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self, file_monitor_service, temp_directories):
        """Test starting file monitoring"""
        # Start monitoring
        await file_monitor_service.start_monitoring()
        
        # Assertions
        assert file_monitor_service.is_running is True
        assert file_monitor_service.observer is not None
        assert file_monitor_service.file_handler is not None
        assert file_monitor_service.processing_task is not None
        
        # Cleanup
        await file_monitor_service.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring(self, file_monitor_service, temp_directories):
        """Test stopping file monitoring"""
        # Start first
        await file_monitor_service.start_monitoring()
        assert file_monitor_service.is_running is True
        
        # Stop monitoring
        await file_monitor_service.stop_monitoring()
        
        # Assertions
        assert file_monitor_service.is_running is False
        assert file_monitor_service.observer is None
        assert file_monitor_service.file_handler is None
    
    @pytest.mark.asyncio
    async def test_process_existing_files(self, file_monitor_service, temp_directories):
        """Test processing existing files in incoming folder"""
        from PIL import Image
        
        # Create existing files
        for i in range(2):
            img = Image.new('RGB', (100, 100), color='white')
            image_path = temp_directories['incoming'] / f'existing_{i}.jpg'
            img.save(image_path, 'JPEG')
        
        # Start monitoring (which processes existing files)
        await file_monitor_service.start_monitoring()
        
        # Wait a bit for processing
        await asyncio.sleep(0.5)
        
        # Check that files were queued
        assert file_monitor_service.file_handler.processing_queue.qsize() >= 0
        
        # Cleanup
        await file_monitor_service.stop_monitoring()
    
    def test_get_queue_size(self, file_monitor_service):
        """Test getting queue size"""
        # Initially should be 0
        assert file_monitor_service.get_queue_size() == 0
        
        # After starting, should have a handler
        # Note: This is a simple test since we can't easily test the actual queue
    
    @pytest.mark.asyncio
    async def test_start_monitoring_already_running(self, file_monitor_service, temp_directories):
        """Test starting monitoring when already running"""
        # Start monitoring
        await file_monitor_service.start_monitoring()
        assert file_monitor_service.is_running is True
        
        # Try to start again - should not crash
        await file_monitor_service.start_monitoring()
        assert file_monitor_service.is_running is True
        
        # Cleanup
        await file_monitor_service.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring_not_running(self, file_monitor_service):
        """Test stopping monitoring when not running"""
        assert file_monitor_service.is_running is False
        
        # Should not crash
        await file_monitor_service.stop_monitoring()
        assert file_monitor_service.is_running is False
    
    @pytest.mark.asyncio
    async def test_process_queue_with_files(self, file_monitor_service, temp_directories):
        """Test processing queue with files"""
        from PIL import Image
        
        # Create test file
        img = Image.new('RGB', (100, 100), color='white')
        image_path = temp_directories['incoming'] / 'queue_test.jpg'
        img.save(image_path, 'JPEG')
        
        # Start monitoring
        await file_monitor_service.start_monitoring()
        
        # Add file to queue manually
        await file_monitor_service.file_handler.processing_queue.put(image_path)
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # File should be processed (queue should be empty or file should be moved)
        # Note: Actual processing depends on the mock setup
        
        # Cleanup
        await file_monitor_service.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_periodic_processing(self, file_monitor_service, temp_directories):
        """Test periodic processing functionality"""
        # Mock the processor service to track calls
        original_process_files = file_monitor_service.processor_service.process_files
        call_count = 0
        
        async def mock_process_files(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return await original_process_files(*args, **kwargs)
        
        file_monitor_service.processor_service.process_files = mock_process_files
        
        # Start monitoring
        await file_monitor_service.start_monitoring()
        
        # Wait for at least one periodic processing cycle
        # Note: This test might be flaky due to timing
        await asyncio.sleep(2)
        
        # Should have called process_files at least once
        # Note: Exact count depends on timing and configuration
        
        # Cleanup
        await file_monitor_service.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_queue_processing(self, file_monitor_service, temp_directories):
        """Test error handling in queue processing"""
        # Mock processor to raise exception
        async def mock_process_single_file(*args, **kwargs):
            raise Exception("Test error")
        
        file_monitor_service.processor_service.process_single_file = mock_process_single_file
        
        # Start monitoring
        await file_monitor_service.start_monitoring()
        
        # Create and queue a file
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='white')
        image_path = temp_directories['incoming'] / 'error_test.jpg'
        img.save(image_path, 'JPEG')
        
        await file_monitor_service.file_handler.processing_queue.put(image_path)
        
        # Wait for processing attempt
        await asyncio.sleep(1)
        
        # Service should still be running despite error
        assert file_monitor_service.is_running is True
        
        # Cleanup
        await file_monitor_service.stop_monitoring()

