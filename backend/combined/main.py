"""ASGI entrypoint for SEGB backend."""

from .api.app import app

__all__ = ["app"]
