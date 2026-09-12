"""
End-to-end IBVAP AI/CV pipeline. Reads a video stream and, for every frame:

  1. checks brightness -> runs low-light enhancement if needed (night detection)
  2. runs YOLO detection + ByteTrack tracking (person/vehicle classes)
  3. for person tracks: runs face detection in the person's ROI
  4. for vehicle tracks: runs plate detection + OCR (ANPR)
  5. feeds every track's bbox into the virtual-fence/loitering analytics rules
  6. logs every detection/alert to the tamper-evident event log
  7. draws all overlays and displays/saves the annotated frame

Config-driven end to end — see configs/config.yaml.
"""
from __future__ import annotations

import argparse
import time
from typing import Dict, Optional

import cv2
import yaml

from src.detection.yolo_detector import YOLODetector, Detection
from src.face.face_detector import YuNetFaceDetector
from src.anpr.plate_detector import PlateDetector
from src.anpr.ocr import PlateOCR, is_plausible_plate
from src.enhancement.retinex import enhance_if_dark
from src.analytics.rules import AnalyticsEngine
from src.utils.video_utils import VideoStream, is_low_light, draw_label
from src.utils.logger import EventLogger


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


class IBVAPPipeline:
    def __init__(self, config: dict):
        self.config = config
        det_cfg = config["detection"]
        face_cfg = config["face"]
        anpr_cfg = config["anpr"]
        enh_cfg = config["enhancement"]

        vehicle_class_ids = [det_cfg["classes"][k] for k in ("car", "motorcycle", "bus", "truck")]
        person_class_id = det_cfg["classes"]["person"]
        self.person_class_id = person_class_id
        self.vehicle_class_ids = set(vehicle_class_ids)

        self.detector = YOLODetector(
            model_path=det_cfg["model_path"],
            confidence=det_cfg["confidence"],
            iou=det_cfg["iou"],
            device=config["runtime"]["device"],
            class_filter=[person_class_id] + vehicle_class_ids,
        )
        self.tracker_cfg = det_cfg["bytetrack_cfg"]

        self.face_detector = YuNetFaceDetector(
            model_path=face_cfg["model_path"],
            input_size=tuple(face_cfg["input_size"]),
            score_threshold=face_cfg["score_threshold"],
            nms_threshold=face_cfg["nms_threshold"],
        )

        self.plate_detector = PlateDetector(
            model_path=anpr_cfg.get("plate_model_path"),
            aspect_ratio_range=tuple(anpr_cfg["plate_aspect_ratio_range"]),
            min_confidence=anpr_cfg["min_plate_confidence"],
        )
        self.plate_ocr = PlateOCR(engine=anpr_cfg["ocr_engine"], languages=anpr_cfg["ocr_languages"])
        self.min_plate_conf = anpr_cfg["min_plate_confidence"]

        self.enhancement_method = enh_cfg["method"]
        self.night_threshold = enh_cfg["night_brightness_threshold"]

        self.analytics = AnalyticsEngine(config)

        self.logger = EventLogger(
            log_dir=config["alerts"]["log_dir"],
            log_file=config["alerts"]["event_log_file"],
            snapshot_dir=config["alerts"]["snapshot_dir"],
            save_snapshots=config["alerts"]["save_snapshots"],
        )

        self._ocr_cache: Dict[int, str] = {}  # track_id -> already-read plate text (avoid re-OCR every frame)

    def _apply_enhancement(self, frame):
        if self.enhancement_method == "none":
            return frame
        if self.enhancement_method == "retinex":
            return enhance_if_dark(frame, brightness_threshold=self.night_threshold)
        if self.enhancement_method == "zero_dce":
            if is_low_light(frame, self.night_threshold):
                # lazy import/instantiate — only pay Zero-DCE's model-load cost if actually used
                if not hasattr(self, "_zero_dce"):
                    from src.enhancement.zero_dce import ZeroDCEEnhancer
                    self._zero_dce = ZeroDCEEnhancer(
                        weights_path=self.config["enhancement"]["zero_dce_weights"],
                        device=self.config["runtime"]["device"],
                    )
                return self._zero_dce.enhance(frame)
            return frame
        return frame

    def process_frame(self, frame):
        frame = self._apply_enhancement(frame)
        detections = self.detector.track(frame, tracker_cfg=self.tracker_cfg)

        active_track_ids = set()

        for det in detections:
            if det.track_id is None:
                continue
            active_track_ids.add(det.track_id)

            if det.class_id == self.person_class_id:
                self._handle_person(frame, det)
            elif det.class_id in self.vehicle_class_ids:
                self._handle_vehicle(frame, det)

            for alert in self.analytics.process_track(det.track_id, det.bbox):
                self.logger.log_event(alert["type"], alert, frame=frame)

            self._draw_detection(frame, det)

        return frame

    def _handle_person(self, frame, det: Detection):
        faces = self.face_detector.detect_in_roi(frame, det.bbox)
        for face in faces:
            self.logger.log_event("face_detected", {
                "track_id": det.track_id,
                "bbox": face.bbox,
                "confidence": face.confidence,
            })
            x, y, w, h = [int(v) for v in face.bbox]
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 200, 0), 2)

    def _handle_vehicle(self, frame, det: Detection):
        if det.track_id in self._ocr_cache:
            return  # already have a confident plate read for this track; don't re-run OCR every frame

        plates = self.plate_detector.detect_plates_in_vehicle(frame, det.bbox)
        for plate in plates:
            if plate.confidence < self.min_plate_conf:
                continue
            reading = self.plate_ocr.read(plate.crop, min_confidence=self.min_plate_conf)
            if reading is None or not is_plausible_plate(reading.text):
                continue

            self._ocr_cache[det.track_id] = reading.text
            self.logger.log_event("anpr_read", {
                "track_id": det.track_id,
                "plate_text": reading.text,
                "confidence": reading.confidence,
                "bbox": plate.bbox,
            }, frame=frame)

            x1, y1, x2, y2 = [int(v) for v in plate.bbox]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 255), 2)
            draw_label(frame, reading.text, x1, y1, color=(0, 200, 255))
            break  # one confident plate per vehicle is enough

    def _draw_detection(self, frame, det: Detection):
        x1, y1, x2, y2 = [int(v) for v in det.bbox]
        color = (0, 255, 0) if det.class_id == self.person_class_id else (255, 140, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"{det.class_name} #{det.track_id} {det.confidence:.2f}"
        draw_label(frame, label, x1, y1, color=color)


def run(config_path: str, source, display: bool = True, save_output: Optional[str] = None):
    config = load_config(config_path)
    pipeline = IBVAPPipeline(config)

    writer = None
    with VideoStream(source, target_fps=config["runtime"]["target_fps"],
                      resize_width=config["video"]["resize_width"]) as stream:
        for frame_data in stream:
            start = time.time()
            annotated = pipeline.process_frame(frame_data.frame)
            fps = 1.0 / max(time.time() - start, 1e-6)
            draw_label(annotated, f"FPS: {fps:.1f}", 10, 30, color=(200, 200, 200))

            if save_output:
                if writer is None:
                    h, w = annotated.shape[:2]
                    writer = cv2.VideoWriter(save_output, cv2.VideoWriter_fourcc(*"mp4v"), 20, (w, h))
                writer.write(annotated)

            if display:
                cv2.imshow("IBVAP - AI/CV Pipeline", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    if writer:
        writer.release()
    if display:
        cv2.destroyAllWindows()

    print("Event log chain valid:", pipeline.logger.verify_chain())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the IBVAP AI/CV pipeline")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--source", required=True, help="Video file path, webcam index, or RTSP URL")
    parser.add_argument("--no-display", action="store_true")
    parser.add_argument("--save", type=str, default=None, help="Path to save annotated output video")
    args = parser.parse_args()

    run(args.config, args.source, display=not args.no_display, save_output=args.save)
