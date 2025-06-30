"""
Enhanced logging system with structured logging and error tracking
"""
import logging
import logging.handlers
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import contextmanager

from config.settings import settings


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for logs"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'process': record.process
        }
        
        # Add extra fields if present
        if hasattr(record, 'file_id'):
            log_entry['file_id'] = record.file_id
        
        if hasattr(record, 'processing_time'):
            log_entry['processing_time'] = record.processing_time
        
        if hasattr(record, 'error_type'):
            log_entry['error_type'] = record.error_type
        
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_entry, ensure_ascii=False)


class ProcessingLogger:
    """Specialized logger for processing operations"""
    
    def __init__(self, name: str = "processing"):
        self.logger = logging.getLogger(name)
        self._setup_processing_handlers()
    
    def _setup_processing_handlers(self):
        """Setup specialized handlers for processing logs"""
        # Processing-specific file handler
        processing_log_file = settings.log_path / "processing_detailed.log"
        processing_handler = logging.handlers.RotatingFileHandler(
            processing_log_file,
            maxBytes=settings.log_max_size_mb * 1024 * 1024,
            backupCount=settings.log_backup_count,
            encoding='utf-8'
        )
        processing_handler.setFormatter(StructuredFormatter())
        processing_handler.setLevel(logging.DEBUG)
        
        # Add filter to only capture processing-related logs
        processing_handler.addFilter(lambda record: 'processing' in record.name.lower())
        
        # Add handler if not already present
        if not any(isinstance(h, logging.handlers.RotatingFileHandler) and 
                  'processing_detailed' in str(h.baseFilename) for h in self.logger.handlers):
            self.logger.addHandler(processing_handler)
    
    def log_file_start(self, file_id: str, filename: str, file_size: float):
        """Log start of file processing"""
        self.logger.info(
            f"Started processing file: {filename}",
            extra={
                'file_id': file_id,
                'filename': filename,
                'file_size_mb': file_size,
                'event_type': 'processing_start'
            }
        )
    
    def log_file_success(self, file_id: str, filename: str, processing_time: float, output_file: str):
        """Log successful file processing"""
        self.logger.info(
            f"Successfully processed file: {filename}",
            extra={
                'file_id': file_id,
                'filename': filename,
                'processing_time': processing_time,
                'output_file': output_file,
                'event_type': 'processing_success'
            }
        )
    
    def log_file_error(self, file_id: str, filename: str, error: Exception, processing_time: float):
        """Log file processing error"""
        self.logger.error(
            f"Failed to process file: {filename} - {str(error)}",
            extra={
                'file_id': file_id,
                'filename': filename,
                'processing_time': processing_time,
                'error_type': type(error).__name__,
                'event_type': 'processing_error'
            },
            exc_info=True
        )
    
    def log_ai_model_error(self, file_id: str, model_name: str, error: Exception):
        """Log AI model specific errors"""
        self.logger.error(
            f"AI model error for file {file_id}: {str(error)}",
            extra={
                'file_id': file_id,
                'model_name': model_name,
                'error_type': type(error).__name__,
                'event_type': 'ai_model_error'
            },
            exc_info=True
        )
    
    def log_file_monitoring_event(self, event_type: str, file_path: str):
        """Log file monitoring events"""
        self.logger.debug(
            f"File monitoring event: {event_type} - {file_path}",
            extra={
                'event_type': f'file_monitor_{event_type}',
                'file_path': file_path
            }
        )


class ErrorTracker:
    """Track and analyze errors for reporting"""
    
    def __init__(self):
        self.error_log_file = settings.log_path / "error_tracking.json"
        self.errors: Dict[str, Any] = self._load_errors()
    
    def _load_errors(self) -> Dict[str, Any]:
        """Load existing error data"""
        try:
            if self.error_log_file.exists():
                with open(self.error_log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            'error_counts': {},
            'recent_errors': [],
            'error_patterns': {}
        }
    
    def _save_errors(self):
        """Save error data to file"""
        try:
            with open(self.error_log_file, 'w', encoding='utf-8') as f:
                json.dump(self.errors, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to save error tracking data: {str(e)}")
    
    def track_error(self, error_type: str, error_message: str, file_id: Optional[str] = None, 
                   context: Optional[Dict[str, Any]] = None):
        """Track an error occurrence"""
        timestamp = datetime.utcnow().isoformat()
        
        # Update error counts
        if error_type not in self.errors['error_counts']:
            self.errors['error_counts'][error_type] = 0
        self.errors['error_counts'][error_type] += 1
        
        # Add to recent errors (keep last 100)
        error_entry = {
            'timestamp': timestamp,
            'error_type': error_type,
            'message': error_message,
            'file_id': file_id,
            'context': context or {}
        }
        
        self.errors['recent_errors'].append(error_entry)
        if len(self.errors['recent_errors']) > 100:
            self.errors['recent_errors'] = self.errors['recent_errors'][-100:]
        
        # Analyze error patterns
        self._analyze_error_patterns(error_type, error_message)
        
        # Save to file
        self._save_errors()
    
    def _analyze_error_patterns(self, error_type: str, error_message: str):
        """Analyze error patterns for insights"""
        # Simple pattern analysis - can be enhanced
        if error_type not in self.errors['error_patterns']:
            self.errors['error_patterns'][error_type] = {
                'common_messages': {},
                'frequency': 0
            }
        
        pattern = self.errors['error_patterns'][error_type]
        pattern['frequency'] += 1
        
        # Track common error messages
        if error_message not in pattern['common_messages']:
            pattern['common_messages'][error_message] = 0
        pattern['common_messages'][error_message] += 1
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary for reporting"""
        return {
            'total_error_types': len(self.errors['error_counts']),
            'total_errors': sum(self.errors['error_counts'].values()),
            'most_common_errors': sorted(
                self.errors['error_counts'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            'recent_error_count': len(self.errors['recent_errors']),
            'error_patterns': self.errors['error_patterns']
        }


class PerformanceLogger:
    """Logger for performance metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger("performance")
        self.metrics_file = settings.log_path / "performance_metrics.json"
        self._setup_performance_handler()
    
    def _setup_performance_handler(self):
        """Setup performance logging handler"""
        perf_handler = logging.handlers.RotatingFileHandler(
            settings.log_path / "performance.log",
            maxBytes=settings.log_max_size_mb * 1024 * 1024,
            backupCount=settings.log_backup_count,
            encoding='utf-8'
        )
        perf_handler.setFormatter(StructuredFormatter())
        perf_handler.setLevel(logging.INFO)
        
        if not any(isinstance(h, logging.handlers.RotatingFileHandler) and 
                  'performance' in str(h.baseFilename) for h in self.logger.handlers):
            self.logger.addHandler(perf_handler)
    
    @contextmanager
    def measure_time(self, operation: str, **context):
        """Context manager to measure operation time"""
        start_time = datetime.utcnow()
        try:
            yield
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info(
                f"Operation completed: {operation}",
                extra={
                    'operation': operation,
                    'duration_seconds': duration,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    **context
                }
            )
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.error(
                f"Operation failed: {operation}",
                extra={
                    'operation': operation,
                    'duration_seconds': duration,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'error_type': type(e).__name__,
                    **context
                },
                exc_info=True
            )
            raise


# Global instances
processing_logger = ProcessingLogger()
error_tracker = ErrorTracker()
performance_logger = PerformanceLogger()


def get_processing_logger() -> ProcessingLogger:
    """Get the processing logger instance"""
    return processing_logger


def get_error_tracker() -> ErrorTracker:
    """Get the error tracker instance"""
    return error_tracker


def get_performance_logger() -> PerformanceLogger:
    """Get the performance logger instance"""
    return performance_logger

