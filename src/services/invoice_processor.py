"""
Invoice processing service using LangChain and AI models
"""
import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from PIL import Image
import base64
import io

from config.settings import settings
from src.models import (
    InvoiceData, ProcessingResult, ProcessingStatus, 
    SystemStats
)
from src.utils.helpers import (
    generate_file_id, create_timestamped_filename,
    ensure_unique_filename, get_file_size_mb
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class InvoiceProcessorService:
    """Service for processing invoice images and extracting data"""
    
    def __init__(self):
        self.processing_results: Dict[str, ProcessingResult] = {}
        self.stats = SystemStats()
        self.is_processing = False
        
        # Initialize AI model
        try:
            self.llm = ChatOllama(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                temperature=0.1,
                timeout=settings.ollama_request_timeout_seconds
            )
            logger.info(f"Initialized Ollama model: {settings.ollama_model}")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama model: {str(e)}")
            self.llm = None
    
    def _encode_image_to_base64(self, image_path: Path) -> str:
        """Encode image to base64 string"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large (max 1024x1024 for better processing)
                max_size = 1024
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Convert to base64
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                img_str = base64.b64encode(buffer.getvalue()).decode()
                return img_str
        except Exception as e:
            logger.error(f"Error encoding image {image_path}: {str(e)}")
            raise
    
    def _create_invoice_extraction_prompt(self) -> str:
        """Create prompt for invoice data extraction"""
        return """
You are an expert invoice data extraction AI. Analyze the provided invoice image and extract all relevant information into a structured JSON format.

Extract the following information if available:
- invoice_number: The invoice number
- date: Invoice date (format: YYYY-MM-DD)
- due_date: Payment due date (format: YYYY-MM-DD)
- vendor_name: Name of the vendor/supplier
- vendor_address: Complete vendor address
- customer_name: Name of the customer/buyer
- customer_address: Complete customer address
- total_amount: Total amount (numeric value only)
- tax_amount: Tax amount (numeric value only)
- subtotal: Subtotal amount (numeric value only)
- currency: Currency code (e.g., USD, EUR, GBP)
- payment_terms: Payment terms description
- notes: Any additional notes or special instructions
- line_items: Array of line items with description, quantity, unit_price, and total

Return ONLY a valid JSON object with the extracted data. Use null for missing information.
Ensure all numeric values are numbers, not strings.
For dates, use YYYY-MM-DD format.

Example response:
{
    "invoice_number": "INV-2024-001",
    "date": "2024-01-15",
    "due_date": "2024-02-15",
    "vendor_name": "ABC Company Ltd",
    "vendor_address": "123 Business St, City, State 12345",
    "customer_name": "XYZ Corp",
    "customer_address": "456 Customer Ave, City, State 67890",
    "total_amount": 1250.00,
    "tax_amount": 125.00,
    "subtotal": 1125.00,
    "currency": "USD",
    "payment_terms": "Net 30",
    "notes": null,
    "line_items": [
        {
            "description": "Product A",
            "quantity": 2,
            "unit_price": 500.00,
            "total": 1000.00
        },
        {
            "description": "Service B",
            "quantity": 1,
            "unit_price": 125.00,
            "total": 125.00
        }
    ]
}
"""
    
    async def process_invoice_image(self, image_path: Path) -> InvoiceData:
        """Process a single invoice image and extract data"""
        if not self.llm:
            raise Exception("AI model not available")
        
        try:
            logger.info(f"Processing invoice image: {image_path}")
            
            # Encode image to base64
            image_base64 = self._encode_image_to_base64(image_path)
            
            # Create message with image
            message = HumanMessage(
                content=[
                    {"type": "text", "text": self._create_invoice_extraction_prompt()},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                    }
                ]
            )
            
            # Process with AI model with timeout
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(self.llm.invoke, [message]),
                    timeout=settings.ai_processing_timeout_seconds
                )
            except asyncio.TimeoutError:
                raise Exception(f"AI processing timeout after {settings.ai_processing_timeout_seconds} seconds")
            
            # Parse JSON response - handle markdown formatted responses
            try:
                response_content = response.content
                logger.info(f"Raw AI response length: {len(response_content)} characters")
                
                # Try to extract JSON from markdown code blocks first
                json_match = re.search(r'```json\s*\n(.*?)\n```', response_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1).strip()
                    logger.info("Found JSON in markdown code block")
                else:
                    # Try to find JSON object directly
                    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0).strip()
                        logger.info("Found JSON object in response")
                    else:
                        # Try to extract from the structured response
                        logger.warning("No JSON block found, attempting fallback extraction")
                        fallback_data = self._extract_fallback_data(response_content)
                        if fallback_data:
                            logger.info("Using fallback data extraction")
                            return InvoiceData(**fallback_data)
                        else:
                            raise Exception("No valid JSON found in AI response")
                
                # Parse the extracted JSON
                invoice_data_dict = json.loads(json_str)
                invoice_data = InvoiceData(**invoice_data_dict)
                logger.info(f"Successfully extracted invoice data from {image_path}")
                return invoice_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                logger.error(f"Raw response: {response_content[:1000]}...")  # Log first 1000 chars
                
                # Try to extract key information manually as fallback
                try:
                    fallback_data = self._extract_fallback_data(response_content)
                    if fallback_data:
                        logger.info("Using fallback data extraction")
                        return InvoiceData(**fallback_data)
                except Exception as fallback_error:
                    logger.error(f"Fallback extraction failed: {str(fallback_error)}")
                
                raise Exception(f"Invalid JSON response from AI model: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error processing invoice image {image_path}: {str(e)}")
            raise
    
    def _extract_fallback_data(self, response_content: str) -> dict:
        """Extract invoice data using regex patterns as fallback"""
        data = {}
        
        # Extract invoice number
        invoice_patterns = [
            r'Invoice Number[:\s]*([^\n\r]+)',
            r'Invoice[:\s]*#?([0-9A-Za-z\-]+)',
            r'Invoice ID[:\s]*([^\n\r]+)'
        ]
        for pattern in invoice_patterns:
            match = re.search(pattern, response_content, re.IGNORECASE)
            if match:
                data['invoice_number'] = match.group(1).strip()
                break
        
        # Extract date
        date_patterns = [
            r'Invoice Date[:\s]*([^\n\r]+)',
            r'Date[:\s]*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})',
            r'Date[:\s]*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{2,4})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, response_content, re.IGNORECASE)
            if match:
                data['date'] = match.group(1).strip()
                break
        
        # Extract vendor name
        vendor_patterns = [
            r'Vendor Name[:\s]*([^\n\r]+)',
            r'Company[:\s]*([^\n\r]+)',
            r'From[:\s]*([^\n\r]+)'
        ]
        for pattern in vendor_patterns:
            match = re.search(pattern, response_content, re.IGNORECASE)
            if match:
                data['vendor_name'] = match.group(1).strip()
                break
        
        # Extract total amount
        total_patterns = [
            r'Total Amount[:\s]*([0-9,]+\.?[0-9]*)',
            r'Total[:\s]*([0-9,]+\.?[0-9]*)',
            r'Amount[:\s]*([0-9,]+\.?[0-9]*)'
        ]
        for pattern in total_patterns:
            match = re.search(pattern, response_content, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    data['total_amount'] = float(amount_str)
                    break
                except ValueError:
                    continue
        
        # Extract currency
        currency_match = re.search(r'Currency[:\s]*([A-Z]{3})', response_content, re.IGNORECASE)
        if currency_match:
            data['currency'] = currency_match.group(1).upper()
        
        # Set defaults for required fields
        data.setdefault('invoice_number', 'UNKNOWN')
        data.setdefault('date', 'UNKNOWN')
        data.setdefault('vendor_name', 'UNKNOWN')
        data.setdefault('total_amount', 0.0)
        data.setdefault('currency', 'USD')
        data.setdefault('line_items', [])
        
        return data if any(v != 'UNKNOWN' and v != 0.0 for v in data.values()) else None
    
    async def process_single_file(self, file_path: Path, force_reprocess: bool = False) -> ProcessingResult:
        """Process a single file with timeout protection"""
        file_id = generate_file_id(file_path.name)
        
        # Check if already processed
        if not force_reprocess and file_id in self.processing_results:
            existing_result = self.processing_results[file_id]
            if existing_result.status == ProcessingStatus.SUCCESS:
                logger.info(f"File {file_path.name} already processed successfully")
                return existing_result
        
        # Create processing result
        result = ProcessingResult(
            file_id=file_id,
            original_filename=file_path.name,
            processed_filename="",
            status=ProcessingStatus.PROCESSING
        )
        
        self.processing_results[file_id] = result
        start_time = time.time()
        
        try:
            # Check file size
            file_size_mb = get_file_size_mb(file_path)
            if file_size_mb > settings.max_file_size_mb:
                raise Exception(f"File size ({file_size_mb:.2f}MB) exceeds maximum allowed size ({settings.max_file_size_mb}MB)")
            
            # Process invoice with overall timeout
            try:
                invoice_data = await asyncio.wait_for(
                    self.process_invoice_image(file_path),
                    timeout=settings.file_processing_timeout_seconds
                )
            except asyncio.TimeoutError:
                raise Exception(f"File processing timeout after {settings.file_processing_timeout_seconds} seconds")
            
            # Create output filename
            timestamp_suffix = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            json_filename = f"{file_path.stem}_{timestamp_suffix}.json"
            json_path = settings.generated_path / json_filename
            
            # Ensure unique filename
            json_path = ensure_unique_filename(json_path)
            
            # Save JSON output
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(invoice_data.dict(), f, indent=2, ensure_ascii=False, default=str)
            
            # Move original file to generated folder
            moved_image_filename = create_timestamped_filename(file_path.name, timestamp_suffix)
            moved_image_path = settings.generated_path / moved_image_filename
            moved_image_path = ensure_unique_filename(moved_image_path)
            
            # Copy file to generated folder
            import shutil
            shutil.copy2(file_path, moved_image_path)
            
            # Remove from incoming folder
            file_path.unlink()
            
            # Update result
            processing_time = time.time() - start_time
            result.status = ProcessingStatus.SUCCESS
            result.processed_filename = json_path.name
            result.invoice_data = invoice_data
            result.processing_time = processing_time
            result.updated_at = datetime.utcnow()
            
            # Update stats
            self.stats.total_processed += 1
            self.stats.successful += 1
            
            logger.info(f"Successfully processed {file_path.name} in {processing_time:.2f}s")
            
        except Exception as e:
            # Update result with error
            processing_time = time.time() - start_time
            result.status = ProcessingStatus.FAILED
            result.error_message = str(e)
            result.processing_time = processing_time
            result.updated_at = datetime.utcnow()
            
            # Update stats
            self.stats.total_processed += 1
            self.stats.failed += 1
            
            logger.error(f"Failed to process {file_path.name}: {str(e)}")
        
        return result
    
    async def process_files(self, specific_file: Optional[str] = None, force_reprocess: bool = False):
        """Process files in the incoming folder"""
        if self.is_processing and not specific_file:
            logger.info("Processing already in progress, skipping")
            return
        
        self.is_processing = True
        
        try:
            incoming_path = settings.incoming_path
            
            if specific_file:
                # Process specific file
                file_path = Path(specific_file)
                if not file_path.exists():
                    file_path = incoming_path / specific_file
                
                if file_path.exists() and file_path.is_file():
                    await self.process_single_file(file_path, force_reprocess)
                else:
                    logger.error(f"File not found: {specific_file}")
            else:
                # Process all files in incoming folder
                supported_formats = settings.supported_formats_list
                
                files_to_process = []
                for file_path in incoming_path.iterdir():
                    if file_path.is_file():
                        file_extension = file_path.suffix.lower().lstrip('.')
                        if file_extension in supported_formats:
                            files_to_process.append(file_path)
                
                if files_to_process:
                    logger.info(f"Found {len(files_to_process)} files to process")
                    
                    # Process files in batches
                    batch_size = settings.batch_size
                    for i in range(0, len(files_to_process), batch_size):
                        batch = files_to_process[i:i + batch_size]
                        
                        # Process batch concurrently
                        tasks = [self.process_single_file(file_path, force_reprocess) for file_path in batch]
                        await asyncio.gather(*tasks, return_exceptions=True)
                        
                        # Small delay between batches
                        if i + batch_size < len(files_to_process):
                            await asyncio.sleep(1)
                else:
                    logger.debug("No files to process in incoming folder")
        
        finally:
            self.is_processing = False
    
    async def get_statistics(self) -> SystemStats:
        """Get processing statistics"""
        # Count current processing status
        processing_count = sum(1 for result in self.processing_results.values() 
                             if result.status == ProcessingStatus.PROCESSING)
        
        self.stats.processing = processing_count
        self.stats.pending = len([f for f in settings.incoming_path.iterdir() 
                                if f.is_file() and f.suffix.lower().lstrip('.') in settings.supported_formats_list])
        
        return self.stats
    
    async def get_recent_results(self, limit: int = 50) -> List[ProcessingResult]:
        """Get recent processing results"""
        results = list(self.processing_results.values())
        # Sort by updated_at descending
        results.sort(key=lambda x: x.updated_at or datetime.min, reverse=True)
        return results[:limit]
    
    async def delete_result(self, file_id: str) -> bool:
        """Delete a processing result"""
        if file_id in self.processing_results:
            del self.processing_results[file_id]
            logger.info(f"Deleted processing result: {file_id}")
            return True
        return False

