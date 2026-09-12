"""IBVAP Video Ingestion Demonstration & Verification Script

This script verifies that the Phase 3A StreamReader service functions properly:
1. Generates a synthetic test video clip if no input file/webcam is supplied.
2. Ingests frames using the background StreamReader worker thread.
3. Simulates a downstream AI pipeline consuming frames from the generator.
4. Cleanly releases all OpenCV resources.

Usage:
    # Test with synthetic generated video:
    python scripts/demo_stream.py

    # Test with local webcam:
    python scripts/demo_stream.py --source 0

    # Test with a local video file:
    python scripts/demo_stream.py --source path/to/video.mp4
"""

import argparse
import os
import sys
import time
from pathlib import Path
import cv2
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.vision.stream_reader import StreamReader


def create_synthetic_test_video(output_path: str = "storage/test_feed.mp4", duration_sec: int = 4, fps: int = 25) -> str:
    """Creates a lightweight synthetic CCTV video with moving objects and timestamp overlays."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    width, height = 640, 360
    total_frames = duration_sec * fps

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print(f"[*] Generating {duration_sec}s synthetic surveillance video at: {output_path}...")
    for i in range(total_frames):
        # Dark green/gray background simulating border terrain
        frame = np.full((height, width, 3), (35, 45, 30), dtype=np.uint8)

        # Draw a simulated fence line
        cv2.line(frame, (0, 260), (width, 260), (0, 200, 255), 2)
        cv2.putText(frame, "PERIMETER ZERO LINE", (20, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

        # Draw a moving simulated target (box moving across the screen)
        x = int((i / total_frames) * (width - 60)) + 30
        y = 230 + int(10 * np.sin(i * 0.2))
        cv2.rectangle(frame, (x, y), (x + 30, y + 50), (0, 0, 255), -1)
        cv2.putText(frame, "TARGET", (x - 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        # Overlay metadata
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"CAM-01 [BOP ALPHA] - {timestamp_str}.{i:02d}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(frame, f"Frame: {i+1}/{total_frames}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

        writer.write(frame)

    writer.release()
    print(f"[✓] Synthetic test video generated ({total_frames} frames).")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Test IBVAP Video Stream Ingestion")
    parser.add_argument("--source", type=str, default=None, help="Video file path or webcam index (e.g. 0)")
    parser.add_argument("--max-frames", type=int, default=30, help="Number of frames to consume in test")
    args = parser.parse_args()

    source = args.source
    if source is None:
        source = create_synthetic_test_video()

    print(f"\n--- Starting StreamReader Test on Source: {source} ---")
    reader = StreamReader(source=source, camera_id=1, target_fps=25.0)

    try:
        reader.start()
        frames_received = 0
        start_time = time.time()

        print("[*] Consuming frames via StreamReader.iter_frames() generator...")
        for packet in reader.iter_frames(timeout=2.0):
            frames_received += 1
            # In Phase 3B, this is where YOLO inference will be called:
            # detections = model(packet.frame)
            print(
                f"  [AI Pipeline Ingest] Frame #{packet.frame_index} | "
                f"Resolution: {packet.width}x{packet.height} | "
                f"Timestamp: {packet.timestamp:.2f} | "
                f"Channels: {packet.frame.shape[2]}"
            )

            if frames_received >= args.max_frames:
                print(f"[*] Reached test limit of {args.max_frames} frames.")
                break

        elapsed = time.time() - start_time
        calc_fps = frames_received / elapsed if elapsed > 0 else 0
        print(f"\n[✓] Ingestion Test Complete:")
        print(f"    Total Frames Consumed: {frames_received}")
        print(f"    Elapsed Time: {elapsed:.2f}s")
        print(f"    Effective Consumer Rate: {calc_fps:.1f} FPS")

    finally:
        print("[*] Stopping StreamReader and releasing OpenCV resources...")
        reader.stop()
        print("[✓] Resources cleanly released.")


if __name__ == "__main__":
    main()
