"""
Video stream helpers: unified reader for file / webcam / RTSP sources,
FPS throttling for low-power edge boxes, and a cheap brightness heuristic
used to decide when to switch on low-light enhancement.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterator, Optional, Union

import cv2
import numpy as np


@dataclass
class FrameData:
    frame: np.ndarray
    frame_idx: int
    timestamp: float


class VideoStream:
    """Wraps cv2.VideoCapture for files, webcams (int index) and RTSP/HTTP URLs.

    Usage:
        with VideoStream("rtsp://cam/stream1", target_fps=10) as stream:
            for frame_data in stream:
                ...
    """

    def __init__(self, source: Union[str, int], target_fps: Optional[int] = None,
                 resize_width: Optional[int] = None):
        self.source = int(source) if isinstance(source, str) and source.isdigit() else source
        self.target_fps = target_fps
        self.resize_width = resize_width
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_idx = 0
        self._min_frame_interval = 1.0 / target_fps if target_fps else 0.0
        self._last_read_time = 0.0

    def __enter__(self) -> "VideoStream":
        self._cap = cv2.VideoCapture(self.source)
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open video source: {self.source}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._cap is not None:
            self._cap.release()

    def _resize(self, frame: np.ndarray) -> np.ndarray:
        if self.resize_width is None:
            return frame
        h, w = frame.shape[:2]
        if w == self.resize_width:
            return frame
        scale = self.resize_width / w
        return cv2.resize(frame, (self.resize_width, int(h * scale)))

    def __iter__(self) -> Iterator[FrameData]:
        assert self._cap is not None, "Use VideoStream as a context manager."
        while True:
            # Edge throttling: skip frames instead of processing every one,
            # so a slow edge box doesn't fall behind an RTSP camera's real-time feed.
            if self._min_frame_interval:
                elapsed = time.time() - self._last_read_time
                if elapsed < self._min_frame_interval:
                    time.sleep(self._min_frame_interval - elapsed)

            ok, frame = self._cap.read()
            if not ok:
                break
            self._last_read_time = time.time()
            self._frame_idx += 1
            yield FrameData(frame=self._resize(frame), frame_idx=self._frame_idx,
                             timestamp=self._last_read_time)


def is_low_light(frame: np.ndarray, threshold: float = 60.0) -> bool:
    """Cheap heuristic to decide whether night-mode enhancement should trigger.

    Uses mean luminance on the grayscale/V-channel. Runs in microseconds, so it's
    safe to call every frame on an edge box before deciding whether to run the
    (more expensive) enhancement network.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(gray.mean()) < threshold


def draw_label(frame: np.ndarray, text: str, x: int, y: int,
                color=(0, 255, 0), scale: float = 0.5) -> None:
    """Draws a filled-background label — used for all overlay annotations
    (detections, track IDs, alerts) so text stays legible over any footage."""
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    cv2.rectangle(frame, (x, y - th - 6), (x + tw + 4, y), color, -1)
    cv2.putText(frame, text, (x + 2, y - 4), cv2.FONT_HERSHEY_SIMPLEX, scale,
                (0, 0, 0), 1, cv2.LINE_AA)
