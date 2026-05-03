"""EventBridge — pub/sub 허브 (in-process).

설계 원칙:
    - 발행자/수신자 결합 해제: publisher 는 누가 듣는지 모르고 publish()
    - 발행 주체는 액션 수행자만 (EventBridge 자신은 publish 안 함)
    - handler 예외 격리: 한 handler 실패가 다른 handler 호출을 막지 않음
    - thread-safe: _handlers dict 접근은 threading.Lock
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from backend.management_v2.core.events import Event, EventType, PublishResult

logger = logging.getLogger(__name__)


@dataclass
class HandlerMeta:
    """내부 구독자 관리용 메타. dataclass — Callable 객체를 Pydantic 에 넣기 부적합."""

    event_type: EventType
    handler: Callable[[Event], None]
    subscriber_name: str
    registered_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@runtime_checkable
class IEventBridge(Protocol):
    """EventBridge 공개 인터페이스. 구현체는 본 Protocol 을 만족해야 한다."""

    def publish(self, event: Event) -> PublishResult: ...
    def subscribe(self, event_type: EventType, handler: Callable[[Event], None], subscriber_name: str) -> None: ...
    def unsubscribe(self, event_type: EventType, subscriber_name: str) -> bool: ...
    def list_subscribers(self, event_type: EventType | None = None) -> list[HandlerMeta]: ...


class EventBridgeImpl:
    """IEventBridge 의 thread-safe 구현체.

    Attributes:
        _handlers: event_type → HandlerMeta 리스트 (등록 순서 유지 → FIFO dispatch)
        _lock: threading.Lock — _handlers 접근 보호
    """

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[HandlerMeta]] = defaultdict(list)
        self._lock = threading.Lock()
        logger.info("EventBridgeImpl 초기화 완료")

    # publish ----------------------------------------------------------
    def publish(self, event: Event) -> PublishResult:
        # dispatch 중 lock 보유하지 않도록 스냅샷 복사
        with self._lock:
            handlers = list(self._handlers.get(event.event_type, []))

        success = 0
        failed = 0
        for meta in handlers:
            try:
                meta.handler(event)
                success += 1
            except Exception as exc:  # noqa: BLE001 — handler 격리 목적 광역 catch
                failed += 1
                logger.warning(
                    "EventBridge handler '%s' 실패 (%s): %s",
                    meta.subscriber_name,
                    event.event_type.value,
                    exc,
                    exc_info=True,
                )

        result = PublishResult(
            event_type=event.event_type,
            handlers_invoked=len(handlers),
            handlers_success=success,
            handlers_failed=failed,
            occurred_at=event.occurred_at,
        )
        logger.info(
            "EventBridge.publish: %s → invoked=%d success=%d failed=%d",
            event.event_type.value,
            result.handlers_invoked,
            result.handlers_success,
            result.handlers_failed,
        )
        return result

    # subscribe --------------------------------------------------------
    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], None],
        subscriber_name: str,
    ) -> None:
        if not subscriber_name or not subscriber_name.strip():
            raise ValueError("subscriber_name 은 빈 문자열일 수 없습니다")

        meta = HandlerMeta(
            event_type=event_type,
            handler=handler,
            subscriber_name=subscriber_name.strip(),
        )
        with self._lock:
            existing = self._handlers.get(event_type, [])
            # 같은 이름 등록 → 이전 핸들러 제거 후 새 핸들러 append (Test 3 가 보는 동작)
            filtered = [m for m in existing if m.subscriber_name != meta.subscriber_name]
            filtered.append(meta)
            self._handlers[event_type] = filtered

        logger.info(
            "EventBridge.subscribe: '%s' → %s",
            meta.subscriber_name,
            event_type.value,
        )

    # unsubscribe ------------------------------------------------------
    def unsubscribe(self, event_type: EventType, subscriber_name: str) -> bool:
        with self._lock:
            existing = self._handlers.get(event_type, [])
            before = len(existing)
            filtered = [m for m in existing if m.subscriber_name != subscriber_name]
            self._handlers[event_type] = filtered
            removed = before - len(filtered)

        if removed > 0:
            logger.info(
                "EventBridge.unsubscribe: '%s' → %s",
                subscriber_name,
                event_type.value,
            )
            return True
        return False

    # list_subscribers -------------------------------------------------
    def list_subscribers(
        self,
        event_type: EventType | None = None,
    ) -> list[HandlerMeta]:
        with self._lock:
            if event_type is None:
                all_metas: list[HandlerMeta] = []
                for metas in self._handlers.values():
                    all_metas.extend(metas)
                return sorted(all_metas, key=lambda m: m.registered_at)
            return list(self._handlers.get(event_type, []))
