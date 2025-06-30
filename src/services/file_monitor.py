"""
File monitoring service for automatic invoice processing
"""
import asyncio
from pathlib import Path
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

from config.settings import settings
from src.utils.helpers import is_supported_format
from src.utils.logger import get_logger

logger = get_logger(__name__)


class InvoiceFileHandler(FileSystemEventHandler):
    """File system event handler for invoice files"""
    
    def __init__(self, processor_service):
        super().__init__()
        self.processor_service = processor_service
        self.processing_queue = asyncio.Queue()
    
    def on_created(self, event):
        """Handle file creation events"""
        if not event.is_directory:
            self._handle_new_file(event.src_path)
    
    def on_moved(self, event):
        """Handle file move events"""
        if not event.is_directory:
            self._handle_new_file(event.dest_path)
    
    def _handle_new_file(self, file_path: str):
        """Handle new file detection"""
        try:
            path = Path(file_path)
            
            # Check if file format is supported
            if is_supported_format(path.name, settings.supported_formats_list):
                logger.info(f"New invoice file detected: {path.name}")
                
                # Add to processing queue
                asyncio.create_task(self._queue_file_for_processing(path))
            else:
                logger.warning(f"Unsupported file format detected: {path.name}")
        
        except Exception as e:
            logger.error(f"Error handling new file {file_path}: {str(e)}")
    
    async def _queue_file_for_processing(self, file_path: Path):
        """Queue file for processing"""
        try:
            # Wait a bit to ensure file is fully written
            await asyncio.sleep(2)
            
            # Check if file still exists and is readable
            if file_path.exists() and file_path.is_file():
                await self.processing_queue.put(file_path)
                logger.info(f"Queued file for processing: {file_path.name}")
            else:
                logger.warning(f"File no longer exists or not readable: {file_path}")
        
        except Exception as e:
            logger.error(f"Error queuing file {file_path}: {str(e)}")


class FileMonitorService:
    """Service for monitoring incoming folder and processing files"""
    
    def __init__(self, processor_service):
        self.processor_service = processor_service
        self.observer: Optional[Observer] = None
        self.file_handler: Optional[InvoiceFileHandler] = None
        self.is_running = False
        self.processing_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self):
        """Start file monitoring"""
        try:
            if self.is_running:
                logger.warning("File monitoring is already running")
                return
            
            logger.info("Starting file monitoring service...")
            
            # Ensure incoming directory exists
            settings.incoming_path.mkdir(parents=True, exist_ok=True)
            
            # Create file handler
            self.file_handler = InvoiceFileHandler(self.processor_service)
            
            # Create and start observer
            self.observer = Observer()
            self.observer.schedule(
                self.file_handler,
                str(settings.incoming_path),
                recursive=False
            )
            self.observer.start()
            
            # Start processing task
            self.processing_task = asyncio.create_task(self._process_queue())
            
            # Start periodic processing task
            asyncio.create_task(self._periodic_processing())
            
            self.is_running = True
            logger.info(f"File monitoring started for: {settings.incoming_path}")
            
            # Process any existing files
            await self._process_existing_files()
            
        except Exception as e:
            logger.error(f"Error starting file monitoring: {str(e)}")
            await self.stop_monitoring()
            raise
    
    async def stop_monitoring(self):
        """Stop file monitoring"""
        try:
            if not self.is_running:
                return
            
            logger.info("Stopping file monitoring service...")
            
            self.is_running = False
            
            # Stop observer
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5)
                self.observer = None
            
            # Cancel processing task
            if self.processing_task and not self.processing_task.done():
                self.processing_task.cancel()
                try:
                    await self.processing_task
                except asyncio.CancelledError:
                    pass
            
            self.file_handler = None
            logger.info("File monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping file monitoring: {str(e)}")
    
    async def _process_queue(self):
        """Process files from the queue"""
        while self.is_running:
            try:
                if self.file_handler:
                    # Wait for file with timeout
                    try:
                        file_path = await asyncio.wait_for(
                            self.file_handler.processing_queue.get(),
                            timeout=1.0
                        )
                        
                        # Process the file
                        await self.processor_service.process_single_file(file_path)
                        
                    except asyncio.TimeoutError:
                        # No file in queue, continue
                        continue
                else:
                    await asyncio.sleep(1)
            
            except Exception as e:
                logger.error(f"Error in queue processing: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _periodic_processing(self):
        """Periodic processing of incoming folder"""
        while self.is_running:
            try:
                await asyncio.sleep(settings.processing_interval_seconds)
                
                # Process any files that might have been missed
                await self.processor_service.process_files()
                
            except Exception as e:
                logger.error(f"Error in periodic processing: {str(e)}")
                await asyncio.sleep(30)  # Wait longer on error
    
    async def _process_existing_files(self):
        """Process any existing files in the incoming folder"""
        try:
            incoming_path = settings.incoming_path
            supported_formats = settings.supported_formats_list
            
            existing_files = []
            for file_path in incoming_path.iterdir():
                if file_path.is_file() and is_supported_format(file_path.name, supported_formats):
                    existing_files.append(file_path)
            
            if existing_files:
                logger.info(f"Found {len(existing_files)} existing files to process")
                
                # Queue existing files for processing
                if self.file_handler:
                    for file_path in existing_files:
                        await self.file_handler.processing_queue.put(file_path)
            
        except Exception as e:
            logger.error(f"Error processing existing files: {str(e)}")
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        if self.file_handler:
            return self.file_handler.processing_queue.qsize()
        return 0

