"""IBVAP YOLO Detector Test & Verification Script

Verifies Phase 3B:
1. Loads the lightweight YOLOv8n detector model.
2. Ingests video frames from storage/test_feed.mp4 using StreamReader (or tests an image).
3. Runs object detection on each frame and prints:
   - Frame number & timestamp
   - Inference latency (processing time in ms)
   - Detected objects (person, car, bus, truck), bounding boxes, ground-contact points, and confidence scores.
4. Cleanly releases all resources upon completion.

Usage:
    # Test on synthetic video:
    python scripts/test_detector.py

    # Test on sample real-world surveillance image:
    python scripts/test_detector.py --source storage/sample_target.jpg

    # Test on webcam:
    python scripts/test_detector.py --source 0
"""

import argparse
from pathlib import Path
import sys
import time
import cv2

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.vision.stream_reader import StreamReader
from app.services.vision.detector import YOLODetector


def test_single_image(detector: YOLODetector, image_path: str):
    """Runs detection on a single still image."""
    print(f"\n[*] Processing static test image: {image_path}...")
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"[!] Error: Could not read image at {image_path}")
        return

    result = detector.detect(frame, camera_id=1, frame_index=1)
    print(f"\n[✓] Detection Complete in {result.processing_time_ms:.1f} ms:")
    print(f"    Total Targets Detected: {result.count}")

    for idx, det in enumerate(result.detections, start=1):
        bbox = det.bbox
        print(
            f"    [{idx}] Target: '{det.class_name.upper()}' | "
            f"Confidence: {det.confidence:.2%} | "
            f"BBox: ({bbox.x1:.0f}, {bbox.y1:.0f}) -> ({bbox.x2:.0f}, {bbox.y2:.0f}) | "
            f"Ground Contact (Feet): ({det.bottom_center[0]:.1f}, {det.bottom_center[1]:.1f})"
        )


def main():
    parser = argparse.ArgumentParser(description="Test IBVAP YOLO Object Detector")
    parser.add_argument("--source", type=str, default="storage/test_feed.mp4", help="Video source (path, webcam index, or RTSP)")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold (default: 0.25)")
    parser.add_argument("--max-frames", type=int, default=15, help="Max frames to process")
    args = parser.parse_args()

    print("=================================================================")
    print("      IBVAP Phase 3B: Lightweight YOLO Detector Verification     ")
    print("=================================================================")
    print(f"[*] Target Source: {args.source}")
    print(f"[*] Confidence Threshold: {args.conf}")

    # Initialize the YOLO detector
    print("\n[*] Initializing YOLOv8n detector...")
    detector = YOLODetector(confidence_threshold=args.conf)
    detector._load_model()
    print(f"[✓] Detector ready on device: [{detector.device}].")

    # If source is an image, run single image test
    if args.source.lower().endswith((".jpg", ".jpeg", ".png")):
        test_single_image(detector, args.source)
        return

    # Otherwise run streaming video test with StreamReader
    print(f"[*] Starting StreamReader for: {args.source}...")
    reader = StreamReader(source=args.source, camera_id=1, target_fps=25.0, loop_file=True)
    reader.start()

    total_frames = 0
    total_detections = 0
    total_inference_ms = 0.0

    try:
        print("\n[*] Running Detection Pipeline (StreamReader -> YOLODetector)...\n")
        for packet in reader.iter_frames(timeout=2.0):
            total_frames += 1

            result = detector.detect(packet)
            total_inference_ms += result.processing_time_ms
            total_detections += result.count

            status_tag = f"🎯 {result.count} targets" if result.has_targets else "⚪ No targets"
            print(
                f"  Frame #{result.frame_index:03d} | "
                f"Latency: {result.processing_time_ms:5.1f} ms | "
                f"{status_tag}"
            )

            for idx, det in enumerate(result.detections, start=1):
                bbox = det.bbox
                print(
                    f"    └─ [{idx}] Class: '{det.class_name.upper()}' | "
                    f"Confidence: {det.confidence:.2%} | "
                    f"Box: ({bbox.x1:.0f}, {bbox.y1:.0f}) -> ({bbox.x2:.0f}, {bbox.y2:.0f}) | "
                    f"Ground Contact: ({det.bottom_center[0]:.1f}, {det.bottom_center[1]:.1f})"
                )

            if total_frames >= args.max_frames:
                break

    finally:
        reader.stop()
        print("\n[*] StreamReader stopped and resources released.")

    avg_latency = total_inference_ms / total_frames if total_frames > 0 else 0.0
    effective_fps = 1000.0 / avg_latency if avg_latency > 0 else 0.0

    print("\n=================================================================")
    print("                 Inference Performance Summary                  ")
    print("=================================================================")
    print(f"  Total Frames Processed : {total_frames}")
    print(f"  Total Targets Detected : {total_detections}")
    print(f"  Average Inference Time : {avg_latency:.1f} ms / frame")
    print(f"  Estimated Maximum FPS  : ~{effective_fps:.1f} FPS")
    print("=================================================================\n")


if __name__ == "__main__":
    main()
