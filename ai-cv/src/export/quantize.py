"""
Model optimisation for edge deployment: ONNX quantization and TensorRT engine
building.

Two independent optimisation paths — pick based on target hardware:
  - CPU-only edge box (no NVIDIA GPU): ONNX dynamic/static INT8 quantization
    via onnxruntime. Smaller model, 2-4x faster CPU inference, small accuracy
    drop.
  - NVIDIA Jetson / edge GPU box: TensorRT engine build (FP16 or INT8) —
    the biggest latency win, but needs the target device's own TensorRT SDK
    (engines are hardware/version-locked, so you *must* build on the actual
    edge box or a matching dev kit, not a generic cloud VM).
"""
from __future__ import annotations

import argparse
import os


# ---------------------------------------------------------------------------
# ONNX Runtime quantization (CPU edge boxes)
# ---------------------------------------------------------------------------
def dynamic_quantize_onnx(onnx_path: str, out_path: str) -> str:
    """Dynamic quantization: weights -> INT8, activations quantized on the fly
    at inference time. No calibration dataset needed — the fastest way to
    shrink a model for a CPU-only edge box, with a modest accuracy trade-off."""
    from onnxruntime.quantization import quantize_dynamic, QuantType

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    quantize_dynamic(
        model_input=onnx_path,
        model_output=out_path,
        weight_type=QuantType.QInt8,
    )
    print(f"Dynamic INT8 quantization complete: {out_path}")
    return out_path


def static_quantize_onnx(onnx_path: str, out_path: str, calibration_image_dir: str,
                           input_name: str = "images", input_hw: tuple = (640, 640)) -> str:
    """Static (calibrated) quantization: both weights and activations -> INT8,
    calibrated against a representative sample of real border-camera frames.
    Better accuracy than dynamic quantization but needs `calibration_image_dir`
    populated with ~100-300 representative frames from the deployment site."""
    import cv2
    import numpy as np
    from onnxruntime.quantization import quantize_static, QuantType, CalibrationDataReader

    class FolderCalibrationReader(CalibrationDataReader):
        def __init__(self, image_dir: str):
            self.image_paths = [
                os.path.join(image_dir, f) for f in os.listdir(image_dir)
                if f.lower().endswith((".jpg", ".jpeg", ".png"))
            ]
            self.index = 0

        def get_next(self):
            if self.index >= len(self.image_paths):
                return None
            img = cv2.imread(self.image_paths[self.index])
            img = cv2.resize(img, input_hw)
            img = img[:, :, ::-1].astype(np.float32) / 255.0  # BGR->RGB, normalise
            img = np.transpose(img, (2, 0, 1))[None, ...]     # NCHW
            self.index += 1
            return {input_name: img}

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    reader = FolderCalibrationReader(calibration_image_dir)
    quantize_static(
        model_input=onnx_path,
        model_output=out_path,
        calibration_data_reader=reader,
        weight_type=QuantType.QInt8,
    )
    print(f"Static INT8 quantization complete: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# TensorRT engine build (NVIDIA Jetson / edge GPU boxes)
# ---------------------------------------------------------------------------
def build_tensorrt_engine_via_ultralytics(pt_model_path: str, imgsz: int = 640,
                                             half: bool = True, int8: bool = False,
                                             workspace_gb: int = 4) -> str:
    """Simplest path when starting from a YOLO .pt checkpoint: Ultralytics'
    exporter drives the ONNX->TensorRT conversion for you, on-device.
    Must be run ON the target Jetson/edge box (or an identical dev kit) since
    TensorRT engines are locked to the exact GPU + TensorRT + CUDA version.
    """
    from ultralytics import YOLO

    model = YOLO(pt_model_path)
    engine_path = model.export(
        format="engine", imgsz=imgsz, half=half, int8=int8, workspace=workspace_gb,
    )
    print(f"TensorRT engine built: {engine_path}")
    return str(engine_path)


def build_tensorrt_engine_via_trtexec(onnx_path: str, engine_path: str,
                                         fp16: bool = True, workspace_mb: int = 4096) -> str:
    """Generic path for any ONNX model (e.g. exported Zero-DCE) using NVIDIA's
    own `trtexec` CLI, which ships with the TensorRT SDK installed on the edge
    device. This function just documents/builds the shell command — run it on
    the edge box itself.
    """
    precision_flag = "--fp16" if fp16 else ""
    command = (
        f"trtexec --onnx={onnx_path} --saveEngine={engine_path} "
        f"{precision_flag} --workspace={workspace_mb}"
    )
    print("Run this on the target edge device (TensorRT SDK required):")
    print(f"  {command}")
    return command


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantize/optimise models for edge deployment")
    sub = parser.add_subparsers(dest="mode", required=True)

    p_dyn = sub.add_parser("dynamic-quantize", help="ONNX dynamic INT8 quantization (CPU edge)")
    p_dyn.add_argument("--onnx", required=True)
    p_dyn.add_argument("--out", required=True)

    p_static = sub.add_parser("static-quantize", help="ONNX static INT8 quantization with calibration data")
    p_static.add_argument("--onnx", required=True)
    p_static.add_argument("--out", required=True)
    p_static.add_argument("--calib-dir", required=True)

    p_trt = sub.add_parser("tensorrt", help="Build a TensorRT engine from a YOLO .pt checkpoint")
    p_trt.add_argument("--pt", required=True)
    p_trt.add_argument("--imgsz", type=int, default=640)
    p_trt.add_argument("--int8", action="store_true")

    args = parser.parse_args()

    if args.mode == "dynamic-quantize":
        dynamic_quantize_onnx(args.onnx, args.out)
    elif args.mode == "static-quantize":
        static_quantize_onnx(args.onnx, args.out, args.calib_dir)
    elif args.mode == "tensorrt":
        build_tensorrt_engine_via_ultralytics(args.pt, imgsz=args.imgsz, int8=args.int8)
