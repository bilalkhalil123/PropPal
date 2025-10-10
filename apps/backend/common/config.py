"""
Configuration management for PropPal backend services.

Uses Pydantic BaseSettings to load and validate environment variables
from the .env file with type safety and validation.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings are sourced from the .env file in the backend directory.
    Uses Pydantic validation to ensure correct types and required fields.
    """
    
    # MongoDB Atlas Configuration
    MONGODB_URL: str = Field(
        ...,
        description="MongoDB Atlas connection string",
        alias="MONGODB_URL"
    )
    
    MONGODB_DB_NAME: str = Field(
        default="proppal",
        description="MongoDB database name"
    )
    
    # Security Configuration
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT token signing and authentication"
    )
    
    ALGORITHM: str = Field(
        default="HS256",
        description="JWT algorithm"
    )
    
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )
    
    # Service URLs
    NLP_SERVICE_URL: str = Field(
        default="http://localhost:8001",
        description="URL of the NLP/RAG service"
    )
    
    # CORS Configuration
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # Application Configuration
    APP_NAME: str = Field(
        default="PropPal API",
        description="Application name"
    )
    
    APP_VERSION: str = Field(
        default="1.0.0",
        description="Application version"
    )
    
    DEBUG: bool = Field(
        default=False,
        description="Debug mode flag"
    )
    
    # Server Configuration
    HOST: str = Field(
        default="0.0.0.0",
        description="Server host"
    )
    
    PORT: int = Field(
        default=8000,
        description="Server port"
    )
    
    # Model configuration for Pydantic v2
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields in .env
    )
    
    def get_allowed_origins_list(self) -> list[str]:
        """Parse ALLOWED_ORIGINS string into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    @property
    def mongo_uri(self) -> str:
        """Alias for MONGODB_URL for backward compatibility."""
        return self.MONGODB_URL


# Singleton pattern using lru_cache
@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings (singleton).
    
    Uses lru_cache to ensure Settings is instantiated only once
    throughout the application lifecycle.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()

