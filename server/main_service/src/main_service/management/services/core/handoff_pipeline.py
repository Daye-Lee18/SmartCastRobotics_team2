"""Handoff + TOF pipeline — debug.py(가상) + server.py(gRPC) 공유 DB 트랜잭션.

debug 라우트(가상 curl)와 Mgmt gRPC 핸들러가 동일 결과를 보장하기 위해 핵심 DB
변경을 본 모듈의 헬퍼로 모았다. 호출자는 SQLAlchemy session 만 넘기면 되며
트랜잭션 commit 여부는 호출자가 결정한다.

제공 함수:
  apply_handoff()  — ESP32 GPIO33 핸드오프 버튼 / 가상 핸드오프 ACK 시
                     5단계 DB 변경 + handoff_acks 감사 (이전 단계 작업)
  apply_tof1()     — 컨베이어 TOF1 진입 (RFID 부착 후 작업자가 컨베이어에 올림)
                     pp_task_txn QUE/PROC → SUCC + item PP→ToINSP +
                     equip_task_txn ToINSP PROC + equip_stat ON
  apply_tof2()     — 컨베이어 TOF2 도달 (검사 시작)
                     equip_task_txn ToINSP SUCC + equip_stat OFF +
                     item ToINSP→INSP + insp_task_txn PROC

idempotency / FSM 전이는 호출자가 처리 (server.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session


@dataclass
class HandoffApplyResult:
    """apply_handoff 결과 — 호출자가 응답 페이로드 구성 시 사용."""

    released: bool
    orphan: bool
    task_id: int | None  # trans_task_txn.trans_task_txn_id
    amr_id: str | None  # trans_id
    item_id: int | None
    ord_id: int | None
    pp_task_txn_ids: list[int]
    item_cur_stat: str | None
    handoff_ack_id: int | None
    reason: str


def apply_handoff(
    db: Session,
    *,
    button_device_id: str,
    ack_source: str,
    via: str,
    idempotency_key: str | None,
    operator_id: int | None = None,
) -> HandoffApplyResult:
    """5단계 핸드오프 DB 변경을 단일 트랜잭션으로 적용.

    호출자 책임:
      - db 세션 생명주기 (get_db / SessionLocal)
      - commit / rollback 결정
      - in-memory AmrStateMachine.confirm_handoff(amr_id) 호출 (FSM 전이)
      - 응답 페이로드(HandoffAckResponse 등) 구성

    Returns:
      HandoffApplyResult — released=False 인 경우 orphan=True (해제 대상 없음)
    """
    # 지연 import: 순환 회피 + 모델 로딩 한 곳에 묶음
    from smart_cast_db.models import (
        HandoffAck,
        Item,
        OrdPpMap,
        PpOption,
        PpTaskTxn,
        TransStat,
        TransTaskTxn,
    )

    # 가장 오래된 ToPP/PROC 중 cur_stat=WAIT_HANDOFF 인 1건 픽업 (FIFO)
    candidates = (
        db.query(TransTaskTxn)
        .filter(TransTaskTxn.task_type == "ToPP", TransTaskTxn.txn_stat == "PROC")
        .order_by(TransTaskTxn.req_at.asc())
        .all()
    )
    target: TransTaskTxn | None = None
    target_stat: TransStat | None = None
    for t in candidates:
        if not t.trans_id:
            continue
        s = db.get(TransStat, t.trans_id)
        if s and s.cur_stat == "WAIT_HANDOFF":
            target = t
            target_stat = s
            break

    now = datetime.now()
    now_utc = datetime.now(UTC)

    if target is None or target_stat is None:
        # orphan: 대기 AMR 없음. handoff_acks 만 INSERT (감사용).
        ack = HandoffAck(
            ack_at=now_utc,
            task_id=None,
            zone="postprocessing",
            amr_id=None,
            ack_source=ack_source,
            button_device_id=button_device_id,
            orphan_ack=True,
            idempotency_key=idempotency_key,
            extra={"via": via},
        )
        db.add(ack)
        db.flush()
        return HandoffApplyResult(
            released=False,
            orphan=True,
            task_id=None,
            amr_id=None,
            item_id=None,
            ord_id=None,
            pp_task_txn_ids=[],
            item_cur_stat=None,
            handoff_ack_id=ack.id,
            reason="orphan_no_waiting_task",
        )

    # (1) trans_stat: WAIT_HANDOFF → WAIT_DLD
    target_stat.cur_stat = "WAIT_DLD"
    target_stat.updated_at = now

    # (2) trans_task_txn: PROC → SUCC
    target.txn_stat = "SUCC"
    target.end_at = now

    # (3) item 갱신
    pp_txn_ids: list[int] = []
    item_id = target.item_id
    item_cur_stat: str | None = None
    item: Item | None = db.get(Item, item_id) if item_id else None
    if item is not None:
        item.cur_stat = "PP"
        item.trans_task_type = None
        item.equip_task_type = "PP"
        item.cur_res = None
        item.updated_at = now
        item_cur_stat = item.cur_stat

        # (4) pp_task_txn 다건 INSERT — ord_pp_map 행 수만큼 QUE
        maps = (
            db.query(OrdPpMap, PpOption)
            .join(PpOption, PpOption.pp_id == OrdPpMap.pp_id)
            .filter(OrdPpMap.ord_id == item.ord_id)
            .all()
        )
        for omap, opt in maps:
            row = PpTaskTxn(
                ord_id=item.ord_id,
                map_id=omap.map_id,
                pp_nm=opt.pp_nm,
                item_id=item.item_id,
                operator_id=operator_id,  # 로그인된 작업자 (없으면 NULL)
                txn_stat="QUE",
                req_at=now,
            )
            db.add(row)
            db.flush()
            pp_txn_ids.append(row.txn_id)

        # 후처리 옵션이 0건이면 PP 단계 건너뛰고 ToINSP 로 직행
        if not maps:
            item.equip_task_type = "ToINSP"
            item.cur_stat = "ToINSP"
            item_cur_stat = item.cur_stat

    # (5) handoff_acks 감사 로그
    # transport_tasks(VARCHAR id) 와 trans_task_txn(SERIAL int) 은 별도 도메인.
    # FK 충돌 회피를 위해 task_id 는 NULL, trans_task_txn_id 는 metadata 에 보관.
    ack = HandoffAck(
        ack_at=now_utc,
        task_id=None,
        zone="postprocessing",
        amr_id=target.trans_id,
        ack_source=ack_source,
        button_device_id=button_device_id,
        orphan_ack=False,
        idempotency_key=idempotency_key,
        extra={"via": via, "trans_task_txn_id": target.trans_task_txn_id},
    )
    db.add(ack)
    db.flush()

    return HandoffApplyResult(
        released=True,
        orphan=False,
        task_id=target.trans_task_txn_id,
        amr_id=target.trans_id,
        item_id=item_id,
        ord_id=target.ord_id,
        pp_task_txn_ids=pp_txn_ids,
        item_cur_stat=item_cur_stat,
        handoff_ack_id=ack.id,
        reason="WAIT_HANDOFF → WAIT_DLD + item PP 진입 + pp_task_txn QUE 등록",
    )


# ============================================================================
# TOF1 — 후처리 완료 + 컨베이어 진입
# ============================================================================


@dataclass
class Tof1ApplyResult:
    ok: bool
    item_id: int | None
    ord_id: int | None
    res_id: str
    pp_task_txn_succ: list[int]
    equip_task_txn_id: int | None
    item_cur_stat: str | None
    reason: str


def apply_tof1(
    db: Session,
    *,
    res_id: str = "CONV-01",
    rfid_payload: str | None = None,
    item_id: int | None = None,
    operator_id: int | None = None,
) -> Tof1ApplyResult:
    """TOF1 진입 — 후처리 완료 처리 + ToINSP equip_task_txn 시작.

    item 선택 우선순위:
      1) explicit item_id
      2) rfid_payload (`order_<ord>_item_<YYYYMMDD>_<seq>`) → item lookup
      3) cur_stat='PP' 인 가장 최근 item

    Returns Tof1ApplyResult (ok=False 면 item 미발견)
    """
    from smart_cast_db.models import EquipStat, EquipTaskTxn, Item, PpTaskTxn

    item: Item | None = None
    if item_id is not None:
        item = db.get(Item, int(item_id))
    elif rfid_payload:
        item = _resolve_item_by_payload(db, rfid_payload)
    else:
        item = db.query(Item).filter(Item.cur_stat == "PP").order_by(desc(Item.updated_at)).first()

    if item is None:
        return Tof1ApplyResult(
            ok=False,
            item_id=None,
            ord_id=None,
            res_id=res_id,
            pp_task_txn_succ=[],
            equip_task_txn_id=None,
            item_cur_stat=None,
            reason="후처리 단계(PP) item 을 찾을 수 없습니다",
        )

    now = datetime.now()

    # (1) pp_task_txn 모두 SUCC 처리 (안 1: 직행)
    open_pp = (
        db.query(PpTaskTxn)
        .filter(PpTaskTxn.item_id == item.item_id, PpTaskTxn.txn_stat.in_(("QUE", "PROC")))
        .all()
    )
    pp_succ_ids: list[int] = []
    for t in open_pp:
        t.txn_stat = "SUCC"
        if t.start_at is None:
            t.start_at = now
        t.end_at = now
        # 로그인된 작업자가 있으면 기존 NULL 만 채움 (다른 작업자가 이미 작업 시작했으면 보존)
        if operator_id is not None and t.operator_id is None:
            t.operator_id = operator_id
        pp_succ_ids.append(t.txn_id)

    # (2) item 갱신 — PP → ToINSP
    item.cur_stat = "ToINSP"
    item.equip_task_type = "ToINSP"
    item.trans_task_type = None
    item.cur_res = res_id
    item.updated_at = now

    # (3) equip_task_txn 신규 (ToINSP, PROC)
    new_txn = EquipTaskTxn(
        res_id=res_id,
        task_type="ToINSP",
        txn_stat="PROC",
        item_id=item.item_id,
        req_at=now,
        start_at=now,
    )
    db.add(new_txn)
    db.flush()

    # (4) equip_stat INSERT (CONV ON)
    db.add(
        EquipStat(
            res_id=res_id,
            item_id=item.item_id,
            txn_type="ToINSP",
            cur_stat="ON",
            updated_at=now,
        )
    )

    return Tof1ApplyResult(
        ok=True,
        item_id=item.item_id,
        ord_id=item.ord_id,
        res_id=res_id,
        pp_task_txn_succ=pp_succ_ids,
        equip_task_txn_id=new_txn.txn_id,
        item_cur_stat=item.cur_stat,
        reason="TOF1 진입 → pp_task_txn SUCC + ToINSP PROC 시작 + CONV ON",
    )


# ============================================================================
# TOF2 — 검사 공정 시작
# ============================================================================


@dataclass
class Tof2ApplyResult:
    ok: bool
    item_id: int | None
    ord_id: int | None
    res_id: str
    equip_task_txn_succ_id: int | None
    insp_task_txn_id: int | None
    item_cur_stat: str | None
    reason: str


def apply_tof2(
    db: Session,
    *,
    res_id: str = "CONV-01",
    item_id: int | None = None,
) -> Tof2ApplyResult:
    """TOF2 도달 — ToINSP 종료 + insp_task_txn 시작.

    item_id 미지정 시 res_id 의 PROC ToINSP equip_task_txn 1건 자동 픽업.
    """
    from smart_cast_db.models import EquipStat, EquipTaskTxn, InspTaskTxn, Item

    q = db.query(EquipTaskTxn).filter(
        EquipTaskTxn.res_id == res_id,
        EquipTaskTxn.task_type == "ToINSP",
        EquipTaskTxn.txn_stat == "PROC",
    )
    if item_id is not None:
        q = q.filter(EquipTaskTxn.item_id == int(item_id))
    txn: EquipTaskTxn | None = q.order_by(EquipTaskTxn.start_at.asc()).first()

    if txn is None:
        return Tof2ApplyResult(
            ok=False,
            item_id=None,
            ord_id=None,
            res_id=res_id,
            equip_task_txn_succ_id=None,
            insp_task_txn_id=None,
            item_cur_stat=None,
            reason=f"{res_id} 에서 PROC 중인 ToINSP equip_task_txn 을 찾을 수 없습니다",
        )

    item = db.get(Item, txn.item_id) if txn.item_id else None
    if item is None:
        return Tof2ApplyResult(
            ok=False,
            item_id=None,
            ord_id=None,
            res_id=res_id,
            equip_task_txn_succ_id=None,
            insp_task_txn_id=None,
            item_cur_stat=None,
            reason="해당 트랜잭션의 item 을 찾을 수 없습니다",
        )

    now = datetime.now()

    # (1) equip_task_txn ToINSP SUCC
    txn.txn_stat = "SUCC"
    txn.end_at = now

    # (2) equip_stat OFF
    db.add(
        EquipStat(
            res_id=res_id,
            item_id=item.item_id,
            txn_type="ToINSP",
            cur_stat="OFF",
            updated_at=now,
        )
    )

    # (3) item ToINSP → INSP
    item.cur_stat = "INSP"
    item.equip_task_type = "INSP"
    item.cur_res = res_id
    item.updated_at = now

    # (4) insp_task_txn 신규 (PROC, start_at=now)
    insp = InspTaskTxn(
        item_id=item.item_id,
        res_id=res_id,
        txn_stat="PROC",
        result=None,
        req_at=now,
        start_at=now,
    )
    db.add(insp)
    db.flush()

    return Tof2ApplyResult(
        ok=True,
        item_id=item.item_id,
        ord_id=item.ord_id,
        res_id=res_id,
        equip_task_txn_succ_id=txn.txn_id,
        insp_task_txn_id=insp.txn_id,
        item_cur_stat=item.cur_stat,
        reason="TOF2 감지 → ToINSP SUCC + CONV OFF + INSP 시작",
    )


# ============================================================================
# Helpers
# ============================================================================

import re as _re

_RFID_PAYLOAD_RE = _re.compile(r"^order_(?P<ord>\d+)_item_(?P<date>\d{8})_(?P<seq>\d+)$")


def _resolve_item_by_payload(db: Session, payload: str):
    """RFID payload → item (ord_id+item_id 매칭, 실패 시 ord_id 의 최신 item)."""
    from smart_cast_db.models import Item

    m = _RFID_PAYLOAD_RE.fullmatch((payload or "").strip())
    if m is None:
        return None
    ord_id = int(m.group("ord"))
    seq = int(m.group("seq"))
    item = db.query(Item).filter(Item.ord_id == ord_id, Item.item_id == seq).first()
    if item is not None:
        return item
    return db.query(Item).filter(Item.ord_id == ord_id).order_by(desc(Item.item_id)).first()


def build_pp_options_view(db: Session, item) -> list[dict]:
    """RFID Wave3: ord_pp_map 정의 + pp_task_txn 진행 현황 동시 노출.

    PyQt 작업자 화면 / Mgmt RfidScanAck 양쪽에서 동일 형식으로 사용.
    """
    from smart_cast_db.models import OrdPpMap, PpOption, PpTaskTxn

    rows = (
        db.query(OrdPpMap, PpOption)
        .join(PpOption, PpOption.pp_id == OrdPpMap.pp_id)
        .filter(OrdPpMap.ord_id == item.ord_id)
        .all()
    )
    if not rows:
        return []

    txns = (
        db.query(PpTaskTxn)
        .filter(PpTaskTxn.item_id == item.item_id)
        .order_by(PpTaskTxn.pp_nm.asc(), desc(PpTaskTxn.req_at))
        .all()
    )
    latest_by_nm: dict[str, PpTaskTxn] = {}
    for t in txns:
        if t.pp_nm and t.pp_nm not in latest_by_nm:
            latest_by_nm[t.pp_nm] = t

    out: list[dict] = []
    for omap, opt in rows:
        latest = latest_by_nm.get(opt.pp_nm)
        out.append(
            {
                "map_id": omap.map_id,
                "pp_id": opt.pp_id,
                "pp_nm": opt.pp_nm,
                "extra_cost": float(opt.extra_cost) if opt.extra_cost is not None else None,
                "txn_stat": (latest.txn_stat if latest else None),
                "txn_id": (latest.txn_id if latest else None),
                "start_at": (latest.start_at.isoformat() if latest and latest.start_at else None),
                "end_at": (latest.end_at.isoformat() if latest and latest.end_at else None),
            }
        )
    return out
