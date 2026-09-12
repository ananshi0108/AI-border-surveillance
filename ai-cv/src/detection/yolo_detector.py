"""
YOLO-based object detector (person / vehicle) wrapper around Ultralytics YOLOv8.

Supports three interchangeable backends behind the same interface, so the rest
of the pipeline doesn't care whether it's running the raw PyTorch checkpoint,
an exported ONNX graph, or a TensorRT engine on an edge box:
    backend="pytorch" | "onnx" | "tensorrt"

Fine-tuning on a custom dataset: use Ultralytics' own CLI/API, e.g.

    from ultralytics import YOLO
    model = YOLO("yolov8n.pt")
    model.train(data="border_dataset.yaml", epochs=100, imgsz=640)

then point `configs/config.yaml -> detection.model_path` at the resulting
`runs/detect/train/weights/best.pt`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np


@dataclass
class Detection:
    bbox: List[float]        # [x1, y1, x2, y2] in pixel coords
    confidence: float
    class_id: int
    class_name: str
    track_id: Optional[int] = None


class YOLODetector:
    def __init__(self, model_path: str, confidence: float = 0.35, iou: float = 0.45,
                 device: str = "cpu", backend: str = "pytorch",
                 class_filter: Optional[List[int]] = None):
        """
        Args:
            model_path: path to .pt (pytorch), .onnx (onnx) or .engine (tensorrt) weights.
            class_filter: list of COCO class ids to keep (e.g. [0,2,3,5,7] for
                person/car/motorcycle/bus/truck). None keeps everything.
        """
        from ultralytics import YOLO  # local import keeps module import light for tooling

        self.model = YOLO(model_path, task="detect")
        self.confidence = confidence
        self.iou = iou
        self.device = device
        self.backend = backend
        self.class_filter = class_filter
        self.names = self.model.names  # {class_id: class_name}

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Single-frame detection (no tracking). Use `track()` for tracked IDs."""
        results = self.model.predict(
            frame, conf=self.confidence, iou=self.iou, device=self.device,
            classes=self.class_filter, verbose=False,
        )
        return self._parse_results(results)

    def track(self, frame: np.ndarray, tracker_cfg: str = "bytetrack.yaml",
               persist: bool = True) -> List[Detection]:
        """Detection + multi-object tracking in one call.

        Ultralytics ships ByteTrack (`bytetrack.yaml`) and BoT-SORT (`botsort.yaml`)
        configs out of the box. `persist=True` keeps track state across calls for
        the same video stream.
        """
        results = self.model.track(
            frame, conf=self.confidence, iou=self.iou, device=self.device,
            classes=self.class_filter, tracker=tracker_cfg, persist=persist,
            verbose=False,
        )
        return self._parse_results(results, with_track_id=True)

    def _parse_results(self, results, with_track_id: bool = False) -> List[Detection]:
        detections: List[Detection] = []
        if not results:
            return detections
        r = results[0]
        if r.boxes is None or len(r.boxes) == 0:
            return detections

        boxes_xyxy = r.boxes.xyxy.cpu().numpy()
        confs = r.boxes.conf.cpu().numpy()
        cls_ids = r.boxes.cls.cpu().numpy().astype(int)
        track_ids = None
        if with_track_id and r.boxes.id is not None:
            track_ids = r.boxes.id.cpu().numpy().astype(int)

        for i in range(len(boxes_xyxy)):
            detections.append(Detection(
                bbox=boxes_xyxy[i].tolist(),
                confidence=float(confs[i]),
                class_id=int(cls_ids[i]),
                class_name=self.names.get(int(cls_ids[i]), str(cls_ids[i])),
                track_id=int(track_ids[i]) if track_ids is not None else None,
            ))
        return detections
