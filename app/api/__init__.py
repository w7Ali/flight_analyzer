"""
API package for the Flight Analyzer application.

This package contains all API endpoints and route definitions.
"""

from .endpoints import flights, health

__all__ = ['flights', 'health']
