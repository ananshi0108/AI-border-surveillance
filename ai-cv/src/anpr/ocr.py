"""
OCR pipeline for ANPR: preprocessing + text recognition + plate-string cleanup.

Two OCR backends supported behind one interface:
  - easyocr   (default): deep-learning based, good on varied fonts/lighting, GPU-optional.
  - tesseract           : lighter, faster on CPU-only edge boxes, needs the system
                          `tesseract-ocr` package installed (`sudo apt install tesseract-ocr`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

import cv2
import numpy as np


@dataclass
class PlateReading:
    text: str
    confidence: float


def preprocess_plate(crop: np.ndarray) -> np.ndarray:
    """Standard ANPR preprocessing: grayscale, upscale small crops, denoise,
    adaptive threshold — makes OCR far more reliable on low-res CCTV footage."""
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop

    h, w = gray.shape[:2]
    if w < 200:  # upscale small/far-away plates before OCR
        scale = 200 / w
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

    gray = cv2.fastNlMeansDenoising(gray, h=10)
    gray = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )
    return gray


def clean_plate_text(raw_text: str) -> str:
    """Strips whitespace/punctuation OCR noise and uppercases — plates are
    alphanumeric only in virtually every jurisdiction's format."""
    text = re.sub(r"[^A-Za-z0-9]", "", raw_text)
    return text.upper()


class PlateOCR:
    def __init__(self, engine: str = "easyocr", languages: Optional[List[str]] = None,
                 gpu: bool = False):
        self.engine = engine
        languages = languages or ["en"]

        if engine == "easyocr":
            import easyocr
            self.reader = easyocr.Reader(languages, gpu=gpu)
        elif engine == "tesseract":
            import pytesseract
            self.pytesseract = pytesseract
        else:
            raise ValueError(f"Unknown OCR engine: {engine}")

    def read(self, plate_crop: np.ndarray, min_confidence: float = 0.4) -> Optional[PlateReading]:
        processed = preprocess_plate(plate_crop)

        if self.engine == "easyocr":
            results = self.reader.readtext(processed, detail=1)
            if not results:
                return None
            # concatenate all detected text fragments (plates sometimes split into
            # two OCR boxes, e.g. state code vs number) and average confidence
            texts = [r[1] for r in results]
            confs = [r[2] for r in results]
            combined = clean_plate_text("".join(texts))
            avg_conf = float(np.mean(confs)) if confs else 0.0
            if not combined or avg_conf < min_confidence:
                return None
            return PlateReading(text=combined, confidence=avg_conf)

        else:  # tesseract
            config = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            raw_text = self.pytesseract.image_to_string(processed, config=config)
            cleaned = clean_plate_text(raw_text)
            if not cleaned:
                return None
            # tesseract's image_to_string doesn't give a simple scalar confidence;
            # treat any non-empty, whitelist-constrained read as confidence 0.6
            return PlateReading(text=cleaned, confidence=0.6)


def is_plausible_plate(text: str, min_len: int = 6, max_len: int = 12) -> bool:
    """Basic sanity filter before an ANPR read is trusted enough to log/alert on."""
    return min_len <= len(text) <= max_len and bool(re.match(r"^[A-Z0-9]+$", text))
