"""Custom API exceptions and error handler helpers."""

from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standardized error response payload."""

    error: str
    message: str
    details: Optional[Any] = None


class CausalAPIException(HTTPException):
    """Base HTTP exception for CausalFidelityPlus API."""

    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error: str = "InternalServerError",
        message: str = "An internal server error occurred.",
        details: Optional[Any] = None,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.error_type = error
        self.message = message
        self.details = details


class ModelNotAvailableException(CausalAPIException):
    """Exception raised when an optional neural metric model cannot be loaded."""

    def __init__(self, metric_name: str, reason: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error="ModelNotAvailable",
            message=f"Neural evaluation metric '{metric_name}' is currently unavailable: {reason}",
            details={"metric_name": metric_name, "reason": reason},
        )


class ResourceNotFoundException(CausalAPIException):
    """Exception raised when a requested resource or report artifact is not found."""

    def __init__(self, resource_name: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error="ResourceNotFound",
            message=f"Requested resource '{resource_name}' was not found.",
            details={"resource_name": resource_name},
        )


class InvalidInputException(CausalAPIException):
    """Exception raised when input validation fails."""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="InvalidInput",
            message=message,
            details=details,
        )


async def custom_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions and return standardized ErrorResponse payload."""
    if isinstance(exc, CausalAPIException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.error_type,
                message=exc.message,
                details=exc.details,
            ).model_dump(),
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTPException",
            message=str(exc.detail),
        ).model_dump(),
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled internal server exceptions without exposing internal tracebacks."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected server error occurred during processing.",
        ).model_dump(),
    )
