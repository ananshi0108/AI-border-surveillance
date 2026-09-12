"""Unit tests for Phase 3C: 2D Geometry Rule Engine (Virtual Fences & Tripwires)"""

import pytest
from app.models.zone import TriggerType, ZoneType
from app.services.vision.detection import BoundingBox, DetectionResult, FrameDetections
from app.services.vision.rules import (
    BreachType,
    GeometryRuleEngine,
    is_threat_match,
    line_segments_intersect,
    point_in_polygon,
)


def test_point_in_polygon():
    """Verify Point-in-Polygon ray casting with known coordinates."""
    # Define a 100x100 square polygon
    square = [(10.0, 10.0), (90.0, 10.0), (90.0, 90.0), (10.0, 90.0)]

    # Center point -> INSIDE
    assert point_in_polygon((50.0, 50.0), square) is True

    # Far outside -> OUTSIDE
    assert point_in_polygon((5.0, 50.0), square) is False
    assert point_in_polygon((95.0, 50.0), square) is False
    assert point_in_polygon((50.0, 5.0), square) is False
    assert point_in_polygon((50.0, 95.0), square) is False

    # Triangle polygon
    triangle = [(0.0, 0.0), (10.0, 0.0), (5.0, 10.0)]
    assert point_in_polygon((5.0, 2.0), triangle) is True
    assert point_in_polygon((5.0, 15.0), triangle) is False


def test_line_segments_intersect():
    """Verify tripwire line segment intersection with motion vectors."""
    # Horizontal tripwire across the middle of the field: (0, 50) -> (100, 50)
    tripwire_p1 = (0.0, 50.0)
    tripwire_p2 = (100.0, 50.0)

    # 1. Target steps directly across: (50, 40) -> (50, 60) -> INTERSECTS
    assert line_segments_intersect((50.0, 40.0), (50.0, 60.0), tripwire_p1, tripwire_p2) is True

    # 2. Target crosses in reverse: (50, 60) -> (50, 40) -> INTERSECTS
    assert line_segments_intersect((50.0, 60.0), (50.0, 40.0), tripwire_p1, tripwire_p2) is True

    # 3. Target walks parallel to wire: (20, 40) -> (80, 40) -> NO INTERSECTION
    assert line_segments_intersect((20.0, 40.0), (80.0, 40.0), tripwire_p1, tripwire_p2) is False

    # 4. Target stops short of wire: (50, 20) -> (50, 49) -> NO INTERSECTION
    assert line_segments_intersect((50.0, 20.0), (50.0, 49.0), tripwire_p1, tripwire_p2) is False

    # 5. Diagonal crossing: (10, 40) -> (90, 60) -> INTERSECTS
    assert line_segments_intersect((10.0, 40.0), (90.0, 60.0), tripwire_p1, tripwire_p2) is True


def test_threat_type_matching():
    """Verify threat classification filters."""
    assert is_threat_match("person", TriggerType.HUMAN) is True
    assert is_threat_match("car", TriggerType.HUMAN) is False
    assert is_threat_match("truck", TriggerType.HUMAN) is False

    assert is_threat_match("car", TriggerType.VEHICLE) is True
    assert is_threat_match("truck", TriggerType.VEHICLE) is True
    assert is_threat_match("motorcycle", TriggerType.VEHICLE) is True
    assert is_threat_match("bus", TriggerType.VEHICLE) is True
    assert is_threat_match("person", TriggerType.VEHICLE) is False

    assert is_threat_match("person", TriggerType.ALL) is True
    assert is_threat_match("car", TriggerType.ALL) is True


def _make_detection(class_name: str, x: float, y: float) -> DetectionResult:
    """Helper to generate a mock detection with a specific normalized bottom_center."""
    w, h = 0.05, 0.1
    return DetectionResult(
        class_id=0,
        class_name=class_name,
        confidence=0.92,
        bbox=BoundingBox(x1=x*640, y1=(y-h)*360, x2=(x+w)*640, y2=y*360),
        normalized_bbox=BoundingBox(x1=x, y1=y-h, x2=x+w, y2=y),
    )


def test_geometry_rule_engine_polygon_breach():
    """Verify that a target inside a polygon zone generates a POLYGON_INTRUSION breach."""
    engine = GeometryRuleEngine()

    # Define a restricted buffer zone polygon: [0.2, 0.2] -> [0.8, 0.8]
    restricted_zone = {
        "id": 101,
        "name": "Buffer Area Alpha",
        "zone_type": ZoneType.POLYGON,
        "coordinates": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]],
        "trigger_type": TriggerType.HUMAN,
        "is_active": True,
    }

    # Case A: Person OUTSIDE the polygon at (0.1, 0.1)
    frame_outside = FrameDetections(
        camera_id=1,
        frame_index=1,
        timestamp=100.0,
        detections=[_make_detection("person", 0.1, 0.1)],
    )
    breaches = engine.evaluate_zones(frame_outside, [restricted_zone])
    assert len(breaches) == 0

    # Case B: Person INSIDE the polygon at (0.5, 0.5)
    frame_inside = FrameDetections(
        camera_id=1,
        frame_index=2,
        timestamp=100.1,
        detections=[_make_detection("person", 0.5, 0.5)],
    )
    breaches = engine.evaluate_zones(frame_inside, [restricted_zone])
    assert len(breaches) == 1
    assert breaches[0].zone_id == 101
    assert breaches[0].breach_type == BreachType.POLYGON_INTRUSION
    assert breaches[0].detection.class_name == "person"

    # Case C: Vehicle INSIDE the polygon, but zone trigger_type is HUMAN
    frame_vehicle = FrameDetections(
        camera_id=1,
        frame_index=3,
        timestamp=100.2,
        detections=[_make_detection("car", 0.5, 0.5)],
    )
    breaches = engine.evaluate_zones(frame_vehicle, [restricted_zone])
    assert len(breaches) == 0  # Filtered out by trigger_type


def test_geometry_rule_engine_tripwire_crossing():
    """Verify that a target crossing a tripwire line across consecutive frames triggers TRIPWIRE_CROSSING."""
    engine = GeometryRuleEngine()

    # Define a horizontal perimeter tripwire line at y = 0.5: [0.0, 0.5] -> [1.0, 0.5]
    tripwire_zone = {
        "id": 202,
        "name": "Zero-Line Tripwire",
        "zone_type": ZoneType.TRIPWIRE,
        "coordinates": [[0.0, 0.5], [1.0, 0.5]],
        "trigger_type": TriggerType.ALL,
        "is_active": True,
    }

    # Frame 1: Person is north of the tripwire at (0.5, 0.4)
    f1 = FrameDetections(
        camera_id=1,
        frame_index=10,
        timestamp=200.0,
        detections=[_make_detection("person", 0.5, 0.4)],
    )
    breaches_f1 = engine.evaluate_zones(f1, [tripwire_zone])
    assert len(breaches_f1) == 0  # First frame, target hasn't crossed yet

    # Frame 2: Person steps across to south side at (0.5, 0.6)
    f2 = FrameDetections(
        camera_id=1,
        frame_index=11,
        timestamp=200.1,
        detections=[_make_detection("person", 0.5, 0.6)],
    )
    breaches_f2 = engine.evaluate_zones(f2, [tripwire_zone])
    assert len(breaches_f2) == 1
    assert breaches_f2[0].zone_id == 202
    assert breaches_f2[0].breach_type == BreachType.TRIPWIRE_CROSSING
    assert breaches_f2[0].detection.class_name == "person"


def test_inactive_zone_ignored():
    """Verify that zones with is_active=False do not generate breaches."""
    engine = GeometryRuleEngine()

    inactive_zone = {
        "id": 303,
        "name": "Disabled Zone",
        "zone_type": ZoneType.POLYGON,
        "coordinates": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        "trigger_type": TriggerType.ALL,
        "is_active": False,  # Disabled
    }

    frame = FrameDetections(
        camera_id=1,
        frame_index=1,
        timestamp=300.0,
        detections=[_make_detection("person", 0.5, 0.5)],
    )
    breaches = engine.evaluate_zones(frame, [inactive_zone])
    assert len(breaches) == 0
