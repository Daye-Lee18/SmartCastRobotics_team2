"""Task allocation and command execution RPC methods."""

from __future__ import annotations

import management_pb2  # type: ignore


class TaskRpcMixin:
    """Task allocator and robot executor RPCs."""

    def AllocateItem(self, request, context):
        result = self.task_allocator.allocate(request.item_id)
        return management_pb2.AllocateResponse(
            item_id=request.item_id,
            chosen_robot_id=result.robot_id,
            score=result.score,
            rationale=result.rationale,
        )

    def ExecuteCommand(self, request, context):
        accepted, reason = self.robot_executor.dispatch(
            item_id=request.item_id,
            robot_id=request.robot_id,
            command=request.command,
            payload=request.payload,
        )
        return management_pb2.ExecuteCommandResponse(accepted=accepted, reason=reason)

