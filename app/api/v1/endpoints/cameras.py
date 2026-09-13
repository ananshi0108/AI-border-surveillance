import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from fastapi.responses import StreamingResponse
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
from app.services.vision.manager import stream_manager

router = APIRouter()

# Target frame rate for the MJPEG live view sent to the frontend.
_STREAM_FPS = 12


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


# ----------------------------------------------------------------------
# LIVE CV STREAMING (connects the vision pipeline to the frontend)
# ----------------------------------------------------------------------


@router.post(
    "/{camera_id}/start",
    summary="Start the live AI detection pipeline for a camera",
)
def start_camera_pipeline(
    camera_id: int,
    db: Session = Depends(get_db),
):
    """Starts StreamReader -> YOLO -> Geometry pipeline for this camera's rtsp_url."""
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with ID {camera_id} not found",
        )

    stream_manager.ensure_started(
        camera_id=camera.id,
        source=camera.rtsp_url,
        camera_name=camera.name,
    )

    camera.status = CameraStatus.ONLINE
    db.add(camera)
    db.commit()
    db.refresh(camera)

    return {"camera_id": camera_id, "running": True}


@router.post(
    "/{camera_id}/stop",
    summary="Stop the live AI detection pipeline for a camera",
)
def stop_camera_pipeline(
    camera_id: int,
    db: Session = Depends(get_db),
):
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with ID {camera_id} not found",
        )

    stream_manager.stop_stream(camera_id)

    camera.status = CameraStatus.OFFLINE
    db.add(camera)
    db.commit()
    db.refresh(camera)

    return {"camera_id": camera_id, "running": False}


@router.get(
    "/{camera_id}/status",
    summary="Get live pipeline connection status for a camera",
)
def get_camera_pipeline_status(camera_id: int):
    pipeline = stream_manager.get_stream(camera_id)
    if pipeline is None:
        return {"camera_id": camera_id, "running": False, "connected": False}

    return {
        "camera_id": camera_id,
        "running": pipeline.reader.is_running,
        "connected": pipeline.reader.is_connected,
        "detections_in_last_frame": pipeline.latest_detection_count,
    }


@router.get(
    "/{camera_id}/snapshot",
    summary="Get a single annotated JPEG frame (boxes + zones drawn)",
)
def get_camera_snapshot(
    camera_id: int,
    db: Session = Depends(get_db),
):
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with ID {camera_id} not found",
        )

    pipeline = stream_manager.ensure_started(
        camera_id=camera.id,
        source=camera.rtsp_url,
        camera_name=camera.name,
    )

    # Give a freshly started pipeline a brief window to decode its first frame.
    jpeg_bytes = None
    for _ in range(40):
        jpeg_bytes = pipeline.get_latest_jpeg()
        if jpeg_bytes is not None:
            break
        time.sleep(0.1)

    if jpeg_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Camera stream is still starting up, try again shortly.",
        )

    return Response(content=jpeg_bytes, media_type="image/jpeg")


@router.get(
    "/{camera_id}/stream",
    summary="MJPEG live video stream with AI detection boxes overlaid",
)
def stream_camera(
    camera_id: int,
    db: Session = Depends(get_db),
):
    """
    Live view for the dashboard: an <img src="this-url"> tag will render
    a continuously updating annotated feed (multipart/x-mixed-replace).
    """
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with ID {camera_id} not found",
        )

    pipeline = stream_manager.ensure_started(
        camera_id=camera.id,
        source=camera.rtsp_url,
        camera_name=camera.name,
    )

    def frame_generator():
        frame_interval = 1.0 / _STREAM_FPS
        while pipeline.reader.is_running:
            jpeg_bytes = pipeline.get_latest_jpeg()
            if jpeg_bytes is None:
                time.sleep(0.1)
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(jpeg_bytes)).encode() + b"\r\n\r\n"
                + jpeg_bytes + b"\r\n"
            )
            time.sleep(frame_interval)

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
