from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.camera import Camera
from app.models.zone import Zone, ZoneType
from app.schemas.zone import (
    ZoneCreate,
    ZoneUpdate,
    ZoneResponse,
)

router = APIRouter()


@router.post(
    "/",
    response_model=ZoneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a virtual fence / zone for a camera",
)
def create_zone(
    zone_in: ZoneCreate,
    db: Session = Depends(get_db),
):
    """Creates a virtual fence (TRIPWIRE line or POLYGON boundary) attached to a registered camera."""
    # Ensure the parent camera exists
    camera = db.get(Camera, zone_in.camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with ID {zone_in.camera_id} does not exist. Please register the camera first.",
        )

    zone = Zone(
        camera_id=zone_in.camera_id,
        name=zone_in.name,
        zone_type=zone_in.zone_type,
        coordinates=zone_in.coordinates,
        trigger_type=zone_in.trigger_type,
        is_active=zone_in.is_active,
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.get(
    "/",
    response_model=List[ZoneResponse],
    summary="List virtual fences / zones",
)
def list_zones(
    camera_id: Optional[int] = Query(None, description="Filter zones by camera ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    zone_type: Optional[ZoneType] = Query(None, description="Filter by TRIPWIRE or POLYGON"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Max zones to return"),
    db: Session = Depends(get_db),
):
    """Lists configured zones with optional filtering by camera, type, or active state."""
    query = select(Zone)
    if camera_id is not None:
        query = query.where(Zone.camera_id == camera_id)
    if is_active is not None:
        query = query.where(Zone.is_active == is_active)
    if zone_type is not None:
        query = query.where(Zone.zone_type == zone_type)

    query = query.offset(skip).limit(limit).order_by(Zone.id.asc())
    zones = db.scalars(query).all()
    return zones


@router.get(
    "/{zone_id}",
    response_model=ZoneResponse,
    summary="Get zone details by ID",
)
def get_zone(
    zone_id: int,
    db: Session = Depends(get_db),
):
    """Retrieves coordinates, trigger rules, and settings for a specific zone."""
    zone = db.get(Zone, zone_id)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone with ID {zone_id} not found",
        )
    return zone


@router.put(
    "/{zone_id}",
    response_model=ZoneResponse,
    summary="Update virtual fence coordinates or rules",
)
def update_zone(
    zone_id: int,
    zone_in: ZoneUpdate,
    db: Session = Depends(get_db),
):
    """Updates zone coordinates, boundary type, trigger condition, or active state."""
    zone = db.get(Zone, zone_id)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone with ID {zone_id} not found",
        )

    update_data = zone_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(zone, field, value)

    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.delete(
    "/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a virtual fence / zone",
)
def delete_zone(
    zone_id: int,
    db: Session = Depends(get_db),
):
    """Deletes a virtual fence / zone boundary."""
    zone = db.get(Zone, zone_id)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone with ID {zone_id} not found",
        )

    db.delete(zone)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
