"""
Configuration settings for the AI Invoice Processing Agent
"""
import os
from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application Settings
    app_name: str = Field(default="AI Invoice Processing Agent", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=True, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Dashboard Settings
    dashboard_port: int = Field(default=8501, env="DASHBOARD_PORT")
    
    # File Processing Settings
    incoming_folder: str = Field(default="./incoming", env="INCOMING_FOLDER")
    generated_folder: str = Field(default="./generated", env="GENERATED_FOLDER")
    log_folder: str = Field(default="./logs", env="LOG_FOLDER")
    max_file_size_mb: int = Field(default=10, env="MAX_FILE_SIZE_MB")
    supported_formats: str = Field(default="jpg,jpeg,png,pdf,tiff", env="SUPPORTED_FORMATS")
    
    # AI Model Settings
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2-vision", env="OLLAMA_MODEL")
    ai_processing_timeout_seconds: int = Field(default=1800, env="AI_PROCESSING_TIMEOUT_SECONDS")  # 30 minutes
    ollama_request_timeout_seconds: int = Field(default=3600, env="OLLAMA_REQUEST_TIMEOUT_SECONDS")  # 60 minutes
    
    # Logging Settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_max_size_mb: int = Field(default=100, env="LOG_MAX_SIZE_MB")
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    # Processing Settings
    batch_size: int = Field(default=10, env="BATCH_SIZE")
    processing_interval_seconds: int = Field(default=5, env="PROCESSING_INTERVAL_SECONDS")
    max_retry_attempts: int = Field(default=3, env="MAX_RETRY_ATTEMPTS")
    file_processing_timeout_seconds: int = Field(default=2400, env="FILE_PROCESSING_TIMEOUT_SECONDS")  # 40 minutes
    
    # Database Settings
    database_url: str = Field(default="sqlite:///./invoice_processing.db", env="DATABASE_URL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def supported_formats_list(self) -> List[str]:
        """Get supported file formats as a list"""
        return [fmt.strip().lower() for fmt in self.supported_formats.split(",")]
    
    def get_absolute_path(self, relative_path: str) -> Path:
        """Convert relative path to absolute path"""
        return Path(relative_path).resolve()
    
    @property
    def incoming_path(self) -> Path:
        """Get absolute path for incoming folder"""
        return self.get_absolute_path(self.incoming_folder)
    
    @property
    def generated_path(self) -> Path:
        """Get absolute path for generated folder"""
        return self.get_absolute_path(self.generated_folder)
    
    @property
    def log_path(self) -> Path:
        """Get absolute path for log folder"""
        return self.get_absolute_path(self.log_folder)


# Global settings instance
settings = Settings()


def ensure_directories():
    """Ensure all required directories exist"""
    directories = [
        settings.incoming_path,
        settings.generated_path,
        settings.log_path
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Ensure directories exist when module is imported
ensure_directories()

