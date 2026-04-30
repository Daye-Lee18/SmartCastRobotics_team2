"""Robot status and state-transition RPC methods."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import management_pb2  # type: ignore

logger = logging.getLogger(__name__)


class RobotRpcMixin:
    """AMR status and state-machine RPCs."""

    def GetRobotStatus(self, request, context):
        entries = []
        for s in self.amr_battery.get_all():
            ctx = self.amr_state_machine.get(s.id)
            entries.append(
                management_pb2.RobotStatusEntry(
                    id=s.id,
                    type=management_pb2.ROBOT_TYPE_AMR,
                    host=s.host,
                    status=s.status,
                    battery=s.battery,
                    voltage=s.voltage,
                    location=s.location,
                    task_state=ctx.state.value,
                    task_id=ctx.task_id,
                    loaded_item=ctx.loaded_item,
                )
            )
        return management_pb2.GetRobotStatusResponse(robots=entries)

    def TransitionAmrState(self, request, context):
        from services.core.amr_state_machine import TaskState

        try:
            new_state = TaskState(request.new_state)
        except ValueError:
            return management_pb2.TransitionAmrStateResponse(
                accepted=False,
                reason=f"invalid_state: {request.new_state}",
            )
        prev_state = self.amr_state_machine.get(request.robot_id).state
        ok = self.amr_state_machine.transition(
            robot_id=request.robot_id,
            new_state=new_state,
            task_id=request.task_id or None,
            loaded_item=request.loaded_item or None,
        )
        if ok:
            if prev_state == TaskState.FAILED and new_state == TaskState.IDLE:
                self._sync_repair_to_db(request.robot_id)
            return management_pb2.TransitionAmrStateResponse(
                accepted=True,
                reason=f"{request.robot_id} -> {new_state.name}",
            )
        ctx = self.amr_state_machine.get(request.robot_id)
        return management_pb2.TransitionAmrStateResponse(
            accepted=False,
            reason=f"invalid_transition: {ctx.state.name} -> {new_state.name}",
        )

    def _sync_repair_to_db(self, robot_id: str) -> None:
        """Sync repaired AMR state back to failed transport tasks."""
        from smart_cast_db.database import SessionLocal
        from smart_cast_db.models import TransportTask

        now = datetime.now(UTC)
        db = SessionLocal()
        try:
            failed_tasks = (
                db.query(TransportTask)
                .filter(
                    TransportTask.assigned_robot_id == robot_id,
                    TransportTask.status == "failed",
                )
                .all()
            )
            for task in failed_tasks:
                task.status = "completed"
                task.completed_at = now.isoformat()
            db.commit()
            if failed_tasks:
                logger.info(
                    "수리 완료 DB 동기화: %s 실패 작업 %d건 -> completed",
                    robot_id,
                    len(failed_tasks),
                )
        except Exception:
            logger.exception("수리 완료 DB 업데이트 실패: %s", robot_id)
            db.rollback()
        finally:
            db.close()

