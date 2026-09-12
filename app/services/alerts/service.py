"""Alert creation service for IBVAP."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertStatus, AlertType
from app.services.vision.rules import BreachType, ZoneBreach


class AlertService:

    def create_alert(
        self,
        db: Session,
        breach: ZoneBreach,
        snapshot_path: Optional[str] = None,
    ) -> Alert:
        """Create and save an alert in the database."""

        if breach.camera_id is None:
            raise ValueError("Cannot create an alert without a camera_id.")

        if breach.breach_type == BreachType.TRIPWIRE_CROSSING:
            alert_type = AlertType.TRIPWIRE_CROSSING
        else:
            alert_type = AlertType.INTRUSION

        event_timestamp = datetime.fromtimestamp(
            breach.timestamp,
            tz=timezone.utc,
        )

        target_class = breach.detection.class_name.upper()
        confidence = float(breach.detection.confidence)

        message = (
            f"{target_class} detected in restricted zone "
            f"'{breach.zone_name}'"
        )

        alert = Alert(
            camera_id=breach.camera_id,
            zone_id=breach.zone_id,
            alert_type=alert_type,
            target_class=target_class,
            confidence=confidence,
            timestamp=event_timestamp,
            snapshot_path=snapshot_path,
            status=AlertStatus.NEW,
            message=message,
        )

        db.add(alert)
        db.commit()
        db.refresh(alert)

        return alert


alert_service = AlertService()