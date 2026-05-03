"""Refactor smoke tests for management services package wiring.

폴더 구조 리팩토링 시 가장 먼저 깨지는 import 경로와 얕은 객체 wiring 을
빠르게 검출하기 위한 안전망이다.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "services.adapters.vision.ai_client",
        "services.adapters.robotics.amr_battery",
        "services.core.command_queue",
        "services.core.event_bridge",
        "services.core.execution_monitor",
        "services.core.legacy.handoff_pipeline",
        "services.adapters.vision.image_forwarder",
        "services.adapters.vision.image_sink",
        "services.adapters.sensors.rfid_service",
        "services.core.robot_executor",
        "services.adapters.robotics.ros2_publisher",
        "services.core.task_allocator",
        "services.core.task_manager",
        "services.core.traffic_manager",
        "services.adapters",
        "services.adapters.jetcobot_adapter",
        "services.adapters.jetson_relay_adapter",
        "services.adapters.ros2_adapter",
        "rpc.field_event_rpc",
        "rpc.hardware_rpc",
        "rpc.monitor_rpc",
        "rpc.production_rpc",
        "rpc.robot_rpc",
        "rpc.task_rpc",
        "rpc.traffic_rpc",
    ],
)
def test_management_modules_remain_importable(module_name: str) -> None:
    module = importlib.import_module(module_name)
    assert module is not None


def test_task_manager_constructs() -> None:
    from services.core.task_manager import TaskManager

    manager = TaskManager()
    assert isinstance(manager, TaskManager)


def test_robot_executor_constructs_without_real_ros2(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.core.robot_executor import RobotExecutor

    monkeypatch.setenv("MGMT_ROS2_ENABLED", "0")
    executor = RobotExecutor()
    try:
        assert isinstance(executor, RobotExecutor)
    finally:
        executor.close()


def test_server_module_remains_importable(monkeypatch: pytest.MonkeyPatch) -> None:
    # server import 시 image forwarder 가 실환경 의존 초기화를 하지 않도록 차단.
    monkeypatch.delenv("AI_SERVER_HOST", raising=False)
    monkeypatch.delenv("MGMT_AI_HOST", raising=False)
    module = importlib.import_module("server")
    assert hasattr(module, "ManagementServicer")
