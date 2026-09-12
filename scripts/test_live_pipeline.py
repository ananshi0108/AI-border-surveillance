import logging
import time

from app.services.vision.live_pipeline import LivePipeline


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


VIDEO_PATH = "storage/border_cctv_demo.mp4"
CAMERA_ID = 1


def main():
    print("Starting IBVAP live pipeline test...")
    print(f"Video: {VIDEO_PATH}")
    print(f"Camera ID: {CAMERA_ID}")

    pipeline = LivePipeline(
        camera_id=CAMERA_ID,
        stream_url=VIDEO_PATH,
        camera_name="BOP Alpha - Watchtower 1",
        target_fps=5.0,
    )

    pipeline.start()

    print("Pipeline started.")
    print("Running for 15 seconds...")
    print()

    try:
        time.sleep(15)
    finally:
        pipeline.stop()

    print()
    print("Pipeline stopped.")
    print("Check storage/snapshots/ for evidence images.")
    print("Check the Alerts API/database for generated alerts.")


if __name__ == "__main__":
    main()