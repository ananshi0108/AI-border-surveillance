"""IBVAP End-to-End Pipeline Demonstration Script

Verifies the integration of:
Phase 3A (StreamReader) -> Phase 3B (YOLODetector) -> Phase 3C (GeometryRuleEngine)

Simulates a camera feed with two configured border zones:
1. "Zero-Line Tripwire" (TRIPWIRE at y=0.5, triggers on ALL)
2. "Restricted Bunker Area" (POLYGON at [0.2, 0.2] -> [0.8, 0.8], triggers on HUMAN)
"""

import sys
from pathlib import Path
import cv2

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.zone import TriggerType, ZoneType
from app.services.vision.detector import YOLODetector
from app.services.vision.rules import GeometryRuleEngine


def main():
    print("=================================================================")
    print("      IBVAP End-to-End Pipeline (Inference + Geometry Rules)     ")
    print("=================================================================")

    # 1. Initialize detector and geometry engine
    detector = YOLODetector(confidence_threshold=0.25)
    detector._load_model()
    engine = GeometryRuleEngine()

    # 2. Configure mock virtual fences
    zones = [
        {
            "id": 1,
            "name": "Zero-Line Tripwire",
            "zone_type": ZoneType.TRIPWIRE,
            "coordinates": [[0.0, 0.6], [1.0, 0.6]],
            "trigger_type": TriggerType.ALL,
            "is_active": True,
        },
        {
            "id": 2,
            "name": "Restricted Pedestrian Zone",
            "zone_type": ZoneType.POLYGON,
            "coordinates": [[0.0, 0.3], [0.9, 0.3], [0.9, 0.95], [0.0, 0.95]],
            "trigger_type": TriggerType.HUMAN,
            "is_active": True,
        },
    ]

    print(f"[*] Loaded {len(zones)} active virtual zones:")
    for z in zones:
        print(f"    - [{z['id']}] {z['name']} ({z['zone_type'].value}) | Trigger: {z['trigger_type'].value}")

    # 3. Load sample surveillance image
    sample_path = "storage/sample_target.jpg"
    frame = cv2.imread(sample_path)
    if frame is None:
        print(f"[!] Sample image not found at {sample_path}")
        return

    # 4. Run detection
    detections = detector.detect(frame, camera_id=1, frame_index=1)
    print(f"\n[*] YOLO Detections: {detections.count} targets found in {detections.processing_time_ms:.1f}ms")

    # 5. Evaluate virtual fences
    breaches = engine.evaluate_zones(detections, zones)

    print(f"\n=================================================================")
    print(f"                    Virtual Fence Evaluation                     ")
    print(f"=================================================================")
    print(f"[*] Total Breaches Detected: {len(breaches)}\n")

    for idx, b in enumerate(breaches, start=1):
        det = b.detection
        print(
            f"  🚨 BREACH #{idx}: Zone '{b.zone_name}' (ID: {b.zone_id})\n"
            f"     Type        : {b.breach_type.value}\n"
            f"     Target      : {det.class_name.upper()} (Confidence: {det.confidence:.2%})\n"
            f"     Ground Point: x={b.contact_point[0]:.3f}, y={b.contact_point[1]:.3f}\n"
        )

    print("=================================================================\n")


if __name__ == "__main__":
    main()
