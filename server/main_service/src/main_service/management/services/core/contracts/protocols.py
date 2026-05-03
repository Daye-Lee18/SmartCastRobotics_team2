from typing import Protocol, Dict, Any, List
from pydantic import BaseModel

from .enums import EventType
from .models import (
    CreateTaskInput, CreateTaskResult,
    AllocateTaskInput, AllocateTaskResult,
    ExecuteTaskInput, ExecuteTaskResult,
    StartProductionOrderAckModel,
    StartProductionBatchAckModel,
)

class IOrchestrator(Protocol):
    async def start_production(self, ord_id: int, qty: int) -> List[int]:
        ...

    async def on_ship(self, ord_id: int | None = None, item_ids: List[int] | None = None) -> List[int]:
        ...

class ITaskManager(Protocol):
    def create_next_tasks(self, input_data: CreateTaskInput) -> CreateTaskResult:
        ...

class ITaskAllocator(Protocol):
    def allocate(self, input_data: AllocateTaskInput) -> AllocateTaskResult:
        ...

class ITaskExecutor(Protocol):
    async def execute(self, input_data: ExecuteTaskInput) -> ExecuteTaskResult:
        ...

class IAdapter(Protocol):
    async def send_task(self, robot_id: str, task_type: str, payload: Dict[str, Any]) -> bool:
        ...

class IStateManager(Protocol):
    def start_production(self, ord_id: int) -> StartProductionOrderAckModel:
        ...

    def create_order_with_items(self, ord_id: int, qty: int) -> List[int]:
        ...

    def find_ship_ready_item_ids(self, ord_id: int | None = None, item_ids: List[int] | None = None) -> List[int]:
        ...

    def get_item(self, item_id: int) -> Dict[str, Any]:
        ...
        
    def add_task(self, task: Dict[str, Any]) -> str:
        ...
        
    def find_available_robot(self, robot_type: str, task_type: str | None = None) -> str | None:
        ...

    def get_robot_available_for_item(self, robot_id: str, item_id: int | None = None) -> bool:
        ...
        
    def assign_task_robot(self, task_id: str, robot_id: str, is_trans: bool) -> None:
        ...
        
    def update_task_status(self, task_id: str, status: str, is_trans: bool) -> None:
        ...

    def mark_task_started(self, task_id: str, robot_id: str, is_trans: bool) -> None:
        ...
        
    def update_item_status(
        self,
        item_id: int,
        flow_stat: str | None = None,
        zone_nm: str | None = None,
        result: bool | None = None,
    ) -> None:
        ...
        
    def update_robot_status_memory(self, robot_id: str, x: float, y: float, battery_pct: int) -> None:
        ...

    def update_amr_runtime_memory(
        self,
        robot_id: str,
        *,
        x: float | None = None,
        y: float | None = None,
        battery_pct: int | None = None,
    ) -> None:
        ...

    def update_robot_task_state(self, task_id: str, robot_id: str, cur_stat: str) -> None:
        ...

class IEventBridge(Protocol):
    def subscribe(self, event_type: EventType, handler) -> None:
        ...
        
    def publish(self, event_type: EventType, payload: BaseModel) -> None:
        ...
