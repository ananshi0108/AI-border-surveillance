from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class BoundingBox:
    """2D Bounding Box coordinates."""
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def bottom_center(self) -> Tuple[float, float]:
        """Ground contact point (feet of a person or base of a vehicle).
        Critical for accurate virtual fence and tripwire crossing calculations in Phase 3C."""
        return ((self.x1 + self.x2) / 2.0, self.y2)

    def to_dict(self) -> Dict[str, float]:
        return {
            "x1": round(self.x1, 2),
            "y1": round(self.y1, 2),
            "x2": round(self.x2, 2),
            "y2": round(self.y2, 2),
        }


@dataclass
class DetectionResult:
    """A single detected target object within a video frame."""
    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox                     # Absolute pixel coordinates
    normalized_bbox: BoundingBox          # Normalized coordinates (0.0 to 1.0)

    def to_dict(self) -> dict:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 4),
            "bbox": self.bbox.to_dict(),
            "normalized_bbox": self.normalized_bbox.to_dict(),
            "bottom_center": {
                "x": round(self.bottom_center[0], 2),
                "y": round(self.bottom_center[1], 2),
            },
        }

    @property
    def bottom_center(self) -> Tuple[float, float]:
        return self.bbox.bottom_center

    @property
    def normalized_bottom_center(self) -> Tuple[float, float]:
        return self.normalized_bbox.bottom_center


@dataclass
class FrameDetections:
    """Aggregated detection results for a single processed video frame."""
    camera_id: Optional[int]
    frame_index: int
    timestamp: float
    detections: List[DetectionResult] = field(default_factory=list)
    processing_time_ms: float = 0.0

    @property
    def count(self) -> int:
        return len(self.detections)

    @property
    def has_targets(self) -> bool:
        return len(self.detections) > 0

    def get_by_class(self, class_name: str) -> List[DetectionResult]:
        """Filters detections by object class (e.g. 'person', 'car')."""
        return [d for d in self.detections if d.class_name.lower() == class_name.lower()]

    def to_dict(self) -> dict:
        return {
            "camera_id": self.camera_id,
            "frame_index": self.frame_index,
            "timestamp": self.timestamp,
            "count": self.count,
            "processing_time_ms": round(self.processing_time_ms, 2),
            "detections": [d.to_dict() for d in self.detections],
        }
