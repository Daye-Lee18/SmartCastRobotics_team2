"""Minimal in-memory StateManager stub for the refactor phase.

This module intentionally avoids any DB or ORM dependency. During the current
core-structure refactor, Management only needs to acknowledge StartProduction
requests and keep the rest of the pipeline dormant.
"""

from __future__ import annotations

import logging
from typing import Any

from .contracts.models import StartProductionOrderAckModel

logger = logging.getLogger(__name__)


class MockStateManager:
    """StateManager stub that only acknowledges production-start requests."""

    def __init__(self) -> None:
        self._items: dict[int, dict[str, Any]] = {}
        self._tasks: dict[str, dict[str, Any]] = {}
        self._next_item_id = 1000
        self._next_equip_task_txn_id = 2000
        logger.info("[MockStateManager] stub mode enabled")

    def start_production(self, ord_id: int) -> StartProductionOrderAckModel:
        """Accept a positive order id and return a deterministic mock ack."""
        logger.info("[MockStateManager] start_production called for ord_id=%s", ord_id)
        if ord_id <= 0:
            return StartProductionOrderAckModel(
                ord_id=ord_id,
                accepted=False,
                reason="Invalid Order ID (Mock)",
            )

        item_id = self._next_item_id
        equip_task_txn_id = self._next_equip_task_txn_id
        self._next_item_id += 1
        self._next_equip_task_txn_id += 1

        self._items[item_id] = {
            "item_id": item_id,
            "ord_id": ord_id,
            "cur_stat": "QUE",
            "cur_res": "RA1",
            "equip_task_type": "MM",
            "trans_task_type": None,
            "is_defective": None,
        }
        self._tasks[f"task_{equip_task_txn_id}"] = {
            "ord_id": ord_id,
            "item_id": item_id,
            "txn_id": equip_task_txn_id,
            "status": "QUE",
        }

        return StartProductionOrderAckModel(
            ord_id=ord_id,
            accepted=True,
            reason="Accepted by MockStateManager.",
            item_id=item_id,
            equip_task_txn_id=equip_task_txn_id,
        )

    def create_order_with_items(self, ord_id: int, qty: int) -> list[int]:
        item_ids: list[int] = []
        for _ in range(max(qty, 0)):
            item_id = self._next_item_id
            self._next_item_id += 1
            self._items[item_id] = {
                "item_id": item_id,
                "ord_id": ord_id,
                "status": "CREATED",
            }
            item_ids.append(item_id)
        return item_ids

    def find_ship_ready_item_ids(
        self,
        ord_id: int | None = None,
        item_ids: list[int] | None = None,
    ) -> list[int]:
        if item_ids is not None:
            return item_ids
        if ord_id is None:
            return []
        return [
            item_id
            for item_id, item in self._items.items()
            if item.get("ord_id") == ord_id
        ]

    def get_item(self, item_id: int) -> dict[str, Any]:
        return self._items.get(item_id, {"item_id": item_id, "status": "MOCK_STATUS"})

    def add_task(self, task: dict[str, Any]) -> str:
        task_id = f"task_{len(self._tasks) + 1}"
        self._tasks[task_id] = dict(task)
        return task_id

    def find_available_robot(self, robot_type: str, task_type: str | None = None) -> str | None:
        return "robot_1"

    def get_robot_available_for_item(self, robot_id: str, item_id: int | None = None) -> bool:
        return True

    def assign_task_robot(self, task_id: str, robot_id: str, is_trans: bool) -> None:
        logger.info("[MockStateManager] assign_task_robot: task=%s robot=%s", task_id, robot_id)

    def update_task_status(self, task_id: str, status: str, is_trans: bool) -> None:
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = status
        logger.info("[MockStateManager] update_task_status: task=%s status=%s", task_id, status)

    def mark_task_started(self, task_id: str, robot_id: str, is_trans: bool) -> None:
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "PROC"
            self._tasks[task_id]["robot_id"] = robot_id
        logger.info("[MockStateManager] mark_task_started: task=%s robot=%s", task_id, robot_id)

    def update_item_status(
        self,
        item_id: int,
        cur_stat: str | None = None,
        equip_task_type: str | None = None,
        trans_task_type: str | None = None,
    ) -> None:
        item = self._items.setdefault(item_id, {"item_id": item_id})
        if cur_stat is not None:
            item["cur_stat"] = cur_stat
        if equip_task_type is not None:
            item["equip_task_type"] = equip_task_type
        if trans_task_type is not None:
            item["trans_task_type"] = trans_task_type
        logger.info("[MockStateManager] update_item_status: item=%s cur_stat=%s", item_id, cur_stat)

    def update_robot_status_memory(self, robot_id: str, x: float, y: float, battery_pct: int) -> None:
        logger.debug(
            "[MockStateManager] update_robot_status_memory: robot=%s x=%s y=%s battery=%s",
            robot_id,
            x,
            y,
            battery_pct,
        )

    def update_amr_runtime_memory(
        self,
        robot_id: str,
        *,
        x: float | None = None,
        y: float | None = None,
        battery_pct: int | None = None,
    ) -> None:
        logger.debug(
            "[MockStateManager] update_amr_runtime_memory: robot=%s x=%s y=%s battery=%s",
            robot_id,
            x,
            y,
            battery_pct,
        )

    def update_robot_task_state(self, task_id: str, robot_id: str, cur_stat: str) -> None:
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = cur_stat
            self._tasks[task_id]["robot_id"] = robot_id
        logger.info(
            "[MockStateManager] update_robot_task_state: task=%s robot=%s cur_stat=%s",
            task_id,
            robot_id,
            cur_stat,
        )
