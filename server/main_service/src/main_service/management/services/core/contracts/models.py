"""Pydantic Models 정의 (Interface Contracts Guide 기준)."""
from typing import Optional, List
from pydantic import BaseModel

from .enums import EventType, EquipTaskType, TransTaskType, EquipStat, TransStat, OrdStat, TxnStat,TaskType

# =======================
# Event Payload Models
# =======================
class TaskCompletedEvent(BaseModel):
    task_id: str
    item_id: int
    task_type: str  # EquipTaskType or TransTaskType string
    status: str     # TxnStat string

class ItemStatusChangedEvent(BaseModel):
    item_id: int
    flow_stat: str
    zone_nm: Optional[str] = None

class TaskAssignedEvent(BaseModel):
    task_id: str
    robot_id: str
    item_id: int

# =======================
# Input / Output Models
# =======================
class CreateTaskInput(BaseModel):
    item_id: int
    flow_stat: Optional[str] = None
    zone_nm: Optional[str] = None

class TaskInfo(BaseModel):
    task_id: str
    task_type: str
    req_robot_type: str

class CreateTaskResult(BaseModel):
    success: bool
    tasks: List[TaskInfo] = []
    reason: Optional[str] = None

class AllocateTaskInput(BaseModel):
    task_id: str
    req_robot_type: str
    item_id: int
    zone_nm: Optional[str] = None
    task_type: Optional[str] = None

class AllocateTaskResult(BaseModel):
    success: bool
    robot_id: Optional[str] = None
    reason: Optional[str] = None

class ExecuteTaskInput(BaseModel):
    task_id: str
    robot_id: str
    item_id: int
    command: str
    payload: dict = {}

class ExecuteTaskResult(BaseModel):
    success: bool
    reason: Optional[str] = None


class StartProductionOrderAckModel(BaseModel):
    ord_id: int
    accepted: bool
    reason: Optional[str] = None
    item_id: Optional[int] = None
    equip_task_txn_id: Optional[int] = None


class StartProductionBatchAckModel(BaseModel):
    requested_count: int
    accepted_count: int
    rejected_count: int
    orders: List[StartProductionOrderAckModel] = []
    message: Optional[str] = None

##

class ItemStatusRecord(BaseModel): #ok -> tm
    item_id: int
    order_id: int  # 어느 주문에 속한 아이tuple인지 추적하기 위해 추가
    last_task_type: Optional[TaskType] = None
    flow_stat: Optional[str] = None
    is_defective: bool = False

class CreateTaskInput(BaseModel): #tm -> sm
    item_id: int
    task_type: TaskType
    rack_pos: Optional[str] = None
    txn_stat: str = "que"
    res_id : Optional[int] = None

class NextTaskResult(BaseModel): # tm -> ok
    item_id: int
    txn_id: int
    task_type: TaskType
    priority: int = 5
    rack_pos: Optional[str] = None