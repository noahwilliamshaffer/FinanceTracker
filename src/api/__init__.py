"""
FastAPI web application for Finance Tracker.

This package provides the web interface for viewing treasury data,
repo spreads, scoring results, and interactive dashboards.
"""

from .main import app
from .routes import router
from .models import *

__all__ = [
    "app",
    "router",
]
