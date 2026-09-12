# IBVAP — Intelligent Border Video Analytics Platform
### AI / Computer Vision Module

This repo implements the **AI/CV subsystem** of IBVAP: turning existing CCTV/IP-camera
streams into an intelligent analytics pipeline, without any proprietary smart-camera hardware.

## What's implemented (mapped to role scope)

| Role requirement | Module |
|---|---|
| Object detection & tracking (YOLO + ByteTrack/DeepSORT) | `src/detection/` |
| Face detection (YuNet / RetinaFace) | `src/face/` |
| OCR pipeline for ANPR | `src/anpr/` |
| Low-light enhancement (Retinex / Zero-DCE) | `src/enhancement/` |
| Edge optimisation (ONNX export, quantization/TensorRT) | `src/export/` |
| Virtual-fence + loitering rules feeding the alert engine | `src/analytics/` |
| End-to-end real-time pipeline | `src/pipeline.py` |

## Project layout

```
ibvap-cv/
├── configs/
│   └── config.yaml            # all tunable parameters (thresholds, model paths, fence line, etc.)
├── models/                    # put downloaded/trained weights here (gitignored)
├── data/sample_videos/        # test clips (gitignored, keep repo light)
├── logs/                      # runtime alert/event logs (gitignored)
├── scripts/
│   ├── download_models.py     # fetches YOLOv8 + YuNet pretrained weights
│   └── run_pipeline.py        # CLI entry point
└── src/
    ├── detection/
    │   ├── yolo_detector.py   # YOLOv8 wrapper (Ultralytics)
    │   └── tracker.py         # ByteTrack / DeepSORT wrapper
    ├── face/
    │   └── face_detector.py   # OpenCV YuNet face detector
    ├── anpr/
    │   ├── plate_detector.py  # license-plate localisation
    │   └── ocr.py             # EasyOCR/Tesseract text recognition + plate cleanup
    ├── enhancement/
    │   ├── retinex.py         # classical MSRCR (no training needed, works immediately)
    │   └── zero_dce.py        # Zero-DCE deep curve estimation network
    ├── export/
    │   ├── export_onnx.py     # PyTorch/Ultralytics -> ONNX
    │   └── quantize.py        # ONNX dynamic/static quantization + TensorRT engine build
    ├── analytics/
    │   └── rules.py           # virtual-fence line-crossing + loitering/suspicious-activity heuristics
    ├── utils/
    │   ├── video_utils.py     # stream reading, FPS throttling, night-mode brightness check
    │   └── logger.py          # tamper-evident (hash-chained) JSONL event/alert log
    └── pipeline.py            # wires everything together frame-by-frame
```

## Setup

```bash
# 1. create environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. install dependencies
pip install -r requirements.txt

# 3. download pretrained weights (YOLOv8n + YuNet face model)
python scripts/download_models.py

# 4. run on a video file or RTSP stream
python scripts/run_pipeline.py --source data/sample_videos/test.mp4
python scripts/run_pipeline.py --source rtsp://<camera-ip>:554/stream1
python scripts/run_pipeline.py --source 0   # webcam, for local testing
```

## Notes for fine-tuning

- Swap `models/yolov8n.pt` for a custom-trained checkpoint (person/vehicle/border-specific
  classes) once you have a labeled dataset — training script hooks are documented inline in
  `src/detection/yolo_detector.py`.
- ANPR plate detector currently defaults to a general YOLO model filtered to `vehicle` classes
  plus a classical contour fallback (`src/anpr/plate_detector.py`); for production accuracy,
  fine-tune a dedicated plate-detection YOLO model and point `configs/config.yaml` at it.
- Everything is config-driven (`configs/config.yaml`) — no need to touch code to change
  thresholds, camera source, fence coordinates, or model paths.

## Edge deployment path

1. Train/fine-tune in PyTorch → `src/export/export_onnx.py` → portable `.onnx`.
2. `src/export/quantize.py` → INT8 dynamic-quantized ONNX (CPU edge boxes) **or**
   TensorRT `.engine` build (NVIDIA Jetson/edge GPU boxes).
3. Point `configs/config.yaml: runtime.backend` at `onnx` or `tensorrt` and the same
   `pipeline.py` runs unchanged — this is what makes the edge-first architecture work
   with poor-connectivity border links (heavy inference stays local; only alerts/metadata
   sync upstream).
