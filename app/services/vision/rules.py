from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple, Union

from app.models.zone import TriggerType, ZoneType
from app.services.vision.detection import DetectionResult, FrameDetections

Point = Tuple[float, float]


def is_threat_match(class_name: str, trigger_type: Union[TriggerType, str]) -> bool:
    """Checks whether a detected object matches a zone's configured threat filter."""
    c_name = class_name.lower().strip()
    t_type = trigger_type.value if hasattr(trigger_type, "value") else str(trigger_type)
    t_type = t_type.upper().strip()

    if t_type == "ALL":
        return True
    if t_type == "HUMAN":
        return c_name == "person"
    if t_type == "VEHICLE":
        return c_name in {"car", "motorcycle", "bus", "truck"}
    return False


def point_in_polygon(point: Point, polygon: List[Point]) -> bool:
    """Ray Casting Algorithm: Determines if a 2D point is inside an arbitrary polygon.
    
    Cast a horizontal ray from the test point to +infinity and count boundary intersections.
    An odd number of crossings means the point is INSIDE; even means OUTSIDE.
    """
    if len(polygon) < 3:
        return False

    x, y = point
    inside = False
    n = len(polygon)
    p1x, p1y = polygon[0]

    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]

        # Check if the ray crosses this segment
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        x_inters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    else:
                        x_inters = p1x

                    if p1x == p2x or x <= x_inters:
                        inside = not inside

        p1x, p1y = p2x, p2y

    return inside


def _orientation(p: Point, q: Point, r: Point) -> int:
    """Finds orientation of ordered triplet (p, q, r).
    0 -> Collinear, 1 -> Clockwise, 2 -> Counterclockwise
    """
    val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
    if abs(val) < 1e-9:
        return 0
    return 1 if val > 0 else 2


def _on_segment(p: Point, q: Point, r: Point) -> bool:
    """Given collinear points p, q, r, checks if point q lies on segment pr."""
    return (
        min(p[0], r[0]) - 1e-9 <= q[0] <= max(p[0], r[0]) + 1e-9
        and min(p[1], r[1]) - 1e-9 <= q[1] <= max(p[1], r[1]) + 1e-9
    )


def line_segments_intersect(p1: Point, p2: Point, q1: Point, q2: Point) -> bool:
    """Determines whether line segment (p1 -> p2) intersects line segment (q1 -> q2).
    
    Used to detect when an intruder steps across a virtual perimeter tripwire line.
    """
    o1 = _orientation(p1, p2, q1)
    o2 = _orientation(p1, p2, q2)
    o3 = _orientation(q1, q2, p1)
    o4 = _orientation(q1, q2, p2)

    # General Case: segments straddle each other's lines
    if o1 != o2 and o3 != o4:
        return True

    # Special Collinear Cases: point lies on the line segment
    if o1 == 0 and _on_segment(p1, q1, p2):
        return True
    if o2 == 0 and _on_segment(p1, q2, p2):
        return True
    if o3 == 0 and _on_segment(q1, p1, q2):
        return True
    if o4 == 0 and _on_segment(q1, p2, q2):
        return True

    return False


class BreachType(str, Enum):
    """Classification of the perimeter rule violation."""
    POLYGON_INTRUSION = "POLYGON_INTRUSION"
    TRIPWIRE_CROSSING = "TRIPWIRE_CROSSING"


@dataclass
class ZoneBreach:
    """Structured record of a verified virtual fence or tripwire intrusion."""
    zone_id: int
    zone_name: str
    breach_type: BreachType
    detection: DetectionResult
    camera_id: Optional[int]
    timestamp: float
    contact_point: Point  # The (x, y) feet/ground point that tripped the boundary

    def to_dict(self) -> dict:
        return {
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "breach_type": self.breach_type.value,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp,
            "contact_point": {"x": round(self.contact_point[0], 3), "y": round(self.contact_point[1], 3)},
            "detection": self.detection.to_dict(),
        }


class GeometryRuleEngine:
    """Stateful 2D geometry evaluation engine for virtual fences and tripwires.
    
    Maintains a short memory of target positions between consecutive frames to detect
    directional line crossing (tripwires) and point-in-polygon containment (restricted zones).
    """

    def __init__(self, max_match_distance: float = 0.25):
        # Maximum normalized distance to consider a target the 'same object' between frames
        self.max_match_distance = max_match_distance
        # Stores previous frame positions: {class_name: List[Point]}
        self._prev_targets: Dict[str, List[Point]] = {}

    def reset_state(self) -> None:
        """Clears previous frame position history (e.g. on stream restart)."""
        self._prev_targets.clear()

    def evaluate_zones(
        self,
        frame_detections: FrameDetections,
        zones: List[Any],
    ) -> List[ZoneBreach]:
        """Evaluates detected objects against a list of active configured zones.
        
        Args:
            frame_detections: Detections from Phase 3B YOLODetector.
            zones: List of Zone objects or dictionaries from Phase 2.
            
        Returns:
            List of ZoneBreach incidents detected in this frame.
        """
        breaches: List[ZoneBreach] = []
        current_targets_by_class: Dict[str, List[Point]] = {}

        # 1. Filter only active zones
        active_zones = [
            z for z in zones
            if (getattr(z, "is_active", None) if not isinstance(z, dict) else z.get("is_active", True))
        ]

        if not active_zones or not frame_detections.detections:
            # Update history even if no active zones to maintain motion vectors
            self._update_history(frame_detections)
            return breaches

        # 2. Process each detection
        for det in frame_detections.detections:
            c_name = det.class_name.lower()
            # Decide coordinate mode based on zone coordinates format (normalized vs pixels)
            # Default to normalized coordinates (0.0 to 1.0)
            norm_point: Point = det.normalized_bottom_center
            pixel_point: Point = det.bottom_center

            # Track current position
            if c_name not in current_targets_by_class:
                current_targets_by_class[c_name] = []
            current_targets_by_class[c_name].append(norm_point)

            # Find closest previous position of the same object class for motion vector
            prev_point = self._find_closest_prev_point(c_name, norm_point)

            # 3. Check against every active zone
            for zone in active_zones:
                z_id = getattr(zone, "id", None) if not isinstance(zone, dict) else zone.get("id", 0)
                z_name = getattr(zone, "name", "Zone") if not isinstance(zone, dict) else zone.get("name", "Zone")
                z_type = getattr(zone, "zone_type", None) if not isinstance(zone, dict) else zone.get("zone_type")
                t_type = getattr(zone, "trigger_type", TriggerType.ALL) if not isinstance(zone, dict) else zone.get("trigger_type", "ALL")
                raw_coords = getattr(zone, "coordinates", []) if not isinstance(zone, dict) else zone.get("coordinates", [])

                # Threat type match check (HUMAN, VEHICLE, ALL)
                if not is_threat_match(c_name, t_type):
                    continue

                if not raw_coords or len(raw_coords) < 2:
                    continue

                # Determine if zone coordinates are normalized (<= 1.0) or pixel coordinates (> 1.0)
                is_normalized = all(max(pt[0], pt[1]) <= 1.05 for pt in raw_coords)
                test_point = norm_point if is_normalized else pixel_point

                formatted_coords = [(float(pt[0]), float(pt[1])) for pt in raw_coords]
                z_type_str = z_type.value if hasattr(z_type, "value") else str(z_type)

                # Case A: POLYGON AREA INTRUSION
                if z_type_str == "POLYGON" and len(formatted_coords) >= 3:
                    if point_in_polygon(test_point, formatted_coords):
                        breaches.append(
                            ZoneBreach(
                                zone_id=z_id,
                                zone_name=z_name,
                                breach_type=BreachType.POLYGON_INTRUSION,
                                detection=det,
                                camera_id=frame_detections.camera_id,
                                timestamp=frame_detections.timestamp,
                                contact_point=test_point,
                            )
                        )

                # Case B: TRIPWIRE LINE CROSSING
                elif z_type_str == "TRIPWIRE" and len(formatted_coords) >= 2:
                    wire_p1 = formatted_coords[0]
                    wire_p2 = formatted_coords[1]

                    # Requires previous position to form a motion line segment
                    if prev_point is not None:
                        motion_start = prev_point if is_normalized else self._norm_to_pixel(prev_point, det)
                        motion_end = test_point

                        if line_segments_intersect(motion_start, motion_end, wire_p1, wire_p2):
                            breaches.append(
                                ZoneBreach(
                                    zone_id=z_id,
                                    zone_name=z_name,
                                    breach_type=BreachType.TRIPWIRE_CROSSING,
                                    detection=det,
                                    camera_id=frame_detections.camera_id,
                                    timestamp=frame_detections.timestamp,
                                    contact_point=test_point,
                                )
                            )

        # 4. Save current frame target points for the next frame
        self._prev_targets = current_targets_by_class
        return breaches

    def _update_history(self, frame_detections: FrameDetections) -> None:
        """Stores normalized bottom center points of detections."""
        new_targets: Dict[str, List[Point]] = {}
        for det in frame_detections.detections:
            c = det.class_name.lower()
            if c not in new_targets:
                new_targets[c] = []
            new_targets[c].append(det.normalized_bottom_center)
        self._prev_targets = new_targets

    def _find_closest_prev_point(self, class_name: str, current_point: Point) -> Optional[Point]:
        """Finds the nearest position of the same object class in the previous frame."""
        candidates = self._prev_targets.get(class_name, [])
        if not candidates:
            return None

        best_point = None
        min_dist = float("inf")

        for prev in candidates:
            dist = math.hypot(current_point[0] - prev[0], current_point[1] - prev[1])
            if dist < min_dist and dist <= self.max_match_distance:
                min_dist = dist
                best_point = prev

        return best_point

    def _norm_to_pixel(self, norm_pt: Point, det: DetectionResult) -> Point:
        """Approximates pixel coordinates from normalized ratio using bbox ratio."""
        if det.normalized_bbox.width > 0:
            scale_x = det.bbox.width / det.normalized_bbox.width
        else:
            scale_x = 1.0
        if det.normalized_bbox.height > 0:
            scale_y = det.bbox.height / det.normalized_bbox.height
        else:
            scale_y = 1.0
        return (norm_pt[0] * scale_x, norm_pt[1] * scale_y)
