from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.alert import AlertStatus, AlertType


class AlertBase(BaseModel):
    camera_id: int
    zone_id: int
    alert_type: AlertType
    target_class: str
    confidence: float
    snapshot_path: str | None = None
    status: AlertStatus = AlertStatus.NEW
    message: str | None = None


class AlertCreate(AlertBase):
    pass


class AlertResponse(AlertBase):
    id: int
    timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)