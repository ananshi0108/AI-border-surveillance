import logging
from typing import Dict, Optional, Union

from app.services.vision.live_pipeline import LivePipeline

logger = logging.getLogger("ibvap.vision.manager")


class StreamManager:
    """
    Manages concurrent live video-analysis pipelines.

    Each camera gets its own background LivePipeline:

        StreamReader
            -> YOLO
            -> Geometry Rules
            -> Snapshot
            -> Database Alert
    """

    def __init__(self):
        self._pipelines: Dict[int, LivePipeline] = {}

    def start_stream(
        self,
        camera_id: int,
        source: Union[str, int],
        target_fps: Optional[float] = None,
        loop_file: bool = True,
        camera_name: Optional[str] = None,
    ) -> LivePipeline:
        """
        Start the complete video-analysis pipeline for a camera.
        """

        # If this camera already has a pipeline, don't start another one.
        if camera_id in self._pipelines:
            existing = self._pipelines[camera_id]

            if existing.reader.is_running:
                logger.info(
                    "[StreamManager] Camera %s pipeline is already running.",
                    camera_id,
                )
                return existing

            existing.stop()

        # LivePipeline handles:
        # StreamReader -> YOLO -> Geometry -> Snapshot -> DB
        pipeline = LivePipeline(
            camera_id=camera_id,
            stream_url=source,
            camera_name=camera_name,
            target_fps=target_fps or 5.0,
        )

        pipeline.start()

        self._pipelines[camera_id] = pipeline

        logger.info(
            "[StreamManager] Started live pipeline for Camera %s.",
            camera_id,
        )

        return pipeline

    def ensure_started(
        self,
        camera_id: int,
        source: Union[str, int],
        target_fps: Optional[float] = None,
        camera_name: Optional[str] = None,
    ) -> LivePipeline:
        """
        Returns the running pipeline for a camera, starting it first
        (with the given source) if it isn't already active.

        Used by the streaming/snapshot API endpoints so a frontend can
        simply request a feed without needing a separate "start" call.
        """

        existing = self._pipelines.get(camera_id)
        if existing is not None and existing.reader.is_running:
            return existing

        return self.start_stream(
            camera_id=camera_id,
            source=source,
            target_fps=target_fps,
            camera_name=camera_name,
        )

    def stop_stream(self, camera_id: int) -> bool:
        """
        Stop the complete pipeline for a camera.
        """

        if camera_id not in self._pipelines:
            return False

        pipeline = self._pipelines.pop(camera_id)

        pipeline.stop()

        logger.info(
            "[StreamManager] Stopped pipeline for Camera %s.",
            camera_id,
        )

        return True

    def get_stream(self, camera_id: int) -> Optional[LivePipeline]:
        """
        Return the active pipeline for a camera.
        """

        return self._pipelines.get(camera_id)

    def is_active(self, camera_id: int) -> bool:
        """
        Check whether a camera pipeline is actively connected.
        """

        pipeline = self._pipelines.get(camera_id)

        if pipeline is None:
            return False

        return bool(
            pipeline.reader.is_running
            and pipeline.reader.is_connected
        )

    def get_all_statuses(self) -> Dict[int, dict]:
        """
        Return health/status information for all camera pipelines.
        """

        statuses = {}

        for cam_id, pipeline in self._pipelines.items():
            reader = pipeline.reader

            statuses[cam_id] = {
                "running": reader.is_running,
                "connected": reader.is_connected,
                "fps": reader.fps,
                "resolution": f"{reader.width}x{reader.height}",
                "total_frames": reader.total_frames_read,
                "source": str(reader.source),
            }

        return statuses

    def stop_all(self) -> None:
        """
        Gracefully stop all camera pipelines.
        """

        logger.info(
            "[StreamManager] Stopping all %s active camera pipelines...",
            len(self._pipelines),
        )

        for camera_id in list(self._pipelines.keys()):
            self.stop_stream(camera_id)


# Global singleton
stream_manager = StreamManager()