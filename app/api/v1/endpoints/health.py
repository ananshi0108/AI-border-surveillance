from fastapi import APIRouter
from app.core.config import settings
from app.core.database import check_db_connection

router = APIRouter()


@router.get("/health", summary="System Health & Connectivity Check")
def get_health():
    """Returns the operational status of the IBVAP edge node and database connectivity."""
    db_connected = check_db_connection()
    return {
        "status": "healthy" if db_connected else "degraded",
        "project": settings.PROJECT_NAME,
        "node_type": settings.NODE_TYPE,
        "database": "connected" if db_connected else "unreachable",
        "version": "0.1.0",
    }
