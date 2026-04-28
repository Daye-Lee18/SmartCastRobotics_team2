"""Jetson Image Publisher — USB 카메라 프레임을 Management Server(:50051) 로 push.

V6 아키텍처 Image Publishing Service (client streaming).
Target: Jetson Orin NX 16GB (JetPack R35.5, Python 3.8, aarch64).
Transport: Tailscale 내부망 (MANAGEMENT_GRPC_HOST 로 Server 지정).

설계 원칙:
- Jetson 은 "dumb producer" — 연속 캡처 + 연속 push 만. 공정 이벤트 판단은 Server.
- Server 측 image_sink 가 카메라별 latest 1 프레임 보관 → image_forwarder 가 스냅샷.
- 저대역 (2Hz JPEG ~50KB = 100KB/s) 로 Tailscale 부담 최소화.

환경변수:
    JETSON_CAMERA_ID       (default: CAM-INSP-01)
    JETSON_CAMERA_INDEX    (default: 0 — /dev/video0)
    JETSON_FRAME_WIDTH     (default: 1280)
    JETSON_FRAME_HEIGHT    (default: 720)
    JETSON_FPS             (default: 2)
    JETSON_JPEG_QUALITY    (default: 85)
    MANAGEMENT_GRPC_HOST   (default: 100.107.120.xx — Mgmt Server Tailscale IP)
    MANAGEMENT_GRPC_PORT   (default: 50051)
    MGMT_GRPC_TLS_ENABLED  (default: 0) — mTLS 켤 때 1
    MGMT_TLS_CA_CRT / CLIENT_CRT / CLIENT_KEY — mTLS 경로

실행:
    python3 publisher.py
종료:
    SIGTERM 또는 Ctrl+C
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time
from datetime import UTC, datetime

import cv2  # opencv-python (Jetson: apt install python3-opencv)
import grpc
from generated import management_pb2 as pb, management_pb2_grpc as pb_grpc

logging.basicConfig(
    level=os.environ.get("JETSON_LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("jetson.publisher")

SHUTDOWN = threading.Event()


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _build_channel() -> grpc.Channel:
    host = os.environ.get("MANAGEMENT_GRPC_HOST", "127.0.0.1")
    port = _env_int("MANAGEMENT_GRPC_PORT", 50051)
    target = f"{host}:{port}"
    tls = os.environ.get("MGMT_GRPC_TLS_ENABLED", "0") == "1"
    # keep-alive — 서버 재시작·Tailscale 끊김을 빠르게 감지해 재연결 트리거
    keepalive = [
        ("grpc.keepalive_time_ms", 30000),
        ("grpc.keepalive_timeout_ms", 10000),
        ("grpc.keepalive_permit_without_calls", 1),
        ("grpc.http2.max_pings_without_data", 0),
    ]
    if not tls:
        log.info("connecting %s (insecure)", target)
        return grpc.insecure_channel(target, options=keepalive)
    ca = open(os.environ["MGMT_TLS_CA_CRT"], "rb").read()
    crt = open(os.environ["MGMT_TLS_CLIENT_CRT"], "rb").read()
    key = open(os.environ["MGMT_TLS_CLIENT_KEY"], "rb").read()
    creds = grpc.ssl_channel_credentials(
        root_certificates=ca, private_key=key, certificate_chain=crt
    )
    log.info("connecting %s (mTLS)", target)
    return grpc.secure_channel(target, creds, options=keepalive)


def _open_camera() -> cv2.VideoCapture:
    idx = _env_int("JETSON_CAMERA_INDEX", 0)
    w = _env_int("JETSON_FRAME_WIDTH", 1280)
    h = _env_int("JETSON_FRAME_HEIGHT", 720)
    cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
    if not cap.isOpened():
        log.warning("V4L2 open failed, retrying default backend")
        cap = cv2.VideoCapture(idx)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera index {idx}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    log.info("camera %d opened %dx%d", idx, w, h)
    return cap


def _frame_iter(cap: cv2.VideoCapture, camera_id: str):
    """OpenCV 프레임을 JPEG ImageFrame 으로 변환하는 generator."""
    fps = max(1, _env_int("JETSON_FPS", 2))
    quality = _env_int("JETSON_JPEG_QUALITY", 85)
    period = 1.0 / fps
    seq = 0
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    while not SHUTDOWN.is_set():
        t0 = time.monotonic()
        ok, frame = cap.read()
        if not ok or frame is None:
            log.warning("frame read failed seq=%d", seq)
            time.sleep(0.1)
            continue
        h, w = frame.shape[:2]
        ok2, buf = cv2.imencode(".jpg", frame, encode_params)
        if not ok2:
            log.warning("jpeg encode failed seq=%d", seq)
            continue
        seq += 1
        yield pb.ImageFrame(
            camera_id=camera_id,
            captured_at=pb.Timestamp(iso8601=datetime.now(UTC).isoformat()),
            encoding="jpeg",
            width=w,
            height=h,
            data=buf.tobytes(),
            sequence=seq,
        )
        elapsed = time.monotonic() - t0
        if elapsed < period:
            SHUTDOWN.wait(period - elapsed)


def run_once() -> int:
    """단일 연결 수명 주기. 실패 시 상위 루프가 재연결."""
    camera_id = os.environ.get("JETSON_CAMERA_ID", "CAM-INSP-01")
    channel = _build_channel()
    stub = pb_grpc.ImagePublisherServiceStub(channel)
    cap = _open_camera()
    try:
        ack = stub.PublishFrames(_frame_iter(cap, camera_id))
        log.info(
            "stream closed by server: accepted=%s seq=%d msg=%s",
            ack.accepted,
            ack.sequence,
            ack.message,
        )
        return 0
    except grpc.RpcError as e:
        log.warning("grpc error: %s %s", e.code(), e.details())
        return 1
    finally:
        cap.release()
        channel.close()


def _install_signal_handlers() -> None:
    def _handler(signum, _frame):
        log.info("signal %s received, shutting down", signum)
        SHUTDOWN.set()

    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(s, _handler)


def main() -> int:
    _install_signal_handlers()
    # ESP32 Serial bridge (opt-in via ESP_BRIDGE_ENABLED=1)
    bridge = None
    if os.environ.get("ESP_BRIDGE_ENABLED", "0") in ("1", "true", "yes"):
        try:
            from esp_bridge import EspBridge

            bridge = EspBridge.from_env(SHUTDOWN)
            bridge.start()
        except Exception:  # noqa: BLE001
            log.exception("ESP bridge 기동 실패")
    else:
        log.info("ESP_BRIDGE_ENABLED 미설정 — Serial bridge 비활성")

    # V6 canonical Phase D-2: Management → Jetson ConveyorCommand 구독
    if bridge is not None and os.environ.get("MGMT_COMMAND_STREAM_ENABLED", "0") in (
        "1",
        "true",
        "yes",
    ):
        try:
            from command_subscriber import CommandSubscriber

            CommandSubscriber.from_env(bridge, SHUTDOWN).start()
        except Exception:  # noqa: BLE001
            log.exception("CommandSubscriber 기동 실패")
    elif bridge is None:
        log.info(
            "ESP bridge 비활성 → CommandSubscriber 미기동 (둘 다 켜야 Serial relay 동작)",
        )
    else:
        log.info("MGMT_COMMAND_STREAM_ENABLED 미설정 — ConveyorCommand 구독 비활성")

    backoff = 1.0
    while not SHUTDOWN.is_set():
        rc = run_once()
        if rc == 0 or SHUTDOWN.is_set():
            break
        log.info("reconnecting in %.1fs", backoff)
        SHUTDOWN.wait(backoff)
        backoff = min(30.0, backoff * 2)
    log.info("bye")
    return 0


if __name__ == "__main__":
    sys.exit(main())
