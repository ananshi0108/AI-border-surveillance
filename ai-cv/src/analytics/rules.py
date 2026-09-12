"""
Rule-based behavioural analytics that turn raw tracked detections into alerts:
  - Virtual fence: flags a track crossing a user-defined line (e.g. the actual
    border line or a perimeter around a BOP).
  - Loitering / suspicious dwell: flags a track that stays in roughly the same
    place for longer than a configured threshold.

These sit on top of src/detection (which supplies track_id + bbox per frame)
and feed src/utils/logger.py for tamper-evident alert logging.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple


Point = Tuple[float, float]


def _centroid(bbox: List[float]) -> Point:
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _which_side(p: Point, a: Point, b: Point) -> float:
    """Sign of the cross product tells you which side of line a->b point p is on."""
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


@dataclass
class VirtualFence:
    line_start: Point
    line_end: Point
    direction: str = "both"   # both | in_to_out | out_to_in
    _last_side: Dict[int, float] = field(default_factory=dict)

    def update(self, track_id: int, bbox: List[float]) -> Optional[str]:
        """Call once per frame per track. Returns a breach direction string
        ("in_to_out" / "out_to_in") the moment a crossing is detected, else None."""
        p = _centroid(bbox)
        side = _which_side(p, self.line_start, self.line_end)

        prev_side = self._last_side.get(track_id)
        self._last_side[track_id] = side

        if prev_side is None or prev_side == 0 or side == 0:
            return None  # not enough history yet, or sitting exactly on the line

        crossed = (prev_side > 0) != (side > 0)
        if not crossed:
            return None

        breach_direction = "in_to_out" if prev_side > 0 else "out_to_in"
        if self.direction != "both" and self.direction != breach_direction:
            return None
        return breach_direction

    def forget(self, track_id: int) -> None:
        self._last_side.pop(track_id, None)


@dataclass
class LoiteringDetector:
    dwell_seconds: float = 30.0
    movement_pixel_threshold: float = 40.0
    history_window: int = 150   # frames of centroid history kept per track
    _first_seen: Dict[int, float] = field(default_factory=dict)
    _history: Dict[int, Deque[Tuple[float, Point]]] = field(default_factory=lambda: defaultdict(deque))
    _already_flagged: Dict[int, bool] = field(default_factory=dict)

    def update(self, track_id: int, bbox: List[float]) -> bool:
        """Call once per frame per track. Returns True the moment a track first
        crosses the loitering threshold (fires once per track, not every frame).

        `_first_seen` tracks total time present (independent of the pruned
        window below) so the dwell threshold is judged against how long the
        track has actually existed, not against whatever happens to remain in
        the recent-movement window.
        """
        now = time.time()
        p = _centroid(bbox)

        if track_id not in self._first_seen:
            self._first_seen[track_id] = now

        hist = self._history[track_id]
        hist.append((now, p))
        while len(hist) > self.history_window:
            hist.popleft()

        # drop points older than the dwell window so movement is judged on recent behaviour only
        while hist and now - hist[0][0] > self.dwell_seconds:
            hist.popleft()

        time_present = now - self._first_seen[track_id]
        if time_present < self.dwell_seconds or not hist:
            return False  # not present long enough yet to judge

        max_disp = max(
            ((p[0] - h[1][0]) ** 2 + (p[1] - h[1][1]) ** 2) ** 0.5
            for h in hist
        )

        is_loitering = max_disp < self.movement_pixel_threshold
        already = self._already_flagged.get(track_id, False)

        if is_loitering and not already:
            self._already_flagged[track_id] = True
            return True
        if not is_loitering:
            self._already_flagged[track_id] = False
        return False

    def forget(self, track_id: int) -> None:
        self._first_seen.pop(track_id, None)
        self._history.pop(track_id, None)
        self._already_flagged.pop(track_id, None)


class AnalyticsEngine:
    """Convenience wrapper combining both rules, built straight from config.yaml."""

    def __init__(self, config: dict):
        fence_cfg = config["analytics"]["virtual_fence"]
        loiter_cfg = config["analytics"]["loitering"]

        self.fence_enabled = fence_cfg["enabled"]
        self.loiter_enabled = loiter_cfg["enabled"]

        self.fence = VirtualFence(
            line_start=tuple(fence_cfg["line_start"]),
            line_end=tuple(fence_cfg["line_end"]),
            direction=fence_cfg["direction"],
        ) if self.fence_enabled else None

        self.loitering = LoiteringDetector(
            dwell_seconds=loiter_cfg["dwell_seconds"],
            movement_pixel_threshold=loiter_cfg["movement_pixel_threshold"],
        ) if self.loiter_enabled else None

    def process_track(self, track_id: int, bbox: List[float]) -> List[dict]:
        """Returns a list of alert dicts (possibly empty) for this track this frame."""
        alerts: List[dict] = []

        if self.fence_enabled:
            breach = self.fence.update(track_id, bbox)
            if breach:
                alerts.append({"type": "virtual_fence_breach", "track_id": track_id,
                                "direction": breach, "bbox": bbox})

        if self.loiter_enabled:
            if self.loitering.update(track_id, bbox):
                alerts.append({"type": "loitering_alert", "track_id": track_id, "bbox": bbox})

        return alerts

    def forget_track(self, track_id: int) -> None:
        """Call when a track is lost (left frame) to free memory."""
        if self.fence_enabled:
            self.fence.forget(track_id)
        if self.loiter_enabled:
            self.loitering.forget(track_id)
