"""
Zero-DCE: Zero-Reference Deep Curve Estimation for low-light image enhancement.

Reference: Guo et al., "Zero-Reference Deep Curve Estimation for Low-Light
Image Enhancement", CVPR 2020. https://github.com/Li-Chongyi/Zero-DCE

Unlike Retinex (classical, instant, zero-training), Zero-DCE is a *learned*
lightweight CNN (~79K params) that estimates a set of pixel-wise curve
parameters and iteratively applies them to brighten the image, with no need
for paired low/normal-light training data (it trains on a self-supervised
combination of exposure/color/spatial-consistency/illumination-smoothness
losses). Use it when Retinex artifacts (occasional color casts on very noisy
CCTV feeds) are unacceptable and you can afford ~5-10ms extra inference per
frame on the target edge hardware.

You need trained weights to use this (`configs/config.yaml: enhancement.zero_dce_weights`).
Either:
  (a) download the official pretrained snapshot from the paper's repo, or
  (b) train your own on your border-camera dataset with `train_zero_dce()` below.
Retinex requires neither and is the safe default until you have weights in place.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class DCENet(nn.Module):
    """The DCE-Net: 7 conv layers, estimates 8 iterations of 3-channel curve
    parameter maps (24 output channels total) from a single low-light input."""

    def __init__(self, num_iterations: int = 8):
        super().__init__()
        self.num_iterations = num_iterations
        n_channels = 32

        self.relu = nn.ReLU(inplace=True)
        self.e_conv1 = nn.Conv2d(3, n_channels, 3, 1, 1)
        self.e_conv2 = nn.Conv2d(n_channels, n_channels, 3, 1, 1)
        self.e_conv3 = nn.Conv2d(n_channels, n_channels, 3, 1, 1)
        self.e_conv4 = nn.Conv2d(n_channels, n_channels, 3, 1, 1)
        # skip connections (U-Net-ish) concatenate features -> double channels in
        self.e_conv5 = nn.Conv2d(n_channels * 2, n_channels, 3, 1, 1)
        self.e_conv6 = nn.Conv2d(n_channels * 2, n_channels, 3, 1, 1)
        self.e_conv7 = nn.Conv2d(n_channels * 2, 3 * num_iterations, 3, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.relu(self.e_conv1(x))
        x2 = self.relu(self.e_conv2(x1))
        x3 = self.relu(self.e_conv3(x2))
        x4 = self.relu(self.e_conv4(x3))
        x5 = self.relu(self.e_conv5(torch.cat([x3, x4], dim=1)))
        x6 = self.relu(self.e_conv6(torch.cat([x2, x5], dim=1)))
        curve_params = torch.tanh(self.e_conv7(torch.cat([x1, x6], dim=1)))
        return curve_params

    def enhance(self, x: torch.Tensor) -> torch.Tensor:
        """Applies the estimated pixel-wise curves iteratively to brighten `x`."""
        curve_params = self.forward(x)
        curves = torch.split(curve_params, 3, dim=1)  # num_iterations tensors of shape [B,3,H,W]
        enhanced = x
        for curve in curves:
            enhanced = enhanced + curve * (torch.pow(enhanced, 2) - enhanced)
        return enhanced


class ZeroDCEEnhancer:
    """Inference-only wrapper: load weights once, call `enhance(frame_bgr)` per frame."""

    def __init__(self, weights_path: Optional[str] = None, device: str = "cpu"):
        self.device = torch.device(device)
        self.model = DCENet().to(self.device)
        if weights_path:
            state_dict = torch.load(weights_path, map_location=self.device)
            self.model.load_state_dict(state_dict)
        self.model.eval()

    @torch.no_grad()
    def enhance(self, frame_bgr: np.ndarray) -> np.ndarray:
        h, w = frame_bgr.shape[:2]
        rgb = frame_bgr[:, :, ::-1].astype(np.float32) / 255.0
        tensor = torch.from_numpy(rgb.copy()).permute(2, 0, 1).unsqueeze(0).to(self.device)

        enhanced = self.model.enhance(tensor)
        enhanced = enhanced.clamp(0, 1).squeeze(0).permute(1, 2, 0).cpu().numpy()

        out_bgr = (enhanced[:, :, ::-1] * 255).astype(np.uint8)
        return out_bgr


# ---------------------------------------------------------------------------
# Reference training loop (self-supervised, no ground-truth needed).
# Run this offline on a folder of low-light border-camera stills to fine-tune
# for your specific cameras before exporting to ONNX/TensorRT for the edge.
# ---------------------------------------------------------------------------
def color_constancy_loss(enhanced: torch.Tensor) -> torch.Tensor:
    mean_rgb = enhanced.mean(dim=[2, 3])
    mr, mg, mb = mean_rgb[:, 0], mean_rgb[:, 1], mean_rgb[:, 2]
    return ((mr - mg) ** 2 + (mg - mb) ** 2 + (mb - mr) ** 2).mean()


def exposure_loss(enhanced: torch.Tensor, patch_size: int = 16, target_exposure: float = 0.6) -> torch.Tensor:
    gray = enhanced.mean(dim=1, keepdim=True)
    pooled = F.avg_pool2d(gray, patch_size)
    return ((pooled - target_exposure) ** 2).mean()


def illumination_smoothness_loss(curve_params: torch.Tensor) -> torch.Tensor:
    dh = curve_params[:, :, 1:, :] - curve_params[:, :, :-1, :]
    dw = curve_params[:, :, :, 1:] - curve_params[:, :, :, :-1]
    return (dh ** 2).mean() + (dw ** 2).mean()


def train_zero_dce(dataloader, epochs: int = 100, lr: float = 1e-4, device: str = "cpu") -> DCENet:
    """Minimal self-supervised training loop. `dataloader` should yield batches
    of low-light images normalised to [0,1], shape [B,3,H,W]. No labels needed."""
    model = DCENet().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    for epoch in range(epochs):
        for batch in dataloader:
            batch = batch.to(device)
            curve_params = model(batch)
            enhanced = batch
            for curve in torch.split(curve_params, 3, dim=1):
                enhanced = enhanced + curve * (torch.pow(enhanced, 2) - enhanced)

            loss = (
                exposure_loss(enhanced)
                + 5 * color_constancy_loss(enhanced)
                + 200 * illumination_smoothness_loss(curve_params)
            )

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        print(f"[Zero-DCE] epoch {epoch + 1}/{epochs} - loss {loss.item():.4f}")

    return model
