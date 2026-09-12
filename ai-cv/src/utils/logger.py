"""
Tamper-evident event/alert logging.

Every log entry stores the SHA-256 hash of the *previous* entry alongside its own
payload hash, forming a hash chain (the same core idea a blockchain audit trail
uses). Any retroactive edit or deletion of a past entry breaks every hash after
it, so the log is verifiable without needing a full blockchain node — a
lightweight way to satisfy the "tamper-evident event logs" requirement from the
Blockchain & Cybersecurity theme.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


GENESIS_HASH = "0" * 64


@dataclass
class EventLogger:
    log_dir: str = "logs"
    log_file: str = "events.jsonl"
    snapshot_dir: str = "logs/snapshots"
    save_snapshots: bool = True
    _prev_hash: str = field(default=GENESIS_HASH, init=False)

    def __post_init__(self):
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        if self.save_snapshots:
            Path(self.snapshot_dir).mkdir(parents=True, exist_ok=True)
        self._log_path = Path(self.log_dir) / self.log_file
        self._prev_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        if not self._log_path.exists():
            return GENESIS_HASH
        last_line = None
        with open(self._log_path, "r") as f:
            for line in f:
                if line.strip():
                    last_line = line
        if last_line is None:
            return GENESIS_HASH
        return json.loads(last_line)["entry_hash"]

    @staticmethod
    def _hash(payload: Dict[str, Any]) -> str:
        blob = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def log_event(self, event_type: str, data: Dict[str, Any],
                   frame: Optional["numpy.ndarray"] = None) -> Dict[str, Any]:
        """Append one tamper-evident event/alert record.

        event_type: e.g. "person_detected", "vehicle_detected", "anpr_read",
                     "virtual_fence_breach", "loitering_alert", "face_detected"
        data: arbitrary JSON-serialisable payload (bbox, track_id, plate text, etc.)
        frame: optional image to save as evidence alongside the alert
        """
        timestamp = time.time()
        entry_body = {
            "timestamp": timestamp,
            "event_type": event_type,
            "data": data,
            "prev_hash": self._prev_hash,
        }
        entry_hash = self._hash(entry_body)
        entry = {**entry_body, "entry_hash": entry_hash}

        if frame is not None and self.save_snapshots:
            snap_name = f"{event_type}_{int(timestamp * 1000)}.jpg"
            snap_path = str(Path(self.snapshot_dir) / snap_name)
            try:
                import cv2
                cv2.imwrite(snap_path, frame)
                entry["snapshot"] = snap_path
            except Exception:
                pass  # snapshotting is best-effort; never let it break the pipeline

        with open(self._log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        self._prev_hash = entry_hash
        return entry

    def verify_chain(self) -> bool:
        """Re-walks the log file and confirms every prev_hash/entry_hash link is
        intact. Returns False the moment a broken or edited entry is found."""
        if not self._log_path.exists():
            return True
        prev = GENESIS_HASH
        with open(self._log_path, "r") as f:
            for line_no, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                entry = json.loads(line)
                claimed_hash = entry.pop("entry_hash")
                snapshot = entry.pop("snapshot", None)
                if entry["prev_hash"] != prev:
                    print(f"Chain broken at line {line_no}: prev_hash mismatch")
                    return False
                recomputed = self._hash(entry)
                if recomputed != claimed_hash:
                    print(f"Chain broken at line {line_no}: entry has been altered")
                    return False
                prev = claimed_hash
        return True


if __name__ == "__main__":
    # quick self-test
    logger = EventLogger(log_dir="logs", log_file="events.jsonl")
    logger.log_event("virtual_fence_breach", {"track_id": 12, "bbox": [10, 20, 100, 200]})
    logger.log_event("anpr_read", {"track_id": 12, "plate_text": "DL01AB1234", "confidence": 0.91})
    print("Chain valid:", logger.verify_chain())
