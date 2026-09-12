from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.zone import ZoneType, TriggerType


class ZoneBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Zone identifier, e.g., 'Zero-Line Fence'")
    zone_type: ZoneType = Field(..., description="TRIPWIRE (line) or POLYGON (area)")
    coordinates: List[List[float]] = Field(
        ...,
        description="Coordinates list, e.g., [[0.1, 0.2], [0.8, 0.2]]",
    )
    trigger_type: TriggerType = Field(default=TriggerType.ALL, description="Target threat to alert on: HUMAN, VEHICLE, or ALL")
    is_active: bool = Field(default=True, description="Enable or disable monitoring on this zone")

    @model_validator(mode="after")
    def validate_coordinates_geometry(self) -> "ZoneBase":
        coords = self.coordinates
        z_type = self.zone_type

        # Validate each coordinate point is [x, y]
        for idx, pt in enumerate(coords):
            if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                raise ValueError(f"Coordinate at index {idx} must be a 2D point [x, y], got {pt}")

        # Validate minimum points based on geometry
        if z_type == ZoneType.TRIPWIRE and len(coords) < 2:
            raise ValueError("TRIPWIRE must contain at least 2 points to define a line")
        if z_type == ZoneType.POLYGON and len(coords) < 3:
            raise ValueError("POLYGON must contain at least 3 points to define an enclosed area")

        return self


class ZoneCreate(ZoneBase):
    camera_id: int = Field(..., description="ID of the camera this zone is attached to")


class ZoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    zone_type: Optional[ZoneType] = None
    coordinates: Optional[List[List[float]]] = None
    trigger_type: Optional[TriggerType] = None
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def validate_coordinates_geometry(self) -> "ZoneUpdate":
        if self.coordinates is not None:
            for idx, pt in enumerate(self.coordinates):
                if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                    raise ValueError(f"Coordinate at index {idx} must be a 2D point [x, y], got {pt}")

            if self.zone_type is not None:
                if self.zone_type == ZoneType.TRIPWIRE and len(self.coordinates) < 2:
                    raise ValueError("TRIPWIRE must contain at least 2 points")
                if self.zone_type == ZoneType.POLYGON and len(self.coordinates) < 3:
                    raise ValueError("POLYGON must contain at least 3 points")
        return self


class ZoneResponse(ZoneBase):
    id: int
    camera_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
