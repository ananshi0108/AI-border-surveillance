from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.camera import CameraStatus
from app.schemas.zone import ZoneResponse


class CameraBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Camera display name / designation")
    location: str = Field(..., min_length=1, max_length=255, description="Physical location (e.g. North Post Tower 2)")
    rtsp_url: str = Field(..., min_length=1, max_length=500, description="RTSP feed URL or simulated video path")
    status: CameraStatus = Field(default=CameraStatus.OFFLINE, description="ONLINE, OFFLINE, or ERROR")
    is_active: bool = Field(default=True, description="Whether camera feed is actively analyzed")


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    location: Optional[str] = Field(None, min_length=1, max_length=255)
    rtsp_url: Optional[str] = Field(None, min_length=1, max_length=500)
    status: Optional[CameraStatus] = None
    is_active: Optional[bool] = None


class CameraResponse(CameraBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CameraDetailResponse(CameraResponse):
    """Detailed view including configured virtual fences/zones."""
    zones: List[ZoneResponse] = []
