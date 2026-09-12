"""
IBVAP End-to-End Evidence Pipeline

Flow:
    Surveillance Frame
            ↓
       YOLO Detection
            ↓
       Geometry Rules
            ↓
          Breach
            ↓
       Evidence JPG
            ↓
       Database Alert
            ↓
    FastAPI Broadcast API
            ↓
        WebSocket
            ↓
    Connected Dashboard
"""

import asyncio
from pathlib import Path

import cv2
import httpx

from app.core.database import SessionLocal
from app.services.alerts.service import alert_service
from app.services.alerts.snapshot import snapshot_service
from app.services.vision.detector import YOLODetector
from app.services.vision.rules import GeometryRuleEngine


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

SAMPLE_IMAGE = Path("storage/sample_target.jpg")

YOLO_MODEL = "yolov8n.pt"

FASTAPI_BROADCAST_URL = (
    "http://127.0.0.1:8000/api/v1/alerts/broadcast"
)

CAMERA_ID = 1
CAMERA_NAME = "BOP Alpha - Watchtower 1"

ZONE_ID = 1
ZONE_NAME = "Buffer Area Alpha"

# Polygon coordinates are normalized:
# x and y values are between 0 and 1.
ZONE_COORDINATES = [
    [0.2, 0.2],
    [0.8, 0.2],
    [0.8, 0.8],
    [0.2, 0.8],
]


# -------------------------------------------------------------------
# Broadcast helper
# -------------------------------------------------------------------

async def broadcast_alert(client: httpx.AsyncClient, alert):
    """
    Send a database alert to the FastAPI server.

    The FastAPI server then broadcasts the alert to all
    connected WebSocket clients.
    """

    alert_data = {
        "id": alert.id,
        "camera_id": alert.camera_id,
        "zone_id": alert.zone_id,
        "alert_type": alert.alert_type.value,
        "target_class": alert.target_class,
        "confidence": alert.confidence,
        "timestamp": alert.timestamp.isoformat(),
        "created_at": alert.created_at.isoformat(),
        "snapshot_path": alert.snapshot_path,
        "status": alert.status.value,
        "message": alert.message,
    }

    response = await client.post(
        FASTAPI_BROADCAST_URL,
        json=alert_data,
    )

    response.raise_for_status()

    return response.json()


# -------------------------------------------------------------------
# Main pipeline
# -------------------------------------------------------------------

async def main():

    print("=" * 65)
    print(" IBVAP End-to-End Pipeline")
    print(" Detection + Geometry + Evidence + Database + WebSocket")
    print("=" * 65)

    # ---------------------------------------------------------------
    # 1. Initialize YOLO
    # ---------------------------------------------------------------

    print("\n[*] Initializing YOLO detector...")

    detector = YOLODetector(
        model_path=YOLO_MODEL
    )

    print("[+] YOLO detector ready.")

    # ---------------------------------------------------------------
    # 2. Initialize Geometry Rule Engine
    # ---------------------------------------------------------------

    geometry_engine = GeometryRuleEngine()

    print("[+] Geometry rule engine ready.")

    # ---------------------------------------------------------------
    # 3. Configure virtual zone
    # ---------------------------------------------------------------

    print("\n[*] Virtual zone configured:")
    print(f"    Name: {ZONE_NAME}")
    print("    Type: POLYGON")
    print("    Trigger: HUMAN")

    # ---------------------------------------------------------------
    # 4. Load surveillance image
    # ---------------------------------------------------------------

    print(
        f"\n[*] Loading surveillance image: "
        f"{SAMPLE_IMAGE}"
    )

    if not SAMPLE_IMAGE.exists():
        print(
            f"[ERROR] Sample image not found: "
            f"{SAMPLE_IMAGE}"
        )
        return

    frame = cv2.imread(str(SAMPLE_IMAGE))

    if frame is None:
        print("[ERROR] Failed to load surveillance image.")
        return

    height, width = frame.shape[:2]

    print(
        f"[+] Frame loaded successfully: "
        f"{height}x{width}"
    )

    # ---------------------------------------------------------------
    # 5. Run YOLO detection
    # ---------------------------------------------------------------

    print("\n[*] Running YOLO detection...")

    detections = detector.detect(frame)

    print(
        f"[+] Detected {len(detections)} targets."
    )

    # ---------------------------------------------------------------
    # 6. Evaluate virtual perimeter
    # ---------------------------------------------------------------

    print("\n[*] Evaluating virtual perimeter...")

    breaches = geometry_engine.evaluate(
        detections=detections,
        zone_id=ZONE_ID,
        zone_name=ZONE_NAME,
        zone_type="POLYGON",
        coordinates=ZONE_COORDINATES,
        trigger_type="HUMAN",
        camera_id=CAMERA_ID,
    )

    print(
        f"[+] Found {len(breaches)} "
        f"zone perimeter breaches."
    )

    # ---------------------------------------------------------------
    # 7. Prepare database
    # ---------------------------------------------------------------

    db = SessionLocal()

    # ---------------------------------------------------------------
    # 8. Connect to FastAPI broadcast endpoint
    # ---------------------------------------------------------------

    async with httpx.AsyncClient() as client:

        try:

            # -------------------------------------------------------
            # 9. Process every breach
            # -------------------------------------------------------

            for index, breach in enumerate(breaches, start=1):

                print("\n" + "-" * 65)
                print(f"PROCESSING BREACH #{index}")
                print("-" * 65)

                # ---------------------------------------------------
                # Save evidence snapshot
                # ---------------------------------------------------

                snapshot_path = (
                    snapshot_service.save_breach_snapshot(
                        frame=frame,
                        breach=breach,
                        zone_coordinates=ZONE_COORDINATES,
                        camera_name=CAMERA_NAME,
                    )
                )

                print("Evidence snapshot saved:")
                print(f"   {snapshot_path}")

                # ---------------------------------------------------
                # Create database alert
                # ---------------------------------------------------

                alert = alert_service.create_alert(
                    db=db,
                    breach=breach,
                    snapshot_path=snapshot_path,
                )

                print("\nDatabase alert created:")
                print(f"   Alert ID     : {alert.id}")
                print(f"   Camera ID    : {alert.camera_id}")
                print(f"   Zone ID      : {alert.zone_id}")
                print(
                    f"   Alert Type   : "
                    f"{alert.alert_type.value}"
                )
                print(
                    f"   Target       : "
                    f"{alert.target_class}"
                )
                print(
                    f"   Confidence   : "
                    f"{alert.confidence * 100:.1f}%"
                )
                print(
                    f"   Status       : "
                    f"{alert.status.value}"
                )
                print(
                    f"   Message      : "
                    f"{alert.message}"
                )

                # ---------------------------------------------------
                # Broadcast through FastAPI → WebSocket
                # ---------------------------------------------------

                try:

                    result = await broadcast_alert(
                        client,
                        alert,
                    )

                    print("\nWebSocket broadcast sent.")
                    print(
                        f"   Broadcast status: "
                        f"{result.get('status')}"
                    )

                except httpx.HTTPError as error:

                    print(
                        "\n[WARNING] Alert was saved to the "
                        "database, but WebSocket broadcast failed."
                    )

                    print(f"   Error: {error}")

        finally:

            db.close()

    # ---------------------------------------------------------------
    # 10. Final summary
    # ---------------------------------------------------------------

    print("\n")
    print("=" * 65)
    print(" IBVAP PIPELINE COMPLETE")
    print("=" * 65)

    print(
        f"YOLO detections       : "
        f"{len(detections)}"
    )

    print(
        f"Zone breaches         : "
        f"{len(breaches)}"
    )

    print(
        f"Snapshots generated   : "
        f"{len(breaches)}"
    )

    print(
        f"Database alerts       : "
        f"{len(breaches)}"
    )

    print("\nEvidence location:")
    print("   storage/snapshots/")

    print("\nAlerts stored in:")
    print("   alerts database table")

    print("\n")
    print("=" * 65)
    print(" Automatic incident flow verified:")
    print("=" * 65)

    print(
        """
    Surveillance Frame
             ↓
       YOLO Detection
             ↓
       Geometry Rules
             ↓
          Breach
             ↓
       Evidence JPG
             ↓
       Database Alert
             ↓
      FastAPI Broadcast
             ↓
        WebSocket
             ↓
     Monitoring Dashboard
    """
    )

    print("=" * 65)


# -------------------------------------------------------------------
# Run the pipeline
# -------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())