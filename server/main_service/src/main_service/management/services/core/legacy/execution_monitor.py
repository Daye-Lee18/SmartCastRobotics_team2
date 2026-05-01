"""Execution Monitor — Item 상태 변경 감지 + SLA 타임아웃 + alerts 통합 (V6 Phase 7).

전략:
- 1초 polling DB 스냅샷 대조 (in-memory cache)
- 변경 감지: cur_stage 가 바뀐 item → ItemEvent emit
- SLA 감시: 같은 stage 머무른 시간이 임계 초과 → alerts INSERT + 경고 ItemEvent emit
- 동일 item-stage 조합 중복 알람 방지 (alert_id 캐시)

stage 별 SLA (초):
- QUE: 무한 (대기는 정상)
- MM:  300 (주형 제작 5분)
- DM:   60 (탈형 1분)
- TR_PP, TR_LD: 60 (이송 1분)
- PP:  600 (후처리 10분)
- IP:   30 (검사 30초)
- SH:  무한 (출고는 외부 트리거)

@MX:NOTE: SLA 초과 시 alerts.severity='warning', type='stage_timeout' 으로 기록.
@MX:WARN: 다중 클라이언트 동시 구독 시 각자 polling — alerts 는 1 source 가 처리하도록 보호 필요.
        본 구현은 클라이언트별 독립 alerts INSERT 가 발생하지 않도록 동일 item-stage 캐시로 해결.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import management_pb2  # type: ignore
from db_session import SessionLocal
from sqlalchemy import select

from smart_cast_db.models import Alert, Item  # SPEC-C3: Alert 는 legacy public-schema · Item 은 smartcast

logger = logging.getLogger(__name__)

# stage 코드 → proto enum int
_STAGE_TO_ENUM = {
    "QUE": 1,
    "MM": 2,
    "DM": 3,
    "TR_PP": 4,
    "PP": 5,
    "IP": 6,
    "TR_LD": 7,
    "SH": 8,
}

# stage 별 SLA (초). 0 또는 음수면 무한 (감시 안 함)
DEFAULT_SLA_SEC: dict[str, float] = {
    "QUE": 0,  # 대기는 무제한
    "MM": 300,
    "DM": 60,
    "TR_PP": 60,
    "PP": 600,
    "IP": 30,
    "TR_LD": 60,
    "SH": 0,  # 출고는 외부 시스템 트리거
}

# 환경 변수로 stage 별 SLA override 가능. 예: MGMT_SLA_IP=3 MGMT_SLA_DM=10
for _stage in list(DEFAULT_SLA_SEC):
    _v = os.environ.get(f"MGMT_SLA_{_stage}")
    if _v:
        try:
            DEFAULT_SLA_SEC[_stage] = float(_v)
        except ValueError:
            pass

# alert 중복 발행 방지 캐시 TTL (초). 같은 item-stage 가 N초 안에 또 SLA 위반이어도 한 번만 alert.
ALERT_DEDUP_TTL_SEC = float(os.environ.get("MGMT_ALERT_DEDUP_TTL_SEC", "300"))

# V6 P-001: Adaptive polling interval (변경 없을 때 점진적으로 늘림, 변경 발생 시 즉시 복귀)
# - QUIET_CYCLES_TO_BACKOFF: N 사이클 연속 변경 0건 시 간격 1단계 증가
# - BACKOFF_FACTOR: 매 backoff 시 곱하기 (기본 2배)
# - 상한: SLA 최단값의 절반 (기본 IP=30s 의 절반=15s, 환경변수 override 가능)
ADAPTIVE_POLLING = os.environ.get("MGMT_ADAPTIVE_POLLING", "1") in ("1", "true", "yes")
QUIET_CYCLES_TO_BACKOFF = int(os.environ.get("MGMT_POLL_QUIET_CYCLES", "5"))
BACKOFF_FACTOR = float(os.environ.get("MGMT_POLL_BACKOFF_FACTOR", "2.0"))
MAX_POLL_INTERVAL_SEC = float(os.environ.get("MGMT_MAX_POLL_INTERVAL_SEC", "8.0"))


def _stage_enum(stage: str | None) -> int:
    return _STAGE_TO_ENUM.get(stage or "QUE", 0)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _now_mono() -> float:
    return time.monotonic()


class ExecutionMonitor:
    """진행 중 Item 감시 + ItemEvent stream + alerts 자동 기록.

    각 클라이언트 연결마다 stream() generator 가 독립 실행되지만, alerts 기록 dedup 캐시는
    인스턴스 공유로 동일 item-stage 중복 INSERT 를 방지한다.
    """

    def __init__(
        self,
        poll_interval_sec: float = 1.0,
        sla_overrides: dict[str, float] | None = None,
        image_forwarder=None,
    ) -> None:
        self._base_interval = poll_interval_sec
        self._interval = poll_interval_sec
        self._sla = dict(DEFAULT_SLA_SEC)
        # V6 AI 학습 데이터 브리지: IP 진입 시 최신 프레임을 AI Server 로 전달
        self._image_forwarder = image_forwarder
        self._ip_camera_id = os.environ.get("MGMT_IP_CAMERA_ID", "CAM-INSP-01")
        # snapshot dedup: (item_id, stage) → last_fired monotonic. bg+stream 양쪽에서 공유
        self._last_snapshot_fired: dict[tuple[int, str], float] = {}
        self._snapshot_lock = __import__("threading").Lock()
        self._SNAPSHOT_TTL_SEC = 60.0  # 같은 item-stage 재발화 최소 간격
        if sla_overrides:
            self._sla.update(sla_overrides)
        # 인스턴스 공유 캐시 (alerts dedup)
        self._last_alert: dict[tuple[int, str], float] = {}
        self._stage_started_mono: dict[int, tuple[str, float]] = {}
        # V6 P-001: Adaptive polling 상태
        # SLA 최단값의 절반을 max interval cap (감지 정확도 보호)
        positive_slas = [v for v in self._sla.values() if v > 0]
        sla_min_half = (min(positive_slas) / 2.0) if positive_slas else MAX_POLL_INTERVAL_SEC
        self._max_interval = min(MAX_POLL_INTERVAL_SEC, max(self._base_interval, sla_min_half))
        self._quiet_cycles = 0
        # 백그라운드 자동 polling — 클라이언트 stream 없어도 SLA 감시 + alerts 발행
        self._bg_snapshot: dict[int, str] = {}
        self._bg_first_pass = True
        self._bg_stop = False
        import threading as _t

        self._bg_thread = _t.Thread(
            target=self._background_loop, daemon=True, name="ExecMonitor-bg"
        )
        self._bg_thread.start()
        logger.info(
            "ExecutionMonitor background SLA polling 시작 (base=%.1fs, max=%.1fs, adaptive=%s)",
            self._base_interval,
            self._max_interval,
            ADAPTIVE_POLLING,
        )

    def _background_loop(self) -> None:
        """클라이언트 연결 여부와 무관하게 SLA 감시. 이벤트는 버리고 alerts 만 INSERT.

        V6 P-001: Adaptive interval — quiet cycles 가 누적되면 점진적으로 늘어나
        DB 부담 최소화. 변경/타임아웃 발생 시 즉시 base interval 로 복귀.
        """
        while not self._bg_stop:
            try:
                events, self._bg_snapshot = self._tick(
                    self._bg_snapshot, order_filter=None, first_pass=self._bg_first_pass
                )
                self._bg_first_pass = False
                self._adapt_interval(activity=len(events))
            except Exception as exc:  # noqa: BLE001
                logger.exception("ExecMonitor background tick error: %s", exc)
            time.sleep(self._interval)

    def _adapt_interval(self, activity: int) -> None:
        """이벤트 수에 따라 다음 polling 간격 조정.

        - activity > 0 (변경/타임아웃 발생): base interval 로 복귀
        - activity == 0 인 사이클이 QUIET_CYCLES_TO_BACKOFF 누적: BACKOFF_FACTOR 적용
        """
        if not ADAPTIVE_POLLING:
            return
        if activity > 0:
            if self._interval != self._base_interval:
                logger.debug("activity 감지 — interval 복귀 → %.1fs", self._base_interval)
            self._interval = self._base_interval
            self._quiet_cycles = 0
            return
        self._quiet_cycles += 1
        if self._quiet_cycles >= QUIET_CYCLES_TO_BACKOFF:
            new_interval = min(self._interval * BACKOFF_FACTOR, self._max_interval)
            if new_interval > self._interval:
                logger.debug(
                    "quiet %d 사이클 — interval 증가 %.1fs → %.1fs",
                    self._quiet_cycles,
                    self._interval,
                    new_interval,
                )
                self._interval = new_interval
            self._quiet_cycles = 0  # 다음 backoff 까지 카운트 리셋

    # ------------------------------------------------------------------
    # gRPC server streaming entrypoint
    # ------------------------------------------------------------------

    def stream(self, order_filter: str | None) -> Iterator:
        snapshot: dict[int, str] = {}
        first_pass = True
        while True:
            try:
                events, snapshot = self._tick(snapshot, order_filter, first_pass)
                first_pass = False
                yield from events
            except Exception as exc:  # noqa: BLE001
                logger.exception("ExecutionMonitor.stream tick error: %s", exc)
            time.sleep(self._interval)

    def stream_alerts(self, severity_filter: str | None) -> Iterator:
        """alerts 테이블 신규 row 를 polling 해서 AlertEvent 로 emit.

        seen_ids 셋 기반으로 신규 INSERT 만 정확히 감지 (timestamp 문자열 정렬에 의존하지 않음).
        - first_pass: 최근 200건 기록 + 최신 1건만 emit (요약 sync)
        - 이후: seen_ids 에 없는 row 가 신규 → 모두 emit, seen_ids 갱신
        - seen_ids 는 최근 1000건 cap (메모리 보호)
        """
        from smart_cast_db.models import Alert  # SPEC-C3: legacy public-schema re-export

        seen_ids: set[str] = set()
        first_pass = True
        sev = (severity_filter or "").strip().lower()
        SEEN_CAP = 1000

        while True:
            try:
                with SessionLocal() as db:
                    q = db.query(Alert).order_by(Alert.timestamp.desc()).limit(200)
                    rows = q.all()

                emit: list = []
                if first_pass:
                    seen_ids.update(r.id for r in rows)
                    if rows:
                        emit = [rows[0]]  # 최신 1건만 표시 (UI sync)
                    first_pass = False
                else:
                    new_rows = [r for r in rows if r.id not in seen_ids]
                    # 과거→최근 시간 순으로 emit
                    new_rows.reverse()
                    emit = new_rows
                    seen_ids.update(r.id for r in new_rows)
                    # cap 초과 시 오래된 절반 정리 (간단)
                    if len(seen_ids) > SEEN_CAP:
                        seen_ids = set(list(seen_ids)[-SEEN_CAP // 2 :])

                for r in emit:
                    if sev and (r.severity or "").lower() != sev:
                        continue
                    yield management_pb2.AlertEvent(
                        id=r.id,
                        type=r.type or "",
                        severity=r.severity or "info",
                        error_code=r.error_code or "",
                        message=r.message or "",
                        equipment_id=r.equipment_id or "",
                        zone=r.zone or "",
                        at=management_pb2.Timestamp(iso8601=r.timestamp or _now_iso()),
                    )
            except Exception as exc:  # noqa: BLE001
                logger.exception("ExecutionMonitor.stream_alerts error: %s", exc)
            time.sleep(self._interval)

    # ------------------------------------------------------------------
    # 내부
    # ------------------------------------------------------------------

    def _tick(
        self, prev: dict[int, str], order_filter: str | None, first_pass: bool
    ) -> tuple[list, dict[int, str]]:
        """1 polling 사이클: DB 읽기 → 변경/타임아웃 이벤트 생성 + alerts 기록."""
        events: list = []
        new_snapshot: dict[int, str] = {}
        now_mono = _now_mono()

        with SessionLocal() as db:
            # SPEC-C3: smartcast Item 컬럼명 (item_id/cur_stat/cur_res/ord_id).
            # 참고: SLA stage 맵(QUE/MM/DM/TR_PP/...)은 smartcast stage 라벨
            # (MM/POUR/DM/PP/ToINSP/INSP/PA/PICK/SHIP/ToPP/ToSTRG/ToSHIP)과 부분 일치.
            # 불일치 stage 는 _stage_enum 이 0 반환 + SLA 무시되어 안전하게 fallback.
            stmt = select(Item.item_id, Item.cur_stat, Item.cur_res, Item.ord_id)
            if order_filter:
                try:
                    stmt = stmt.where(Item.ord_id == int(order_filter))
                except (TypeError, ValueError):
                    # order_filter 가 smartcast int ord_id 가 아니면 필터 적용 불가 → 전체
                    pass
            rows = db.execute(stmt).all()

            for row in rows:
                item_id = int(row[0])
                stage = str(row[1] or "QUE")
                robot = row[2] or ""
                new_snapshot[item_id] = stage

                # 1) 변경 감지
                old = prev.get(item_id)
                stage_changed = old is not None and old != stage
                first_seen = old is None and not first_pass

                if first_pass or stage_changed or first_seen:
                    self._stage_started_mono[item_id] = (stage, now_mono)
                    events.append(
                        self._make_event(
                            item_id, stage, robot, message="" if first_pass else "stage_changed"
                        )
                    )
                    # IP 진입 트리거 — AI 학습 데이터셋용 스냅샷 (bg+stream 중복 방지)
                    if stage_changed and stage == "IP" and self._image_forwarder is not None:
                        key = (item_id, "IP")
                        with self._snapshot_lock:
                            last = self._last_snapshot_fired.get(key)
                            if last is not None and (now_mono - last) < self._SNAPSHOT_TTL_SEC:
                                fire = False
                            else:
                                self._last_snapshot_fired[key] = now_mono
                                fire = True
                        if fire:
                            try:
                                self._image_forwarder.snapshot(
                                    item_id=item_id,
                                    stage="IP",
                                    camera_id=self._ip_camera_id,
                                )
                            except Exception:  # noqa: BLE001
                                logger.exception("image_forwarder.snapshot 실패 item=%d", item_id)

                # 2) SLA 타임아웃 검사 (변경 없을 때만)
                if not first_pass and not stage_changed:
                    timeout_event = self._check_sla(db, item_id, stage, robot, now_mono)
                    if timeout_event is not None:
                        events.append(timeout_event)

            db.commit()  # alerts INSERT 반영

        return events, new_snapshot

    def _make_event(self, item_id: int, stage: str, robot_id: str, message: str):
        return management_pb2.ItemEvent(
            item_id=item_id,
            stage=_stage_enum(stage),
            robot_id=robot_id or "",
            message=message,
            at=management_pb2.Timestamp(iso8601=_now_iso()),
        )

    def _check_sla(self, db, item_id: int, stage: str, robot_id: str, now_mono: float):
        """SLA 초과 여부 판정. 위반 시 alerts INSERT + 경고 ItemEvent 반환."""
        sla = self._sla.get(stage, 0)
        if sla <= 0:
            return None
        started = self._stage_started_mono.get(item_id)
        if started is None or started[0] != stage:
            self._stage_started_mono[item_id] = (stage, now_mono)
            return None
        elapsed = now_mono - started[1]
        if elapsed < sla:
            return None

        # dedup
        key = (item_id, stage)
        last = self._last_alert.get(key)
        if last is not None and (now_mono - last) < ALERT_DEDUP_TTL_SEC:
            return None
        self._last_alert[key] = now_mono

        # alerts INSERT
        alert_id = f"ALT-{uuid.uuid4().hex[:12]}"
        msg = f"Item {item_id} stage={stage} elapsed={elapsed:.0f}s > SLA {sla:.0f}s"
        try:
            db.add(
                Alert(
                    id=alert_id,
                    equipment_id=robot_id or "",
                    type="stage_timeout",
                    severity="warning",
                    error_code=f"SLA_{stage}",
                    message=msg,
                    abnormal_value=f"{elapsed:.0f}s",
                    zone=stage,
                    timestamp=_now_iso(),
                    acknowledged=False,
                )
            )
            logger.warning("SLA 위반: %s (alert=%s)", msg, alert_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("alerts INSERT 실패: %s", exc)

        return self._make_event(item_id, stage, robot_id, message=f"sla_timeout:{sla:.0f}s")
