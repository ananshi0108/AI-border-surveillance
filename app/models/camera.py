from __future__ import annotations

from datetime import datetime, timezone
import enum
from typing import TYPE_CHECKING, List
from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.zone import Zone

class CameraStatus(str, enum.Enum):
    """Operational connection status of a CCTV/IP camera."""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    ERROR = "ERROR"


class Camera(Base):
    """Camera model representing a registered border CCTV/IP camera feed."""
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    rtsp_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[CameraStatus] = mapped_column(
        SAEnum(CameraStatus, name="camera_status_enum", native_enum=False),
        default=CameraStatus.OFFLINE,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # 1 Camera -> Many Virtual Fences / Zones
    zones: Mapped[List["Zone"]] = relationship(
        "Zone",
        back_populates="camera",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
