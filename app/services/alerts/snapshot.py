import logging
import os
from pathlib import Path
import time
from typing import Any, List, Optional, Tuple, Union
import uuid
import cv2
import numpy as np

from app.core.config import settings
from app.services.vision.rules import BreachType, ZoneBreach

logger = logging.getLogger("ibvap.alerts.snapshot")


class SnapshotService:
    """Modular evidence capture and annotation service.
    
    When a perimeter intrusion or tripwire breach is confirmed by the GeometryRuleEngine,
    this service burns visual overlays (bounding boxes, zone boundaries, incident metadata)
    onto the frame and saves a permanent, uniquely named JPEG evidence file.
    """

    def __init__(self, snapshot_dir: Optional[str] = None):
        self.snapshot_dir = Path(snapshot_dir or settings.SNAPSHOT_DIR)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def save_breach_snapshot(
        self,
        frame: np.ndarray,
        breach: ZoneBreach,
        zone_coordinates: Optional[List[Union[List[float], Tuple[float, float]]]] = None,
        camera_name: Optional[str] = None,
    ) -> str:
        """Annotates and saves an incident snapshot for a verified perimeter breach.
        
        Args:
            frame: Raw BGR video frame from FramePacket.
            breach: The ZoneBreach event emitted by GeometryRuleEngine.
            zone_coordinates: Optional boundary coordinates of the breached zone.
            camera_name: Optional human-readable camera name.
            
        Returns:
            Relative file path string of the saved JPEG evidence snapshot.
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            raise ValueError("Invalid frame supplied for snapshot capture.")

        # 1. Clone frame so the original video feed remains untouched
        annotated = frame.copy()
        height, width = annotated.shape[:2]

        # 2. Draw Virtual Fence / Zone Boundary if coordinates are provided
        if zone_coordinates and len(zone_coordinates) >= 2:
            self._draw_zone_boundary(annotated, zone_coordinates, breach.breach_type, width, height)

        # 3. Draw Target Bounding Box & Ground Contact Point
        self._draw_target_evidence(annotated, breach, width, height)

        # 4. Burn Top Incident Header Banner
        self._draw_incident_header(annotated, breach, camera_name, width)

        # 5. Generate collision-resistant unique filename
        cam_id = breach.camera_id or 0
        timestamp_ms = int(time.time() * 1000)
        unique_suffix = uuid.uuid4().hex[:6]
        filename = f"alert_cam{cam_id}_z{breach.zone_id}_{timestamp_ms}_{unique_suffix}.jpg"
        file_path = self.snapshot_dir / filename

        # 6. Save image to disk as high-quality JPEG
        success = cv2.imwrite(
            str(file_path),
            annotated,
            [int(cv2.IMWRITE_JPEG_QUALITY), 90],
        )

        if not success:
            logger.error(f"Failed to write snapshot to disk: {file_path}")
            raise IOError(f"Failed to save snapshot to {file_path}")

        logger.info(f"[SnapshotService] Evidence saved: {file_path}")
        return str(file_path)

    def _draw_zone_boundary(
        self,
        img: np.ndarray,
        coords: List[Any],
        breach_type: BreachType,
        width: int,
        height: int,
    ) -> None:
        """Draws the virtual tripwire line or polygon zone on the image."""
        # Check if coordinates are normalized (<= 1.0) or in pixels (> 1.0)
        is_normalized = all(max(float(pt[0]), float(pt[1])) <= 1.05 for pt in coords)

        pts = []
        for pt in coords:
            if is_normalized:
                pts.append([int(float(pt[0]) * width), int(float(pt[1]) * height)])
            else:
                pts.append([int(float(pt[0])), int(float(pt[1]))])

        pts_array = np.array(pts, np.int32)

        if breach_type == BreachType.TRIPWIRE_CROSSING or len(pts) == 2:
            # Draw Tripwire Line (Neon Yellow/Amber)
            cv2.line(img, tuple(pts[0]), tuple(pts[1]), (0, 230, 255), 3, cv2.LINE_AA)
            cv2.putText(
                img,
                "VIRTUAL TRIPWIRE",
                (pts[0][0] + 10, pts[0][1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 230, 255),
                1,
                cv2.LINE_AA,
            )
        else:
            # Draw Polygon Boundary (Neon Cyan with semi-transparent overlay)
            pts_reshaped = pts_array.reshape((-1, 1, 2))
            overlay = img.copy()
            cv2.fillPoly(overlay, [pts_reshaped], (0, 255, 200))
            # Blend 25% transparency
            cv2.addWeighted(overlay, 0.25, img, 0.75, 0, img)
            # Solid perimeter border
            cv2.polylines(img, [pts_reshaped], isClosed=True, color=(0, 255, 200), thickness=2, lineType=cv2.LINE_AA)

    def _draw_target_evidence(
        self,
        img: np.ndarray,
        breach: ZoneBreach,
        width: int,
        height: int,
    ) -> None:
        """Draws target bounding box, ground-contact point, and detection tag."""
        det = breach.detection
        bbox = det.bbox

        x1, y1 = max(0, int(bbox.x1)), max(0, int(bbox.y1))
        x2, y2 = min(width - 1, int(bbox.x2)), min(height - 1, int(bbox.y2))

        # 1. Bounding box in crimson red (0, 0, 230)
        box_color = (0, 0, 230)
        cv2.rectangle(img, (x1, y1), (x2, y2), box_color, 2, cv2.LINE_AA)

        # 2. Label tag with solid background
        label_text = f"BREACH: {det.class_name.upper()} {det.confidence:.0%}"
        font_scale = 0.5
        font_thickness = 1
        (label_w, label_h), baseline = cv2.getTextSize(
            label_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            font_thickness,
        )

        label_y1 = max(0, y1 - label_h - 8)
        label_y2 = label_y1 + label_h + 8
        label_x2 = min(width - 1, x1 + label_w + 10)

        # Solid tag header
        cv2.rectangle(img, (x1, label_y1), (label_x2, label_y2), box_color, -1)
        cv2.putText(
            img,
            label_text,
            (x1 + 5, label_y2 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),
            font_thickness,
            cv2.LINE_AA,
        )

        # 3. Ground contact point (feet / base marker)
        cx, cy = breach.contact_point
        if cx <= 1.05 and cy <= 1.05:
            # Normalized
            px, py = int(cx * width), int(cy * height)
        else:
            px, py = int(cx), int(cy)

        # Red bullseye with white core
        cv2.circle(img, (px, py), 7, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.circle(img, (px, py), 3, (255, 255, 255), -1, cv2.LINE_AA)

    def _draw_incident_header(
        self,
        img: np.ndarray,
        breach: ZoneBreach,
        camera_name: Optional[str],
        width: int,
    ) -> None:
        """Burns a high-contrast tactical security header banner across the top."""
        banner_h = 36
        overlay = img.copy()
        # Dark charcoal header bar
        cv2.rectangle(overlay, (0, 0), (width, banner_h), (20, 20, 25), -1)
        cv2.addWeighted(overlay, 0.85, img, 0.15, 0, img)

        # Left red alert accent bar
        cv2.rectangle(img, (0, 0), (8, banner_h), (0, 0, 220), -1)

        # Header text
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(breach.timestamp))
        cam_tag = camera_name or f"CAMERA {breach.camera_id or 1}"
        header_text = f"[IBVAP INTRUSION] {cam_tag} | ZONE: {breach.zone_name.upper()} | {time_str}"

        cv2.putText(
            img,
            header_text,
            (18, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )


# Global singleton instance
snapshot_service = SnapshotService()
