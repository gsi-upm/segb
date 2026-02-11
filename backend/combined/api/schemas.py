"""HTTP request bodies for backend API."""

from __future__ import annotations

from pydantic import BaseModel


class TTLContent(BaseModel):
    ttl_content: str
    user: str | None = None


class DeleteRequest(BaseModel):
    user: str | None = None
