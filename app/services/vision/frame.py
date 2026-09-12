from dataclasses import dataclass
from typing import Optional
import cv2
import numpy as np


@dataclass
class FramePacket:
    """Represents a single decoded video frame passed to the AI inference pipeline."""
    camera_id: Optional[int]
    frame_index: int
    timestamp: float          # POSIX timestamp when the frame was captured
    frame: np.ndarray         # Raw BGR image matrix from OpenCV
    width: int
    height: int
    fps: float                # Source or detected frame rate

    def to_jpeg(self, quality: int = 85) -> Optional[bytes]:
        """Encodes the frame as JPEG bytes (useful for alert snapshots or web previews)."""
        success, encoded = cv2.imencode(
            ".jpg",
            self.frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), quality],
        )
        if success:
            return encoded.tobytes()
        return None
