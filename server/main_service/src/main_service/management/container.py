import logging
import os

from services.adapters.sensors.rfid_service import RfidService
from services.adapters.robotics.amr_battery import AmrBatteryService

from services.core.legacy.execution_monitor import ExecutionMonitor
from services.core.legacy.core.robot_executor import RobotExecutor
from services.core.task_allocator import TaskAllocator
from services.core.task_manager import TaskManager
from services.core.traffic_manager import TrafficManager
from services.core.orchestrator import Orchestrator
from services.core.event_bridge import EventBridge
from services.core.mock_state_manager import MockStateManager

from services.adapters.vision.ai_client import AIServerConfig, AIUploader
from services.adapters.vision.image_forwarder import ForwarderConfig, ImageForwarder
from services.adapters.vision.image_sink import sink as image_sink

logger = logging.getLogger(__name__)

def _build_image_forwarder():
    """ImageForwarder 를 구성. AI Server 설정이 없으면 None 반환 → 훅 비활성."""
    ai_cfg = AIServerConfig.from_env()
    if not ai_cfg.enabled:
        logger.info("image_forwarder 비활성: AI Server 환경변수 미설정")
        return None
    fwd = ImageForwarder(
        config=ForwarderConfig.from_env(),
        sink_latest=image_sink.latest,
        uploader=AIUploader(ai_cfg),
    )
    fwd.start()
    logger.info(
        "image_forwarder 활성: spool=%s batch=%.1fs", fwd.cfg.spool_dir, fwd.cfg.batch_interval_sec
    )
    return fwd

class Container:
    """Dependency Injection Container

    모든 Adapter와 Core 비즈니스 로직을 여기서 생성하고 서로 주입(연결)합니다.
    server.py 에서는 이 container 인스턴스만 import 해서 사용합니다.
    """
    def __init__(self):
        logger.info("Initializing Dependency Container...")
        
        # 1. Base Core Managers
        self.task_manager = TaskManager()
        self.rfid_service = RfidService()
        self.task_allocator = TaskAllocator()
        self.traffic_manager = TrafficManager()

        # 2. Event-Driven Core
        self.event_bridge = EventBridge()
        self.state_manager = MockStateManager()
        self.orchestrator = Orchestrator(
            event_bridge=self.event_bridge,
            task_manager=self.task_manager,
            task_allocator=self.task_allocator,
            state_manager=self.state_manager,
        )

        # 3. Vision / Monitor Adapters
        self.image_forwarder = _build_image_forwarder()
        self.execution_monitor = ExecutionMonitor(
            image_forwarder=self.image_forwarder,
        )

        # 4. Robotics Adapters
        self.amr_battery = AmrBatteryService()
        self.amr_battery.start()

        self.robot_executor = RobotExecutor()

# Singleton Container Instance
container = Container()
