"""
Exception handling utilities and custom exceptions
"""
import functools
import asyncio
from typing import Type, Callable, Any, Optional
from datetime import datetime

from src.utils.logger import get_logger
from src.utils.enhanced_logging import get_error_tracker

logger = get_logger(__name__)
error_tracker = get_error_tracker()


class InvoiceProcessingError(Exception):
    """Base exception for invoice processing errors"""
    
    def __init__(self, message: str, error_code: str = None, file_id: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "GENERAL_ERROR"
        self.file_id = file_id
        self.timestamp = datetime.utcnow()


class FileProcessingError(InvoiceProcessingError):
    """Exception for file processing errors"""
    
    def __init__(self, message: str, file_path: str = None, **kwargs):
        super().__init__(message, error_code="FILE_PROCESSING_ERROR", **kwargs)
        self.file_path = file_path


class AIModelError(InvoiceProcessingError):
    """Exception for AI model errors"""
    
    def __init__(self, message: str, model_name: str = None, **kwargs):
        super().__init__(message, error_code="AI_MODEL_ERROR", **kwargs)
        self.model_name = model_name


class ValidationError(InvoiceProcessingError):
    """Exception for data validation errors"""
    
    def __init__(self, message: str, field_name: str = None, **kwargs):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        self.field_name = field_name


class ConfigurationError(InvoiceProcessingError):
    """Exception for configuration errors"""
    
    def __init__(self, message: str, config_key: str = None, **kwargs):
        super().__init__(message, error_code="CONFIGURATION_ERROR", **kwargs)
        self.config_key = config_key


class FileSystemError(InvoiceProcessingError):
    """Exception for file system errors"""
    
    def __init__(self, message: str, operation: str = None, **kwargs):
        super().__init__(message, error_code="FILESYSTEM_ERROR", **kwargs)
        self.operation = operation


def handle_exceptions(
    default_return=None,
    log_error: bool = True,
    track_error: bool = True,
    reraise: bool = False,
    exception_types: tuple = (Exception,)
):
    """Decorator for handling exceptions in functions"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                if log_error:
                    logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                
                if track_error:
                    error_tracker.track_error(
                        error_type=type(e).__name__,
                        error_message=str(e),
                        context={
                            'function': func.__name__,
                            'args': str(args)[:200],  # Limit length
                            'kwargs': str(kwargs)[:200]
                        }
                    )
                
                if reraise:
                    raise
                
                return default_return
        
        return wrapper
    
    return decorator


def handle_async_exceptions(
    default_return=None,
    log_error: bool = True,
    track_error: bool = True,
    reraise: bool = False,
    exception_types: tuple = (Exception,)
):
    """Decorator for handling exceptions in async functions"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except exception_types as e:
                if log_error:
                    logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                
                if track_error:
                    error_tracker.track_error(
                        error_type=type(e).__name__,
                        error_message=str(e),
                        context={
                            'function': func.__name__,
                            'args': str(args)[:200],
                            'kwargs': str(kwargs)[:200]
                        }
                    )
                
                if reraise:
                    raise
                
                return default_return
        
        return wrapper
    
    return decorator


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exception_types: tuple = (Exception,)
):
    """Decorator for retrying functions on failure"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exception_types as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay} seconds..."
                        )
                        import time
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {str(e)}"
                        )
            
            raise last_exception
        
        return wrapper
    
    return decorator


def retry_async_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exception_types: tuple = (Exception,)
):
    """Decorator for retrying async functions on failure"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exception_types as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay} seconds..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {str(e)}"
                        )
            
            raise last_exception
        
        return wrapper
    
    return decorator


class ErrorContext:
    """Context manager for error handling with additional context"""
    
    def __init__(self, operation: str, file_id: str = None, **context):
        self.operation = operation
        self.file_id = file_id
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        logger.debug(f"Starting operation: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        if exc_type is None:
            logger.debug(f"Operation completed successfully: {self.operation} ({duration:.2f}s)")
        else:
            logger.error(
                f"Operation failed: {self.operation} ({duration:.2f}s) - {str(exc_val)}",
                exc_info=(exc_type, exc_val, exc_tb)
            )
            
            # Track error
            error_tracker.track_error(
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                file_id=self.file_id,
                context={
                    'operation': self.operation,
                    'duration_seconds': duration,
                    **self.context
                }
            )
        
        # Don't suppress exceptions
        return False


def validate_file_format(filename: str, supported_formats: list) -> bool:
    """Validate file format"""
    from pathlib import Path
    
    extension = Path(filename).suffix.lower().lstrip('.')
    if extension not in supported_formats:
        raise ValidationError(
            f"Unsupported file format: {extension}. Supported formats: {supported_formats}",
            field_name="file_format"
        )
    return True


def validate_file_size(file_path, max_size_mb: float) -> bool:
    """Validate file size"""
    from pathlib import Path
    
    file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise ValidationError(
            f"File size ({file_size_mb:.2f}MB) exceeds maximum allowed size ({max_size_mb}MB)",
            field_name="file_size"
        )
    return True


def safe_json_loads(json_str: str, default=None):
    """Safely load JSON with error handling"""
    try:
        import json
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse JSON: {str(e)}")
        error_tracker.track_error(
            error_type="JSONParseError",
            error_message=str(e),
            context={'json_preview': json_str[:100] if json_str else None}
        )
        return default


def safe_file_operation(operation: Callable, *args, **kwargs):
    """Safely perform file operations with error handling"""
    try:
        return operation(*args, **kwargs)
    except (OSError, IOError, PermissionError) as e:
        raise FileSystemError(
            f"File operation failed: {str(e)}",
            operation=operation.__name__
        )
    except Exception as e:
        raise FileProcessingError(
            f"Unexpected error during file operation: {str(e)}"
        )

