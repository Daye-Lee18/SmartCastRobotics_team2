"""TimescaleDB 런타임 검출 + 시계열 집계 helper.

DB 서버에 timescaledb extension 이 있으면 hypertable 기반 time_bucket() 쿼리,
없으면 기본 GROUP BY date_trunc 로 폴백 (집계 동작은 동일, 성능만 차이).

검출 결과는 1회 캐시되어 매 요청마다 pg_extension 조회를 반복하지 않는다.
설치/제거 시 backend 재시작 필요.

2026-04-27 schema-aware 패치:
  이전: 모든 쿼리가 'smartcast.item', 'smartcast.equip_err_log' 등 하드코딩.
  현재 개발 DB(public 스키마) 에서는 테이블 미존재 → 500 발생.
  → app.models.models.SCHEMA 환경변수와 동일한 SCHEMA prefix 사용 + 테이블
    미존재 시 빈 배열 반환 (UndefinedTable 예외 swallow).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _schema() -> str:
    """models.SCHEMA 와 동일 (런타임 import 로 순환참조 회피)."""
    from smart_cast_db.models._base import SCHEMA

    return SCHEMA


@lru_cache(maxsize=1)
def has_timescaledb() -> bool:
    """pg_extension 에 timescaledb 가 있는지 1회 검사 후 캐시."""
    from smart_cast_db.database import engine

    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'timescaledb' LIMIT 1")
            ).first()
            return row is not None
    except Exception:
        return False


def _safe_query(db: Session, sql: str, params: dict, label: str) -> list:
    """SQL 실행. 테이블 미존재(UndefinedTable) 등 스키마 불일치 시 빈 배열.

    상위 라우트에 500 이 새어나가는 것을 차단한다.
    """
    try:
        return list(db.execute(text(sql), params).all())
    except ProgrammingError as exc:
        # 테이블/스키마 미존재 — 환경에 따라 정상 (예: public 스키마 + ERP 테이블 누락).
        logger.info("[%s] schema/table missing, returning []: %s", label, exc.orig)
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        return []
    except Exception:  # noqa: BLE001
        logger.exception("[%s] unexpected query error", label)
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        return []


def hourly_item_production(db: Session, hours: int = 24) -> list[dict]:
    """최근 N 시간 시간대별 item 생산 카운트.

    TimescaleDB + smartcast 스키마면 hypertable continuous aggregate 사용,
    그 외에는 schema-aware date_trunc 폴백.
    """
    since = datetime.now() - timedelta(hours=hours)
    schema = _schema()

    # continuous aggregate 는 smartcast 스키마 + timescale 둘 다일 때만 시도
    if schema == "smartcast" and has_timescaledb():
        rows = _safe_query(
            db,
            f"""
                SELECT bucket, produced
                FROM {schema}.item_hourly
                WHERE bucket >= :since
                ORDER BY bucket
            """,
            {"since": since},
            "hourly_item_production[ts]",
        )
        if rows:
            return [{"bucket": r.bucket.isoformat(), "produced": r.produced} for r in rows]

    # 기본 폴백 — group by date_trunc('hour', updated_at)
    rows = _safe_query(
        db,
        f"""
            SELECT date_trunc('hour', updated_at) AS bucket, COUNT(*) AS produced
            FROM {schema}.item
            WHERE updated_at >= :since
            GROUP BY bucket
            ORDER BY bucket
        """,
        {"since": since},
        "hourly_item_production[fallback]",
    )
    return [{"bucket": r.bucket.isoformat(), "produced": r.produced} for r in rows]


def weekly_item_production(db: Session, weeks: int = 8) -> list[dict]:
    """최근 N 주 주간 item 생산 카운트."""
    since = datetime.now() - timedelta(weeks=weeks)
    schema = _schema()
    rows = _safe_query(
        db,
        f"""
            SELECT date_trunc('week', updated_at) AS bucket, COUNT(*) AS produced
            FROM {schema}.item
            WHERE updated_at >= :since
            GROUP BY bucket
            ORDER BY bucket
        """,
        {"since": since},
        "weekly_item_production",
    )
    return [{"bucket": r.bucket.date().isoformat(), "produced": r.produced} for r in rows]


def err_log_trend(db: Session, hours: int = 24) -> list[dict]:
    """equip + trans err_log 시간대별 발생 카운트.

    err_log 테이블이 없으면 빈 배열. 두 테이블 중 하나만 있어도 부분 결과 반환.
    """
    since = datetime.now() - timedelta(hours=hours)
    schema = _schema()

    equip_rows = _safe_query(
        db,
        f"""
            SELECT date_trunc('hour', occured_at) AS bucket, COUNT(*) AS count
            FROM {schema}.equip_err_log
            WHERE occured_at >= :since
            GROUP BY bucket
            ORDER BY bucket
        """,
        {"since": since},
        "err_log_trend[equip]",
    )
    trans_rows = _safe_query(
        db,
        f"""
            SELECT date_trunc('hour', occured_at) AS bucket, COUNT(*) AS count
            FROM {schema}.trans_err_log
            WHERE occured_at >= :since
            GROUP BY bucket
            ORDER BY bucket
        """,
        {"since": since},
        "err_log_trend[trans]",
    )

    out = [
        {"bucket": r.bucket.isoformat(), "source": "equip", "count": r.count} for r in equip_rows
    ] + [{"bucket": r.bucket.isoformat(), "source": "trans", "count": r.count} for r in trans_rows]
    out.sort(key=lambda d: (d["bucket"], d["source"]))
    return out
