"""ImageForwarder 단위 테스트 (sink/uploader 가짜)."""

from __future__ import annotations

from pathlib import Path

import pytest
from services.image_forwarder import ForwarderConfig, ImageForwarder


class FakeSink:
    def __init__(self) -> None:
        self._frames: dict[str, dict] = {}

    def set(
        self,
        camera_id: str,
        data: bytes = b"\xff\xd8\xff jpeg",
        seq: int = 1,
        captured_at: str = "2026-04-15T10:00:00+00:00",
    ) -> None:
        self._frames[camera_id] = {
            "encoding": "jpeg",
            "width": 640,
            "height": 480,
            "size": len(data),
            "sequence": seq,
            "captured_at": captured_at,
            "received_at": captured_at,
            "data": data,
        }

    def latest(self, camera_id: str) -> dict | None:
        return self._frames.get(camera_id)


class FakeUploader:
    def __init__(self, enabled: bool = True, fail: bool = False) -> None:
        self.enabled = enabled
        self.fail = fail
        self.uploads: list[tuple[str, str, str]] = []

    def upload_image(self, local_path, remote_subdir, remote_filename):
        if self.fail:
            raise RuntimeError("upload boom")
        self.uploads.append((str(local_path), remote_subdir, remote_filename))
        return f"/remote/{remote_subdir}/{remote_filename}"


def _cfg(tmp: Path, spool_max: int = 100) -> ForwarderConfig:
    return ForwarderConfig(
        spool_dir=tmp,
        batch_interval_sec=60.0,
        batch_max_files=10,
        spool_max_files=spool_max,
    )


def test_snapshot_writes_jpeg_and_meta(tmp_path: Path) -> None:
    sink = FakeSink()
    sink.set("CAM-INSP-01")
    fwd = ImageForwarder(_cfg(tmp_path), sink.latest, FakeUploader())
    out = fwd.snapshot(item_id=42, stage="IP", camera_id="CAM-INSP-01")
    assert out is not None and out.exists()
    assert out.with_suffix(".json").exists()
    assert fwd.stats()["snapshot"] == 1


def test_snapshot_no_frame_returns_none(tmp_path: Path) -> None:
    fwd = ImageForwarder(_cfg(tmp_path), FakeSink().latest, FakeUploader())
    assert fwd.snapshot(1, "IP", "CAM-X") is None
    assert fwd.stats()["snapshot"] == 0


def test_snapshot_non_jpeg_skipped(tmp_path: Path) -> None:
    class RawSink:
        def latest(self, _):
            return {"encoding": "raw_rgb", "data": b"x", "size": 1}

    fwd = ImageForwarder(_cfg(tmp_path), RawSink().latest, FakeUploader())
    assert fwd.snapshot(1, "IP", "C") is None


def test_flush_uploads_and_deletes(tmp_path: Path) -> None:
    sink = FakeSink()
    sink.set("CAM-INSP-01")
    up = FakeUploader()
    fwd = ImageForwarder(_cfg(tmp_path), sink.latest, up)
    fwd.snapshot(1, "IP", "CAM-INSP-01")
    fwd.snapshot(2, "IP", "CAM-INSP-01")
    assert fwd.flush() == 2
    assert len(up.uploads) == 2
    assert not list(tmp_path.glob("*.jpg"))
    assert not list(tmp_path.glob("*.json"))
    assert fwd.stats()["uploaded"] == 2


def test_flush_uploader_disabled(tmp_path: Path) -> None:
    sink = FakeSink()
    sink.set("C")
    fwd = ImageForwarder(_cfg(tmp_path), sink.latest, FakeUploader(enabled=False))
    fwd.snapshot(1, "IP", "C")
    assert fwd.flush() == 0
    # 파일은 스풀에 남음
    assert list(tmp_path.glob("*.jpg"))


def test_flush_failure_keeps_file(tmp_path: Path) -> None:
    sink = FakeSink()
    sink.set("C")
    fwd = ImageForwarder(_cfg(tmp_path), sink.latest, FakeUploader(fail=True))
    fwd.snapshot(1, "IP", "C")
    assert fwd.flush() == 0
    assert list(tmp_path.glob("*.jpg"))  # 다음 배치 재시도
    assert fwd.stats()["failed"] == 1


def test_spool_limit_drops_oldest(tmp_path: Path) -> None:
    sink = FakeSink()
    cfg = _cfg(tmp_path, spool_max=2)
    fwd = ImageForwarder(cfg, sink.latest, FakeUploader())
    for i in range(4):
        sink.set("C", seq=i, captured_at=f"2026-04-15T10:00:0{i}+00:00")
        fwd.snapshot(i, "IP", "C")
    # 스풀에 2개만 남아야 함
    assert len(list(tmp_path.glob("*.jpg"))) <= 2
    assert fwd.stats()["dropped"] >= 1


def test_config_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MGMT_IMAGE_SPOOL_DIR", str(tmp_path))
    monkeypatch.setenv("MGMT_IMAGE_BATCH_SEC", "15")
    monkeypatch.setenv("MGMT_IMAGE_BATCH_MAX", "25")
    cfg = ForwarderConfig.from_env()
    assert cfg.spool_dir == tmp_path
    assert cfg.batch_interval_sec == 15.0
    assert cfg.batch_max_files == 25
