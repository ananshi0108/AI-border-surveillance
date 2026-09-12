"""Unit tests for Phase 3D: Automatic Incident Snapshot & Evidence Saving"""

from pathlib import Path
import cv2
import numpy as np
import pytest

from app.services.alerts.snapshot import SnapshotService
from app.services.vision.detection import BoundingBox, DetectionResult
from app.services.vision.rules import BreachType, ZoneBreach


def _create_mock_breach(zone_id: int = 1, class_name: str = "person") -> ZoneBreach:
    """Helper to create a synthetic ZoneBreach instance."""
    bbox = BoundingBox(x1=100.0, y1=150.0, x2=200.0, y2=350.0)
    norm_bbox = BoundingBox(x1=0.156, y1=0.417, x2=0.312, y2=0.972)

    detection = DetectionResult(
        class_id=0,
        class_name=class_name,
        confidence=0.885,
        bbox=bbox,
        normalized_bbox=norm_bbox,
    )

    return ZoneBreach(
        zone_id=zone_id,
        zone_name="Perimeter Zero-Line Fence",
        breach_type=BreachType.TRIPWIRE_CROSSING,
        detection=detection,
        camera_id=1,
        timestamp=1700000000.0,
        contact_point=(150.0, 350.0),
    )


def test_breach_produces_valid_snapshot(tmp_path: Path):
    """Verify that saving a breach produces a real, readable JPEG on disk."""
    service = SnapshotService(snapshot_dir=str(tmp_path))

    # Create dummy 640x360 image
    frame = np.full((360, 640, 3), 40, dtype=np.uint8)
    breach = _create_mock_breach(zone_id=1, class_name="person")
    coords = [[0.1, 0.5], [0.9, 0.5]]

    saved_path = service.save_breach_snapshot(
        frame=frame,
        breach=breach,
        zone_coordinates=coords,
        camera_name="BOP Alpha Tower",
    )

    # 1. File exists on disk
    assert Path(saved_path).exists()
    assert Path(saved_path).is_file()
    assert Path(saved_path).stat().st_size > 0

    # 2. Image can be opened and decoded cleanly
    loaded_img = cv2.imread(saved_path)
    assert loaded_img is not None
    assert loaded_img.shape == (360, 640, 3)


def test_polygon_breach_snapshot(tmp_path: Path):
    """Verify that polygon zone coordinates are drawn without error."""
    service = SnapshotService(snapshot_dir=str(tmp_path))
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    breach = _create_mock_breach(zone_id=2, class_name="truck")
    breach.breach_type = BreachType.POLYGON_INTRUSION

    polygon_coords = [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]

    saved_path = service.save_breach_snapshot(
        frame=frame,
        breach=breach,
        zone_coordinates=polygon_coords,
    )

    assert Path(saved_path).exists()
    img = cv2.imread(saved_path)
    assert img is not None
    assert img.shape == (480, 640, 3)


def test_snapshot_filename_uniqueness(tmp_path: Path):
    """Verify that multiple rapid snapshots generate unique collision-free filenames."""
    service = SnapshotService(snapshot_dir=str(tmp_path))
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    breach = _create_mock_breach(zone_id=1)

    filenames = set()
    for _ in range(10):
        saved = service.save_breach_snapshot(frame, breach)
        filenames.add(saved)

    # All 10 filenames must be distinct
    assert len(filenames) == 10


def test_invalid_frame_rejected(tmp_path: Path):
    """Verify that attempting to snapshot an empty or non-image raises ValueError."""
    service = SnapshotService(snapshot_dir=str(tmp_path))
    breach = _create_mock_breach()

    with pytest.raises(ValueError):
        service.save_breach_snapshot(frame=None, breach=breach)  # type: ignore

    with pytest.raises(ValueError):
        service.save_breach_snapshot(frame=np.array([]), breach=breach)
