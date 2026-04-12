"""Vercel FastAPI entrypoint: export ``app`` (https://vercel.com/docs/frameworks/backend/fastapi)."""

from ai_events.webapp.app import app

__all__ = ["app"]
