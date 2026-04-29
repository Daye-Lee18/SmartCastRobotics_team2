"""Hardware streaming RPC methods and image publisher servicer."""

from __future__ import annotations

import logging

import grpc
import management_pb2  # type: ignore
import management_pb2_grpc  # type: ignore

from services.core.command_queue import queue as command_queue
from services.adapters.vision.image_sink import sink as image_sink

logger = logging.getLogger(__name__)


class HardwareRpcMixin:
    """Conveyor command and camera frame stream RPCs."""

    def WatchConveyorCommands(self, request, context):
        subscriber_id = request.subscriber_id or "unknown"
        filter_ = request.robot_id_filter or ""
        logger.info(
            "WatchConveyorCommands subscriber=%s filter=%s",
            subscriber_id,
            filter_ or "<all>",
        )
        while context.is_active():
            cmd = command_queue.wait_next(filter_ or None, timeout=10.0)
            if cmd is None:
                continue
            yield management_pb2.ConveyorCommand(
                robot_id=cmd.robot_id,
                command=cmd.command,
                payload=cmd.payload,
                item_id=cmd.item_id,
                issued_at=management_pb2.Timestamp(iso8601=cmd.issued_at_iso),
                issued_by=cmd.issued_by,
            )
        logger.info("WatchConveyorCommands closed subscriber=%s", subscriber_id)

    def WatchCameraFrames(self, request, context):
        cam = request.camera_id or ""
        if not cam:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("camera_id required")
            return
        last_seq = int(request.after_sequence)
        logger.info("WatchCameraFrames subscriber camera=%s after_seq=%d", cam, last_seq)
        while context.is_active():
            frame = image_sink.wait_new(cam, last_seq, timeout=10.0)
            if frame is None:
                continue
            last_seq = int(frame.get("sequence", 0))
            yield self._frame_to_response(cam, frame)
        logger.info("WatchCameraFrames subscriber closed camera=%s", cam)

    @staticmethod
    def _frame_to_response(cam: str, frame: dict):
        return management_pb2.CameraFrameResponse(
            available=True,
            camera_id=cam,
            encoding=frame.get("encoding", ""),
            width=int(frame.get("width", 0) or 0),
            height=int(frame.get("height", 0) or 0),
            data=frame.get("data", b""),
            sequence=int(frame.get("sequence", 0) or 0),
            captured_at=management_pb2.Timestamp(iso8601=frame.get("captured_at", "") or ""),
            received_at=management_pb2.Timestamp(iso8601=frame.get("received_at", "") or ""),
        )


class ImagePublisherServicer(management_pb2_grpc.ImagePublisherServiceServicer):
    """HW Image Publishing Service (Jetson) -> Server."""

    def PublishFrames(self, request_iterator, context):
        last_seq = 0
        count = 0
        for frame in request_iterator:
            try:
                image_sink.push(
                    camera_id=frame.camera_id,
                    encoding=frame.encoding,
                    width=frame.width,
                    height=frame.height,
                    data=frame.data,
                    sequence=frame.sequence,
                    captured_at_iso=frame.captured_at.iso8601
                    if frame.HasField("captured_at")
                    else "",
                )
                last_seq = frame.sequence
                count += 1
            except Exception as exc:  # noqa: BLE001
                logger.exception("ImagePublisher push 실패: %s", exc)
        logger.info("ImagePublisher 스트림 종료: %d frames, last_seq=%d", count, last_seq)
        return management_pb2.ImageAck(
            sequence=last_seq,
            accepted=True,
            message=f"received {count} frames",
        )

