from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.camera import Camera, CameraStatus
from app.schemas.camera import (
    CameraCreate,
    CameraUpdate,
    CameraResponse,
    CameraDetailResponse,
)

router = APIRouter()


@router.post(
    "/",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new CCTV/IP camera",
)
def create_camera(
    camera_in: CameraCreate,
    db: Session = Depends(get_db),
):
    """Registers an existing standard IP or RTSP camera feed in the IBVAP surveillance network."""
    camera = Camera(
        name=camera_in.name,
        location=camera_in.location,
        rtsp_url=camera_in.rtsp_url,
        status=camera_in.status,
        is_active=camera_in.is_active,
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


@router.get(
    "/",
    response_model=List[CameraResponse],
    summary="List all registered cameras",
)
def list_cameras(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Max cameras to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active state"),
    camera_status: Optional[CameraStatus] = Query(None, alias="status", description="Filter by connection status"),
    db: Session = Depends(get_db),
):
    """Retrieves all registered cameras with optional status and active filtering."""
    query = select(Camera)
    if is_active is not None:
        query = query.where(Camera.is_active == is_active)
    if camera_status is not None:
        query = query.where(Camera.status == camera_status)

    query = query.offset(skip).limit(limit).order_by(Camera.id.asc())
    cameras = db.scalars(query).all()
    return cameras


@router.get(
    "/{camera_id}",
    response_model=CameraDetailResponse,
    summary="Get camera details by ID",
)
def get_camera(
    camera_id: int,
    db: Session = Depends(get_db),
):
    """Returns details of a specific camera, including its configured virtual fences/zones."""
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with ID {camera_id} not found",
        )
    return camera


@router.put(
    "/{camera_id}",
    response_model=CameraResponse,
    summary="Update camera settings or status",
)
def update_camera(
    camera_id: int,
    camera_in: CameraUpdate,
    db: Session = Depends(get_db),
):
    """Updates camera parameters such as name, location, RTSP stream URL, or active status."""
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with ID {camera_id} not found",
        )

    update_data = camera_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(camera, field, value)

    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a camera",
)
def delete_camera(
    camera_id: int,
    db: Session = Depends(get_db),
):
    """Permanently removes a camera and its associated virtual fences from the system."""
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with ID {camera_id} not found",
        )

    db.delete(camera)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
