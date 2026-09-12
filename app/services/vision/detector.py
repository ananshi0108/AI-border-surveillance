import logging
import time
from typing import List, Optional, Set, Union
import numpy as np

from app.services.vision.detection import BoundingBox, DetectionResult, FrameDetections
from app.services.vision.frame import FramePacket

logger = logging.getLogger("ibvap.vision.detector")

# Default surveillance target classes of interest on border perimeters
DEFAULT_TARGET_CLASSES = {
    "person",
    "car",
    "motorcycle",
    "bus",
    "truck",
}


class YOLODetector:
    """Lightweight YOLO object detector for border surveillance video feeds.
    
    Consumes FramePacket objects from StreamReader and outputs structured
    FrameDetections containing bounding boxes, confidence scores, and target classes.
    """

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.35,
        target_classes: Optional[Set[str]] = None,
        device: Optional[str] = None,
    ):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.target_classes = target_classes or DEFAULT_TARGET_CLASSES
        self.device = device

        self._model = None
        self._is_loaded = False

    def _load_model(self) -> None:
        """Loads the YOLO model into memory on demand."""
        if self._is_loaded:
            return

        from ultralytics import YOLO
        import torch

        # Default to CPU for predictable, zero-compilation latency on laptops
        if self.device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"

        logger.info(f"Loading YOLO detector [{self.model_name}] on device: {self.device}...")
        self._model = YOLO(self.model_name)
        # Warm up the model with a dummy inference to eliminate first-frame latency
        dummy_frame = np.zeros((360, 640, 3), dtype=np.uint8)
        self._model.predict(source=dummy_frame, device=self.device, verbose=False)
        self._is_loaded = True
        logger.info(f"YOLO detector [{self.model_name}] ready and warmed up. Active target classes: {self.target_classes}")

    def detect(
        self,
        target: Union[FramePacket, np.ndarray],
        camera_id: Optional[int] = None,
        frame_index: int = 0,
        timestamp: Optional[float] = None,
    ) -> FrameDetections:
        """Runs object detection on a video frame.
        
        Args:
            target: Either a FramePacket from StreamReader or a raw BGR numpy array.
            camera_id: Optional camera identifier (overridden if FramePacket is provided).
            frame_index: Frame sequence number.
            timestamp: Capture timestamp (defaults to current time if None).
            
        Returns:
            FrameDetections containing detected target objects and inference latency.
        """
        self._load_model()

        # Extract frame data and metadata
        if isinstance(target, FramePacket):
            frame = target.frame
            cam_id = target.camera_id
            f_idx = target.frame_index
            t_stamp = target.timestamp
        else:
            frame = target
            cam_id = camera_id
            f_idx = frame_index
            t_stamp = timestamp or time.time()

        height, width = frame.shape[:2]
        start_time = time.perf_counter()

        # Run model inference without verbose stdout logs
        results = self._model.predict(
            source=frame,
            conf=self.confidence_threshold,
            device=self.device,
            verbose=False,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        detections: List[DetectionResult] = []
        if results and len(results) > 0:
            first_result = results[0]
            boxes = first_result.boxes

            for box in boxes:
                cls_id = int(box.cls[0].item())
                cls_name = self._model.names.get(cls_id, f"class_{cls_id}").lower()

                # Filter: only keep targets relevant for border surveillance
                if self.target_classes and cls_name not in self.target_classes:
                    continue

                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].tolist()

                # Pixel coordinates
                x1, y1, x2, y2 = xyxy
                pixel_bbox = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)

                # Normalized coordinates (0.0 to 1.0)
                norm_bbox = BoundingBox(
                    x1=max(0.0, min(1.0, x1 / width)),
                    y1=max(0.0, min(1.0, y1 / height)),
                    x2=max(0.0, min(1.0, x2 / width)),
                    y2=max(0.0, min(1.0, y2 / height)),
                )

                detections.append(
                    DetectionResult(
                        class_id=cls_id,
                        class_name=cls_name,
                        confidence=conf,
                        bbox=pixel_bbox,
                        normalized_bbox=norm_bbox,
                    )
                )

        return FrameDetections(
            camera_id=cam_id,
            frame_index=f_idx,
            timestamp=t_stamp,
            detections=detections,
            processing_time_ms=elapsed_ms,
        )
