"""
FastAPI main application module
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import settings
from src.models import (
    APIResponse, SystemStats, ProcessingRequest, 
    HealthCheck, LogEntry, ProcessingResult
)
from src.services.invoice_processor import InvoiceProcessorService
from src.services.file_monitor import FileMonitorService
from src.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Global services
invoice_processor: InvoiceProcessorService = None
file_monitor: FileMonitorService = None
app_start_time = datetime.utcnow()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global invoice_processor, file_monitor
    
    logger.info("Starting AI Invoice Processing Agent...")
    
    # Initialize services
    invoice_processor = InvoiceProcessorService()
    file_monitor = FileMonitorService(invoice_processor)
    
    # Start file monitoring
    await file_monitor.start_monitoring()
    
    logger.info("Application started successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down application...")
    if file_monitor:
        await file_monitor.stop_monitoring()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise AI agent for automated invoice processing",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    uptime = datetime.utcnow() - app_start_time
    
    services_status = {
        "invoice_processor": "healthy" if invoice_processor else "unavailable",
        "file_monitor": "healthy" if file_monitor and file_monitor.is_running else "stopped",
        "ai_model": "healthy"  # TODO: Add actual AI model health check
    }
    
    return HealthCheck(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.utcnow(),
        services=services_status
    )


@app.get("/status", response_model=APIResponse)
async def get_system_status():
    """Get detailed system status"""
    try:
        stats = await get_processing_stats()
        uptime = str(datetime.utcnow() - app_start_time)
        
        status_data = {
            "uptime": uptime,
            "stats": stats.dict(),
            "settings": {
                "incoming_folder": str(settings.incoming_path),
                "generated_folder": str(settings.generated_path),
                "processing_interval": settings.processing_interval_seconds,
                "supported_formats": settings.supported_formats_list,
                "ai_timeout": settings.ai_processing_timeout_seconds,
                "ollama_timeout": settings.ollama_request_timeout_seconds
            }
        }
        
        return APIResponse(
            success=True,
            message="System status retrieved successfully",
            data=status_data
        )
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=SystemStats)
async def get_processing_stats():
    """Get processing statistics"""
    try:
        if not invoice_processor:
            raise HTTPException(status_code=503, detail="Invoice processor not available")
        
        stats = await invoice_processor.get_statistics()
        uptime = str(datetime.utcnow() - app_start_time)
        stats.uptime = uptime
        
        return stats
    except Exception as e:
        logger.error(f"Error getting processing stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process", response_model=APIResponse)
async def trigger_processing(
    request: ProcessingRequest,
    background_tasks: BackgroundTasks
):
    """Manually trigger file processing"""
    try:
        if not invoice_processor:
            raise HTTPException(status_code=503, detail="Invoice processor not available")
        
        # Add processing task to background
        background_tasks.add_task(
            invoice_processor.process_files,
            specific_file=request.file_path,
            force_reprocess=request.force_reprocess
        )
        
        return APIResponse(
            success=True,
            message="Processing triggered successfully",
            data={"request": request.dict()}
        )
    except Exception as e:
        logger.error(f"Error triggering processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload", response_model=APIResponse)
async def upload_invoice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Upload invoice file for processing"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file format
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in settings.supported_formats_list:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Supported: {settings.supported_formats_list}"
            )
        
        # Save file to incoming folder
        file_path = settings.incoming_path / file.filename
        
        # Handle duplicate filenames
        counter = 1
        original_path = file_path
        while file_path.exists():
            name_parts = original_path.stem, counter, original_path.suffix
            file_path = original_path.parent / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
            counter += 1
        
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"File uploaded successfully: {file_path}")
        
        # Trigger background processing (don't wait for completion)
        if invoice_processor:
            background_tasks.add_task(
                invoice_processor.process_files,
                specific_file=str(file_path)
            )
        
        return APIResponse(
            success=True,
            message="File uploaded successfully and queued for processing",
            data={
                "filename": file_path.name, 
                "size": len(content),
                "status": "queued_for_processing",
                "note": "Processing will happen in background. Check /results endpoint for status."
            }
        )
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/results", response_model=List[ProcessingResult])
async def get_processing_results(limit: int = 50):
    """Get recent processing results"""
    try:
        if not invoice_processor:
            raise HTTPException(status_code=503, detail="Invoice processor not available")
        
        results = await invoice_processor.get_recent_results(limit)
        return results
    except Exception as e:
        logger.error(f"Error getting processing results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/results/{file_id}", response_model=ProcessingResult)
async def get_processing_result(file_id: str):
    """Get specific processing result by file ID"""
    try:
        if not invoice_processor:
            raise HTTPException(status_code=503, detail="Invoice processor not available")
        
        result = invoice_processor.processing_results.get(file_id)
        if not result:
            raise HTTPException(status_code=404, detail="Processing result not found")
        
        return result
    except Exception as e:
        logger.error(f"Error getting processing result: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs", response_model=List[LogEntry])
async def get_recent_logs(limit: int = 100):
    """Get recent log entries"""
    try:
        # TODO: Implement log retrieval from log files
        # For now, return empty list
        return []
    except Exception as e:
        logger.error(f"Error getting logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/results/{file_id}", response_model=APIResponse)
async def delete_processing_result(file_id: str):
    """Delete a processing result"""
    try:
        if not invoice_processor:
            raise HTTPException(status_code=503, detail="Invoice processor not available")
        
        success = await invoice_processor.delete_result(file_id)
        
        if success:
            return APIResponse(
                success=True,
                message="Processing result deleted successfully",
                data={"file_id": file_id}
            )
        else:
            raise HTTPException(status_code=404, detail="Processing result not found")
    except Exception as e:
        logger.error(f"Error deleting processing result: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_keep_alive=3600,  # 1 hour keep-alive timeout
        timeout_graceful_shutdown=60  # 1 minute graceful shutdown
    )

