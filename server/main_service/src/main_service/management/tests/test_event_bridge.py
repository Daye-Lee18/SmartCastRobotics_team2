"""EventBridge 계약 테스트 (Contract Section 6 Result 기준).

대응 구현: backend/management/services/event_bridge.py
검증 항목은 계약 파일의 섹션 6 "RESULT" 에 명시된 기준을 그대로 따른다.
"""

from __future__ import annotations

import threading
import time

import pytest
from services.core.event_bridge import (
    Event,
    EventBridgeImpl,
    EventType,
    IEventBridge,
    PublishResult,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def bridge() -> EventBridgeImpl:
    """매 테스트마다 깨끗한 EventBridgeImpl."""
    return EventBridgeImpl()


@pytest.fixture
def sample_event() -> Event:
    return Event(event_type=EventType.TASK_CREATED, txn_id=1, ord_id=1, item_id=1)


# ============================================================================
# Protocol 만족 검증
# ============================================================================


def test_impl_satisfies_protocol(bridge):
    """EventBridgeImpl 이 IEventBridge Protocol 을 만족한다."""
    assert isinstance(bridge, IEventBridge)


# ============================================================================
# publish() 성공 기준
# ============================================================================


def test_publish_with_no_subscribers_returns_zero_counts(bridge, sample_event):
    """구독자가 0개여도 publish() 는 정상 완료, 카운트 전부 0."""
    result = bridge.publish(sample_event)
    assert isinstance(result, PublishResult)
    assert result.handlers_invoked == 0
    assert result.handlers_success == 0
    assert result.handlers_failed == 0
    assert result.event_type == EventType.TASK_CREATED


def test_publish_invokes_single_handler(bridge, sample_event):
    """등록된 handler 가 정확히 1회 호출되고 카운트에 반영된다."""
    received: list[Event] = []
    bridge.subscribe(EventType.TASK_CREATED, received.append, "test_sub")

    result = bridge.publish(sample_event)

    assert len(received) == 1
    assert received[0].txn_id == 1
    assert result.handlers_invoked == 1
    assert result.handlers_success == 1
    assert result.handlers_failed == 0


def test_publish_invokes_multiple_handlers_in_registration_order(bridge, sample_event):
    """복수 handler 가 등록 순서 (FIFO) 대로 호출된다."""
    order: list[str] = []
    bridge.subscribe(EventType.TASK_CREATED, lambda e: order.append("first"), "sub_1")
    bridge.subscribe(EventType.TASK_CREATED, lambda e: order.append("second"), "sub_2")
    bridge.subscribe(EventType.TASK_CREATED, lambda e: order.append("third"), "sub_3")

    result = bridge.publish(sample_event)

    assert order == ["first", "second", "third"]
    assert result.handlers_invoked == 3
    assert result.handlers_success == 3


def test_publish_routes_by_event_type(bridge):
    """다른 event_type 의 구독자는 호출되지 않는다."""
    created_calls: list[Event] = []
    failed_calls: list[Event] = []
    bridge.subscribe(EventType.TASK_CREATED, created_calls.append, "on_created")
    bridge.subscribe(EventType.TASK_FAILED, failed_calls.append, "on_failed")

    bridge.publish(Event(event_type=EventType.TASK_CREATED, txn_id=1))

    assert len(created_calls) == 1
    assert len(failed_calls) == 0


# ============================================================================
# publish() 실패 격리 기준
# ============================================================================


def test_failing_handler_does_not_block_other_handlers(bridge, sample_event):
    """한 handler 예외가 다른 handler 호출을 막지 않는다."""
    calls: list[str] = []

    def failing(_e):
        calls.append("failing")
        raise RuntimeError("boom")

    def good(_e):
        calls.append("good")

    bridge.subscribe(EventType.TASK_CREATED, failing, "bad_sub")
    bridge.subscribe(EventType.TASK_CREATED, good, "good_sub")

    result = bridge.publish(sample_event)

    assert "failing" in calls
    assert "good" in calls  # 실패 이후에도 호출됨
    assert result.handlers_invoked == 2
    assert result.handlers_success == 1
    assert result.handlers_failed == 1


def test_publish_itself_does_not_raise_on_handler_exception(bridge, sample_event):
    """publish() 는 handler 예외를 다시 던지지 않는다 (격리)."""
    bridge.subscribe(
        EventType.TASK_CREATED,
        lambda e: (_ for _ in ()).throw(ValueError("handler error")),
        "bad",
    )
    # 예외 없이 PublishResult 반환
    result = bridge.publish(sample_event)
    assert result.handlers_failed == 1


# ============================================================================
# subscribe() 기준
# ============================================================================


def test_subscribe_with_empty_name_raises(bridge):
    """빈 subscriber_name 은 ValueError."""
    with pytest.raises(ValueError):
        bridge.subscribe(EventType.TASK_CREATED, lambda e: None, "")


def test_subscribe_with_whitespace_only_name_raises(bridge):
    """공백만 있는 subscriber_name 도 거부."""
    with pytest.raises(ValueError):
        bridge.subscribe(EventType.TASK_CREATED, lambda e: None, "   ")


def test_subscribe_same_name_replaces_existing(bridge, sample_event):
    """동일 subscriber_name 등록 시 기존 handler 를 교체한다."""
    calls: list[str] = []

    bridge.subscribe(EventType.TASK_CREATED, lambda e: calls.append("old"), "sub_x")
    bridge.subscribe(EventType.TASK_CREATED, lambda e: calls.append("new"), "sub_x")

    bridge.publish(sample_event)

    assert calls == ["new"]  # old handler 는 호출되지 않음


def test_subscribe_strips_whitespace_from_name(bridge):
    """subscriber_name 양 끝 공백은 제거된다."""
    bridge.subscribe(EventType.TASK_CREATED, lambda e: None, "  padded  ")
    subs = bridge.list_subscribers(EventType.TASK_CREATED)
    assert len(subs) == 1
    assert subs[0].subscriber_name == "padded"


# ============================================================================
# unsubscribe() 기준
# ============================================================================


def test_unsubscribe_removes_handler(bridge, sample_event):
    """unsubscribe 후 해당 handler 는 호출되지 않는다."""
    calls: list[str] = []
    bridge.subscribe(EventType.TASK_CREATED, lambda e: calls.append("kept"), "keep")
    bridge.subscribe(EventType.TASK_CREATED, lambda e: calls.append("removed"), "remove_me")

    ok = bridge.unsubscribe(EventType.TASK_CREATED, "remove_me")
    bridge.publish(sample_event)

    assert ok is True
    assert calls == ["kept"]


def test_unsubscribe_returns_false_for_unknown_name(bridge):
    """등록되지 않은 subscriber_name unsubscribe → False (예외 아님)."""
    result = bridge.unsubscribe(EventType.TASK_CREATED, "never_registered")
    assert result is False


# ============================================================================
# list_subscribers() 기준
# ============================================================================


def test_list_subscribers_filtered_by_event_type(bridge):
    """event_type 지정 시 해당 타입 구독자만 반환."""
    bridge.subscribe(EventType.TASK_CREATED, lambda e: None, "c1")
    bridge.subscribe(EventType.TASK_CREATED, lambda e: None, "c2")
    bridge.subscribe(EventType.TASK_FAILED, lambda e: None, "f1")

    created_subs = bridge.list_subscribers(EventType.TASK_CREATED)
    failed_subs = bridge.list_subscribers(EventType.TASK_FAILED)

    assert {m.subscriber_name for m in created_subs} == {"c1", "c2"}
    assert {m.subscriber_name for m in failed_subs} == {"f1"}


def test_list_subscribers_all_when_event_type_none(bridge):
    """event_type=None 이면 전체 구독자 반환."""
    bridge.subscribe(EventType.TASK_CREATED, lambda e: None, "c1")
    bridge.subscribe(EventType.TASK_FAILED, lambda e: None, "f1")
    bridge.subscribe(EventType.HANDOFF_ACK, lambda e: None, "h1")

    all_subs = bridge.list_subscribers(None)

    assert len(all_subs) == 3
    assert {m.subscriber_name for m in all_subs} == {"c1", "f1", "h1"}


def test_list_subscribers_returns_copy_not_internal_reference(bridge):
    """반환된 리스트를 외부에서 변조해도 내부 영향 없음."""
    bridge.subscribe(EventType.TASK_CREATED, lambda e: None, "safe")
    external = bridge.list_subscribers(EventType.TASK_CREATED)
    external.clear()

    # 내부 상태는 유지
    assert len(bridge.list_subscribers(EventType.TASK_CREATED)) == 1


# ============================================================================
# Thread Safety
# ============================================================================


def test_concurrent_publish_is_threadsafe(bridge):
    """여러 스레드에서 동시 publish 해도 누락 없이 handler 호출."""
    counter = {"value": 0}
    lock = threading.Lock()

    def handler(_e):
        with lock:
            counter["value"] += 1

    bridge.subscribe(EventType.TASK_CREATED, handler, "counter")

    num_threads = 10
    publishes_per_thread = 20

    def worker():
        for _ in range(publishes_per_thread):
            bridge.publish(Event(event_type=EventType.TASK_CREATED, txn_id=1))

    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert counter["value"] == num_threads * publishes_per_thread


def test_concurrent_subscribe_and_publish(bridge):
    """구독 등록과 publish 가 동시에 일어나도 race 없이 일관성 유지."""
    results: list[int] = []

    def subscriber_thread():
        for i in range(50):
            bridge.subscribe(
                EventType.TASK_CREATED,
                lambda e: results.append(1),
                f"sub_{i}",
            )

    def publisher_thread():
        for _ in range(50):
            bridge.publish(Event(event_type=EventType.TASK_CREATED))
            time.sleep(0.001)

    t1 = threading.Thread(target=subscriber_thread)
    t2 = threading.Thread(target=publisher_thread)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # 구체 횟수는 스케줄링 의존이지만 최종 구독자 수는 50 이어야 함
    subs = bridge.list_subscribers(EventType.TASK_CREATED)
    assert len(subs) == 50


# ============================================================================
# Event 페이로드 전달 검증
# ============================================================================


def test_event_payload_fields_passed_through(bridge):
    """Event 의 모든 필드가 handler 에 원본 그대로 전달된다."""
    captured: dict = {}

    def handler(e: Event):
        captured["event_type"] = e.event_type
        captured["txn_id"] = e.txn_id
        captured["ord_id"] = e.ord_id
        captured["item_id"] = e.item_id
        captured["resource_id"] = e.resource_id
        captured["payload"] = e.payload

    bridge.subscribe(EventType.TASK_FAILED, handler, "capture")

    e = Event(
        event_type=EventType.TASK_FAILED,
        txn_id=42,
        ord_id=99,
        item_id=7,
        resource_id="PAT",
        payload={"error_code": "E001", "reason": "grip_fail"},
    )
    bridge.publish(e)

    assert captured["event_type"] == EventType.TASK_FAILED
    assert captured["txn_id"] == 42
    assert captured["ord_id"] == 99
    assert captured["item_id"] == 7
    assert captured["resource_id"] == "PAT"
    assert captured["payload"] == {"error_code": "E001", "reason": "grip_fail"}


# ============================================================================
# Event 자체 검증 (Pydantic)
# ============================================================================


def test_event_occurred_at_auto_default():
    """occurred_at 을 명시하지 않으면 현재 시각이 자동 부여."""
    e = Event(event_type=EventType.TASK_CREATED)
    assert e.occurred_at is not None
    # timezone-aware 확인
    assert e.occurred_at.tzinfo is not None
