"""Dev-only debug router — smartcast schema 가상 시뮬레이션.

본 라우터는 실 HW 없이 후처리 라인 4단계 시나리오를 검증하기 위한
시뮬레이션 엔드포인트만 노출한다. APP_ENV=development 일 때만 활성화.

지원 시나리오 (사용자 요청 2026-04-26):

  S1. ToPP 도착 + 작업자 핸드오프 버튼
        POST /api/debug/handoff-ack
        → trans_stat.cur_stat: WAIT_HANDOFF → WAIT_DLD
        → trans_task_txn(ToPP).txn_stat: PROC → SUCC
        → item.cur_stat: ToPP → PP, equip_task_type=PP, trans_task_type=NULL, cur_res=NULL
        → pp_task_txn 다건 INSERT (ord_pp_map 기준, txn_stat=QUE)
        → handoff_acks 감사 로그 INSERT

  S2. 작업자 RFID 스캔 (조회 only — 상태 변경 없음 + rfid_scan_log append)
        POST /api/debug/sim/rfid-scan
        → rfid_scan_log INSERT (item_id 바인딩)
        → 응답에 item + 후처리 옵션(정의+진행) 포함 (lookup 헬퍼 재사용)

  S3. 후처리 완료 + RFID 부착 + 컨베이어 TOF1 진입
        POST /api/debug/sim/conveyor-tof1
        → 해당 item 의 모든 pp_task_txn(QUE/PROC) → SUCC, end_at=now()
        → item.cur_stat: PP → ToINSP, equip_task_type=ToINSP
        → equip_task_txn 신규 INSERT (task_type=ToINSP, txn_stat=PROC, res_id=CONV-01)
        → equip_stat INSERT (cur_stat=ON)

  S4. 컨베이어 TOF2 도달 → 검사 시작
        POST /api/debug/sim/conveyor-tof2
        → equip_task_txn(ToINSP, PROC) → SUCC, end_at=now()
        → equip_stat INSERT (cur_stat=OFF)
        → item.cur_stat: ToINSP → INSP, equip_task_type=INSP, cur_res=CONV-01
        → insp_task_txn 신규 INSERT (txn_stat=PROC, start_at=now())

규칙:
  - 안 1 (pp_task_txn 자동화): TOF1 진입 = 모든 QUE → SUCC 직행
  - 안 b (lookup 응답): ord_pp_map 정의 + pp_task_txn 진행 현황 동시 노출
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Item,
    OrdPpMap,
    PpOption,
    PpTaskTxn,
    RfidScanLog,
)

router = APIRouter(prefix="/api/debug", tags=["debug"])

# RFID payload 형식: order_<ord_id>_item_<YYYYMMDD>_<seq>
RFID_PAYLOAD_RE = re.compile(r"^order_(?P<ord>\d+)_item_(?P<date>\d{8})_(?P<seq>\d+)$")

# 가상 모드의 기본 컨베이어 자원 ID
DEFAULT_CONV_RES_ID = "CONV-01"


# ----------------------------------------------------------------------------
# 공용 헬퍼
# ----------------------------------------------------------------------------


def _resolve_item_by_payload(db: Session, payload: str) -> Item | None:
    """RFID payload (`order_X_item_YYYYMMDD_N`) → smartcast.item 1건.

    payload 의 ord_id 와 item.ord_id 만 사용해 동일 ord 의 가장 최근 item 을 매칭.
    sequence 정합성은 가상 모드에서 강하게 검사하지 않는다.
    """
    m = RFID_PAYLOAD_RE.fullmatch(payload.strip())
    if m is None:
        return None
    ord_id = int(m.group("ord"))
    seq = int(m.group("seq"))
    # 우선 ord_id + seq 매칭 시도, 실패 시 ord_id 의 최신 item
    item = db.query(Item).filter(Item.ord_id == ord_id, Item.item_id == seq).first()
    if item is not None:
        return item
    return db.query(Item).filter(Item.ord_id == ord_id).order_by(desc(Item.item_id)).first()


def _build_pp_options_view(db: Session, item: Item) -> list[dict]:
    """안 b: ord_pp_map 정의 + pp_task_txn 진행 현황 동시 노출."""
    rows = (
        db.query(OrdPpMap, PpOption)
        .join(PpOption, PpOption.pp_id == OrdPpMap.pp_id)
        .filter(OrdPpMap.ord_id == item.ord_id)
        .all()
    )
    if not rows:
        return []

    # item 별 pp_task_txn 최신 1건씩 (pp_nm 기준)
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
                "txn_stat": (latest.txn_stat if latest else None),  # None = 아직 INSERT 안 됨
                "txn_id": (latest.txn_id if latest else None),
                "start_at": (latest.start_at.isoformat() if latest and latest.start_at else None),
                "end_at": (latest.end_at.isoformat() if latest and latest.end_at else None),
            }
        )
    return out


# ----------------------------------------------------------------------------
# S1. 핸드오프 ACK (가상 푸시 버튼)
# ----------------------------------------------------------------------------


@router.post("/handoff-ack")
def simulate_handoff_ack(
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
) -> dict:
    """가상 푸시 버튼 — ToPP 도착 AMR 1대 해제 + item 후처리 라인 진입.

    Body (모두 optional):
      operator_id : int  (로그인된 작업자 user_id; pp_task_txn.operator_id 에 기록)

    실 HW 동작 (ESP32 GPIO33 → Jetson esp_bridge.py → Mgmt gRPC ReportHandoffAck) 와
    동일 결과를 FastAPI 측 DB 에 반영. 공유 헬퍼 apply_handoff() 사용.
    """
    import os as _os
    import sys

    _MGMT_DIR = _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))),
        "management",
    )
    if _MGMT_DIR not in sys.path:
        sys.path.insert(0, _MGMT_DIR)
    from services.handoff_pipeline import apply_handoff  # type: ignore

    operator_id = payload.get("operator_id")
    now_ms = int(datetime.now().timestamp() * 1000)
    result = apply_handoff(
        db,
        button_device_id="SIM-KEYBOARD",
        ack_source="debug_endpoint",
        via="fastapi_debug",
        idempotency_key=f"sim:{now_ms}",
        operator_id=int(operator_id) if operator_id is not None else None,
    )
    db.commit()

    return {
        "released": result.released,
        "orphan": result.orphan,
        "task_id": result.task_id,
        "amr_id": result.amr_id,
        "item_id": result.item_id,
        "ord_id": result.ord_id,
        "pp_task_txn_ids": result.pp_task_txn_ids,
        "item_cur_stat": result.item_cur_stat,
        "reason": result.reason,
    }


# ----------------------------------------------------------------------------
# S2. 가상 RFID 스캔 (작업자가 도착 주물 식별 + 옵션 조회)
# ----------------------------------------------------------------------------


@router.post("/sim/rfid-scan")
def simulate_rfid_scan(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
) -> dict:
    """가상 RFID 스캔 — rfid_scan_log INSERT + item + 후처리 옵션 조회.

    Body:
      reader_id   : str  (default "ESP-CONV-01")
      zone        : str  (default "postprocessing")
      raw_payload : str  required, 형식 "order_<ord_id>_item_<YYYYMMDD>_<seq>"
    """
    reader_id = (payload.get("reader_id") or "ESP-CONV-01").strip()
    zone = (payload.get("zone") or "postprocessing").strip() or None
    raw_payload = (payload.get("raw_payload") or "").strip()
    if not raw_payload:
        raise HTTPException(status_code=400, detail="raw_payload required")

    item = _resolve_item_by_payload(db, raw_payload)
    parse_status = "ok" if RFID_PAYLOAD_RE.fullmatch(raw_payload) else "bad_format"
    now_utc = datetime.now(UTC)

    # 가상 모드 idempotency_key — 매 호출 고유 (재현 호출도 그대로 INSERT)
    idem = f"sim:{reader_id}:{int(now_utc.timestamp() * 1000)}"

    db.add(
        RfidScanLog(
            scanned_at=now_utc,
            reader_id=reader_id,
            zone=zone,
            raw_payload=raw_payload,
            ord_id=str(item.ord_id) if item else None,
            item_key=raw_payload,
            item_id=item.item_id if item else None,
            parse_status=parse_status,
            idempotency_key=idem,
            extra={"via": "fastapi_debug_sim"},
        )
    )
    db.commit()

    if item is None:
        return {
            "matched": False,
            "parse_status": parse_status,
            "raw_payload": raw_payload,
            "reason": "payload regex mismatch or item not found",
        }

    return {
        "matched": True,
        "parse_status": parse_status,
        "item": {
            "item_id": item.item_id,
            "ord_id": item.ord_id,
            "cur_stat": item.cur_stat,
            "equip_task_type": item.equip_task_type,
            "trans_task_type": item.trans_task_type,
            "cur_res": item.cur_res,
            "is_defective": item.is_defective,
        },
        "pp_options": _build_pp_options_view(db, item),
    }


# ----------------------------------------------------------------------------
# S3. 컨베이어 TOF1 진입 (후처리 완료 + 검사 라인 진입)
# ----------------------------------------------------------------------------


@router.post("/sim/conveyor-tof1")
def simulate_conveyor_tof1(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
) -> dict:
    """가상 TOF1 진입 — 후처리 완료 처리 + ToINSP equip_task_txn 시작.

    구현은 services/handoff_pipeline.py:apply_tof1() 공유 헬퍼를 사용한다.
    Mgmt gRPC ReportConveyorEvent(event_type='tof1_entry') 와 동일 결과.
    """
    import os as _os
    import sys

    _MGMT_DIR = _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))),
        "management",
    )
    if _MGMT_DIR not in sys.path:
        sys.path.insert(0, _MGMT_DIR)
    from services.handoff_pipeline import apply_tof1  # type: ignore

    res_id = (payload.get("res_id") or DEFAULT_CONV_RES_ID).strip()
    explicit_item_id = payload.get("item_id")
    rfid_payload = (payload.get("rfid_payload") or "").strip() or None
    operator_id = payload.get("operator_id")

    result = apply_tof1(
        db,
        res_id=res_id,
        rfid_payload=rfid_payload,
        item_id=int(explicit_item_id) if explicit_item_id is not None else None,
        operator_id=int(operator_id) if operator_id is not None else None,
    )
    if not result.ok:
        raise HTTPException(status_code=404, detail=result.reason)
    db.commit()
    return {
        "ok": True,
        "item_id": result.item_id,
        "ord_id": result.ord_id,
        "res_id": result.res_id,
        "pp_task_txn_succ": result.pp_task_txn_succ,
        "equip_task_txn_id": result.equip_task_txn_id,
        "item_cur_stat": result.item_cur_stat,
        "reason": result.reason,
    }


# ----------------------------------------------------------------------------
# S4. 컨베이어 TOF2 도달 (검사 공정 시작)
# ----------------------------------------------------------------------------


@router.post("/sim/conveyor-tof2")
def simulate_conveyor_tof2(
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
) -> dict:
    """가상 TOF2 도달 — ToINSP 종료 + insp_task_txn 시작.

    구현은 services/handoff_pipeline.py:apply_tof2() 공유 헬퍼를 사용한다.
    Mgmt gRPC ReportConveyorEvent(event_type='tof2_exit') 와 동일 결과.
    """
    import os as _os
    import sys

    _MGMT_DIR = _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))),
        "management",
    )
    if _MGMT_DIR not in sys.path:
        sys.path.insert(0, _MGMT_DIR)
    from services.handoff_pipeline import apply_tof2  # type: ignore

    res_id = (payload.get("res_id") or DEFAULT_CONV_RES_ID).strip()
    explicit_item_id = payload.get("item_id")

    result = apply_tof2(
        db,
        res_id=res_id,
        item_id=int(explicit_item_id) if explicit_item_id is not None else None,
    )
    if not result.ok:
        raise HTTPException(status_code=404, detail=result.reason)
    db.commit()
    return {
        "ok": True,
        "item_id": result.item_id,
        "ord_id": result.ord_id,
        "res_id": result.res_id,
        "equip_task_txn_succ_id": result.equip_task_txn_succ_id,
        "insp_task_txn_id": result.insp_task_txn_id,
        "item_cur_stat": result.item_cur_stat,
        "reason": result.reason,
    }


# ----------------------------------------------------------------------------
# Lookup — RFID payload 로 item + 후처리 옵션 조회 (read-only)
# ----------------------------------------------------------------------------


@router.get("/items/by-rfid")
def lookup_item_by_rfid(
    payload: str = Query(..., description="order_<ord>_item_<YYYYMMDD>_<seq>"),
    db: Session = Depends(get_db),
) -> dict:
    """RFID payload 로 item + 후처리 옵션(정의 + 진행 현황) 조회.

    PyQt 후처리 작업자 화면이 RFID 스캔 시 호출. 상태 변경 없음.
    """
    item = _resolve_item_by_payload(db, payload)
    if item is None:
        raise HTTPException(status_code=404, detail=f"item not found for payload={payload}")
    return {
        "item": {
            "item_id": item.item_id,
            "ord_id": item.ord_id,
            "cur_stat": item.cur_stat,
            "equip_task_type": item.equip_task_type,
            "trans_task_type": item.trans_task_type,
            "cur_res": item.cur_res,
            "is_defective": item.is_defective,
        },
        "pp_options": _build_pp_options_view(db, item),
    }
