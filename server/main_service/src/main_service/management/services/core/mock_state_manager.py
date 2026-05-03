"""Minimal in-memory StateManager stub for the refactor phase.

This module intentionally avoids any DB or ORM dependency. During the current
core-structure refactor, Management only needs to acknowledge StartProduction
requests and keep the rest of the pipeline dormant.
"""

from __future__ import annotations

from datetime import datetime
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
        self._db_ready = False
        self._session_factory = None
        self._ord_model = None
        self._ord_stat_model = None
        self._ord_log_model = None
        self._pattern_model = None
        self._item_model = None
        self._equip_task_txn_model = None
        try:
            from db_session import SessionLocal
            from smart_cast_db.models import EquipTaskTxn, ItemStat, Ord, OrdLog, OrdStat, Pattern

            self._session_factory = SessionLocal
            self._ord_model = Ord
            self._ord_stat_model = OrdStat
            self._ord_log_model = OrdLog
            self._pattern_model = Pattern
            self._item_model = ItemStat
            self._equip_task_txn_model = EquipTaskTxn
            self._db_ready = True
            logger.info("[MockStateManager] DB-backed start_production enabled")
        except Exception as exc:
            logger.warning("[MockStateManager] DB-backed start_production unavailable: %s", exc)
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

        if self._db_ready:
            return self._start_production_db(ord_id)

        item_id = self._next_item_id
        equip_task_txn_id = self._next_equip_task_txn_id
        self._next_item_id += 1
        self._next_equip_task_txn_id += 1

        self._items[item_id] = {
            "item_id": item_id,
            "ord_id": ord_id,
            "flow_stat": "CREATED",
            "zone_nm": None,
            "result": None,
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

    def _start_production_db(self, ord_id: int) -> StartProductionOrderAckModel:
        if (
            self._session_factory is None
            or self._ord_model is None
            or self._ord_stat_model is None
            or self._ord_log_model is None
            or self._pattern_model is None
            or self._item_model is None
            or self._equip_task_txn_model is None
        ):
            return StartProductionOrderAckModel(
                ord_id=ord_id,
                accepted=False,
                reason="DB-backed start_production is not fully initialized.",
            )

        with self._session_factory() as db:
            ord_obj = db.get(self._ord_model, ord_id)
            if ord_obj is None:
                return StartProductionOrderAckModel(
                    ord_id=ord_id,
                    accepted=False,
                    reason=f"ord_id={ord_id} not found",
                )
            if db.get(self._pattern_model, ord_id) is None:
                return StartProductionOrderAckModel(
                    ord_id=ord_id,
                    accepted=False,
                    reason=f"pattern for ord_id={ord_id} not registered",
                )

            existing_item = db.query(self._item_model).filter(self._item_model.ord_id == ord_id).first()
            existing_txn = (
                db.query(self._equip_task_txn_model)
                .join(self._item_model, self._item_model.item_stat_id == self._equip_task_txn_model.item_id)
                .filter(self._item_model.ord_id == ord_id)
                .first()
            )
            if existing_item is not None or existing_txn is not None:
                return StartProductionOrderAckModel(
                    ord_id=ord_id,
                    accepted=False,
                    reason=f"ord_id={ord_id} already started on line",
                    item_id=getattr(existing_item, "item_stat_id", None),
                    equip_task_txn_id=getattr(existing_txn, "txn_id", None),
                )

            stat = db.query(self._ord_stat_model).filter(self._ord_stat_model.ord_id == ord_id).first()
            prev_stat = stat.ord_stat if stat is not None else None
            if stat is None:
                stat = self._ord_stat_model(ord_id=ord_id, ord_stat="MFG")
                db.add(stat)
            else:
                stat.ord_stat = "MFG"
                stat.updated_at = datetime.utcnow()
            if prev_stat != "MFG":
                db.add(
                    self._ord_log_model(
                        ord_id=ord_id,
                        prev_stat=prev_stat,
                        new_stat="MFG",
                        changed_by=None,
                    )
                )

            new_item = self._item_model(
                ord_id=ord_id,
                cur_stat="CREATED",
                cur_res="PAT",
                is_defective=None,
            )
            db.add(new_item)
            db.flush()

            txn = self._equip_task_txn_model(
                res_id="PAT",
                task_type="MM",
                txn_stat="QUE",
                item_id=new_item.item_id,
            )
            db.add(txn)
            db.commit()
            db.refresh(new_item)
            db.refresh(txn)

            self._items[new_item.item_id] = {
                "item_id": new_item.item_id,
                "ord_id": ord_id,
                "flow_stat": new_item.flow_stat,
                "zone_nm": new_item.zone_nm,
                "result": new_item.result,
            }
            self._tasks[f"task_{txn.txn_id}"] = {
                "ord_id": ord_id,
                "item_id": new_item.item_id,
                "txn_id": txn.txn_id,
                "status": txn.txn_stat,
                "res_id": txn.res_id,
            }

            return StartProductionOrderAckModel(
                ord_id=ord_id,
                accepted=True,
                reason="Production started: item and equip_task_txn created.",
                item_id=new_item.item_id,
                equip_task_txn_id=txn.txn_id,
            )

    def create_order_with_items(self, ord_id: int, qty: int) -> list[int]:
        item_ids: list[int] = []
        for _ in range(max(qty, 0)):
            item_id = self._next_item_id
            self._next_item_id += 1
            self._items[item_id] = {
                "item_id": item_id,
                "ord_id": ord_id,
                "flow_stat": "CREATED",
                "zone_nm": None,
                "result": None,
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
        item = dict(self._items.get(item_id, {"item_id": item_id, "flow_stat": "HOLD"}))
        flow_stat = item.get("flow_stat")
        zone_nm = item.get("zone_nm")
        result = item.get("result")
        item.setdefault("cur_stat", flow_stat)
        item.setdefault("cur_res", zone_nm)
        item.setdefault("is_defective", None if result is None else (not result))
        return item

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
        flow_stat: str | None = None,
        zone_nm: str | None = None,
        result: bool | None = None,
    ) -> None:
        item = self._items.setdefault(item_id, {"item_id": item_id})
        if flow_stat is not None:
            item["flow_stat"] = flow_stat
        if zone_nm is not None:
            item["zone_nm"] = zone_nm
        if result is not None:
            item["result"] = result
        logger.info(
            "[MockStateManager] update_item_status: item=%s flow_stat=%s zone_nm=%s",
            item_id,
            flow_stat,
            zone_nm,
        )

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
