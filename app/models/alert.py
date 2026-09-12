from datetime import datetime, timezone
import enum

from sqlalchemy import DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AlertType(str, enum.Enum):
    """Type of security incident detected by the vision system."""

    INTRUSION = "INTRUSION"
    TRIPWIRE_CROSSING = "TRIPWIRE_CROSSING"


class AlertStatus(str, enum.Enum):
    """Current handling status of an alert."""

    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class Alert(Base):
    """Security incident generated when a virtual fence is breached."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
    )

    camera_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    zone_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    alert_type: Mapped[AlertType] = mapped_column(
        SAEnum(AlertType, name="alert_type_enum", native_enum=False),
        nullable=False,
    )

    target_class: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    snapshot_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    status: Mapped[AlertStatus] = mapped_column(
        SAEnum(AlertStatus, name="alert_status_enum", native_enum=False),
        default=AlertStatus.NEW,
        nullable=False,
        index=True,
    )

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )