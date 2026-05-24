from __future__ import annotations

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    engine: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
