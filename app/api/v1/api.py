from fastapi import APIRouter

from app.api.v1.endpoints import health, cameras, zones, alerts


api_router = APIRouter()


# Register endpoint modules
api_router.include_router(
    health.router,
    tags=["System Health"]
)

api_router.include_router(
    cameras.router,
    prefix="/cameras",
    tags=["Cameras"]
)

api_router.include_router(
    zones.router,
    prefix="/zones",
    tags=["Virtual Fences / Zones"]
)

api_router.include_router(
    alerts.router,
    prefix="/alerts",
    tags=["Alerts"]
)