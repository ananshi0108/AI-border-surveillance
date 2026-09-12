"""Pydantic request and response validation schemas."""
from app.schemas.camera import (
    CameraBase,
    CameraCreate,
    CameraUpdate,
    CameraResponse,
    CameraDetailResponse,
)
from app.schemas.zone import (
    ZoneBase,
    ZoneCreate,
    ZoneUpdate,
    ZoneResponse,
)

__all__ = [
    "CameraBase",
    "CameraCreate",
    "CameraUpdate",
    "CameraResponse",
    "CameraDetailResponse",
    "ZoneBase",
    "ZoneCreate",
    "ZoneUpdate",
    "ZoneResponse",
]
