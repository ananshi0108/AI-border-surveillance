from datetime import datetime, timezone
import enum
from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ZoneType(str, enum.Enum):
    """Geometry type for a virtual fence or region of interest."""
    TRIPWIRE = "TRIPWIRE"  # 2-point crossing line
    POLYGON = "POLYGON"    # Multi-point bounded area


class TriggerType(str, enum.Enum):
    """Target threat classification that triggers an alert."""
    HUMAN = "HUMAN"
    VEHICLE = "VEHICLE"
    ALL = "ALL"


class Zone(Base):
    """Virtual fence / region of interest attached to a camera feed."""
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    zone_type: Mapped[ZoneType] = mapped_column(
        SAEnum(ZoneType, name="zone_type_enum", native_enum=False),
        nullable=False,
    )
    coordinates: Mapped[list] = mapped_column(JSON, nullable=False)
    trigger_type: Mapped[TriggerType] = mapped_column(
        SAEnum(TriggerType, name="trigger_type_enum", native_enum=False),
        default=TriggerType.ALL,
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

    # Many Zones -> 1 Camera
    camera: Mapped["Camera"] = relationship("Camera", back_populates="zones")
