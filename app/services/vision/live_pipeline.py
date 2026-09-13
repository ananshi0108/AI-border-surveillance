"""
Live video processing pipeline for IBVAP.

Pipeline:
Camera Stream
    -> YOLO Detection
    -> Geometry Rule Engine
    -> Snapshot Evidence
    -> Database Alert
"""

import logging
import threading
import time
from typing import List, Optional

import cv2
import numpy as np
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.camera import Camera
from app.models.zone import Zone
from app.services.alerts.service import alert_service
from app.services.alerts.snapshot import snapshot_service
from app.services.vision.detection import DetectionResult
from app.services.vision.detector import YOLODetector
from app.services.vision.rules import GeometryRuleEngine
from app.services.vision.stream_reader import StreamReader

logger = logging.getLogger("ibvap.vision.live_pipeline")


class LivePipeline:
    """
    Runs the complete backend video-analysis pipeline for one camera.

    One pipeline instance handles:
        StreamReader -> YOLO -> Geometry -> Snapshot -> Alert DB
    """

    def __init__(
        self,
        camera_id: int,
        stream_url: str,
        camera_name: Optional[str] = None,
        target_fps: float = 5.0,
    ):
        self.camera_id = camera_id
        self.stream_url = stream_url
        self.camera_name = camera_name or f"Camera {camera_id}"
        self.target_fps = target_fps

        self.reader = StreamReader(
        source=stream_url,
        camera_id=camera_id,
        target_fps=target_fps,
        loop_file=True,
    )

        # Existing AI detector. We are only using it here.
        self.detector = YOLODetector(
            model_name="yolov8n.pt",
            confidence_threshold=0.35,
        )

        # Stateful because tripwire detection needs the previous position.
        self.rule_engine = GeometryRuleEngine()

        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Prevent processing the same frame multiple times.
        self._last_frame_index = -1

        # Reload zones periodically so dashboard changes eventually
        # become active without restarting the pipeline.
        self._zones = []
        self._last_zone_refresh = 0.0
        self._zone_refresh_interval = 2.0

        # Prevent repeated alerts for the same camera/zone/class.
        self._last_alert_times = {}
        self._alert_cooldown = 10.0

        # Latest annotated (boxes + zones drawn) frame, exposed to the
        # frontend via the MJPEG / snapshot API endpoints.
        self._frame_lock = threading.Lock()
        self._latest_annotated_frame: Optional[np.ndarray] = None
        self._latest_detection_count: int = 0

    # ------------------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the video processing pipeline in a background thread."""

        if self._running:
            logger.warning(
                "[LivePipeline] Camera %s is already running.",
                self.camera_id,
            )
            return

        self._running = True

        self.reader.start()

        self._thread = threading.Thread(
            target=self._run,
            name=f"ibvap-camera-{self.camera_id}",
            daemon=True,
        )
        self._thread.start()

        logger.info(
            "[LivePipeline] Started camera %s (%s)",
            self.camera_id,
            self.camera_name,
        )

    def stop(self) -> None:
        """Stop the pipeline and release the video stream."""

        if not self._running:
            return

        logger.info(
            "[LivePipeline] Stopping camera %s",
            self.camera_id,
        )

        self._running = False
        self.reader.stop()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        self._thread = None

        logger.info(
            "[LivePipeline] Camera %s stopped.",
            self.camera_id,
        )

    # ------------------------------------------------------------------
    # MAIN PIPELINE
    # ------------------------------------------------------------------

    def _run(self) -> None:
        """Main background processing loop."""

        logger.info(
            "[LivePipeline] Processing started for camera %s",
            self.camera_id,
        )

        while self._running:
            try:
                frame_packet = self.reader.get_latest_frame(timeout=2.0)

                if frame_packet is None:
                    continue

                # StreamReader may return the same latest frame repeatedly.
                if frame_packet.frame_index == self._last_frame_index:
                    time.sleep(0.01)
                    continue

                self._last_frame_index = frame_packet.frame_index

                # Refresh zones periodically.
                self._refresh_zones_if_needed()

                # ------------------------------------------------------
                # STEP 1: YOLO DETECTION
                # ------------------------------------------------------
                # Detection always runs (even with zero configured zones)
                # so the live camera view / virtual fence editor on the
                # frontend has a real, boxed video feed to show.

                frame_detections = self.detector.detect(
                    frame_packet,
                )

                logger.debug(
                    "[LivePipeline] Camera %s | Frame %s | Detections: %s",
                    self.camera_id,
                    frame_packet.frame_index,
                    len(frame_detections.detections),
                )

                # Publish an annotated JPEG-ready frame for the streaming
                # endpoints, independent of whether any zone was breached.
                self._update_annotated_frame(
                    frame_packet.frame,
                    frame_detections.detections,
                )

                if not self._zones or not frame_detections.detections:
                    continue

                # ------------------------------------------------------
                # STEP 2: GEOMETRY / VIRTUAL FENCE
                # ------------------------------------------------------

                breaches = self.rule_engine.evaluate_zones(
                    frame_detections,
                    self._zones,
                )

                if not breaches:
                    continue

                logger.info(
                    "[LivePipeline] Camera %s | Frame %s | Breaches: %s",
                    self.camera_id,
                    frame_packet.frame_index,
                    len(breaches),
                )

                # ------------------------------------------------------
                # STEP 3: SNAPSHOT + DATABASE ALERT
                # ------------------------------------------------------

                for breach in breaches:
                    self._handle_breach(
                        frame_packet.frame,
                        breach,
                    )

            except Exception:
                logger.exception(
                    "[LivePipeline] Error while processing camera %s",
                    self.camera_id,
                )

                # Prevent a tight error loop.
                time.sleep(1.0)

        logger.info(
            "[LivePipeline] Processing ended for camera %s",
            self.camera_id,
        )

    # ------------------------------------------------------------------
    # LIVE FRAME PUBLISHING (used by /cameras/{id}/stream & /snapshot)
    # ------------------------------------------------------------------

    def _update_annotated_frame(
        self,
        frame: np.ndarray,
        detections: List[DetectionResult],
    ) -> None:
        """Draws bounding boxes + configured zones onto a copy of the frame
        and stores it so the API layer can serve it as MJPEG/JPEG."""

        annotated = frame.copy()
        height, width = annotated.shape[:2]

        # Draw configured zones (virtual fences / tripwires) for context.
        for zone in self._zones:
            raw_coords = getattr(zone, "coordinates", None) or []
            if len(raw_coords) < 2:
                continue

            is_normalized = all(max(pt[0], pt[1]) <= 1.05 for pt in raw_coords)
            points = []
            for x, y in raw_coords:
                if is_normalized:
                    points.append((int(x * width), int(y * height)))
                else:
                    points.append((int(x), int(y)))

            zone_type = getattr(zone, "zone_type", None)
            zone_type_str = zone_type.value if hasattr(zone_type, "value") else str(zone_type)
            color = (0, 60, 255) if zone_type_str == "POLYGON" else (0, 165, 255)

            if zone_type_str == "POLYGON" and len(points) >= 3:
                cv2.polylines(
                    annotated,
                    [np.array(points, dtype=np.int32)],
                    isClosed=True,
                    color=color,
                    thickness=2,
                )
            elif len(points) >= 2:
                cv2.line(annotated, points[0], points[1], color, 2)

        # Draw detection boxes + labels.
        for det in detections:
            x1, y1, x2, y2 = (
                int(det.bbox.x1),
                int(det.bbox.y1),
                int(det.bbox.x2),
                int(det.bbox.y2),
            )
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 220, 90), 2)
            label = f"{det.class_name} {det.confidence:.2f}"
            label_y = max(14, y1 - 6)
            cv2.putText(
                annotated,
                label,
                (x1, label_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 220, 90),
                1,
                cv2.LINE_AA,
            )

        with self._frame_lock:
            self._latest_annotated_frame = annotated
            self._latest_detection_count = len(detections)

    def get_latest_jpeg(self, quality: int = 80) -> Optional[bytes]:
        """Returns the most recent annotated frame encoded as JPEG bytes,
        or None if no frame has been processed yet."""

        with self._frame_lock:
            frame = self._latest_annotated_frame

        if frame is None:
            return None

        ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ok:
            return None

        return buffer.tobytes()

    @property
    def latest_detection_count(self) -> int:
        with self._frame_lock:
            return self._latest_detection_count

    # ------------------------------------------------------------------
    # ZONE MANAGEMENT
    # ------------------------------------------------------------------

    def _refresh_zones_if_needed(self) -> None:
        """Load active zones for this camera periodically."""

        now = time.time()

        if now - self._last_zone_refresh < self._zone_refresh_interval:
            return

        db = SessionLocal()

        try:
            statement = (
                select(Zone)
                .where(
                    Zone.camera_id == self.camera_id,
                    Zone.is_active.is_(True),
                )
            )

            self._zones = list(db.scalars(statement).all())
            self._last_zone_refresh = now

            logger.debug(
                "[LivePipeline] Camera %s | Active zones: %s",
                self.camera_id,
                len(self._zones),
            )

        except Exception:
            logger.exception(
                "[LivePipeline] Failed to load zones for camera %s",
                self.camera_id,
            )

        finally:
            db.close()

    # ------------------------------------------------------------------
    # BREACH HANDLING
    # ------------------------------------------------------------------

    def _handle_breach(self, frame, breach) -> None:
        """
        Convert one geometry breach into permanent evidence
        and a database alert.
        """
                # Create a simple identity for this type of alert.
        # Currently we don't have a tracking ID, so we use
        # camera + zone + detected class.
        alert_key = (
            self.camera_id,
            breach.zone_id,
            breach.detection.class_name.lower(),
        )

        now = time.time()
        last_alert_time = self._last_alert_times.get(alert_key)

        # Ignore repeated alerts during the cooldown period.
        if (
            last_alert_time is not None
            and now - last_alert_time < self._alert_cooldown
        ):
            logger.debug(
                "[LivePipeline] Duplicate alert suppressed | "
                "camera=%s zone=%s class=%s",
                self.camera_id,
                breach.zone_id,
                breach.detection.class_name,
            )
            return

        # Record this alert before creating the snapshot/database entry.
        self._last_alert_times[alert_key] = now
    
        db = SessionLocal()

        try:
            # Find the matching Zone so we can draw its boundary
            # on the evidence snapshot.
            zone = db.get(Zone, breach.zone_id)

            zone_coordinates = None

            if zone is not None:
                zone_coordinates = zone.coordinates

            # ----------------------------------------------------------
            # SAVE EVIDENCE SNAPSHOT
            # ----------------------------------------------------------

            snapshot_path = snapshot_service.save_breach_snapshot(
                frame=frame,
                breach=breach,
                zone_coordinates=zone_coordinates,
                camera_name=self.camera_name,
            )

            # ----------------------------------------------------------
            # CREATE DATABASE ALERT
            # ----------------------------------------------------------

            alert = alert_service.create_alert(
                db=db,
                breach=breach,
                snapshot_path=snapshot_path,
            )

            logger.info(
                "[LivePipeline] ALERT CREATED | "
                "alert_id=%s camera=%s zone=%s type=%s snapshot=%s",
                alert.id,
                self.camera_id,
                breach.zone_id,
                breach.breach_type.value,
                snapshot_path,
            )

        except Exception:
            logger.exception(
                "[LivePipeline] Failed to handle breach "
                "for camera %s, zone %s",
                self.camera_id,
                breach.zone_id,
            )

        finally:
            db.close()


# ----------------------------------------------------------------------
# SIMPLE SINGLE-CAMERA HELPER
# ----------------------------------------------------------------------

def start_camera_pipeline(
    camera_id: int,
    stream_url: str,
    camera_name: Optional[str] = None,
    target_fps: float = 5.0,
) -> LivePipeline:
    """
    Convenience function for starting a camera pipeline.
    """

    pipeline = LivePipeline(
        camera_id=camera_id,
        stream_url=stream_url,
        camera_name=camera_name,
        target_fps=target_fps,
    )

    pipeline.start()

    return pipeline