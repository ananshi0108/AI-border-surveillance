import logging
import threading
import time
from typing import Generator, Optional, Union
import cv2
import numpy as np

from app.services.vision.frame import FramePacket

logger = logging.getLogger("ibvap.vision.stream")


class StreamReader:
    """Modular video stream ingestion engine.
    
    Supports:
    - Local video files (.mp4, .avi, etc.) for testing/replay
    - Local webcams (source=0 or "0")
    - Network IP/RTSP streams (source="rtsp://...") without code changes
    
    Runs a dedicated background thread to ingest frames continuously, preventing
    buffer bloat and ensuring the AI inference pipeline always sees the newest frame.
    """

    def __init__(
        self,
        source: Union[str, int],
        camera_id: Optional[int] = None,
        target_fps: Optional[float] = None,
        reconnect_interval: float = 2.0,
        loop_file: bool = False,
    ):
        # Allow integer camera indices passed as strings (e.g. "0" -> 0 for webcam)
        if isinstance(source, str) and source.isdigit():
            self.source: Union[str, int] = int(source)
        else:
            self.source = source

        self.camera_id = camera_id
        self.target_fps = target_fps
        self.reconnect_interval = reconnect_interval
        self.loop_file = loop_file

        # State tracking
        self.is_running = False
        self.is_connected = False
        self.is_file_source = isinstance(self.source, str) and not self.source.startswith("rtsp://")

        # Stream properties
        self.width = 0
        self.height = 0
        self.fps = 25.0
        self.total_frames_read = 0

        # Threading & frame exchange
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._new_frame_event = threading.Event()
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_timestamp: float = 0.0

        # OpenCV capture instance
        self._cap: Optional[cv2.VideoCapture] = None

    def start(self) -> "StreamReader":
        """Starts the background frame ingestion thread."""
        if self.is_running:
            logger.warning(f"[Camera {self.camera_id}] Stream reader is already running.")
            return self

        self.is_running = True
        self._thread = threading.Thread(
            target=self._capture_worker,
            name=f"StreamWorker-Cam{self.camera_id or 'Local'}",
            daemon=True,
        )
        self._thread.start()
        logger.info(f"[Camera {self.camera_id}] Ingestion thread started for source: {self.source}")
        return self

    def _open_capture(self) -> bool:
        """Attempts to open or re-open the video capture resource."""
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass

        logger.info(f"[Camera {self.camera_id}] Opening stream: {self.source}")
        self._cap = cv2.VideoCapture(self.source)

        # For live RTSP streams, minimize internal buffering to prevent latency
        if isinstance(self.source, str) and self.source.startswith("rtsp://"):
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self._cap.isOpened():
            logger.warning(f"[Camera {self.camera_id}] Failed to open video source: {self.source}")
            self.is_connected = False
            return False

        # Read video metadata
        self.width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        self.height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
        detected_fps = self._cap.get(cv2.CAP_PROP_FPS)
        self.fps = detected_fps if (detected_fps and detected_fps > 0) else (self.target_fps or 25.0)

        self.is_connected = True
        logger.info(
            f"[Camera {self.camera_id}] Stream opened successfully "
            f"({self.width}x{self.height} @ {self.fps:.1f} FPS)"
        )
        return True

    def _capture_worker(self) -> None:
        """Background loop continuously grabbing frames from the source."""
        while self.is_running:
            # 1. Connect or Reconnect if disconnected
            if not self.is_connected or self._cap is None or not self._cap.isOpened():
                if not self._open_capture():
                    if self.is_file_source and not self.loop_file and self.total_frames_read > 0:
                        # Reached end of static file and not looping
                        logger.info(f"[Camera {self.camera_id}] End of video file reached.")
                        self.is_running = False
                        break

                    logger.info(f"[Camera {self.camera_id}] Reconnecting in {self.reconnect_interval}s...")
                    time.sleep(self.reconnect_interval)
                    continue

            # 2. Read next frame
            frame_start_time = time.time()
            success, frame = self._cap.read()

            if not success or frame is None:
                logger.warning(f"[Camera {self.camera_id}] Frame read returned empty or failed.")
                if self.is_file_source:
                    if self.loop_file:
                        logger.info(f"[Camera {self.camera_id}] Looping video file to beginning.")
                        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        logger.info(f"[Camera {self.camera_id}] Video file finished.")
                        self.is_running = False
                        break
                else:
                    # Live RTSP / Webcam disconnection: mark disconnected and retry
                    self.is_connected = False
                    time.sleep(self.reconnect_interval)
                    continue

            # 3. Store the newest frame thread-safely
            with self._lock:
                self._latest_frame = frame
                self._latest_timestamp = time.time()
                self.total_frames_read += 1
                self._new_frame_event.set()

            # 4. FPS Throttling (especially for local video files so they don't read at 1000 FPS)
            target = self.target_fps or (self.fps if self.is_file_source else None)
            if target and target > 0:
                elapsed = time.time() - frame_start_time
                sleep_duration = (1.0 / target) - elapsed
                if sleep_duration > 0:
                    time.sleep(sleep_duration)

        # Clean release when loop finishes
        self._release_resources()

    def get_latest_frame(self, timeout: float = 1.0) -> Optional[FramePacket]:
        """Retrieves the latest frame packet. Waits up to `timeout` seconds for a new frame."""
        if not self.is_running and not self.is_connected:
            return None

        # Wait for the worker to signal a fresh frame
        flag = self._new_frame_event.wait(timeout=timeout)
        if not flag:
            return None

        with self._lock:
            self._new_frame_event.clear()
            if self._latest_frame is None:
                return None

            return FramePacket(
                camera_id=self.camera_id,
                frame_index=self.total_frames_read,
                timestamp=self._latest_timestamp,
                frame=self._latest_frame.copy(),
                width=self.width,
                height=self.height,
                fps=self.fps,
            )

    def iter_frames(self, timeout: float = 2.0) -> Generator[FramePacket, None, None]:
        """Clean generator yielding frames to the downstream AI pipeline.
        
        Usage in future AI engine:
            for packet in reader.iter_frames():
                results = model(packet.frame)
        """
        while self.is_running:
            packet = self.get_latest_frame(timeout=timeout)
            if packet is not None:
                yield packet
            elif not self.is_connected and self.is_file_source:
                # Video file reached end
                break

    def stop(self) -> None:
        """Signals the stream ingestion worker to stop and releases resources."""
        if not self.is_running:
            return

        logger.info(f"[Camera {self.camera_id}] Stopping stream reader...")
        self.is_running = False
        self._new_frame_event.set()  # Unblock any waiting consumers

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

        self._release_resources()
        logger.info(f"[Camera {self.camera_id}] Stream reader stopped successfully.")

    def _release_resources(self) -> None:
        """Safely closes OpenCV capture handle."""
        self.is_connected = False
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception as e:
                logger.error(f"[Camera {self.camera_id}] Error releasing capture: {e}")
            finally:
                self._cap = None

    def __enter__(self) -> "StreamReader":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
