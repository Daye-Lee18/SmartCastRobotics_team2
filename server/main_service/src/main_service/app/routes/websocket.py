"""WebSocket router — smartcast schema (간소화).

연결: ws://host/ws/dashboard
브로드캐스트:
  - equip_stat 업데이트 (5초 간격 polling)
  - trans_stat 업데이트 (5초 간격 polling)
  - 새 ord_stat / err_log 발생 (5초 polling)

레거시의 random mock 데이터 제거; 실제 DB 폴링으로 교체.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database import SessionLocal
from app.models import EquipStat, OrdStat, TransStat

router = APIRouter()


class _Pool:
    """간단한 connection pool."""

    def __init__(self) -> None:
        self.conns: list[WebSocket] = []

    async def join(self, ws: WebSocket) -> None:
        await ws.accept()
        self.conns.append(ws)

    def leave(self, ws: WebSocket) -> None:
        if ws in self.conns:
            self.conns.remove(ws)

    async def broadcast(self, payload: dict) -> None:
        msg = json.dumps(payload, default=str)
        for ws in list(self.conns):
            try:
                await ws.send_text(msg)
            except Exception:
                self.leave(ws)


_pool = _Pool()


def _snapshot() -> dict:
    """현재 시점 상태 스냅샷 (DB 폴링)."""
    db = SessionLocal()
    try:
        equip_stats = [
            {
                "res_id": s.res_id,
                "cur_stat": s.cur_stat,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                "err_msg": s.err_msg,
            }
            for s in db.query(EquipStat).all()
        ]
        trans_stats = [
            {
                "res_id": s.res_id,
                "cur_stat": s.cur_stat,
                "battery_pct": s.battery_pct,
                "cur_zone_type": s.cur_zone_type,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in db.query(TransStat).all()
        ]
        latest_ord_stats = [
            {
                "ord_id": s.ord_id,
                "ord_stat": s.ord_stat,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in db.query(OrdStat).order_by(OrdStat.updated_at.desc()).limit(20).all()
        ]
    finally:
        db.close()
    return {
        "ts": datetime.utcnow().isoformat() + "Z",
        "equip": equip_stats,
        "trans": trans_stats,
        "ord_stats_recent": latest_ord_stats,
    }


@router.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket) -> None:
    await _pool.join(ws)
    try:
        # 첫 스냅샷 즉시 전송
        await ws.send_text(json.dumps(_snapshot(), default=str))
        # 5초 polling broadcast loop
        while True:
            await asyncio.sleep(5)
            await ws.send_text(json.dumps(_snapshot(), default=str))
    except WebSocketDisconnect:
        _pool.leave(ws)
    except Exception:
        _pool.leave(ws)
