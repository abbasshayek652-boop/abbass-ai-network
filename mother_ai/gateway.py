"""Re-export the primary FastAPI application for uvicorn."""
from __future__ import annotations

from gateway import app

__all__ = ["app"]
