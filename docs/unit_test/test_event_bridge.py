"""EventBridgeImpl 단위 테스트 — V1.

가짜 함수만 쓰고, DB / 다른 컴포넌트 / HW 안 부른다.
V1 은 EventBridge 자체 계약 (publish/subscribe/unsubscribe + 세 줄 약속) 만 본다.
"""

from __future__ import annotations

import threading

import pytest

from backend.management_v2.core.events import Event, EventType
from backend.management_v2.services.event_bridge import EventBridgeImpl


@pytest.fixture
def bridge() -> EventBridgeImpl:
    return EventBridgeImpl()


# Test 1) 등록한 핸들러를 등록 순서대로 한 번씩 호출 (0명 케이스 같이 검증)
def test_publish_invokes_subscribers_in_order(bridge):
    # 0명일 때 안 깨지는지
    empty_result = bridge.publish(Event(event_type=EventType.TASK_CREATED, txn_id=1))
    assert (empty_result.handlers_invoked, empty_result.handlers_success) == (0, 0)

    # 등록 순서대로 호출되는지
    call_order: list[str] = []
    for name in ("first", "second", "third"):
        bridge.subscribe(
            EventType.TASK_STARTED,
            lambda _e, n=name: call_order.append(n),
            name,
        )

    event = Event(event_type=EventType.TASK_STARTED, txn_id=101, resource_id="RA1")
    result = bridge.publish(event)

    assert call_order == ["first", "second", "third"]
    assert result.handlers_invoked == 3 and result.handlers_success == 3


# Test 2) 한 명이 예외 던져도 나머지는 계속 돈다. publish 자체는 예외 안 냄.
def test_failing_handler_does_not_block_others(bridge):
    succeeded: list[str] = []

    def failing(_event: Event) -> None:
        raise RuntimeError("일부러 던지는 예외")

    bridge.subscribe(EventType.TASK_FAILED, failing, "broken")
    bridge.subscribe(EventType.TASK_FAILED, lambda _e: succeeded.append("ok"), "good")

    result = bridge.publish(Event(event_type=EventType.TASK_FAILED, txn_id=99, resource_id="RA2"))

    assert result.handlers_invoked == 2
    assert result.handlers_success == 1
    assert result.handlers_failed == 1
    assert succeeded == ["ok"]


# Test 3) 같은 이름으로 또 등록하면 새 걸로 갈아치움
def test_subscribe_replaces_handler_with_same_name(bridge):
    calls: list[str] = []
    bridge.subscribe(EventType.TASK_CREATED, lambda _e: calls.append("old"), "same")
    bridge.subscribe(EventType.TASK_CREATED, lambda _e: calls.append("new"), "same")

    bridge.publish(Event(event_type=EventType.TASK_CREATED, txn_id=1))

    assert calls == ["new"]
    assert len(bridge.list_subscribers(EventType.TASK_CREATED)) == 1


# Test 4) 등록한 거 unsubscribe → True, 모르는 거 → False (예외 안 던짐)
def test_unsubscribe_returns_true_or_false(bridge):
    bridge.subscribe(EventType.HANDOFF_ACK, lambda _e: None, "amr.fsm")

    assert bridge.unsubscribe(EventType.HANDOFF_ACK, "amr.fsm") is True
    assert bridge.unsubscribe(EventType.HANDOFF_ACK, "ghost") is False


# Test 5) thread 4개 동시 실행해도 누락 / 중복 없음
def test_concurrent_publish_is_threadsafe(bridge):
    counter: list[int] = []
    counter_lock = threading.Lock()

    def collector(_event: Event) -> None:
        with counter_lock:
            counter.append(1)

    bridge.subscribe(EventType.ALERT_RAISED, collector, "alert.audit")

    def worker_publish() -> None:
        for _ in range(100):
            bridge.publish(
                Event(
                    event_type=EventType.ALERT_RAISED,
                    payload={"severity": "info", "message": "heartbeat"},
                )
            )

    def worker_subscribe(idx: int) -> None:
        for i in range(50):
            bridge.subscribe(EventType.ALERT_RAISED, lambda _e: None, f"sub-{idx}-{i}")

    threads = [
        threading.Thread(target=worker_publish),
        threading.Thread(target=worker_subscribe, args=(0,)),
        threading.Thread(target=worker_publish),
        threading.Thread(target=worker_subscribe, args=(1,)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    assert len(counter) == 200
