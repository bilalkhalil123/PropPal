"""
Common backend utilities for PropPal FastAPI services.

This package provides shared functionality across all backend services:
- Configuration management (config.py)
- Database connection handling (db.py)
- Error handling utilities (errors.py)
"""

from .config import Settings, get_settings
from .db import DatabaseClient, get_db_client
from .errors import (
    ResourceNotFoundException,
    AuthenticationFailedException,
    ValidationErrorException,
    register_exception_handlers,
)

__all__ = [
    "Settings",
    "get_settings",
    "DatabaseClient",
    "get_db_client",
    "ResourceNotFoundException",
    "AuthenticationFailedException",
    "ValidationErrorException",
    "register_exception_handlers",
]

