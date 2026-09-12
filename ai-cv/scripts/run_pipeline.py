#!/usr/bin/env python3
"""
Thin CLI wrapper so you can run from the repo root as:
    python scripts/run_pipeline.py --source data/sample_videos/test.mp4
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import run

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the IBVAP AI/CV pipeline")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--source", required=True, help="Video file path, webcam index (e.g. 0), or RTSP URL")
    parser.add_argument("--no-display", action="store_true", help="Don't open a display window (headless/edge box)")
    parser.add_argument("--save", type=str, default=None, help="Path to save annotated output video")
    args = parser.parse_args()

    run(args.config, args.source, display=not args.no_display, save_output=args.save)
