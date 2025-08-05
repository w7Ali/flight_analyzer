#!/usr/bin/env python3
"""
Flight Analyzer - Main Entry Point

This module serves as the entry point for the Flight Analyzer application.
It initializes the FastAPI application and starts the Uvicorn server.
"""
import uvicorn
from app.main import app, settings

def main():
    """Run the FastAPI application using Uvicorn"""
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
    )

if __name__ == "__main__":
    main()
