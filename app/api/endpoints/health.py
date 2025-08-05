from fastapi import APIRouter, Depends, status
from typing import Dict, Any

router = APIRouter()

@router.get("/", response_model=Dict[str, str])
async def health_check() -> Dict[str, str]:
    """Health check endpoint to verify the API is running"""
    return {"status": "healthy"}

@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict[str, str]:
    """Readiness check for container orchestration"""
    # Add any additional readiness checks here
    return {"status": "ready"}

@router.get("/startup", status_code=status.HTTP_200_OK)
async def startup_check() -> Dict[str, str]:
    """Startup check for container orchestration"""
    # Add any startup checks here
    return {"status": "started"}
