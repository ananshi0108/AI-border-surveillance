"""
Export models to ONNX for edge deployment.

Two paths, since the two model families in this repo come from different worlds:
  - YOLO models: Ultralytics has a built-in, battle-tested exporter — use it.
  - Custom PyTorch models (e.g. Zero-DCE): plain torch.onnx.export.

Usage:
    python -m src.export.export_onnx --yolo models/yolov8n.pt
    python -m src.export.export_onnx --zero-dce models/zero_dce.pth --out models/zero_dce.onnx
"""
from __future__ import annotations

import argparse
import os

import torch


def export_yolo_to_onnx(model_path: str, imgsz: int = 640, half: bool = False,
                          dynamic: bool = False, simplify: bool = True) -> str:
    """Exports a YOLO .pt checkpoint to ONNX using Ultralytics' own exporter,
    which already handles opset selection, NMS-friendly output shapes, etc."""
    from ultralytics import YOLO

    model = YOLO(model_path)
    exported_path = model.export(
        format="onnx", imgsz=imgsz, half=half, dynamic=dynamic, simplify=simplify,
    )
    print(f"YOLO ONNX export complete: {exported_path}")
    return str(exported_path)


def export_zero_dce_to_onnx(weights_path: str, out_path: str,
                              input_hw: tuple = (480, 640), opset: int = 12) -> str:
    """Exports the Zero-DCE DCENet to ONNX. Uses the `.enhance()` path so the
    exported graph outputs the final enhanced image directly (curve application
    included), not just raw curve parameters."""
    from src.enhancement.zero_dce import DCENet

    class WrappedForExport(torch.nn.Module):
        """torch.onnx.export needs a plain forward() -> tensor; DCENet.enhance()
        already returns exactly that, so this thin wrapper just exposes it."""
        def __init__(self, net: DCENet):
            super().__init__()
            self.net = net

        def forward(self, x):
            return self.net.enhance(x)

    model = DCENet()
    state_dict = torch.load(weights_path, map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()

    wrapped = WrappedForExport(model)
    dummy_input = torch.randn(1, 3, *input_hw)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    torch.onnx.export(
        wrapped, dummy_input, out_path,
        input_names=["input"], output_names=["enhanced"],
        dynamic_axes={"input": {2: "height", 3: "width"}, "enhanced": {2: "height", 3: "width"}},
        opset_version=opset,
    )
    print(f"Zero-DCE ONNX export complete: {out_path}")
    return out_path


def verify_onnx(onnx_path: str) -> None:
    """Sanity-checks the exported graph loads and runs before you ship it to an
    edge box — cheap insurance against a silently broken export."""
    import onnx
    import onnxruntime as ort
    import numpy as np

    onnx_model = onnx.load(onnx_path)
    onnx.checker.check_model(onnx_model)

    session = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    input_meta = session.get_inputs()[0]
    dummy_shape = [d if isinstance(d, int) else 1 for d in input_meta.shape]
    dummy = np.random.randn(*dummy_shape).astype(np.float32)
    outputs = session.run(None, {input_meta.name: dummy})
    print(f"ONNX model verified OK. Output shapes: {[o.shape for o in outputs]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export models to ONNX for edge deployment")
    parser.add_argument("--yolo", type=str, help="Path to YOLO .pt checkpoint to export")
    parser.add_argument("--zero-dce", type=str, help="Path to Zero-DCE .pth weights to export")
    parser.add_argument("--out", type=str, default="models/zero_dce.onnx", help="Output path for --zero-dce")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--verify", action="store_true", help="Run a sanity inference after export")
    args = parser.parse_args()

    if args.yolo:
        path = export_yolo_to_onnx(args.yolo, imgsz=args.imgsz)
        if args.verify:
            verify_onnx(path)

    if args.zero_dce:
        path = export_zero_dce_to_onnx(args.zero_dce, args.out)
        if args.verify:
            verify_onnx(path)

    if not args.yolo and not args.zero_dce:
        parser.print_help()
