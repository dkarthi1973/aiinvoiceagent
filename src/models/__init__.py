"""
Data models for the AI Invoice Processing Agent
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    """Processing status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"


class FileType(str, Enum):
    """Supported file types"""
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    PDF = "pdf"
    TIFF = "tiff"


class InvoiceData(BaseModel):
    """Structured invoice data model"""
    invoice_number: Optional[str] = Field(None, description="Invoice number")
    date: Optional[str] = Field(None, description="Invoice date")
    due_date: Optional[str] = Field(None, description="Due date")
    vendor_name: Optional[str] = Field(None, description="Vendor/supplier name")
    vendor_address: Optional[str] = Field(None, description="Vendor address")
    customer_name: Optional[str] = Field(None, description="Customer name")
    customer_address: Optional[str] = Field(None, description="Customer address")
    total_amount: Optional[float] = Field(None, description="Total amount")
    tax_amount: Optional[float] = Field(None, description="Tax amount")
    subtotal: Optional[float] = Field(None, description="Subtotal amount")
    currency: Optional[str] = Field(None, description="Currency code")
    line_items: List[Dict[str, Any]] = Field(default_factory=list, description="Invoice line items")
    payment_terms: Optional[str] = Field(None, description="Payment terms")
    notes: Optional[str] = Field(None, description="Additional notes")


class ProcessingResult(BaseModel):
    """Processing result model"""
    file_id: str = Field(..., description="Unique file identifier")
    original_filename: str = Field(..., description="Original filename")
    processed_filename: str = Field(..., description="Processed filename")
    status: ProcessingStatus = Field(..., description="Processing status")
    invoice_data: Optional[InvoiceData] = Field(None, description="Extracted invoice data")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")


class SystemStats(BaseModel):
    """System statistics model"""
    total_processed: int = Field(0, description="Total files processed")
    successful: int = Field(0, description="Successfully processed files")
    failed: int = Field(0, description="Failed processing files")
    pending: int = Field(0, description="Pending files")
    processing: int = Field(0, description="Currently processing files")
    average_processing_time: float = Field(0.0, description="Average processing time")
    uptime: str = Field("", description="System uptime")


class APIResponse(BaseModel):
    """Standard API response model"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class ProcessingRequest(BaseModel):
    """Manual processing request model"""
    file_path: Optional[str] = Field(None, description="Specific file path to process")
    force_reprocess: bool = Field(False, description="Force reprocessing of already processed files")


class LogEntry(BaseModel):
    """Log entry model"""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Log timestamp")
    level: str = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    module: str = Field(..., description="Module name")
    file_id: Optional[str] = Field(None, description="Related file ID")


class HealthCheck(BaseModel):
    """Health check response model"""
    status: str = Field("healthy", description="Service status")
    version: str = Field("1.0.0", description="Application version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    services: Dict[str, str] = Field(default_factory=dict, description="Service statuses")

