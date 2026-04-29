"""AIServerConfig / AIUploader 테스트 (paramiko 의존 없음)."""

from __future__ import annotations

import pytest
from services.adapters.vision.ai_client import AIServerConfig, AIUploader


def test_config_disabled_when_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ("MGMT_AI_HOST", "MGMT_AI_USER", "MGMT_AI_PASS", "MGMT_AI_SSH_KEY"):
        monkeypatch.delenv(k, raising=False)
    cfg = AIServerConfig.from_env()
    assert cfg.enabled is False
    assert AIUploader(cfg).enabled is False


def test_config_enabled_with_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MGMT_AI_HOST", "100.66.177.119")
    monkeypatch.setenv("MGMT_AI_USER", "team2")
    monkeypatch.setenv("MGMT_AI_PASS", "secret")
    monkeypatch.delenv("MGMT_AI_SSH_KEY", raising=False)
    cfg = AIServerConfig.from_env()
    assert cfg.enabled is True
    assert cfg.host == "100.66.177.119"
    assert cfg.user == "team2"
    assert cfg.port == 22


def test_config_enabled_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MGMT_AI_HOST", "10.0.0.1")
    monkeypatch.setenv("MGMT_AI_USER", "team2")
    monkeypatch.setenv("MGMT_AI_SSH_KEY", "/tmp/id_ed25519")
    monkeypatch.delenv("MGMT_AI_PASS", raising=False)
    cfg = AIServerConfig.from_env()
    assert cfg.enabled is True
    assert cfg.key_path == "/tmp/id_ed25519"


def test_config_requires_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    """host+user 만 있고 pass/key 모두 없으면 비활성."""
    monkeypatch.setenv("MGMT_AI_HOST", "x")
    monkeypatch.setenv("MGMT_AI_USER", "y")
    monkeypatch.delenv("MGMT_AI_PASS", raising=False)
    monkeypatch.delenv("MGMT_AI_SSH_KEY", raising=False)
    assert AIServerConfig.from_env().enabled is False


def test_upload_raises_when_disabled(tmp_path) -> None:
    f = tmp_path / "a.jpg"
    f.write_bytes(b"x")
    uploader = AIUploader(AIServerConfig(host="", user="", enabled=False))
    with pytest.raises(RuntimeError, match="비활성화"):
        uploader.upload_image(f)


def test_health_check_disabled_returns_false() -> None:
    uploader = AIUploader(AIServerConfig(host="", user="", enabled=False))
    assert uploader.health_check() is False
