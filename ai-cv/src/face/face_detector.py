"""
Face detection using YuNet (cv2.FaceDetectorYN) — a tiny (~230KB) ONNX model
shipped by OpenCV Zoo. Chosen over RetinaFace as the primary edge detector
because it runs comfortably in real time on CPU-only border boxes; RetinaFace
is heavier but more robust at extreme angles/scales, so it's kept as a
documented drop-in alternative below for sites with GPU edge hardware.

Model download (also handled by scripts/download_models.py):
    https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/
    face_detection_yunet_2023mar.onnx
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np


@dataclass
class FaceDetection:
    bbox: List[float]          # [x, y, w, h]
    confidence: float
    landmarks: List[Tuple[float, float]]  # 5 points: right eye, left eye, nose, mouth corners


class YuNetFaceDetector:
    def __init__(self, model_path: str, input_size: Tuple[int, int] = (320, 320),
                 score_threshold: float = 0.7, nms_threshold: float = 0.3, top_k: int = 500):
        self.input_size = input_size
        self.detector = cv2.FaceDetectorYN.create(
            model=model_path,
            config="",
            input_size=input_size,
            score_threshold=score_threshold,
            nms_threshold=nms_threshold,
            top_k=top_k,
        )

    def detect(self, frame: np.ndarray) -> List[FaceDetection]:
        h, w = frame.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(frame)

        results: List[FaceDetection] = []
        if faces is None:
            return results

        for face in faces:
            x, y, bw, bh = face[0:4]
            landmarks = [(face[4 + 2 * i], face[5 + 2 * i]) for i in range(5)]
            confidence = float(face[14])
            results.append(FaceDetection(
                bbox=[float(x), float(y), float(bw), float(bh)],
                confidence=confidence,
                landmarks=landmarks,
            ))
        return results

    def detect_in_roi(self, frame: np.ndarray, bbox: List[float]) -> List[FaceDetection]:
        """Run face detection restricted to a person's bounding box (from the
        YOLO+tracker output), which is both faster and more accurate than
        scanning the whole frame for small/distant faces at border checkpoints."""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        x1, y1 = max(0, x1), max(0, y1)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return []
        faces = self.detect(crop)
        # offset back into full-frame coordinates
        for f in faces:
            f.bbox[0] += x1
            f.bbox[1] += y1
            f.landmarks = [(lx + x1, ly + y1) for lx, ly in f.landmarks]
        return faces


# ---------------------------------------------------------------------------
# Optional heavier alternative: RetinaFace (better at extreme pose/scale, GPU-friendly)
#
#   pip install retina-face
#   from retinaface import RetinaFace
#   faces = RetinaFace.detect_faces(frame)
#
# Swap in behind the same FaceDetection interface if a site has GPU edge
# hardware and needs the extra robustness (e.g. steep-angle gate cameras).
# ---------------------------------------------------------------------------
