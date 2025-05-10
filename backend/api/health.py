from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict
from ..db.connection import get_db

router = APIRouter()

@router.get("/health", response_model=Dict[str, str])
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint that verifies database connection.
    Returns:
        Dict: Status of the service and database connection
    """
    try:
        # Try a simple query to verify connection
        db.execute("SELECT 1").fetchone()
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": str(e)
        }
