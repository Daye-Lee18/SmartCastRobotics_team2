from __future__ import annotations

import heapq
import math
import threading
from collections import deque
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Iterable, Sequence
from uuid import uuid4


try:
    from services.core.contracts.enums import TransTaskType
except ModuleNotFoundError:
    # Standalone unit test fallback.
    # 실제 프로젝트에서는 services.core.contracts.enums.TransTaskType을 사용한다.
    class TransTaskType(str, Enum):
        ToPP = "ToPP"
        ToSTRG = "ToSTRG"
        ToSHIP = "ToSHIP"
        ToCHG = "ToCHG"
        ToCAST = "ToCAST"
        ToINSP = "ToINSP"


# ============================================================================
# ENUM
# ============================================================================

class TrafficDecisionType(str, Enum):
    GO = "GO"
    HOLD = "HOLD"


class ReservationStatus(str, Enum):
    GRANTED = "GRANTED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


class StepAction(str, Enum):
    MOVE = "MOVE"
    WAIT = "WAIT"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass(slots=True)
class NodePose:
    """Waypoint pose used by downstream adapters."""

    x: float
    y: float
    yaw: float = 0.0
    frame_id: str = "map"


@dataclass(slots=True)
class TrafficPathStep:
    """A single move or wait step that the executor can consume."""

    action: StepAction
    from_node: str
    to_node: str
    pose: NodePose | None = None

    start_slot: int = 0
    end_slot: int = 0

    reserved_start_at: float = 0.0
    reserved_end_at: float = 0.0

    edge: tuple[str, str] | None = None

    def __post_init__(self) -> None:
        if self.start_slot < 0:
            raise ValueError("start_slot must be >= 0")
        if self.end_slot < self.start_slot:
            raise ValueError("end_slot must be >= start_slot")


@dataclass(slots=True)
class RoutePermissionInput:
    """Request payload for route reservation."""

    trans_task_txn_id: int
    trans_id: str
    task_type: TransTaskType

    item_stat_id: int | None = None
    ord_id: int | None = None

    priority: int = 0
    loaded: bool = False
    current_node: str | None = None

    def __post_init__(self) -> None:
        if self.trans_task_txn_id <= 0:
            raise ValueError("trans_task_txn_id must be greater than 0")

        self.trans_id = self.trans_id.strip()
        if not self.trans_id:
            raise ValueError("trans_id cannot be blank")

        if self.priority < 0:
            raise ValueError("priority must be >= 0")

        if self.current_node is not None:
            self.current_node = self.current_node.strip()
            if not self.current_node:
                raise ValueError("current_node cannot be blank")

    @classmethod
    def from_trans_task_record(
        cls,
        record: Any,
        *,
        priority: int = 0,
        current_node: str | None = None,
    ) -> "RoutePermissionInput":
        """
        DB record / Pydantic record에서 Traffic Manager 입력으로 변환.

        record 필드 가정:
        - txn_id 또는 trans_task_txn_id
        - res_id 또는 trans_id
        - task_type
        - item_stat_id
        - ord_id
        """
        trans_task_txn_id = getattr(
            record,
            "txn_id",
            getattr(record, "trans_task_txn_id", None),
        )
        if trans_task_txn_id is None:
            raise ValueError("txn_id or trans_task_txn_id is required")

        trans_id = getattr(
            record,
            "res_id",
            getattr(record, "trans_id", None),
        )
        if trans_id is None:
            raise ValueError("res_id or trans_id is required for traffic planning")

        return cls(
            trans_task_txn_id=trans_task_txn_id,
            trans_id=trans_id,
            task_type=getattr(record, "task_type"),
            item_stat_id=getattr(record, "item_stat_id", None),
            ord_id=getattr(record, "ord_id", None),
            priority=priority,
            loaded=getattr(record, "item_stat_id", None) is not None,
            current_node=current_node,
        )


@dataclass(slots=True)
class TrafficDecision:
    """Decision returned by the traffic manager."""

    trans_task_txn_id: int
    trans_id: str
    decision: TrafficDecisionType

    route_nodes: list[str] = field(default_factory=list)
    path_steps: list[TrafficPathStep] = field(default_factory=list)

    reservation_id: str | None = None
    reason: str | None = None


@dataclass(slots=True)
class RouteReservation:
    """Active route reservation."""

    reservation_id: str
    trans_task_txn_id: int
    trans_id: str
    task_type: TransTaskType

    item_stat_id: int | None = None
    ord_id: int | None = None

    route_nodes: list[str] = field(default_factory=list)
    path_steps: list[TrafficPathStep] = field(default_factory=list)

    status: ReservationStatus = ReservationStatus.GRANTED
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime | None = None


@dataclass(slots=True)
class FinishedReservationRecord:
    """Completed or expired reservation history."""

    reservation_id: str
    trans_task_txn_id: int
    trans_id: str
    task_type: TransTaskType

    final_status: ReservationStatus
    created_at: datetime
    finished_at: datetime
    finish_reason: str

    item_stat_id: int | None = None
    ord_id: int | None = None

    route_nodes: list[str] = field(default_factory=list)
    path_steps: list[TrafficPathStep] = field(default_factory=list)


@dataclass(slots=True)
class EdgeReservation:
    reservation_id: str
    trans_id: str
    edge: tuple[str, str]
    start_slot: int
    end_slot: int


@dataclass(slots=True)
class NodeReservation:
    reservation_id: str
    trans_id: str
    node_id: str
    start_slot: int
    end_slot: int


@dataclass(slots=True)
class TrafficPlan:
    points: list[tuple[float, float, str]]
    reserved_edges: list[str]
    duration_sec: float

    route_nodes: list[str] = field(default_factory=list)
    path_steps: list[TrafficPathStep] = field(default_factory=list)
    reservation_id: str | None = None


# ============================================================================
# TRAFFIC MANAGER
# ============================================================================

class TrafficManager:
    """
    Graph-based traffic manager with route reservation support.

    현재 구조:
    - task_type을 실제 waypoint 목적지로 매핑
    - A*로 node 경로 생성
    - 생성된 경로를 edge/node reservation으로 등록
    - 기존 reservation과 시간 구간이 겹치면 start_slot을 뒤로 밀어 예약
    - planning horizon 안에서 예약 불가 시 HOLD 반환

    주의:
    - 현재 방식은 "충돌 edge 회피 우회 탐색"보다 "시간 지연 기반 예약 조정"에 가까움
    - 우회 경로를 적극적으로 찾으려면 A* 탐색 중 conflict edge를 제외하는 time-expanded A*로 확장 필요
    """

    def __init__(
        self,
        graph: dict[str, dict[str, Any]] | None = None,
        *,
        robot_speed_mps: float = 0.20,
        time_step_sec: float = 1.0,
        safety_margin_sec: float = 0.5,
        max_horizon_sec: float = 180.0,
        reservation_ttl_sec: float = 60.0,
        finished_history_size: int = 500,
    ) -> None:
        if robot_speed_mps <= 0:
            raise ValueError("robot_speed_mps must be greater than 0")
        if time_step_sec <= 0:
            raise ValueError("time_step_sec must be greater than 0")
        if safety_margin_sec < 0:
            raise ValueError("safety_margin_sec must be >= 0")
        if max_horizon_sec <= 0:
            raise ValueError("max_horizon_sec must be greater than 0")
        if reservation_ttl_sec <= 0:
            raise ValueError("reservation_ttl_sec must be greater than 0")
        if finished_history_size <= 0:
            raise ValueError("finished_history_size must be greater than 0")

        self._lock = threading.RLock()

        self._robot_speed_mps = robot_speed_mps
        self._time_step_sec = time_step_sec
        self._safety_margin_sec = safety_margin_sec
        self._max_horizon_slots = max(1, int(max_horizon_sec / time_step_sec))
        self._reservation_ttl_sec = reservation_ttl_sec

        self._graph = graph or self._default_graph()
        self._validate_graph()

        self._reservations: dict[str, RouteReservation] = {}
        self._finished_reservations: deque[FinishedReservationRecord] = deque(
            maxlen=finished_history_size
        )

        self._edge_reservations: list[EdgeReservation] = []
        self._node_reservations: list[NodeReservation] = []

    # ----------------------------------------------------------------------
    # Public Interface
    # ----------------------------------------------------------------------

    def request_route_permission(
        self,
        input_data: RoutePermissionInput,
    ) -> TrafficDecision:
        """
        AMR 이동 요청을 받아 경로 계산, 충돌 검사, reservation 생성을 수행한다.

        동일 trans_id가 재요청하면 기존 active reservation은 superseded 처리 후 제거한다.
        """
        with self._lock:
            self.handle_timeouts()
            self._release_by_trans_id(input_data.trans_id)

            try:
                start_node, goal_node = self._get_task_endpoints(input_data)

                start_pose = self._get_node_pose(start_node)
                goal_pose = self._get_node_pose(goal_node)

                plan = self._plan_route_internal(
                    trans_task_txn_id=input_data.trans_task_txn_id,
                    trans_id=input_data.trans_id,
                    task_type=input_data.task_type,
                    start_node=start_node,
                    goal_node=goal_node,
                    start_pose=(start_pose.x, start_pose.y),
                    goal_pose=(goal_pose.x, goal_pose.y),
                    loaded=input_data.loaded,
                    priority=input_data.priority,
                    item_stat_id=input_data.item_stat_id,
                    ord_id=input_data.ord_id,
                    reservation_context=input_data.current_node,
                )

            except Exception as exc:
                return TrafficDecision(
                    trans_task_txn_id=input_data.trans_task_txn_id,
                    trans_id=input_data.trans_id,
                    decision=TrafficDecisionType.HOLD,
                    reason=str(exc),
                )

            return TrafficDecision(
                trans_task_txn_id=input_data.trans_task_txn_id,
                trans_id=input_data.trans_id,
                decision=TrafficDecisionType.GO,
                route_nodes=plan.route_nodes,
                path_steps=plan.path_steps,
                reservation_id=plan.reservation_id,
                reason="route_reserved",
            )

    def plan_route(
        self,
        *,
        robot_id: str,
        priority: int,
        start: Sequence[float],
        goal: Sequence[float],
        loaded: bool = False,
        current_node: str | None = None,
    ) -> TrafficPlan:
        """
        좌표 기반 경로 계획 API.
        start/goal 좌표에서 가장 가까운 graph node를 찾은 뒤 예약까지 수행한다.
        """
        with self._lock:
            self.handle_timeouts()
            self._release_by_trans_id(robot_id)

            start_node = self._nearest_node_to_point(start)
            goal_node = self._nearest_node_to_point(goal)

            return self._plan_route_internal(
                trans_task_txn_id=0,
                trans_id=robot_id,
                task_type=TransTaskType.ToPP,
                start_node=start_node,
                goal_node=goal_node,
                start_pose=tuple(start[:2]),
                goal_pose=tuple(goal[:2]),
                loaded=loaded,
                priority=priority,
                reservation_context=current_node,
            )

    def plan_with_yield(
        self,
        *,
        robot_id: str,
        priority: int,
        start: Sequence[float],
        goal: Sequence[float],
        loaded: bool = False,
        current_node: str | None = None,
    ) -> TrafficPlan:
        """
        향후 양보/yield 정책 확장용 wrapper.
        현재는 plan_route와 동일하게 동작한다.
        """
        return self.plan_route(
            robot_id=robot_id,
            priority=priority,
            start=start,
            goal=goal,
            loaded=loaded,
            current_node=current_node,
        )

    def release_passed_edge(
        self,
        reservation_id: str,
        edge: tuple[str, str],
    ) -> bool:
        """
        AMR이 특정 edge를 통과했을 때 해당 edge reservation만 제거한다.

        주의:
        - RouteReservation.path_steps는 이 함수에서 줄이지 않는다.
        - 실제 충돌 검사에 쓰이는 _edge_reservations에서만 제거된다.
        """
        with self._lock:
            if reservation_id not in self._reservations:
                return False

            before = len(self._edge_reservations)

            self._edge_reservations = [
                item
                for item in self._edge_reservations
                if not (
                    item.reservation_id == reservation_id
                    and item.edge == edge
                )
            ]

            return len(self._edge_reservations) != before

    def release_reservation(self, reservation_id: str) -> bool:
        """
        전체 경로 완료 시 active reservation을 제거하고 finished history로 이동한다.
        """
        with self._lock:
            reservation = self._reservations.pop(reservation_id, None)
            if reservation is None:
                return False

            self._remove_edge_node_reservations(reservation_id)
            self._move_to_finished(
                reservation,
                ReservationStatus.RELEASED,
                "completed",
            )
            return True

    def handle_timeouts(self) -> list[FinishedReservationRecord]:
        """
        TTL이 지난 reservation을 EXPIRED 처리한다.
        """
        with self._lock:
            finished: list[FinishedReservationRecord] = []
            now = datetime.now()

            for reservation_id, reservation in list(self._reservations.items()):
                if reservation.expires_at is None:
                    continue

                if reservation.expires_at <= now:
                    self._reservations.pop(reservation_id, None)
                    self._remove_edge_node_reservations(reservation_id)
                    finished.append(
                        self._move_to_finished(
                            reservation,
                            ReservationStatus.EXPIRED,
                            "timeout",
                        )
                    )

            return finished

    def get_active_reservation(
        self,
        reservation_id: str,
    ) -> RouteReservation | None:
        with self._lock:
            return self._reservations.get(reservation_id)

    def list_active_reservations(self) -> list[RouteReservation]:
        with self._lock:
            return list(self._reservations.values())

    def list_finished_reservations(self) -> list[FinishedReservationRecord]:
        with self._lock:
            return list(self._finished_reservations)

    # 기존 테스트/호출부 호환 alias
    def get_reservation(self, reservation_id: str) -> RouteReservation | None:
        return self.get_active_reservation(reservation_id)

    def list_reservations(self) -> list[RouteReservation]:
        return self.list_active_reservations()

    # ----------------------------------------------------------------------
    # Planning
    # ----------------------------------------------------------------------

    def _plan_route_internal(
        self,
        *,
        trans_task_txn_id: int,
        trans_id: str,
        task_type: TransTaskType,
        start_node: str,
        goal_node: str,
        start_pose: Sequence[float],
        goal_pose: Sequence[float],
        loaded: bool,
        priority: int,
        item_stat_id: int | None = None,
        ord_id: int | None = None,
        reservation_context: str | None = None,
    ) -> TrafficPlan:
        del start_pose, goal_pose, reservation_context

        route_nodes = self._a_star_route(start_node, goal_node)
        if not route_nodes:
            raise ValueError(f"no route found from {start_node} to {goal_node}")

        route_points = [self._get_node_pose(node) for node in route_nodes]
        duration_sec = self._path_duration(route_nodes)

        start_slot = self._epoch_to_slot(datetime.now().timestamp())
        route_steps = self._build_path_steps(route_nodes, start_slot=start_slot)

        reservation = self._create_reservation(
            trans_task_txn_id=trans_task_txn_id,
            trans_id=trans_id,
            task_type=task_type,
            route_nodes=route_nodes,
            path_steps=route_steps,
            item_stat_id=item_stat_id,
            ord_id=ord_id,
            priority=priority,
            loaded=loaded,
        )

        return TrafficPlan(
            points=[
                (pose.x, pose.y, node)
                for node, pose in zip(route_nodes, route_points)
            ],
            reserved_edges=[
                f"{step.from_node}->{step.to_node}"
                for step in reservation.path_steps
                if step.edge is not None
            ],
            duration_sec=duration_sec,
            route_nodes=route_nodes,
            path_steps=reservation.path_steps,
            reservation_id=reservation.reservation_id,
        )

    def _a_star_route(
        self,
        start_node: str,
        goal_node: str,
    ) -> list[str]:
        """
        일반 A* shortest path.
        현재 reservation은 이 단계에서 고려하지 않고, reservation 단계에서 시간 조정한다.
        """
        if start_node == goal_node:
            return [start_node]

        open_heap: list[tuple[float, int, str]] = []
        sequence = 0

        heapq.heappush(open_heap, (0.0, sequence, start_node))

        came_from: dict[str, str] = {}
        g_score: dict[str, float] = {start_node: 0.0}
        visited: set[str] = set()

        while open_heap:
            _, _, current = heapq.heappop(open_heap)

            if current in visited:
                continue

            if current == goal_node:
                return self._reconstruct_node_path(came_from, current)

            visited.add(current)

            for neighbor, distance_m in self._graph[current]["neighbors"].items():
                if neighbor in visited:
                    continue

                tentative = g_score[current] + float(distance_m)

                if tentative < g_score.get(neighbor, math.inf):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative

                    f_score = tentative + self._euclidean_distance(
                        neighbor,
                        goal_node,
                    )

                    sequence += 1
                    heapq.heappush(open_heap, (f_score, sequence, neighbor))

        return []

    def _a_star_shortest_nodes(
        self,
        start_node: str,
        goal_node: str,
    ) -> list[str]:
        return self._a_star_route(start_node, goal_node)

    def _reconstruct_path(
        self,
        came_from: dict[str, str],
        current: str,
    ) -> list[str]:
        return self._reconstruct_node_path(came_from, current)

    def _reconstruct_node_path(
        self,
        came_from: dict[str, str],
        current: str,
    ) -> list[str]:
        path = [current]

        while current in came_from:
            current = came_from[current]
            path.append(current)

        path.reverse()
        return path

    # ----------------------------------------------------------------------
    # Reservation
    # ----------------------------------------------------------------------

    def _build_path_steps(
        self,
        route_nodes: list[str],
        *,
        start_slot: int,
    ) -> list[TrafficPathStep]:
        steps: list[TrafficPathStep] = []
        current_slot = start_slot

        for from_node, to_node in zip(route_nodes, route_nodes[1:]):
            travel_slots = self._get_edge_travel_slots(from_node, to_node)
            end_slot = current_slot + travel_slots

            pose = self._get_node_pose(to_node)

            steps.append(
                TrafficPathStep(
                    action=StepAction.MOVE,
                    from_node=from_node,
                    to_node=to_node,
                    pose=pose,
                    start_slot=current_slot,
                    end_slot=end_slot,
                    reserved_start_at=self._slot_to_epoch(current_slot),
                    reserved_end_at=self._slot_to_epoch(end_slot),
                    edge=(from_node, to_node),
                )
            )

            current_slot = end_slot

        return steps

    def _create_reservation(
        self,
        *,
        trans_task_txn_id: int,
        trans_id: str,
        task_type: TransTaskType,
        route_nodes: list[str],
        path_steps: list[TrafficPathStep],
        item_stat_id: int | None,
        ord_id: int | None,
        priority: int,
        loaded: bool,
    ) -> RouteReservation:
        base_slot = self._epoch_to_slot(datetime.now().timestamp())
        initial_delay_slots = self._wait_cost(priority=priority, loaded=loaded)

        start_slot = base_slot + initial_delay_slots
        deadline_slot = base_slot + self._max_horizon_slots

        shifted_steps = self._shift_path_steps(path_steps, start_slot)

        while shifted_steps and self._has_conflict(shifted_steps):
            start_slot += 1

            if start_slot > deadline_slot:
                raise RuntimeError("unable to reserve route within planning horizon")

            shifted_steps = self._shift_path_steps(path_steps, start_slot)

        reservation_id = str(uuid4())

        reservation = RouteReservation(
            reservation_id=reservation_id,
            trans_task_txn_id=trans_task_txn_id,
            trans_id=trans_id,
            task_type=task_type,
            item_stat_id=item_stat_id,
            ord_id=ord_id,
            route_nodes=route_nodes,
            path_steps=shifted_steps,
            expires_at=datetime.now() + timedelta(seconds=self._reservation_ttl_sec),
        )

        self._reservations[reservation.reservation_id] = reservation
        self._reserve_path(reservation)

        return reservation

    def _shift_path_steps(
        self,
        path_steps: list[TrafficPathStep],
        start_slot: int,
    ) -> list[TrafficPathStep]:
        if not path_steps:
            return []

        shifted: list[TrafficPathStep] = []
        offset = start_slot - path_steps[0].start_slot

        for step in path_steps:
            new_start = step.start_slot + offset
            new_end = step.end_slot + offset

            shifted.append(
                replace(
                    step,
                    start_slot=new_start,
                    end_slot=new_end,
                    reserved_start_at=self._slot_to_epoch(new_start),
                    reserved_end_at=self._slot_to_epoch(new_end),
                )
            )

        return shifted

    def _reserve_path(self, reservation: RouteReservation) -> None:
        for step in reservation.path_steps:
            if step.edge is not None:
                self._reserve_edge(
                    reservation.reservation_id,
                    reservation.trans_id,
                    step,
                )

        route_nodes = self._path_steps_to_route_nodes(reservation.path_steps)
        protected_nodes = self._protected_nodes(route_nodes)

        if reservation.path_steps:
            start_slot = reservation.path_steps[0].start_slot
            end_slot = reservation.path_steps[-1].end_slot
        else:
            start_slot = 0
            end_slot = 0

        for node_id in protected_nodes:
            self._reserve_node(
                reservation.reservation_id,
                reservation.trans_id,
                node_id,
                start_slot,
                end_slot,
            )

    def _reserve_edge(
        self,
        reservation_id: str,
        trans_id: str,
        step: TrafficPathStep,
    ) -> None:
        assert step.edge is not None

        self._edge_reservations.append(
            EdgeReservation(
                reservation_id=reservation_id,
                trans_id=trans_id,
                edge=step.edge,
                start_slot=step.start_slot,
                end_slot=step.end_slot,
            )
        )

    def _reserve_node(
        self,
        reservation_id: str,
        trans_id: str,
        node_id: str,
        start_slot: int,
        end_slot: int,
    ) -> None:
        self._node_reservations.append(
            NodeReservation(
                reservation_id=reservation_id,
                trans_id=trans_id,
                node_id=node_id,
                start_slot=start_slot,
                end_slot=end_slot,
            )
        )

    def _release_by_trans_id(self, trans_id: str) -> None:
        for reservation_id, reservation in list(self._reservations.items()):
            if reservation.trans_id != trans_id:
                continue

            self._reservations.pop(reservation_id, None)
            self._remove_edge_node_reservations(reservation_id)
            self._move_to_finished(
                reservation,
                ReservationStatus.RELEASED,
                "superseded_by_new_request",
            )

    def _remove_edge_node_reservations(self, reservation_id: str) -> None:
        self._edge_reservations = [
            item
            for item in self._edge_reservations
            if item.reservation_id != reservation_id
        ]

        self._node_reservations = [
            item
            for item in self._node_reservations
            if item.reservation_id != reservation_id
        ]

    def _move_to_finished(
        self,
        reservation: RouteReservation,
        final_status: ReservationStatus,
        finish_reason: str,
    ) -> FinishedReservationRecord:
        reservation.status = final_status

        record = FinishedReservationRecord(
            reservation_id=reservation.reservation_id,
            trans_task_txn_id=reservation.trans_task_txn_id,
            trans_id=reservation.trans_id,
            task_type=reservation.task_type,
            item_stat_id=reservation.item_stat_id,
            ord_id=reservation.ord_id,
            route_nodes=reservation.route_nodes,
            path_steps=reservation.path_steps,
            final_status=final_status,
            created_at=reservation.created_at,
            finished_at=datetime.now(),
            finish_reason=finish_reason,
        )

        self._finished_reservations.append(record)
        return record

    # ----------------------------------------------------------------------
    # Conflict
    # ----------------------------------------------------------------------

    def _has_conflict(self, path_steps: list[TrafficPathStep]) -> bool:
        if not path_steps:
            return False

        for step in path_steps:
            if step.edge is None:
                continue

            if self._is_edge_conflict(
                step.edge,
                step.start_slot,
                step.end_slot,
            ):
                return True

        route_nodes = self._path_steps_to_route_nodes(path_steps)

        for node in self._protected_nodes(route_nodes):
            if self._is_node_conflict(
                node,
                path_steps[0].start_slot,
                path_steps[-1].end_slot,
            ):
                return True

        return False

    def _is_edge_conflict(
        self,
        edge: tuple[str, str],
        start_slot: int,
        end_slot: int,
    ) -> bool:
        reverse_edge = (edge[1], edge[0])

        for reservation in self._edge_reservations:
            if reservation.edge not in (edge, reverse_edge):
                continue

            if self._is_time_overlap(
                reservation.start_slot,
                reservation.end_slot,
                start_slot,
                end_slot,
            ):
                return True

        return False

    def _is_node_conflict(
        self,
        node_id: str,
        start_slot: int,
        end_slot: int,
    ) -> bool:
        for reservation in self._node_reservations:
            if reservation.node_id != node_id:
                continue

            if self._is_time_overlap(
                reservation.start_slot,
                reservation.end_slot,
                start_slot,
                end_slot,
            ):
                return True

        return False

    @staticmethod
    def _is_time_overlap(
        left_start: int,
        left_end: int,
        right_start: int,
        right_end: int,
    ) -> bool:
        return max(left_start, right_start) < min(left_end, right_end)

    # ----------------------------------------------------------------------
    # Task / Node Helpers
    # ----------------------------------------------------------------------

    def _get_task_endpoints(
        self,
        input_data: RoutePermissionInput,
    ) -> tuple[str, str]:
        return self._get_task_endpoints_from_task_type(
            input_data.task_type,
            input_data.current_node,
        )

    def _get_task_endpoints_from_task_type(
        self,
        task_type: TransTaskType,
        current_node: str | None,
    ) -> tuple[str, str]:
        start_node = current_node or "HOME"

        goal_lookup: dict[TransTaskType, str] = {
            TransTaskType.ToPP: "ToPP1",
            TransTaskType.ToSTRG: "ToSTRG1",
            TransTaskType.ToSHIP: "ToSHIP",
            TransTaskType.ToCHG: "ToCHG1",
        }

        optional_mappings = (
            ("ToCAST", "ToCAST1"),
            ("ToINSP", "ToINSP"),
        )

        for attr, node in optional_mappings:
            member = getattr(TransTaskType, attr, None)
            if member is not None:
                goal_lookup[member] = node

        try:
            goal_node = goal_lookup[task_type]
        except KeyError as exc:
            raise ValueError(f"unsupported task_type: {task_type}") from exc

        if start_node not in self._graph:
            raise ValueError(f"unknown current_node: {start_node}")

        if goal_node not in self._graph:
            raise ValueError(f"unknown goal_node: {goal_node}")

        return start_node, goal_node

    def _path_steps_to_route_nodes(
        self,
        path_steps: list[TrafficPathStep],
    ) -> list[str]:
        if not path_steps:
            return []

        nodes = [path_steps[0].from_node]
        nodes.extend(step.to_node for step in path_steps)

        return nodes

    # ----------------------------------------------------------------------
    # Geometry / Time / Cost
    # ----------------------------------------------------------------------

    def _get_edge_travel_slots(
        self,
        from_node: str,
        to_node: str,
    ) -> int:
        distance = self._get_edge_distance(from_node, to_node)

        travel_sec = distance / self._robot_speed_mps
        travel_sec += self._safety_margin_sec

        return max(1, math.ceil(travel_sec / self._time_step_sec))

    def _get_edge_distance(
        self,
        from_node: str,
        to_node: str,
    ) -> float:
        try:
            return float(self._graph[from_node]["neighbors"][to_node])
        except KeyError as exc:
            raise ValueError(f"edge not found: {from_node} -> {to_node}") from exc

    def _heuristic_slots(
        self,
        node_a: str,
        node_b: str,
    ) -> float:
        distance = self._euclidean_distance(node_a, node_b)
        return distance / self._robot_speed_mps / self._time_step_sec

    def _euclidean_distance(
        self,
        node_a: str,
        node_b: str,
    ) -> float:
        pose_a = self._get_node_pose(node_a)
        pose_b = self._get_node_pose(node_b)

        return math.hypot(pose_a.x - pose_b.x, pose_a.y - pose_b.y)

    def _get_node_pose(self, node_id: str) -> NodePose:
        node = self._graph.get(node_id)
        if node is None:
            raise KeyError(f"unknown node: {node_id}")

        pose = node.get("pose")

        if isinstance(pose, NodePose):
            return pose

        if isinstance(pose, dict):
            return NodePose(**pose)

        if isinstance(pose, (tuple, list)) and len(pose) >= 2:
            x = float(pose[0])
            y = float(pose[1])
            yaw = float(pose[2]) if len(pose) > 2 else 0.0
            return NodePose(x=x, y=y, yaw=yaw)

        raise TypeError(f"invalid pose for node {node_id}")

    def _nearest_node_to_point(self, point: Sequence[float]) -> str:
        if len(point) < 2:
            raise ValueError("point must contain at least x and y")

        x = float(point[0])
        y = float(point[1])

        best_node: str | None = None
        best_distance = math.inf

        for node_id in self._graph:
            pose = self._get_node_pose(node_id)
            distance = math.hypot(pose.x - x, pose.y - y)

            if distance < best_distance:
                best_distance = distance
                best_node = node_id

        if best_node is None:
            raise ValueError("graph is empty")

        return best_node

    def _epoch_to_slot(self, epoch_time: float) -> int:
        return int(epoch_time / self._time_step_sec)

    def _slot_to_epoch(self, slot: int) -> float:
        return float(slot * self._time_step_sec)

    @staticmethod
    def _wait_cost(priority: int, loaded: bool) -> int:
        """
        초기 예약 시작 지연 slot.

        priority가 높을수록 더 빨리 시작한다.
        loaded=True이면 적재 작업을 약간 더 우선한다.
        """
        delay = max(0, 2 - priority)

        if loaded:
            delay = max(0, delay - 1)

        return delay

    def _path_duration(self, route_nodes: list[str]) -> float:
        if len(route_nodes) < 2:
            return 0.0

        distance = 0.0

        for from_node, to_node in zip(route_nodes, route_nodes[1:]):
            distance += self._get_edge_distance(from_node, to_node)

        return distance / self._robot_speed_mps

    def _protected_nodes(self, route_nodes: Iterable[str]) -> list[str]:
        """
        neighbor가 3개 이상인 node를 교차로/protected node로 간주한다.
        """
        protected: list[str] = []

        for node_id in route_nodes:
            neighbors = self._graph[node_id]["neighbors"]

            if len(neighbors) >= 3:
                protected.append(node_id)

        return protected

    # ----------------------------------------------------------------------
    # Graph Validation / Default Graph
    # ----------------------------------------------------------------------

    def _validate_graph(self) -> None:
        if not self._graph:
            raise ValueError("graph cannot be empty")

        for node_id, payload in self._graph.items():
            if "pose" not in payload:
                raise ValueError(f"graph node {node_id} missing pose")

            if "neighbors" not in payload:
                raise ValueError(f"graph node {node_id} missing neighbors")

            if not isinstance(payload["neighbors"], dict):
                raise ValueError(f"graph node {node_id} neighbors must be dict")

            for neighbor in payload["neighbors"]:
                if neighbor not in self._graph:
                    raise ValueError(
                        f"graph node {node_id} references unknown neighbor {neighbor}"
                    )

    @staticmethod
    def _default_graph() -> dict[str, dict[str, Any]]:
        """
        실측 waypoint graph.

        pose = (x, y, yaw_rad)
        unit = meter
        frame = map

        Task destination nodes:
        - ToINSP
        - ToSHIP
        - ToCAST1, ToCAST2
        - ToCHG1, ToCHG2, ToCHG3
        - ToSTRG1, ToSTRG2
        - ToPP1, ToPP2

        Routing infrastructure nodes:
        - HOME
        - J_UPPER
        - J_CENTER
        - J_LOWER
        """
        nodes: dict[str, dict[str, Any]] = {
            # Task destination nodes
            "ToINSP": {
                "pose": (-0.670, -0.150, -1.57),
                "neighbors": {},
            },
            "ToSHIP": {
                "pose": (-0.670, 0.450, 1.57),
                "neighbors": {},
            },
            "ToCAST1": {
                "pose": (-0.256, 0.200, 1.57),
                "neighbors": {},
            },
            "ToCAST2": {
                "pose": (-0.413, 0.200, 1.57),
                "neighbors": {},
            },
            "ToCHG1": {
                "pose": (0.044, 0.095, 0.00),
                "neighbors": {},
            },
            "ToCHG2": {
                "pose": (0.044, -0.027, 0.00),
                "neighbors": {},
            },
            "ToCHG3": {
                "pose": (0.044, -0.179, 0.00),
                "neighbors": {},
            },
            "ToSTRG1": {
                "pose": (-0.136, -0.587, -1.57),
                "neighbors": {},
            },
            "ToSTRG2": {
                "pose": (-0.223, -0.415, -1.57),
                "neighbors": {},
            },
            "ToPP1": {
                "pose": (-0.480, -1.050, 3.14),
                "neighbors": {},
            },
            "ToPP2": {
                "pose": (-0.480, -1.130, 3.14),
                "neighbors": {},
            },

            # Infrastructure nodes
            "HOME": {
                "pose": (0.200, 0.000, 0.00),
                "neighbors": {},
            },
            "J_UPPER": {
                "pose": (-0.350, 0.220, 0.00),
                "neighbors": {},
            },
            "J_CENTER": {
                "pose": (-0.100, -0.050, 0.00),
                "neighbors": {},
            },
            "J_LOWER": {
                "pose": (-0.350, -0.650, 0.00),
                "neighbors": {},
            },
        }

        def _link(a: str, b: str) -> None:
            pa = nodes[a]["pose"]
            pb = nodes[b]["pose"]

            dist = round(
                math.hypot(pa[0] - pb[0], pa[1] - pb[1]),
                4,
            )

            nodes[a]["neighbors"][b] = dist
            nodes[b]["neighbors"][a] = dist

        # CHG vertical corridor
        _link("HOME", "ToCHG1")
        _link("ToCHG1", "ToCHG2")
        _link("ToCHG2", "ToCHG3")
        _link("ToCHG1", "J_CENTER")
        _link("ToCHG3", "J_CENTER")

        # Upper area
        _link("J_UPPER", "ToCAST1")
        _link("J_UPPER", "ToCAST2")
        _link("J_UPPER", "ToSHIP")
        _link("J_UPPER", "J_CENTER")

        # Center area
        _link("J_CENTER", "HOME")
        _link("J_CENTER", "ToINSP")
        _link("J_CENTER", "J_LOWER")

        # Left corridor
        _link("ToINSP", "ToSHIP")
        _link("ToINSP", "J_LOWER")

        # Lower area
        _link("J_LOWER", "ToSTRG1")
        _link("J_LOWER", "ToSTRG2")
        _link("J_LOWER", "ToPP1")
        _link("ToSTRG1", "ToSTRG2")
        _link("ToPP1", "ToPP2")

        return nodes
