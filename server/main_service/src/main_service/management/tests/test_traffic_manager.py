from pprint import pprint

import pytest

from enums import TransTaskType
from traffic_manager import RoutePermissionInput, TrafficDecisionType, TrafficManager


# =========================================================
# Fixture
# =========================================================

@pytest.fixture
def tm():
    return TrafficManager()


# =========================================================
# 1. 기본 경로 생성 테스트
# =========================================================

def test_basic_route_success(tm):
    req = RoutePermissionInput(
        trans_task_txn_id=1,
        trans_id="AMR-A",
        task_type=TransTaskType.ToPP,
    )

    result = tm.request_route_permission(req)

    print("\n=== test_basic_route_success ===")
    print("Decision:", result.decision)
    print("Route Nodes:", result.route_nodes)
    print("Reservation ID:", result.reservation_id)
    print("===============================\n")

    assert result.decision == TrafficDecisionType.GO
    assert len(result.route_nodes) > 0


# =========================================================
# 2. 동일 trans_id 재요청
# =========================================================

def test_duplicate_trans_id_replaces_reservation(tm):
    req = RoutePermissionInput(
        trans_task_txn_id=1,
        trans_id="AMR-A",
        task_type=TransTaskType.ToPP,
    )

    first = tm.request_route_permission(req)
    second = tm.request_route_permission(req)

    reservations = tm.list_reservations()

    print("\n=== test_duplicate_trans_id ===")
    print("First reservation:", first.reservation_id)
    print("Second reservation:", second.reservation_id)
    print("Active reservations:")
    pprint(reservations)
    print("===============================\n")

    assert len(reservations) == 1
    assert reservations[0].reservation_id == second.reservation_id


# =========================================================
# 3. 충돌 상황 테스트
# =========================================================

def test_conflict_hold(tm):
    req_a = RoutePermissionInput(
        trans_task_txn_id=1,
        trans_id="A",
        task_type=TransTaskType.ToPP,
    )

    req_b = RoutePermissionInput(
        trans_task_txn_id=2,
        trans_id="B",
        task_type=TransTaskType.ToSTRG,
    )

    result_a = tm.request_route_permission(req_a)
    result_b = tm.request_route_permission(req_b)

    print("\n=== test_conflict_hold ===")
    print("A Decision:", result_a.decision)
    print("B Decision:", result_b.decision)
    print("=========================\n")

    assert result_b.decision in [
        TrafficDecisionType.GO,
        TrafficDecisionType.HOLD,
    ]


# =========================================================
# 4. 전체 예약 해제
# =========================================================

def test_release_reservation(tm):
    req = RoutePermissionInput(
        trans_task_txn_id=1,
        trans_id="A",
        task_type=TransTaskType.ToPP,
    )

    decision = tm.request_route_permission(req)

    print("\n=== BEFORE RELEASE ===")
    pprint(tm.list_reservations())

    success = tm.release_reservation(decision.reservation_id)

    print("=== AFTER RELEASE ===")
    pprint(tm.list_reservations())
    print("=====================\n")

    assert success is True
    assert len(tm.list_reservations()) == 0


# =========================================================
# 5. 부분 edge 해제
# =========================================================

def test_release_passed_edge(tm):
    req = RoutePermissionInput(
        trans_task_txn_id=1,
        trans_id="A",
        task_type=TransTaskType.ToPP,
    )

    decision = tm.request_route_permission(req)

    if not decision.path_steps:
        pytest.skip("No path generated")

    step = decision.path_steps[0]

    print("\n=== test_release_passed_edge ===")
    print("Releasing edge:", step.edge)

    success = tm.release_passed_edge(
        reservation_id=decision.reservation_id,
        edge=step.edge,
    )

    print("Success:", success)
    print("===============================\n")

    assert success is True


# =========================================================
# 6. timeout 처리
# =========================================================

def test_handle_timeouts(tm):
    req = RoutePermissionInput(
        trans_task_txn_id=1,
        trans_id="A",
        task_type=TransTaskType.ToPP,
    )

    decision = tm.request_route_permission(req)

    reservation = tm.get_reservation(decision.reservation_id)

    print("\n=== BEFORE TIMEOUT ===")
    pprint(tm.list_reservations())

    # 강제 만료
    reservation.expires_at = reservation.created_at

    expired = tm.handle_timeouts()

    print("Expired reservations:", expired)
    print("=== AFTER TIMEOUT ===")
    pprint(tm.list_reservations())
    print("=====================\n")

    assert len(expired) == 1
    assert len(tm.list_reservations()) == 0


# =========================================================
# 7. finished history 저장
# =========================================================

def test_finished_history(tm):
    req = RoutePermissionInput(
        trans_task_txn_id=1,
        trans_id="A",
        task_type=TransTaskType.ToPP,
    )

    decision = tm.request_route_permission(req)

    tm.release_reservation(decision.reservation_id)

    finished = tm.list_finished_reservations()

    print("\n=== test_finished_history ===")
    pprint(finished)
    print("=============================\n")

    assert len(finished) == 1
    assert finished[0].final_status.name == "RELEASED"
