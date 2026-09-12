"""SQLAlchemy database models for IBVAP."""
from app.core.database import Base
from app.models.camera import Camera, CameraStatus
from app.models.zone import Zone, ZoneType, TriggerType
from app.models.alert import Alert, AlertType, AlertStatus

__all__ = [
    "Base",
    "Camera",
    "CameraStatus",
    "Zone",
    "ZoneType",
    "TriggerType",
    "Alert",
    "AlertType",
    "AlertStatus",
]
