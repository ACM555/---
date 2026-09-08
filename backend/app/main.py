"""Compatibility entry point for legacy ``uvicorn app.main:app`` commands."""

from main import app

__all__ = ["app"]
