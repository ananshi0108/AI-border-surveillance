from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.alert import Alert
from app.schemas.alert import AlertCreate, AlertResponse, AlertStatusUpdate


router = APIRouter()


@router.post("/", response_model=AlertResponse, status_code=201)
def create_alert(
    alert_data: AlertCreate,
    db: Session = Depends(get_db),
):
    alert = Alert(**alert_data.model_dump())

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return alert



@router.get("/", response_model=List[AlertResponse])
def get_alerts(
    db: Session = Depends(get_db),
):
    statement = select(Alert).order_by(Alert.timestamp.desc())

    return db.scalars(statement).all()


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
):
    alert = db.get(Alert, alert_id)

    if alert is None:
        raise HTTPException(
            status_code=404,
            detail="Alert not found",
        )

    return alert

@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert_status(
    alert_id: int,
    alert_data: AlertStatusUpdate,
    db: Session = Depends(get_db),
):
    alert = db.get(Alert, alert_id)

    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = alert_data.status

    db.commit()
    db.refresh(alert)

    return alert