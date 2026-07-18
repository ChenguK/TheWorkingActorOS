from typing import Any

from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictError(HTTPException):
    def __init__(self, detail: str | dict[str, Any] = "Resource conflict") -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class ValidationError(HTTPException):
    def __init__(self, detail: str = "Invalid request") -> None:
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
