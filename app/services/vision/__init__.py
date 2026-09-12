"""Computer vision, video stream ingestion, & geometry analytics package."""
from app.services.vision.frame import FramePacket
from app.services.vision.stream_reader import StreamReader
from app.services.vision.manager import StreamManager, stream_manager
from app.services.vision.detection import BoundingBox, DetectionResult, FrameDetections
from app.services.vision.detector import YOLODetector
from app.services.vision.rules import (
    Point,
    BreachType,
    ZoneBreach,
    GeometryRuleEngine,
    point_in_polygon,
    line_segments_intersect,
    is_threat_match,
)

__all__ = [
    "FramePacket",
    "StreamReader",
    "StreamManager",
    "stream_manager",
    "BoundingBox",
    "DetectionResult",
    "FrameDetections",
    "YOLODetector",
    "Point",
    "BreachType",
    "ZoneBreach",
    "GeometryRuleEngine",
    "point_in_polygon",
    "line_segments_intersect",
    "is_threat_match",
]
