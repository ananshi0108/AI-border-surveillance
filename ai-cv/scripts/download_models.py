#!/usr/bin/env python3
"""
Downloads the pretrained weights needed to run the pipeline out of the box:
  - yolov8n.pt                          (Ultralytics, auto-downloads on first use too)
  - face_detection_yunet_2023mar.onnx   (OpenCV Zoo)

Zero-DCE and any fine-tuned plate/detection models are NOT auto-downloaded
here since they're project-specific — see README.md for where to plug those in.
"""
import os
import sys
from pathlib import Path

import requests

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

FILES = {
    "yolov8n.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt",
    "face_detection_yunet_2023mar.onnx": (
        "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/"
        "face_detection_yunet/face_detection_yunet_2023mar.onnx"
    ),
}


def download(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"[skip] {dest.name} already present")
        return
    print(f"[download] {dest.name} <- {url}")
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"[done] saved to {dest}")


def main():
    for filename, url in FILES.items():
        try:
            download(url, MODELS_DIR / filename)
        except Exception as exc:
            print(f"[error] failed to download {filename}: {exc}", file=sys.stderr)
    print("\nModel setup complete. See models/README.md for optional fine-tuned models.")


if __name__ == "__main__":
    main()
