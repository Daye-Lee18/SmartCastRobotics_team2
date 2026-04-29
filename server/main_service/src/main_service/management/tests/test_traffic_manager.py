"""TrafficManager 단위 테스트 — Phase 6 산출물 검증.

순수 알고리즘 (DB/네트워크 의존 없음) — 가장 testable 한 V6 모듈.
"""

from __future__ import annotations

import pytest
from services.traffic_manager import (
    AMR_SPEED_MPS,
    WAYPOINTS,
    TrafficManager,
    _edge_key,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tm():
    """Fresh TrafficManager 인스턴스 (테스트마다 reservation 초기화)."""
    return TrafficManager()


# ---------------------------------------------------------------------------
# Waypoint 그래프 정의
# ---------------------------------------------------------------------------


class TestWaypointGraph:
    def test_8_nodes_defined(self):
        assert len(WAYPOINTS) == 8
        assert {"HOME", "JUNCT_A", "JUNCT_B", "POST", "INSP_IN", "INSP_OUT", "LOAD", "SHIP"} == set(
            WAYPOINTS
        )

    def test_all_coordinates_within_map(self):
        # 1m × 2m 맵 가정
        for name, (x, y) in WAYPOINTS.items():
            assert 0.0 <= x <= 1.0, f"{name} x out of range: {x}"
            assert 0.0 <= y <= 2.0, f"{name} y out of range: {y}"

    def test_edge_key_canonicalization(self):
        # 양방향 edge 는 같은 key 로 정규화
        assert _edge_key("A", "B") == _edge_key("B", "A")
        assert _edge_key("HOME", "JUNCT_A") == "HOME|JUNCT_A"


# ---------------------------------------------------------------------------
# Dijkstra 최단 경로
# ---------------------------------------------------------------------------


class TestDijkstra:
    def test_same_start_goal_returns_single_node(self, tm):
        plan = tm.plan("AMR-001", WAYPOINTS["HOME"], WAYPOINTS["HOME"])
        assert plan.nodes == ["HOME"]
        assert plan.duration_sec == 0.0

    def test_home_to_ship_5_nodes(self, tm):
        plan = tm.plan("AMR-001", WAYPOINTS["HOME"], WAYPOINTS["SHIP"])
        assert plan.nodes == ["HOME", "JUNCT_A", "JUNCT_B", "INSP_OUT", "SHIP"]
        assert len(plan.reserved_edges) == 4
        assert plan.duration_sec > 0

    def test_home_to_load_3_nodes(self, tm):
        plan = tm.plan("AMR-001", WAYPOINTS["HOME"], WAYPOINTS["LOAD"])
        assert plan.nodes == ["HOME", "JUNCT_A", "JUNCT_B", "LOAD"]
        assert len(plan.reserved_edges) == 3

    def test_nearest_node_resolution(self, tm):
        # HOME(0.10, 0.10) 과 가까운 임의 좌표
        plan = tm.plan("AMR-001", (0.05, 0.05), WAYPOINTS["LOAD"])
        assert plan.nodes[0] == "HOME"

    def test_duration_uses_amr_speed(self, tm):
        # HOME → JUNCT_A 거리 / 속도
        from math import sqrt

        d = sqrt(0.4**2 + 0.4**2)
        plan = tm.plan("AMR-001", WAYPOINTS["HOME"], WAYPOINTS["JUNCT_A"])
        assert plan.duration_sec == pytest.approx(d / AMR_SPEED_MPS, rel=0.01)


# ---------------------------------------------------------------------------
# Edge 차단 우회
# ---------------------------------------------------------------------------


class TestEdgeAvoidance:
    def test_default_path_uses_junct_b_shortcut(self, tm):
        nodes = tm._dijkstra("HOME", "LOAD")
        assert "JUNCT_B" in nodes
        assert "POST" not in nodes

    def test_blocked_junct_a_b_forces_post_detour(self, tm):
        nodes = tm._dijkstra("HOME", "LOAD", exclude_edge="JUNCT_A|JUNCT_B")
        assert "POST" in nodes
        assert nodes[0] == "HOME" and nodes[-1] == "LOAD"


# ---------------------------------------------------------------------------
# Backtrack Yield (충돌 회피)
# ---------------------------------------------------------------------------


class TestBacktrackYield:
    def test_first_robot_no_yield(self, tm):
        plan = tm.plan_with_yield(
            "AMR-001", priority=1, start=WAYPOINTS["HOME"], goal=WAYPOINTS["SHIP"]
        )
        assert plan.yielded is False
        assert plan.delay_sec == 0.0
        assert len(plan.nodes) > 0

    def test_lower_priority_yields_with_delay(self, tm):
        # AMR-001 (priority=1) 먼저 점유
        tm.plan_with_yield("AMR-001", priority=1, start=WAYPOINTS["HOME"], goal=WAYPOINTS["SHIP"])
        # AMR-002 (priority=3) 같은 경로 시도 → 양보 발생
        p2 = tm.plan_with_yield(
            "AMR-002", priority=3, start=WAYPOINTS["HOME"], goal=WAYPOINTS["SHIP"]
        )
        assert p2.yielded is True
        assert p2.delay_sec > 0

    def test_higher_priority_evicts_existing_reservation(self, tm):
        # 낮은 priority 가 먼저 점유
        tm.plan_with_yield("AMR-002", priority=5, start=WAYPOINTS["HOME"], goal=WAYPOINTS["LOAD"])
        # 높은 priority 가 같은 경로 → 강제 회수
        p1 = tm.plan_with_yield(
            "AMR-001", priority=1, start=WAYPOINTS["HOME"], goal=WAYPOINTS["LOAD"]
        )
        # AMR-001 은 양보 없이 본래 경로
        assert p1.yielded is False
        assert "JUNCT_B" in p1.nodes  # 기본 경로 그대로

    def test_three_robots_concurrent_all_get_path(self, tm):
        plans = []
        for rid, prio, s, g in [
            ("AMR-A", 1, WAYPOINTS["HOME"], WAYPOINTS["SHIP"]),
            ("AMR-B", 2, WAYPOINTS["HOME"], WAYPOINTS["LOAD"]),
            ("AMR-C", 3, WAYPOINTS["POST"], WAYPOINTS["SHIP"]),
        ]:
            plans.append(tm.plan_with_yield(rid, prio, s, g))
        # 셋 다 빈 경로 아님 (모두 경로 확보)
        assert all(len(p.nodes) > 0 for p in plans)

    def test_cancel_releases_reservations(self, tm):
        tm.plan_with_yield("AMR-001", priority=1, start=WAYPOINTS["HOME"], goal=WAYPOINTS["SHIP"])
        tm.cancel("AMR-001")
        # 같은 priority 또는 더 낮아도 충돌 없이 진행 가능
        p = tm.plan_with_yield(
            "AMR-002", priority=5, start=WAYPOINTS["HOME"], goal=WAYPOINTS["SHIP"]
        )
        assert p.yielded is False

    def test_reset_clears_all_reservations(self, tm):
        tm.plan_with_yield("AMR-001", priority=1, start=WAYPOINTS["HOME"], goal=WAYPOINTS["SHIP"])
        tm.reset()
        p = tm.plan_with_yield(
            "AMR-002", priority=5, start=WAYPOINTS["HOME"], goal=WAYPOINTS["SHIP"]
        )
        assert p.yielded is False
