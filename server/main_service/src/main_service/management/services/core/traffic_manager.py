"""Traffic Manager — AMR 경로 계획 + 충돌 회피 (Backtrack Yield).

설계 근거: docs/fleet_traffic_management.html (Waypoint/Edge + Backtrack Yield).
물리 제약: 1m × 2m 맵 + 0.12m AMR 3대.

핵심 알고리즘:
1. Waypoint 그래프 (8개 노드 + 양방향 edges, weight=유클리드 거리)
2. Dijkstra 최단 경로
3. Edge 예약 테이블 (edge_key → 점유 [start_t, end_t, robot_id, priority] 리스트)
4. Backtrack Yield: 충돌 시 priority_rank 가 낮은 AMR 이 양보
   - 시도 1: 같은 출발/도착 유지하되 우회 노드 경유
   - 시도 2: 출발 시각을 충돌 종료 후로 미룸 (대기)

@MX:ANCHOR: Phase 6 산출물. PlanRoute gRPC RPC 의 본체.
@MX:NOTE: 그래프는 in-code 정의. 향후 yaml/db 로 외부화 가능 (load_graph 함수).
@MX:WARN: reservation 은 in-memory. 다중 Mgmt 인스턴스 시 Redis 등으로 공유 필요.
"""

from __future__ import annotations

import heapq
import logging
import threading
from dataclasses import dataclass, field
from math import sqrt

logger = logging.getLogger(__name__)

# AMR 평균 속도 (m/s) — Confluence: 약 0.3 m/s
AMR_SPEED_MPS = 0.3
# 안전 마진 (각 통과 시간에 더해 reservation 길이를 늘림)
SAFETY_MARGIN_SEC = 1.0


# ---------------------------------------------------------------------------
# Waypoint 그래프 (1m × 2m 맵, 8 노드)
# ---------------------------------------------------------------------------

WAYPOINTS: dict[str, tuple[float, float]] = {
    "HOME": (0.10, 0.10),  # 충전/대기
    "JUNCT_A": (0.50, 0.50),  # 교차로 A
    "JUNCT_B": (0.70, 0.50),  # 교차로 B
    "POST": (0.50, 1.00),  # 후처리 구역
    "INSP_IN": (0.50, 1.50),  # 검사 입구
    "INSP_OUT": (0.70, 1.50),  # 검사 출구
    "LOAD": (0.90, 0.30),  # 적재 구역
    "SHIP": (0.90, 1.70),  # 출고 구역
}

# 양방향 edges (튜플 정렬해 중복 제거)
_EDGE_LIST: list[tuple[str, str]] = [
    ("HOME", "JUNCT_A"),
    ("JUNCT_A", "JUNCT_B"),
    ("JUNCT_A", "POST"),
    ("JUNCT_B", "LOAD"),
    ("POST", "INSP_IN"),
    ("INSP_IN", "INSP_OUT"),
    ("INSP_OUT", "JUNCT_B"),
    ("INSP_OUT", "SHIP"),
]


def _dist(a: str, b: str) -> float:
    ax, ay = WAYPOINTS[a]
    bx, by = WAYPOINTS[b]
    return sqrt((ax - bx) ** 2 + (ay - by) ** 2)


def _edge_key(a: str, b: str) -> str:
    """양방향 edge 의 정규화 key (충돌 감지용)."""
    return "|".join(sorted([a, b]))


# 인접 리스트 + 거리 캐시
_ADJ: dict[str, list[tuple[str, float]]] = {n: [] for n in WAYPOINTS}
for u, v in _EDGE_LIST:
    d = _dist(u, v)
    _ADJ[u].append((v, d))
    _ADJ[v].append((u, d))


# ---------------------------------------------------------------------------
# 결과 dataclass
# ---------------------------------------------------------------------------


@dataclass
class RoutePlan:
    """TrafficManager.plan / plan_with_yield 결과.

    points: proto RoutePoint 호환 (server.py 가 변환).
    """

    nodes: list[str] = field(default_factory=list)  # 노드 이름 시퀀스
    points: list[tuple[float, float, str]] = field(default_factory=list)  # (x, y, waypoint_id)
    reserved_edges: list[str] = field(default_factory=list)  # edge_key 리스트
    duration_sec: float = 0.0
    yielded: bool = False  # Backtrack Yield 발동 여부
    delay_sec: float = 0.0  # 대기 지연 시간


# ---------------------------------------------------------------------------
# Edge Reservation 매니저
# ---------------------------------------------------------------------------


@dataclass
class _Reservation:
    edge_key: str
    start_t: float
    end_t: float
    robot_id: str
    priority: int


class _ReservationTable:
    """Edge 별 시간창 점유 내역. priority 비교로 양보 결정."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_edge: dict[str, list[_Reservation]] = {}

    def conflicts(
        self, edge_key: str, start_t: float, end_t: float, ignore_robot: str | None = None
    ) -> list[_Reservation]:
        with self._lock:
            existing = self._by_edge.get(edge_key, [])
            return [
                r
                for r in existing
                if r.robot_id != ignore_robot and not (end_t <= r.start_t or start_t >= r.end_t)
            ]

    def reserve(self, r: _Reservation) -> None:
        with self._lock:
            self._by_edge.setdefault(r.edge_key, []).append(r)

    def clear_robot(self, robot_id: str) -> None:
        with self._lock:
            for k, lst in self._by_edge.items():
                self._by_edge[k] = [r for r in lst if r.robot_id != robot_id]

    def clear_all(self) -> None:
        with self._lock:
            self._by_edge.clear()


# ---------------------------------------------------------------------------
# Traffic Manager
# ---------------------------------------------------------------------------


class TrafficManager:
    """Waypoint 그래프 + Dijkstra + Backtrack Yield."""

    def __init__(self) -> None:
        self._reservations = _ReservationTable()

    # ----- 공개 API (server.py 가 호출) -----

    def plan(
        self, robot_id: str, start: tuple[float, float], goal: tuple[float, float]
    ) -> RoutePlan:
        """단순 최단 경로 (예약/충돌 무시)."""
        s_node = self._nearest_node(start)
        g_node = self._nearest_node(goal)
        nodes = self._dijkstra(s_node, g_node)
        if not nodes:
            return RoutePlan()
        return self._make_plan(nodes, t0=0.0)

    def plan_with_yield(
        self,
        robot_id: str,
        priority: int,
        start: tuple[float, float],
        goal: tuple[float, float],
        depart_at_sec: float = 0.0,
    ) -> RoutePlan:
        """예약/충돌 검사 포함. 충돌 시 lower priority 가 양보 (대기 또는 우회).

        priority 가 클수록 우선 (1=최고). 충돌 시 자기 priority 가 더 높으면 (숫자 더 작음)
        그대로 진행 + 충돌하는 lower priority 예약을 무효화. 반대면 자기가 yield.

        return.yielded=True 면 우회 또는 지연이 발생.
        """
        s_node = self._nearest_node(start)
        g_node = self._nearest_node(goal)

        # 1차: 단순 최단 경로 시도
        nodes = self._dijkstra(s_node, g_node)
        if not nodes:
            return RoutePlan()

        plan = self._try_reserve(robot_id, priority, nodes, depart_at_sec)
        if plan is not None:
            return plan

        # 2차: 우회 시도 — 충돌 edge 회피하는 우회 경로
        for blocked_edge in self._collect_blocked_edges(robot_id, priority, nodes, depart_at_sec):
            avoid_nodes = self._dijkstra(s_node, g_node, exclude_edge=blocked_edge)
            if not avoid_nodes:
                continue
            alt_plan = self._try_reserve(robot_id, priority, avoid_nodes, depart_at_sec)
            if alt_plan is not None:
                alt_plan.yielded = True
                return alt_plan

        # 3차: 대기 (출발 시각을 충돌 종료 시점 이후로 미룸)
        latest_conflict_end = self._latest_conflict_end(robot_id, priority, nodes, depart_at_sec)
        if latest_conflict_end > depart_at_sec:
            delayed = self._try_reserve(
                robot_id, priority, nodes, latest_conflict_end + SAFETY_MARGIN_SEC
            )
            if delayed is not None:
                delayed.yielded = True
                delayed.delay_sec = latest_conflict_end - depart_at_sec
                return delayed

        # 모두 실패 — 빈 plan (caller 가 대기/재시도)
        return RoutePlan()

    def cancel(self, robot_id: str) -> None:
        """해당 로봇의 모든 예약 해제 (도착 또는 작업 취소 시)."""
        self._reservations.clear_robot(robot_id)

    def reset(self) -> None:
        """전체 예약 초기화 (테스트 / 운영 재시작 시)."""
        self._reservations.clear_all()

    # ----- 내부 -----

    @staticmethod
    def _nearest_node(pos: tuple[float, float]) -> str:
        x, y = pos
        return min(WAYPOINTS, key=lambda n: (WAYPOINTS[n][0] - x) ** 2 + (WAYPOINTS[n][1] - y) ** 2)

    @staticmethod
    def _dijkstra(start: str, goal: str, exclude_edge: str | None = None) -> list[str]:
        if start == goal:
            return [start]
        dist = {n: float("inf") for n in WAYPOINTS}
        prev: dict[str, str | None] = dict.fromkeys(WAYPOINTS)
        dist[start] = 0.0
        pq: list[tuple[float, str]] = [(0.0, start)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            if u == goal:
                break
            for v, w in _ADJ[u]:
                if exclude_edge and _edge_key(u, v) == exclude_edge:
                    continue
                nd = d + w
                if nd < dist[v]:
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))
        if dist[goal] == float("inf"):
            return []
        # 경로 복원
        path: list[str] = []
        cur: str | None = goal
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        return list(reversed(path))

    def _make_plan(self, nodes: list[str], t0: float) -> RoutePlan:
        """nodes → RoutePlan (각 edge 통과 시간 + 예약 키 계산)."""
        points = [(WAYPOINTS[n][0], WAYPOINTS[n][1], n) for n in nodes]
        edges_keys: list[str] = []
        total_time = 0.0
        for u, v in zip(nodes, nodes[1:], strict=False):
            edges_keys.append(_edge_key(u, v))
            total_time += _dist(u, v) / AMR_SPEED_MPS
        return RoutePlan(
            nodes=nodes,
            points=points,
            reserved_edges=edges_keys,
            duration_sec=total_time + t0,
        )

    def _edge_time_windows(
        self, nodes: list[str], depart_at_sec: float
    ) -> list[tuple[str, float, float]]:
        """경로의 각 edge 별 (edge_key, start_t, end_t) 윈도우 산출."""
        windows: list[tuple[str, float, float]] = []
        t = depart_at_sec
        for u, v in zip(nodes, nodes[1:], strict=False):
            travel = _dist(u, v) / AMR_SPEED_MPS
            start_t, end_t = t, t + travel + SAFETY_MARGIN_SEC
            windows.append((_edge_key(u, v), start_t, end_t))
            t += travel
        return windows

    def _try_reserve(
        self, robot_id: str, priority: int, nodes: list[str], depart_at_sec: float
    ) -> RoutePlan | None:
        """경로 전체를 atomic 하게 예약 시도. 충돌 시 None.

        priority 비교: 자기보다 낮은(숫자 큰) priority 의 기존 예약은 강제 양보(취소)됨.
        """
        windows = self._edge_time_windows(nodes, depart_at_sec)

        # Pre-check: 자기보다 같거나 높은 priority(숫자 작거나 같은) 예약과 충돌 있으면 실패
        for key, s_t, e_t in windows:
            blockers = self._reservations.conflicts(key, s_t, e_t, ignore_robot=robot_id)
            higher_or_equal = [b for b in blockers if b.priority <= priority]
            if higher_or_equal:
                return None

        # 자기보다 낮은 priority 예약은 무효화 (강제 양보)
        for key, s_t, e_t in windows:
            losers = self._reservations.conflicts(key, s_t, e_t, ignore_robot=robot_id)
            for r in losers:
                if r.priority > priority:
                    logger.info(
                        "Backtrack Yield: %s (p=%d) → %s (p=%d) edge=%s 양보",
                        r.robot_id,
                        r.priority,
                        robot_id,
                        priority,
                        key,
                    )
                    self._reservations.clear_robot(r.robot_id)

        # 새 예약 등록
        for key, s_t, e_t in windows:
            self._reservations.reserve(_Reservation(key, s_t, e_t, robot_id, priority))

        plan = self._make_plan(nodes, t0=depart_at_sec)
        return plan

    def _collect_blocked_edges(
        self, robot_id: str, priority: int, nodes: list[str], depart_at_sec: float
    ) -> list[str]:
        windows = self._edge_time_windows(nodes, depart_at_sec)
        blocked: list[str] = []
        for key, s_t, e_t in windows:
            for r in self._reservations.conflicts(key, s_t, e_t, ignore_robot=robot_id):
                if r.priority <= priority:
                    blocked.append(key)
                    break
        return blocked

    def _latest_conflict_end(
        self, robot_id: str, priority: int, nodes: list[str], depart_at_sec: float
    ) -> float:
        latest = depart_at_sec
        for key, s_t, e_t in self._edge_time_windows(nodes, depart_at_sec):
            for r in self._reservations.conflicts(key, s_t, e_t, ignore_robot=robot_id):
                if r.priority <= priority and r.end_t > latest:
                    latest = r.end_t
        return latest
