"""Traffic and route-planning RPC methods."""

from __future__ import annotations

import management_pb2  # type: ignore


class TrafficRpcMixin:
    """Traffic manager RPCs."""

    def PlanRoute(self, request, context):
        plan = self.traffic_manager.plan_with_yield(
            robot_id=request.robot_id,
            priority=5,
            start=(request.start.x, request.start.y),
            goal=(request.goal.x, request.goal.y),
        )
        proto_points = [
            management_pb2.RoutePoint(x=x, y=y, waypoint_id=wid) for (x, y, wid) in plan.points
        ]
        return management_pb2.PlanRouteResponse(
            path=proto_points,
            reserved_edges=plan.reserved_edges,
            estimated_duration_sec=plan.duration_sec,
        )

