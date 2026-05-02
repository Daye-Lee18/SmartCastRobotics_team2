"""FMS 자동 진행 시퀀서 (asyncio background task).

실기 PLC/로봇 컨트롤러가 없을 때 데모/통합 테스트용으로 task 진행을 자동화한다.
환경변수 FMS_AUTOPLAY=1 일 때만 활성. 운영(=실기 연동) 시에는 OFF.

동작:
  1. POLL_INTERVAL_SECONDS 마다 DB 폴링
  2. equip_task_txn:
     - QUE 발견 → res 미배정이면 task_type 별 res 자동 할당 → PROC 으로 전환
     - PROC + 마지막 cur_stat 시각이 STEP_DELAY 이상 경과 → 다음 cur_stat INSERT
     - cur_stat == IDLE → SUCC 전환 + RA_NEXT_TASK 다음 task 자동 enqueue
     - SHIP SUCC → ord_stat = COMP 자동 INSERT
  3. trans_task_txn: 동일 패턴, 단순화된 단일 단계 흐름

종료: cancel() 호출 시 즉시 정리.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.constants import next_state
from app.constants.workflow import (
    ERROR_RATE_DEFAULT,
    HANDOFF_WAIT_TASK_TYPES,
    POLL_INTERVAL_SECONDS,
    RA_NEXT_TASK,
    STEP_DELAY_SECONDS,
)
from smart_cast_db.database import SessionLocal
from smart_cast_db.models import (
    EquipStat,
    EquipTaskTxn,
    Item,
    LogErrEquip,
    LogErrTrans,
    OrdStat,
    Res,
    TransStat,
    TransTaskTxn,
)
from services.adapters.robotics.ros2_publisher import publish_state

logger = logging.getLogger("management.fms_sequencer")

# task_type → 어느 res_type 에 할당할지 (간단 라우팅)
TASK_TO_RES_TYPE: dict[str, str] = {
    # RA 가 처리
    "MM": "RA",
    "POUR": "RA",
    "DM": "RA",
    "PP": "RA",
    "PA_GP": "RA",
    "PA_DP": "RA",
    "PICK": "RA",
    "SHIP": "RA",
    # CONV 가 처리
    "ToINSP": "CONV",
}


def is_enabled() -> bool:
    """env FMS_AUTOPLAY=1 일 때만 시퀀서 가동."""
    return os.environ.get("FMS_AUTOPLAY", "0").strip() in ("1", "true", "True")


def _error_rate() -> float:
    """env FMS_ERROR_RATE 으로 0.0~1.0 사이 확률 설정. 기본 0.0 (오류 없음)."""
    raw = os.environ.get("FMS_ERROR_RATE", str(ERROR_RATE_DEFAULT)).strip()
    try:
        rate = float(raw)
    except ValueError:
        return ERROR_RATE_DEFAULT
    return max(0.0, min(1.0, rate))


def _maybe_inject_error() -> str | None:
    """확률 기반으로 에러 메시지 반환. None 이면 정상 진행."""
    rate = _error_rate()
    if rate <= 0.0:
        return None
    if random.random() < rate:
        # 임의 에러 메시지 (실기에서는 ROS2/펌웨어 메시지가 들어옴)
        msgs = [
            "GRIPPER_TIMEOUT: gripper close 명령에 대한 ACK 없음",
            "MOTION_PLAN_FAIL: 목표 위치 inverse kinematics 해 없음",
            "FORCE_OVER_LIMIT: 가압 힘이 안전 임계값을 초과",
            "JOINT_LIMIT_EXCEEDED: 관절각 한계 도달",
            "VISION_NO_TARGET: 카메라 타겟 인식 실패",
            "BATTERY_LOW: 배터리 < 15%",
        ]
        return random.choice(msgs)
    return None


# -----------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------


def _pick_res(db: Session, res_type: str) -> str | None:
    """res_type 의 가용 res 1개 (가장 한가한 — 진행중 task 수가 적은 것)."""
    candidates = db.query(Res).filter(Res.res_type == res_type).all()
    if not candidates:
        return None
    busy_counts = []
    for r in candidates:
        n = (
            db.query(EquipTaskTxn)
            .filter(EquipTaskTxn.res_id == r.res_id, EquipTaskTxn.txn_stat == "PROC")
            .count()
            if res_type in ("RA", "CONV")
            else db.query(TransTaskTxn)
            .filter(TransTaskTxn.trans_id == r.res_id, TransTaskTxn.txn_stat == "PROC")
            .count()
        )
        busy_counts.append((n, r.res_id))
    busy_counts.sort()
    return busy_counts[0][1]


def _enqueue_next_equip_task(db: Session, prev: EquipTaskTxn) -> None:
    """RA_NEXT_TASK 매핑에 따라 다음 equip_task_txn 자동 생성."""
    nxt = RA_NEXT_TASK.get(prev.task_type or "")
    if nxt is None:
        return
    next_res_type = TASK_TO_RES_TYPE.get(nxt)
    next_res = _pick_res(db, next_res_type) if next_res_type else None
    new_txn = EquipTaskTxn(
        res_id=next_res,
        task_type=nxt,
        txn_stat="QUE",
        item_id=prev.item_id,
    )
    db.add(new_txn)


def _last_stat_age(db: Session, res_id: str) -> float | None:
    """해당 res 의 가장 최근 equip_stat 으로부터 경과 초 (없으면 None)."""
    latest = (
        db.query(EquipStat)
        .filter(EquipStat.res_id == res_id)
        .order_by(desc(EquipStat.updated_at))
        .first()
    )
    if not latest or not latest.updated_at:
        return None
    return (datetime.now() - latest.updated_at).total_seconds()


# -----------------------------------------------------------------------
# main loop
# -----------------------------------------------------------------------


async def run_sequencer() -> None:
    """asyncio background task. 안전 종료 보장."""
    print(
        f"[FMS] sequencer 시작 (polling={POLL_INTERVAL_SECONDS}s, step_delay={STEP_DELAY_SECONDS}s)",
        flush=True,
    )
    logger.info("FMS sequencer 시작")
    try:
        while True:
            try:
                await _tick_once()
            except Exception as exc:  # noqa: BLE001
                print(f"[FMS] tick 실패: {type(exc).__name__}: {exc}", flush=True)
                logger.exception("sequencer tick 실패: %s", exc)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        print("[FMS] sequencer 종료", flush=True)
        raise


async def _tick_once() -> None:
    """단일 polling cycle. asyncio 친화적이도록 DB I/O 는 sync 으로 묶고 짧게 끝낸다."""
    db = SessionLocal()
    try:
        _process_equip_tasks(db)
        _process_trans_tasks(db)
        db.commit()
    finally:
        db.close()


def _process_equip_tasks(db: Session) -> None:
    """모든 equip_task_txn 의 단계 진행."""
    # 1. QUE → PROC 전환 (res 미배정이면 자동 할당)
    for t in db.query(EquipTaskTxn).filter(EquipTaskTxn.txn_stat == "QUE").all():
        if t.res_id is None:
            res_type = TASK_TO_RES_TYPE.get(t.task_type or "")
            if res_type:
                rid = _pick_res(db, res_type)
                if rid:
                    t.res_id = rid
        if t.res_id:
            t.txn_stat = "PROC"
            t.start_at = datetime.now()
            # item.cur_stat / cur_res 업데이트
            if t.item_id:
                item = db.get(Item, t.item_id)
                if item:
                    item.cur_stat = t.task_type
                    item.cur_res = t.res_id
                    item.equip_task_type = t.task_type

    # 2. PROC 진행 — 마지막 cur_stat 시각이 STEP_DELAY 초과면 다음 단계
    proc_tasks = db.query(EquipTaskTxn).filter(EquipTaskTxn.txn_stat == "PROC").all()
    for t in proc_tasks:
        if not t.res_id:
            continue
        # 같은 task 의 최신 equip_stat — item_id 일치까지 확인하여 task 격리
        latest = (
            db.query(EquipStat)
            .filter(
                EquipStat.res_id == t.res_id,
                EquipStat.item_id == t.item_id,
                EquipStat.txn_type == t.task_type,
            )
            .order_by(desc(EquipStat.updated_at))
            .first()
        )
        cur = latest.cur_stat if latest else None
        if cur is None:
            nxt = next_state(t.task_type or "", None)
        else:
            age = (datetime.now() - latest.updated_at).total_seconds() if latest.updated_at else 999
            if age < STEP_DELAY_SECONDS:
                continue
            nxt = next_state(t.task_type or "", cur)
        if nxt is None:
            continue

        # 오류 시뮬: 단계 전환 직전 확률적으로 FAIL 처리
        err_msg = _maybe_inject_error()
        if err_msg is not None:
            print(
                f"[FMS] task {t.txn_id} ({t.task_type}) FAIL @ {cur or 'START'}: {err_msg}",
                flush=True,
            )
            db.add(
                EquipStat(
                    res_id=t.res_id,
                    item_id=t.item_id,
                    txn_type=t.task_type,
                    cur_stat="ERR",
                    err_msg=err_msg,
                )
            )
            db.add(
                LogErrEquip(
                    res_id=t.res_id,
                    task_txn_id=t.txn_id,
                    failed_stat=cur or "START",
                    err_msg=err_msg,
                )
            )
            t.txn_stat = "FAIL"
            t.end_at = datetime.now()
            continue

        print(f"[FMS] task {t.txn_id} ({t.task_type}) {cur or 'START'} -> {nxt}", flush=True)
        db.add(
            EquipStat(
                res_id=t.res_id,
                item_id=t.item_id,
                txn_type=t.task_type,
                cur_stat=nxt,
            )
        )
        # ROS2 publish (rclpy 미설치 시 print 폴백)
        res_obj = db.get(Res, t.res_id)
        if res_obj:
            publish_state(res_obj.res_type or "?", t.res_id, nxt, t.task_type)
        # IDLE 도달 → SUCC 전환 + 다음 task enqueue
        if nxt == "IDLE":
            t.txn_stat = "SUCC"
            t.end_at = datetime.now()
            _enqueue_next_equip_task(db, t)
            # SHIP 완료 시 ord_stat=COMP 자동 INSERT
            if t.task_type == "SHIP" and t.item_id:
                item = db.get(Item, t.item_id)
                if item:
                    db.add(OrdStat(ord_id=item.ord_id, ord_stat="COMP"))


def _process_trans_tasks(db: Session) -> None:
    """trans_task_txn 진행 (QUE → PROC → SUCC, 단계 simulation 1초 후).

    HANDOFF_WAIT_TASK_TYPES (예: ToPP) 는 MV_DEST 도달 시 WAIT_HANDOFF 정지.
    /api/debug/handoff-ack 호출 시 cur_stat 이 WAIT_DLD 로 풀리면 진행 재개.
    """
    for t in db.query(TransTaskTxn).filter(TransTaskTxn.txn_stat == "QUE").all():
        if not t.trans_id:
            rid = _pick_res(db, "TAT")
            if rid:
                t.trans_id = rid
        if t.trans_id:
            t.txn_stat = "PROC"
            t.start_at = datetime.now()
            stat = db.get(TransStat, t.trans_id) or TransStat(res_id=t.trans_id)
            stat.item_id = t.item_id
            stat.cur_stat = "MV_SRC"
            stat.cur_zone_type = None
            db.add(stat)

    for t in db.query(TransTaskTxn).filter(TransTaskTxn.txn_stat == "PROC").all():
        if not t.trans_id:
            continue
        stat = db.get(TransStat, t.trans_id)
        if not stat or not stat.updated_at:
            continue
        age = (datetime.now() - stat.updated_at).total_seconds()
        if age < STEP_DELAY_SECONDS:
            continue

        # HANDOFF_WAIT 단계는 자동 진행 안 함 (사람 ACK 대기)
        if stat.cur_stat == "WAIT_HANDOFF":
            continue

        # 오류 주입
        err_msg = _maybe_inject_error()
        if err_msg is not None:
            print(
                f"[FMS] trans task {t.trans_task_txn_id} ({t.task_type}) FAIL @ {stat.cur_stat}: {err_msg}",
                flush=True,
            )
            stat.cur_stat = "FAIL"
            stat.updated_at = datetime.now()
            db.add(
                LogErrTrans(
                    res_id=t.trans_id,
                    task_txn_id=t.trans_task_txn_id,
                    failed_stat=stat.cur_stat,
                    err_msg=err_msg,
                    battery_pct=stat.battery_pct,
                )
            )
            t.txn_stat = "FAIL"
            t.end_at = datetime.now()
            continue

        # 단순 시퀀스: MV_SRC → WAIT_LD → MV_DEST → (WAIT_HANDOFF? or) WAIT_DLD → SUCC
        seq = ["MV_SRC", "WAIT_LD", "MV_DEST", "WAIT_DLD", "SUCC"]
        cur = stat.cur_stat or "MV_SRC"
        try:
            idx = seq.index(cur)
        except ValueError:
            idx = 0
        if idx + 1 < len(seq):
            nxt = seq[idx + 1]
            # ToPP 는 MV_DEST 도달 후 WAIT_DLD 대신 WAIT_HANDOFF 로 정지
            if cur == "MV_DEST" and t.task_type in HANDOFF_WAIT_TASK_TYPES:
                nxt = "WAIT_HANDOFF"
                print(
                    f"[FMS] trans task {t.trans_task_txn_id} ({t.task_type}) -> WAIT_HANDOFF (사람 ACK 대기)",
                    flush=True,
                )
            stat.cur_stat = nxt
            stat.updated_at = datetime.now()
            # ROS2 publish — TAT 전용 토픽
            publish_state("TAT", t.trans_id, nxt, t.task_type)
        if stat.cur_stat == "SUCC":
            t.txn_stat = "SUCC"
            t.end_at = datetime.now()
            stat.cur_stat = "IDLE"
