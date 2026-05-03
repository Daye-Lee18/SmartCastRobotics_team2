"""Pydantic Models 정의 (Interface Contracts Guide 기준)."""
from typing import Optional, List
from pydantic import BaseModel

from .enums import EventType, EquipTaskType, TransTaskType, EquipStat, TransStat, OrdStat, TxnStat

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
