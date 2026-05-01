"""
################################################################################
#                                                                              #
#   Interface Contract  —  EventBridge                                         #
#                                                                              #
################################################################################

이 파일의 목적:
    관제 시스템 전반의 "상태 변화 전파" 를 중재하는 in-process 이벤트 허브.
    Confluence 41648180 (관제 개발 프로세스 정리) 의 6개 역할 중 "흐름 연결"
    담당. 다른 컴포넌트가 이벤트를 발행하면 구독자에게 라우팅한다.

적용 범위 (중요):
    EventBridge 는 ★ 상태 변화 전파 전용 ★.
    CRUD, 명령, 조회는 EventBridge 를 거치지 않고 직접 호출해야 한다.
    판단 기준 (하이브리드 설계):
        응답 필요 → 직접 호출 (State Manager / Robot Executor / Adapter)
        1:1 명령  → 직접 호출
        트랜잭션  → 직접 호출
        상태 전파 → EventBridge (publish → 1:N 구독자)
        워크플로우 트리거 → EventBridge (TASK_COMPLETED → 다음 공정)

관련 문서:
    - docs/event_bridge_design.html (SVG 관계도 + 시퀀스)
    - Confluence 41648180 (6개 역할 + polling→event 단계 전환)
    - Confluence 42205202 (코드 interface contracts 가이드)
"""

from __future__ import annotations

# ── 필수 import ────────────────────────────────────────────────────────────────
import logging
import threading
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. OVERVIEW  ←  역할 정의 (문서화)
#    "이 컴포넌트가 왜 존재하는가"를 한 문단으로 설명합니다.
#    → 어디에 반영: INTERFACE_CONTRACTS.md 문서 / 본 docstring
# ==============================================================================
"""
[EventBridge]

역할:
    관제 시스템의 컴포넌트 간 상태 변화를 느슨한 결합(loose coupling) 으로
    중계하는 in-process pub/sub 허브. 발행자(publisher) 는 수신자가 누구인지
    모른 채 publish() 로 이벤트를 보내고, 구독자(subscriber) 는 subscribe()
    로 관심 이벤트 타입을 등록한다. Bridge 는 매핑 테이블을 보고 등록된
    handler 를 호출한다.

책임 범위:
    - 이벤트 타입별 구독자 등록/해제 (subscribe / unsubscribe)
    - 이벤트 발행 시 모든 구독자 handler 호출 (publish)
    - handler 호출 오류 격리 — 한 handler 실패가 다른 handler 에 전파되지 않음
    - 이벤트 발행/수신 감사 로그

책임 밖:
    - DB read / write → StateManager
    - 장비 명령 발행 → RobotExecutor
    - 설비 배정 결정 → TaskAllocator
    - 이벤트 스스로 생성 (★ 이벤트 발행 주체는 액션 수행자 에 고정)
    - 외부 네트워크 통신 (in-process 전용, 프로세스 경계를 넘지 않음)
    - 이벤트 영속화 (저장이 필요하면 구독자에서 StateManager 호출)

판단 기준 (무엇을 이벤트로, 무엇을 직접 호출로):
    이벤트 (publish)    : 상태 변화 전파, 워크플로우 트리거, N개 구독자, 응답 불필요
    직접 호출 (call)     : CRUD, 1:1 명령, 응답 필요, 트랜잭션 원자성 필요
"""


# ==============================================================================
# 2. ENUM  ←  상태값을 코드에서 강제
#    EventBridge 는 DB 상태 전이를 갖지 않지만, 이벤트 타입과 전달 상태를
#    Enum 으로 선언한다.
#    → 어디에 반영: Enum 코드
# ==============================================================================


class EventType(StrEnum):
    """
    시스템 전반에서 발행 가능한 이벤트 타입.

    분류:
      - 관리자 액션 발 이벤트  : ORDER_APPROVED
      - Task 생명주기 이벤트    : TASK_CREATED, TASK_STARTED, TASK_COMPLETED, TASK_FAILED
      - 외부 입력 이벤트         : HANDOFF_ACK, RFID_SCANNED
      - 상태 변화 이벤트         : STATE_CHANGED

    새 이벤트 추가 시 규칙:
      - 명명: 대문자 + 언더스코어 (예: AMR_DOCKED)
      - 문서화: 섹션 5 이벤트 카탈로그에 발행 조건 + 수신 컴포넌트 기입 필수
      - 발행 주체가 EventBridge 자신이 되지 않도록 주의 (외부 액션 수행자만 발행)
    """

    # 관리자 액션
    ORDER_APPROVED = "ORDER_APPROVED"  # 관리자가 발주 승인 (ord_stat RCVD → APPR)

    # Task 생명주기
    TASK_CREATED = "TASK_CREATED"  # TaskManager.create_task() 성공 후
    TASK_STARTED = "TASK_STARTED"  # QUE → PROC 전이 완료 시
    TASK_COMPLETED = "TASK_COMPLETED"  # PROC → SUCC 전이 완료 시
    TASK_FAILED = "TASK_FAILED"  # PROC → FAIL 전이 완료 시

    # 외부 입력 (하드웨어 이벤트)
    HANDOFF_ACK = "HANDOFF_ACK"  # ESP32 GPIO 33 버튼 눌림 (SPEC-AMR-001 Wave 3)
    RFID_SCANNED = "RFID_SCANNED"  # RFID / 바코드 태그 인식 (SPEC-RFID-001)

    # 상태 변화
    STATE_CHANGED = "STATE_CHANGED"  # 일반 상태 변경 (WebSocket broadcast 용)


class DeliveryStatus(StrEnum):
    """
    개별 handler 호출 결과.
    publish() 의 로그/감사 반환에 사용. DB 기록 아님.
    """

    SUCCESS = "SUCCESS"  # handler 정상 완료
    FAILED = "FAILED"  # handler 예외 발생 (다른 handler 호출은 계속)


# EventBridge 는 상태 전이 규칙이 필요 없음 (stateless router).
# Task 처럼 QUE→PROC→SUCC 흐름이 없으므로 _TRANSITIONS dict 미정의.


# ==============================================================================
# 3. DATATYPE  ←  데이터 구조 정의
#    Pydantic BaseModel 선언 + dataclass (핸들러 메타용) 혼용
#    → 어디에 반영: Pydantic 모델 + dataclass
# ==============================================================================


class Event(BaseModel):
    """
    publish() 로 발행되는 이벤트 페이로드.

    공통 필드 + 이벤트 타입별 자유 payload dict 로 확장성 확보.
    구독자는 event_type 을 보고 payload 의 스키마를 해석한다.
    """

    event_type: EventType
    # 공통 필드 (해당 없으면 None)
    txn_id: int | None = Field(default=None, description="equip_task_txn / trans_task_txn ID")
    ord_id: int | None = Field(default=None, description="발주 ID")
    item_id: int | None = Field(default=None, description="item ID")
    resource_id: str | None = Field(default=None, description="AMR / RA / CONV ID")
    # 타입별 자유 payload
    payload: dict = Field(default_factory=dict, description="이벤트 타입별 추가 데이터")
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_id: str | None = Field(default=None, description="감사 추적용 고유 ID (옵션)")


class SubscribeInput(BaseModel):
    """subscribe() 입력값 — Pydantic 검증용 (handler 는 별도 인자)"""

    event_type: EventType
    subscriber_name: str = Field(..., min_length=1, description="구독자 식별자 (디버깅/로그용)")


class PublishResult(BaseModel):
    """publish() 반환값 — 감사/디버깅용 요약"""

    event_type: EventType
    handlers_invoked: int
    handlers_success: int
    handlers_failed: int
    occurred_at: datetime


@dataclass
class HandlerMeta:
    """
    내부 구독자 관리용 메타. 외부 공개 아님.
    dataclass 사용 이유: Callable 객체를 Pydantic 에 넣기 부적합.
    """

    event_type: EventType
    handler: Callable[[Event], None]
    subscriber_name: str
    registered_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ==============================================================================
# 4. INPUT / OUTPUT  ←  인터페이스 계약 (Protocol)
#    Protocol로 선언 → 구현 클래스가 이 시그니처를 반드시 따라야 함
#    → 어디에 반영: Protocol + Pydantic
# ==============================================================================


@runtime_checkable
class IEventBridge(Protocol):
    """
    EventBridge 가 외부에 노출하는 공개 인터페이스.
    구현체는 반드시 이 Protocol 을 만족해야 한다.

    INPUT  → Event (publish), event_type + handler + subscriber_name (subscribe)
    OUTPUT → PublishResult (publish), None (subscribe/unsubscribe)
    """

    def publish(self, event: Event) -> PublishResult:
        """
        이벤트를 모든 구독 handler 에게 라우팅한다.

        Input:  Event (섹션 3)
        Output: PublishResult (감사 요약)
        Raises: 하지 않음 — handler 예외는 내부에서 격리·로깅
        Side Effects:
          - 등록된 handler(들) 호출
          - INFO 로그 "Event published: {event_type}"
          - handler 실패 시 WARN 로그 (다른 handler 호출은 계속)
        """
        ...

    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], None],
        subscriber_name: str,
    ) -> None:
        """
        특정 EventType 에 handler 를 등록한다.

        Input:
          - event_type: 수신할 이벤트 타입
          - handler:   Event → None 시그니처의 callable
          - subscriber_name: 로그/디버깅용 식별자 (예: "TaskAllocator.on_task_created")
        Output: None
        Raises: ValueError — subscriber_name 이 빈 문자열
        Side Effects: _handlers[event_type] 리스트에 HandlerMeta 추가
        """
        ...

    def unsubscribe(
        self,
        event_type: EventType,
        subscriber_name: str,
    ) -> bool:
        """
        등록된 handler 를 해제한다. subscriber_name 으로 식별.

        Input:  event_type, subscriber_name
        Output: True — 해제 성공 / False — 해당 구독자 없음
        Side Effects: _handlers[event_type] 에서 해당 항목 제거
        """
        ...

    def list_subscribers(self, event_type: EventType | None = None) -> list[HandlerMeta]:
        """
        등록된 구독자 목록을 반환 (디버깅/모니터링용).

        Input:  event_type (None 이면 전체)
        Output: HandlerMeta 리스트 (registered_at 오름차순)
        Side Effects: 없음 (read-only)
        """
        ...


# ==============================================================================
# 5. EVENT  ←  시스템 상태가 바뀌는 지점 (물리/DB)
#    EventBridge 자체는 이벤트를 발생시키지 않지만, "중계하는 이벤트 카탈로그"
#    를 본 컴포넌트의 계약에 명시한다. 새 EventType 추가 시 이 표도 갱신한다.
#    → 어디에 반영: 문서 + EventType Enum (섹션 2)
# ==============================================================================
"""
[EventBridge 가 중계하는 이벤트 카탈로그]

이벤트                발행 주체                 발생 조건                                  수신 컴포넌트 (구독자)
─────────────────────────────────────────────────────────────────────────────────────────────────
ORDER_APPROVED        Admin API Handler         PyQt "생산 시작" 버튼 → Management.Start    TaskManager.on_order_approved
                                                Production RPC 호출 + ord_stat=APPR 저장 후

TASK_CREATED          TaskManager               create_task() 성공 후                      TaskAllocator.on_task_created
                                                                                           AuditLogger.on_task_created

TASK_STARTED          RobotExecutor             equip_task_txn.txn_stat QUE→PROC 전이      AuditLogger.on_task_started
                      (또는 Adapter)             완료 시

TASK_COMPLETED        RobotExecutor             equip_task_txn.txn_stat PROC→SUCC 전이     EventBridge 구독: 다음 공정
                                                완료 시                                      TaskManager.on_task_completed
                                                                                           AuditLogger
                                                                                           WebSocket broadcaster

TASK_FAILED           RobotExecutor             equip_task_txn.txn_stat PROC→FAIL 전이     StateManager.on_task_failed
                                                완료 시                                      (설비 ERROR 마킹)
                                                                                           AlertService

HANDOFF_ACK           Management RPC Handler    ReportHandoffAck gRPC 수신 + DB append 후  AmrStateMachine.on_handoff_ack
                      (외부 입력: ESP32 버튼)                                                WebSocket broadcaster

RFID_SCANNED          Management RPC Handler    ReportRfidScan gRPC 수신 + rfid_scan_log   ItemBinder.on_rfid_scanned
                      (외부 입력: RFID/바코드)   append 후                                   WebSocket broadcaster

STATE_CHANGED         StateManager              주요 상태 UPDATE 직후 (설비/AMR/주문 등)   WebSocket broadcaster
                                                                                           AuditLogger

[EventBridge 가 발행하지 않는 것 (중요)]
  ✗ EventBridge 자신은 publish() 호출자가 되지 않는다.
  ✗ 이벤트는 반드시 "상태를 실제로 바꾼 액션 수행자" 가 발행한다.
    (Confluence 41648180 의 고정 규칙: 이벤트 발행 주체 = Executor/액션 수행자)

[구독 등록 시점]
  - Management Service 부팅 시 `wire_event_bridge(bridge, task_mgr, allocator, ...)` 가 모든
    subscribe() 호출을 한 번에 수행한다. 런타임 중 동적 subscribe 는 현재 미지원 범위 밖.
"""


# ==============================================================================
# 6. RESULT  ←  인터페이스의 성공/실패 기준
#    테스트 파일(tests/test_event_bridge.py) 에서 이 기준을 검증한다.
#    → 어디에 반영: 테스트 코드
# ==============================================================================
"""
[publish() 성공 기준]
  ✅ 등록된 handler 가 모두 한 번씩 호출됨
  ✅ PublishResult.handlers_invoked == 등록된 구독자 수
  ✅ PublishResult.handlers_success == 예외 없이 완료된 handler 수
  ✅ 구독자가 0 개여도 예외 없이 PublishResult 반환
  ✅ 등록 순서대로 handler 호출 (FIFO)

[publish() 실패 격리 기준]
  ✅ 한 handler 가 예외 던져도 다른 handler 는 정상 호출됨
  ✅ publish() 자체는 예외를 다시 던지지 않음 (handler 예외는 WARN 로그)
  ✅ PublishResult.handlers_failed 에 실패 개수 반영

[subscribe() 성공 기준]
  ✅ list_subscribers(event_type) 에 등록된 항목 포함
  ✅ 동일 subscriber_name 중복 등록 시 기존 것 교체 (덮어쓰기)

[subscribe() 실패 기준]
  ❌ subscriber_name 이 빈 문자열 → ValueError

[unsubscribe() 성공 기준]
  ✅ 해제 후 해당 구독자는 publish() 호출 대상에서 제외
  ✅ 반환값 True

[unsubscribe() 실패 기준]
  ✅ 등록되지 않은 subscriber_name → 반환값 False (예외 아님)

[Thread Safety 기준]
  ✅ 동시 publish/subscribe 호출 시 _handlers dict 일관성 유지 (threading.Lock)
  ✅ handler 호출 자체는 publish() 스레드에서 동기 실행
      (비동기는 향후 AsyncEventBridge 로 확장)

[테스트 파일 위치]
  backend/management/tests/test_event_bridge.py

[테스트 케이스 예시]
  - test_publish_with_no_subscribers_returns_zero_counts
  - test_publish_invokes_single_handler
  - test_publish_invokes_multiple_handlers_in_order
  - test_failing_handler_does_not_block_others
  - test_subscribe_with_empty_name_raises
  - test_subscribe_same_name_replaces_existing
  - test_unsubscribe_returns_false_for_unknown_name
  - test_list_subscribers_filtered_by_event_type
  - test_concurrent_publish_is_threadsafe
"""


# ==============================================================================
# 7. SIDE EFFECTS  ←  시스템에 미치는 영향
#    실제 구현 — stub 이 아닌 완성본 (단순 dispatch 이라 stub 불필요).
#    → 어디에 반영: 실제 구현 코드
# ==============================================================================


class EventBridgeImpl:
    """
    IEventBridge 의 실제 구현체.

    이 구현의 Side Effects:
      publish()
        → 등록된 모든 handler 호출 (등록 순서 = 호출 순서)
        → handler 예외는 격리 + WARN 로그 (publish 자체는 예외 전파 X)
        → INFO 로그: "Event published: {event_type} → {N} handlers"
        → DB 접근 없음 ★

      subscribe()
        → self._handlers[event_type] 에 HandlerMeta 추가
        → 기존 동일 subscriber_name 이 있으면 교체
        → INFO 로그: "Subscribed {subscriber_name} to {event_type}"

      unsubscribe()
        → self._handlers[event_type] 에서 subscriber_name 항목 제거
        → 삭제 여부 반환

      list_subscribers()
        → 읽기 전용 — dict 복사본 반환 (외부에서 수정해도 내부 영향 없음)

    Thread Safety:
      - _handlers dict 접근은 self._lock (threading.Lock) 으로 보호
      - handler 호출은 publish() 스레드에서 동기 실행
      - 여러 스레드가 동시 publish 해도 각 event 의 handler 리스트는
        스냅샷 복사본으로 dispatch (publish 중 lock 해제)

    금지 행위 (설계 원칙):
      ✗ DB 직접 조회/갱신 (StateManager 에게 위임)
      ✗ 장비 명령 (RobotExecutor 에게 위임)
      ✗ 이벤트 스스로 발행 (상태를 바꾼 액션 수행자만 발행)
      ✗ handler 예외를 publish 바깥으로 전파 (격리 원칙)
    """

    def __init__(self) -> None:
        # event_type → HandlerMeta 리스트 (등록 순서 유지 → FIFO dispatch)
        self._handlers: dict[EventType, list[HandlerMeta]] = defaultdict(list)
        self._lock = threading.Lock()
        logger.info("EventBridgeImpl initialized")

    # ── publish ──────────────────────────────────────────────────────────
    def publish(self, event: Event) -> PublishResult:
        """IEventBridge.publish 참조."""
        with self._lock:
            # dispatch 중 lock 을 잡고 있지 않도록 스냅샷 복사
            handlers = list(self._handlers.get(event.event_type, []))

        success = 0
        failed = 0
        for meta in handlers:
            try:
                meta.handler(event)
                success += 1
            except Exception as e:  # noqa: BLE001 — handler 격리 목적 광역 catch
                failed += 1
                logger.warning(
                    "EventBridge handler '%s' failed for %s: %s",
                    meta.subscriber_name,
                    event.event_type.value,
                    e,
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

    # ── subscribe ───────────────────────────────────────────────────────
    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], None],
        subscriber_name: str,
    ) -> None:
        """IEventBridge.subscribe 참조."""
        if not subscriber_name or not subscriber_name.strip():
            raise ValueError("subscriber_name 은 빈 문자열일 수 없습니다")

        meta = HandlerMeta(
            event_type=event_type,
            handler=handler,
            subscriber_name=subscriber_name.strip(),
        )

        with self._lock:
            # 동일 subscriber_name 있으면 교체 (덮어쓰기)
            existing = self._handlers.get(event_type, [])
            filtered = [m for m in existing if m.subscriber_name != meta.subscriber_name]
            filtered.append(meta)
            self._handlers[event_type] = filtered

        logger.info(
            "EventBridge.subscribe: '%s' → %s",
            meta.subscriber_name,
            event_type.value,
        )

    # ── unsubscribe ─────────────────────────────────────────────────────
    def unsubscribe(
        self,
        event_type: EventType,
        subscriber_name: str,
    ) -> bool:
        """IEventBridge.unsubscribe 참조."""
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

    # ── list_subscribers ────────────────────────────────────────────────
    def list_subscribers(
        self,
        event_type: EventType | None = None,
    ) -> list[HandlerMeta]:
        """IEventBridge.list_subscribers 참조."""
        with self._lock:
            if event_type is None:
                # 전체 반환
                all_metas: list[HandlerMeta] = []
                for metas in self._handlers.values():
                    all_metas.extend(metas)
                return sorted(all_metas, key=lambda m: m.registered_at)
            return list(self._handlers.get(event_type, []))


# ==============================================================================
# 참고: 부팅 시 구독 등록 예시 (wire_event_bridge)
# 실제 배선은 server.py startup 시 호출한다. 여기서는 계약 예시만 제공.
# ==============================================================================
"""
예시 배선 (backend/management/server.py 에서 호출):

    from backend.management.services.event_bridge import (
        EventBridgeImpl, EventType, Event,
    )

    bridge = EventBridgeImpl()

    # TASK_CREATED → TaskAllocator
    bridge.subscribe(
        EventType.TASK_CREATED,
        lambda e: task_allocator.assign_task(e.txn_id),
        subscriber_name="TaskAllocator.assign_task",
    )

    # TASK_COMPLETED → 다음 공정 create_task
    def on_task_completed(e: Event) -> None:
        # State Manager 의 read-only 래퍼로 다음 공정 타입 조회 (DB 직접 접근 아님)
        task   = state_manager.get_task(e.txn_id)
        next_t = state_manager.get_next_task_type(task)
        if next_t:
            task_manager.create_task(TaskCreateInput(
                ord_id=task.ord_id, item_id=task.item_id, task_type=next_t,
            ))
    bridge.subscribe(
        EventType.TASK_COMPLETED,
        on_task_completed,
        subscriber_name="TaskManager.on_task_completed",
    )

    # TASK_FAILED → StateManager ERROR 마킹
    bridge.subscribe(
        EventType.TASK_FAILED,
        lambda e: state_manager.mark_error(e.resource_id, e.payload.get("error_code")),
        subscriber_name="StateManager.mark_error",
    )

    # HANDOFF_ACK → AMR FSM
    bridge.subscribe(
        EventType.HANDOFF_ACK,
        lambda e: amr_state_machine.confirm_handoff(e.resource_id),
        subscriber_name="AmrStateMachine.confirm_handoff",
    )

    # ORDER_APPROVED → TaskManager.on_order_approved
    bridge.subscribe(
        EventType.ORDER_APPROVED,
        lambda e: task_manager.on_order_approved(e.ord_id),
        subscriber_name="TaskManager.on_order_approved",
    )

    return bridge
"""
