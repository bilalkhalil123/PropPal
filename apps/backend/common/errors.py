"""
Error handling utilities for PropPal backend services.

Provides custom exception classes and FastAPI exception handlers
for consistent error responses across all services.
"""

from typing import Any, Dict

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


# =====================================================================
# Custom Exception Classes
# =====================================================================

class PropPalException(Exception):
    """Base exception for all PropPal custom exceptions."""
    
    def __init__(self, message: str, details: Dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ResourceNotFoundException(PropPalException):
    """
    Raised when a requested resource is not found.
    
    Maps to HTTP 404 Not Found.
    """
    pass


class AuthenticationFailedException(PropPalException):
    """
    Raised when authentication fails.
    
    Maps to HTTP 401 Unauthorized.
    """
    pass


class ValidationErrorException(PropPalException):
    """
    Raised when validation fails.
    
    Maps to HTTP 422 Unprocessable Entity.
    """
    pass


class DatabaseConnectionException(PropPalException):
    """
    Raised when database connection fails.
    
    Maps to HTTP 503 Service Unavailable.
    """
    pass


class UnauthorizedException(PropPalException):
    """
    Raised when user lacks permissions for an action.
    
    Maps to HTTP 403 Forbidden.
    """
    pass


# =====================================================================
# Exception Handlers
# =====================================================================

async def resource_not_found_handler(
    request: Request, 
    exc: ResourceNotFoundException
) -> JSONResponse:
    """Handle ResourceNotFoundException."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "ResourceNotFound",
            "message": exc.message,
            "details": exc.details,
            "path": str(request.url)
        }
    )


async def authentication_failed_handler(
    request: Request,
    exc: AuthenticationFailedException
) -> JSONResponse:
    """Handle AuthenticationFailedException."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "AuthenticationFailed",
            "message": exc.message,
            "details": exc.details,
            "path": str(request.url)
        },
        headers={"WWW-Authenticate": "Bearer"}
    )


async def validation_error_handler(
    request: Request,
    exc: ValidationErrorException
) -> JSONResponse:
    """Handle ValidationErrorException."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": exc.message,
            "details": exc.details,
            "path": str(request.url)
        }
    )


async def database_connection_handler(
    request: Request,
    exc: DatabaseConnectionException
) -> JSONResponse:
    """Handle DatabaseConnectionException."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "DatabaseConnectionError",
            "message": exc.message,
            "details": exc.details,
            "path": str(request.url)
        }
    )


async def unauthorized_handler(
    request: Request,
    exc: UnauthorizedException
) -> JSONResponse:
    """Handle UnauthorizedException."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "Unauthorized",
            "message": exc.message,
            "details": exc.details,
            "path": str(request.url)
        }
    )


async def generic_proppal_exception_handler(
    request: Request,
    exc: PropPalException
) -> JSONResponse:
    """Handle any unhandled PropPalException."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": exc.message,
            "details": exc.details,
            "path": str(request.url)
        }
    )


# =====================================================================
# Registration Function
# =====================================================================

def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all custom exception handlers with the FastAPI application.
    
    Args:
        app: FastAPI application instance
        
    Usage:
        ```python
        from fastapi import FastAPI
        from common.errors import register_exception_handlers
        
        app = FastAPI()
        register_exception_handlers(app)
        ```
    """
    app.add_exception_handler(ResourceNotFoundException, resource_not_found_handler)
    app.add_exception_handler(AuthenticationFailedException, authentication_failed_handler)
    app.add_exception_handler(ValidationErrorException, validation_error_handler)
    app.add_exception_handler(DatabaseConnectionException, database_connection_handler)
    app.add_exception_handler(UnauthorizedException, unauthorized_handler)
    app.add_exception_handler(PropPalException, generic_proppal_exception_handler)

