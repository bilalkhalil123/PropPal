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
    
    # PostgreSQL (Neon) - primary database
    DATABASE_URL: str = Field(
        default="",
        description="PostgreSQL connection string (Neon). e.g. postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require",
    )
    POSTGRES_URL: Optional[str] = Field(
        default=None,
        description="Alternative to DATABASE_URL. If set and DATABASE_URL is empty, used as the PostgreSQL connection string.",
    )
    
    # Qdrant Vector Database Configuration
    QDRANT_URL: str = Field(
        default="http://localhost:6333",
        description="Qdrant server URL"
    )
    
    QDRANT_API_KEY: Optional[str] = Field(
        default=None,
        description="Qdrant API key (optional, for cloud instances)"
    )
    
    # Clerk Authentication Configuration
    CLERK_SECRET_KEY: str = Field(
        default="",
        description="Clerk secret key for webhook verification"
    )
    
    CLERK_WEBHOOK_SECRET: str = Field(
        default="",
        description="Clerk webhook secret for signature verification"
    )

    CLERK_JWKS_URL: Optional[str] = Field(
        default=None,
        description="Clerk JWKS URL for JWT verification (e.g. https://<frontend-api>/.well-known/jwks.json)"
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
    
    # Backblaze B2 Configuration (S3-compatible API)
    B2_ENDPOINT: Optional[str] = Field(
        default=None,
        description="Backblaze B2 S3-compatible endpoint URL"
    )
    
    B2_ACCESS_KEY: Optional[str] = Field(
        default=None,
        description="Backblaze B2 Access Key (S3-compatible)"
    )
    
    B2_SECRET_KEY: Optional[str] = Field(
        default=None,
        description="Backblaze B2 Secret Key (S3-compatible)"
    )
    
    B2_BUCKET: Optional[str] = Field(
        default=None,
        description="Backblaze B2 Bucket Name"
    )
    
    B2_PUBLIC_URL_TEMPLATE: Optional[str] = Field(
        default=None,
        description="Public URL template for uploaded files (e.g., https://{bucket}.s3.us-west-002.backblazeb2.com/{key})"
    )

    # Embedding provider: "local" (sentence-transformers), "huggingface" (HF Inference API), "openai"
    EMBEDDING_PROVIDER: str = Field(
        default="openai",
        description="Embedding backend: local | huggingface | openai. Use huggingface or openai on Render to avoid loading torch.",
    )
    HF_TOKEN: Optional[str] = Field(default=None, description="Hugging Face token for Inference API (embedding provider=huggingface)")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key for embeddings (embedding provider=openai)")

    # ASR Configuration
    ASR_MODEL_PATH: str = Field(
        default="services/asr/models/ur_en_whisper_ct2_int8",
        description="Relative or absolute path to the local Whisper model directory",
    )
    ASR_DEVICE: str = Field(default="cpu", description="Device for ASR model: cpu | cuda")
    ASR_COMPUTE_TYPE: str = Field(default="int8", description="Compute type for Whisper (e.g., int8, float16, float32)")
    ASR_CPU_THREADS: int = Field(default=4, description="CPU threads for ASR model loading on Windows")
    ASR_FEATURE_SIZE: int = Field(default=128, description="Number of mel bands for Whisper feature extraction")
    ASR_SAMPLE_RATE: int = Field(default=16000, description="Target sample rate for ASR input audio")
    ASR_VAD_FILTER: bool = Field(default=True, description="Enable VAD filter for ASR")
    ASR_MIN_SILENCE_MS: int = Field(default=500, description="Minimum silence duration in ms for VAD")
    ASR_BEAM_SIZE: int = Field(default=1, description="Beam size for ASR decoding")

    # Groq (LLM) configuration for translation or chat augmentation
    GROQ_API_KEY: Optional[str] = Field(default=None, description="Groq API key for translation")
    GROQ_TRANSLATION_MODEL: str = Field(default="llama-3.1-8b-instant", description="Groq model for translation")
    
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

    def get_postgres_url(self) -> str:
        """Return PostgreSQL connection string (Neon). Prefer DATABASE_URL, fallback to POSTGRES_URL."""
        return (self.DATABASE_URL or self.POSTGRES_URL or "").strip()


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

