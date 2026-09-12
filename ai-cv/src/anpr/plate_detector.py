"""
License plate localisation.

Two modes:
1. `model_path` given and file exists -> uses a YOLO model fine-tuned for plates
   (recommended for production accuracy; train on a labeled plate dataset the
   same way as src/detection/yolo_detector.py describes).
2. No plate model available -> falls back to a classical edge/contour-based
   heuristic (Sobel + morphology + aspect-ratio filtering) restricted to the
   bounding box of vehicles already found by YOLODetector. Works out of the box
   with zero extra training data — good enough for a hackathon demo, and a
   sane fallback in the field if a plate model isn't deployed to a given site yet.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class PlateCandidate:
    bbox: List[float]      # [x1, y1, x2, y2] in full-frame coordinates
    confidence: float
    crop: np.ndarray       # cropped plate image, ready for OCR


class PlateDetector:
    def __init__(self, model_path: Optional[str] = None,
                 aspect_ratio_range: Tuple[float, float] = (2.0, 6.0),
                 min_confidence: float = 0.4):
        self.aspect_ratio_range = aspect_ratio_range
        self.min_confidence = min_confidence
        self.model = None
        if model_path and os.path.exists(model_path):
            from ultralytics import YOLO
            self.model = YOLO(model_path, task="detect")

    def detect_plates_in_vehicle(self, frame: np.ndarray, vehicle_bbox: List[float]) -> List[PlateCandidate]:
        x1, y1, x2, y2 = [int(v) for v in vehicle_bbox]
        x1, y1 = max(0, x1), max(0, y1)
        vehicle_crop = frame[y1:y2, x1:x2]
        if vehicle_crop.size == 0:
            return []

        if self.model is not None:
            return self._detect_with_model(vehicle_crop, offset=(x1, y1))
        return self._detect_with_contours(vehicle_crop, offset=(x1, y1))

    # -- YOLO-based path -----------------------------------------------------
    def _detect_with_model(self, crop: np.ndarray, offset: Tuple[int, int]) -> List[PlateCandidate]:
        ox, oy = offset
        results = self.model.predict(crop, conf=self.min_confidence, verbose=False)
        candidates: List[PlateCandidate] = []
        if not results or results[0].boxes is None:
            return candidates
        boxes = results[0].boxes.xyxy.cpu().numpy()
        confs = results[0].boxes.conf.cpu().numpy()
        for box, conf in zip(boxes, confs):
            px1, py1, px2, py2 = box
            plate_crop = crop[int(py1):int(py2), int(px1):int(px2)]
            if plate_crop.size == 0:
                continue
            candidates.append(PlateCandidate(
                bbox=[px1 + ox, py1 + oy, px2 + ox, py2 + oy],
                confidence=float(conf),
                crop=plate_crop,
            ))
        return candidates

    # -- Classical fallback path ---------------------------------------------
    def _detect_with_contours(self, crop: np.ndarray, offset: Tuple[int, int]) -> List[PlateCandidate]:
        ox, oy = offset
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)

        # vertical Sobel highlights the dense vertical edges typical of plate text
        sobel_x = cv2.Sobel(gray, cv2.CV_8U, 1, 0, ksize=3)
        _, thresh = cv2.threshold(sobel_x, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 4))
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        morph = cv2.dilate(morph, None, iterations=2)

        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates: List[PlateCandidate] = []
        min_ar, max_ar = self.aspect_ratio_range
        crop_h, crop_w = crop.shape[:2]

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h == 0:
                continue
            aspect_ratio = w / float(h)
            area_fraction = (w * h) / float(crop_w * crop_h)
            # plates are a modest fraction of the vehicle crop, with a fixed aspect ratio band
            if min_ar <= aspect_ratio <= max_ar and 0.01 < area_fraction < 0.35:
                plate_crop = crop[y:y + h, x:x + w]
                candidates.append(PlateCandidate(
                    bbox=[x + ox, y + oy, x + w + ox, y + h + oy],
                    confidence=0.5,  # heuristic method — fixed, conservative confidence
                    crop=plate_crop,
                ))

        # keep only the most plate-shaped candidate to avoid flooding OCR with noise
        candidates.sort(key=lambda c: abs((c.bbox[2] - c.bbox[0]) / max(1, c.bbox[3] - c.bbox[1]) - 3.14))
        return candidates[:2]
