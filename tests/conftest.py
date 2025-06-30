"""
Test configuration and fixtures
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock
import json

from config.settings import Settings
from src.services.invoice_processor import InvoiceProcessorService
from src.services.file_monitor import FileMonitorService
from src.models import InvoiceData, ProcessingResult, ProcessingStatus


@pytest.fixture
def temp_directories():
    """Create temporary directories for testing"""
    temp_dir = Path(tempfile.mkdtemp())
    
    directories = {
        'incoming': temp_dir / 'incoming',
        'generated': temp_dir / 'generated',
        'logs': temp_dir / 'logs'
    }
    
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    
    yield directories
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_settings(temp_directories):
    """Create test settings with temporary directories"""
    settings = Settings(
        incoming_folder=str(temp_directories['incoming']),
        generated_folder=str(temp_directories['generated']),
        log_folder=str(temp_directories['logs']),
        debug=True,
        processing_interval_seconds=1,
        batch_size=5
    )
    return settings


@pytest.fixture
def mock_llm():
    """Mock LangChain LLM for testing"""
    mock = Mock()
    
    # Mock successful response
    mock_response = Mock()
    mock_response.content = json.dumps({
        "invoice_number": "TEST-001",
        "date": "2024-01-15",
        "vendor_name": "Test Vendor",
        "total_amount": 100.00,
        "currency": "USD",
        "line_items": [
            {
                "description": "Test Item",
                "quantity": 1,
                "unit_price": 100.00,
                "total": 100.00
            }
        ]
    })
    
    # Make invoke return the mock response directly (not async)
    mock.invoke.return_value = mock_response
    return mock


@pytest.fixture
def sample_invoice_data():
    """Sample invoice data for testing"""
    return InvoiceData(
        invoice_number="TEST-001",
        date="2024-01-15",
        vendor_name="Test Vendor",
        total_amount=100.00,
        currency="USD",
        line_items=[
            {
                "description": "Test Item",
                "quantity": 1,
                "unit_price": 100.00,
                "total": 100.00
            }
        ]
    )


@pytest.fixture
def sample_image_file(temp_directories):
    """Create a sample image file for testing"""
    from PIL import Image
    
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='white')
    image_path = temp_directories['incoming'] / 'test_invoice.jpg'
    img.save(image_path, 'JPEG')
    
    return image_path


@pytest.fixture
def invoice_processor_service(test_settings, mock_llm):
    """Create invoice processor service with mocked dependencies"""
    service = InvoiceProcessorService()
    service.llm = mock_llm
    return service


@pytest.fixture
def file_monitor_service(invoice_processor_service):
    """Create file monitor service"""
    return FileMonitorService(invoice_processor_service)


@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

