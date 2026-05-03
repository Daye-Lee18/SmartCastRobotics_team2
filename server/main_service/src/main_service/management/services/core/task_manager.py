"""Canonical TaskManager entrypoint for Management production queue writes.

This module exposes the currently supported smartcast v2 production-start
behavior from the legacy implementation under the stable `services.core`
import path. The orchestrator and RPC layer should depend on this module,
not the legacy path directly.
"""

from __future__ import annotations

from services.legacy.task_manager import (
    StartProductionResult,
    TaskManager as LegacyTaskManager,
    TaskManagerError,
)


class TaskManager(LegacyTaskManager):
    """Stable TaskManager facade used by the orchestrator and RPC layer."""

