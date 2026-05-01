"""Robot status RPC methods with telemetry-first behavior."""

from __future__ import annotations

import logging

import management_pb2  # type: ignore

logger = logging.getLogger(__name__)


class RobotRpcMixin:
    """AMR telemetry/status RPCs."""

    def GetRobotStatus(self, request, context):
        entries = []
        for s in self.amr_battery.get_all():
            entries.append(
                management_pb2.RobotStatusEntry(
                    id=s.id,
                    type=management_pb2.ROBOT_TYPE_AMR,
                    host=s.host,
                    status=s.status,
                    battery=s.battery,
                    voltage=s.voltage,
                    location=s.location,
                    task_state=int(getattr(s, "task_state", 1) or 1),
                    task_id=getattr(s, "task_id", "") or "",
                    loaded_item=getattr(s, "loaded_item", "") or "",
                )
            )
        return management_pb2.GetRobotStatusResponse(robots=entries)

    def TransitionAmrState(self, request, context):
        logger.info(
            "TransitionAmrState ignored in telemetry-only mode: robot=%s new_state=%s",
            request.robot_id,
            request.new_state,
        )
        return management_pb2.TransitionAmrStateResponse(
            accepted=False,
            reason="deprecated: telemetry_only_mode",
        )
