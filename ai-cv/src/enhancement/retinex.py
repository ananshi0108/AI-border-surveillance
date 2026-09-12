"""
Multi-Scale Retinex with Color Restoration (MSRCR).

Classical, no-training-needed low-light enhancement — the pragmatic default for
IBVAP because it runs instantly on any edge box (pure numpy/OpenCV, no model
weights, no GPU) and is robust across arbitrary border camera hardware.
Zero-DCE (zero_dce.py) is offered as a learned alternative when a bit more
quality/naturalness matters and a small inference cost is acceptable.

Reference: Jobson, Rahman & Woodell, "A Multiscale Retinex for Bridging the Gap
Between Color Images and the Human Observation of Scenes" (1997).
"""
from __future__ import annotations

from typing import List

import cv2
import numpy as np


def _single_scale_retinex(channel: np.ndarray, sigma: float) -> np.ndarray:
    blurred = cv2.GaussianBlur(channel, (0, 0), sigma)
    # log domain, +1 avoids log(0); float32 throughout for precision
    retinex = np.log10(channel.astype(np.float32) + 1.0) - np.log10(blurred.astype(np.float32) + 1.0)
    return retinex


def _multi_scale_retinex(channel: np.ndarray, sigmas: List[float]) -> np.ndarray:
    msr = np.zeros_like(channel, dtype=np.float32)
    for sigma in sigmas:
        msr += _single_scale_retinex(channel, sigma)
    return msr / len(sigmas)


def _color_restoration(image: np.ndarray, alpha: float = 125.0, beta: float = 46.0) -> np.ndarray:
    img_sum = np.sum(image, axis=2, keepdims=True)
    img_sum[img_sum == 0] = 1.0  # avoid divide-by-zero on pure-black pixels
    return beta * (np.log10(alpha * image + 1.0) - np.log10(img_sum + 1.0))


def _simplest_color_balance(image: np.ndarray, low_clip: float = 0.01, high_clip: float = 0.99) -> np.ndarray:
    out = np.zeros_like(image)
    for c in range(image.shape[2]):
        channel = image[:, :, c]
        low_val = np.percentile(channel, low_clip * 100)
        high_val = np.percentile(channel, high_clip * 100)
        out[:, :, c] = np.clip((channel - low_val) / max(high_val - low_val, 1e-6), 0, 1)
    return out


def enhance_msrcr(frame_bgr: np.ndarray, sigmas: List[float] = [15, 80, 250],
                    alpha: float = 125.0, beta: float = 46.0,
                    gain: float = 128.0, offset: float = 128.0) -> np.ndarray:
    """Applies MSRCR to a BGR uint8 frame and returns an enhanced BGR uint8 frame.

    Good default entry point: `enhance_msrcr(frame)` with no tuning needed for
    most CCTV footage.
    """
    img = frame_bgr.astype(np.float32) + 1.0  # avoid log(0)

    msr = np.zeros_like(img, dtype=np.float32)
    for c in range(3):
        msr[:, :, c] = _multi_scale_retinex(img[:, :, c], sigmas)

    color_restored = _color_restoration(img, alpha=alpha, beta=beta)
    msrcr = gain * (msr * color_restored) + offset

    # normalise per-channel and rescale to 0-255
    balanced = _simplest_color_balance(msrcr)
    output = np.clip(balanced * 255, 0, 255).astype(np.uint8)
    return output


def enhance_if_dark(frame_bgr: np.ndarray, brightness_threshold: float = 60.0) -> np.ndarray:
    """Convenience wrapper used by the pipeline: only pays the MSRCR compute cost
    when the frame is actually dark, so daytime footage isn't needlessly processed."""
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    if gray.mean() < brightness_threshold:
        return enhance_msrcr(frame_bgr)
    return frame_bgr
