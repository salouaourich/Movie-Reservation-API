"""
Single source of truth for the error response shape, matching the Phase-1 contract:
{
  "error": { "code": "...", "message": "...", "details": {...} }
}
"""

from typing import Any, Optional
from fastapi import HTTPException


class APIError(HTTPException):
    """An HTTPException whose detail is already in our contract shape."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "error": {
                    "code": code,
                    "message": message,
                    "details": details or {},
                }
            },
        )
