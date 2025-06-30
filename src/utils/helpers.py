"""
Utility functions and helpers
"""
import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


def generate_file_id(filename: str) -> str:
    """Generate unique file ID based on filename and timestamp"""
    timestamp = datetime.utcnow().isoformat()
    content = f"{filename}_{timestamp}_{uuid.uuid4()}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def generate_timestamp_suffix() -> str:
    """Generate timestamp suffix for filenames"""
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return Path(filename).suffix.lower().lstrip('.')


def is_supported_format(filename: str, supported_formats: list) -> bool:
    """Check if file format is supported"""
    extension = get_file_extension(filename)
    return extension in supported_formats


def create_timestamped_filename(original_filename: str, suffix: Optional[str] = None) -> str:
    """Create filename with timestamp"""
    path = Path(original_filename)
    timestamp = suffix or generate_timestamp_suffix()
    return f"{path.stem}_{timestamp}{path.suffix}"


def safe_filename(filename: str) -> str:
    """Create safe filename by removing/replacing invalid characters"""
    import re
    # Remove or replace invalid characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove multiple underscores
    safe_name = re.sub(r'_+', '_', safe_name)
    return safe_name


def get_file_size_mb(file_path: Path) -> float:
    """Get file size in MB"""
    if file_path.exists():
        return file_path.stat().st_size / (1024 * 1024)
    return 0.0


def ensure_unique_filename(target_path: Path) -> Path:
    """Ensure filename is unique by adding counter if needed"""
    if not target_path.exists():
        return target_path
    
    counter = 1
    original_path = target_path
    
    while target_path.exists():
        name_parts = original_path.stem, counter, original_path.suffix
        target_path = original_path.parent / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
        counter += 1
    
    return target_path


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.2f} hours"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

