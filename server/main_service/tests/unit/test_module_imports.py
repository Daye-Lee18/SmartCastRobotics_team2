from main_service.event_bridge import EventBridge
from main_service.main import Orchestrator
from main_service.monitor_agent import MonitorAgent
from main_service.robot_adapter import RobotAdapter
from main_service.state_manager import StateManager
from main_service.task_allocator import TaskAllocator
from main_service.task_executor import TaskExecutor
from main_service.task_manager import TaskManager
from main_service.traffic_manager import TrafficManager


def test_main_service_modules_are_importable():
    assert Orchestrator
    assert TaskManager
    assert TaskAllocator
    assert TaskExecutor
    assert RobotAdapter
    assert StateManager
    assert EventBridge
    assert TrafficManager
    assert MonitorAgent

