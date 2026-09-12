"""
DeepSORT tracker wrapper.

ByteTrack is used via YOLODetector.track() (Ultralytics has it built in and it's
the better default: no re-ID model to load, lower latency, ideal for edge boxes).

This module exists for the alternative path — when you have a *separate* custom
detector (not Ultralytics) and need a standalone tracker with appearance-based
re-identification, which DeepSORT provides and pure ByteTrack does not. Useful if
occlusion/re-entry at a border gate is common and appearance matching helps
re-acquire the same track ID after a person briefly leaves frame.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from src.detection.yolo_detector import Detection


class DeepSortTracker:
    def __init__(self, max_age: int = 30, n_init: int = 3, max_cosine_distance: float = 0.3):
        from deep_sort_realtime.deepsort_tracker import DeepSort

        self.tracker = DeepSort(
            max_age=max_age,
            n_init=n_init,
            max_cosine_distance=max_cosine_distance,
            nn_budget=None,
            embedder="mobilenet",   # lightweight embedder, edge-friendly
            half=True,
            bgr=True,
        )

    def update(self, detections: List[Detection], frame: np.ndarray) -> List[Detection]:
        """Feed raw per-frame detections in, get the same detections back with
        `track_id` populated and stabilised across frames."""
        ds_input: List[Tuple[List[float], float, int]] = []
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            w, h = x2 - x1, y2 - y1
            ds_input.append(([x1, y1, w, h], det.confidence, det.class_id))

        tracks = self.tracker.update_tracks(ds_input, frame=frame)

        tracked_detections: List[Detection] = []
        for t in tracks:
            if not t.is_confirmed():
                continue
            x1, y1, x2, y2 = t.to_ltrb()
            tracked_detections.append(Detection(
                bbox=[x1, y1, x2, y2],
                confidence=t.get_det_conf() or 0.0,
                class_id=t.get_det_class() if t.get_det_class() is not None else -1,
                class_name="",
                track_id=int(t.track_id) if str(t.track_id).isdigit() else hash(t.track_id) % 100000,
            ))
        return tracked_detections
