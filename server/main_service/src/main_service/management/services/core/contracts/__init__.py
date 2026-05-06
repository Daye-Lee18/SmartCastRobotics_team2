"""Contracts definitions (Models and Protocols)."""
from .models import (
    TaskCompletedEvent,
    ItemStatusChangedEvent,
    TaskAssignedEvent,
    CreateTaskInput,
    TaskInfo,
    CreateTaskResult,
    AllocateTaskInput,
    AllocateTaskResult,
    ExecuteTaskInput,
    ExecuteTaskResult,
)

from .protocols import (
    IEventBridge,
    IStateManager,
    ITaskManager,
    ITaskAllocator,
    IOrchestrator,
    ITaskExecutor,
    IAdapter,
)

__all__ = [
    "TaskCompletedEvent",
    "ItemStatusChangedEvent",
    "TaskAssignedEvent",
    "CreateTaskInput",
    "TaskInfo",
    "CreateTaskResult",
    "AllocateTaskInput",
    "AllocateTaskResult",
    "ExecuteTaskInput",
    "ExecuteTaskResult",
    "IEventBridge",
    "IStateManager",
    "ITaskManager",
    "ITaskAllocator",
    "IOrchestrator",
    "ITaskExecutor",
    "IAdapter",
]
