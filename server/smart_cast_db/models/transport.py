"""Transport 트랜잭션 모델 — TransTaskTxn, TransStat, LogErrTrans.

AMR 이송 작업 + 실시간 상태 (배터리 포함) + 에러 로그.
생산 설비 (RA/CONV) 는 equipment.py 에 별도.
"""

from __future__ import annotations

from ._base import (
    SCHEMA,
    Base,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)


class TransTaskTxn(Base):
    """AMR 이송 작업 트랜잭션."""

    __tablename__ = "trans_task_txn"
    __table_args__ = (
        CheckConstraint("txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')", name="chk_trans_txn_stat"),
        {"schema": SCHEMA},
    )

    trans_task_txn_id = Column(Integer, primary_key=True, autoincrement=True)
    trans_id = Column(String, ForeignKey(f"{SCHEMA}.trans.res_id"))
    task_type = Column(String)
    txn_stat = Column(String)
    chg_loc_id = Column(Integer, ForeignKey(f"{SCHEMA}.chg_location_stat.loc_id"))
    item_id = Column(Integer, ForeignKey(f"{SCHEMA}.item.item_id"))
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"))
    req_at = Column(DateTime, server_default=func.now())
    start_at = Column(DateTime)
    end_at = Column(DateTime)


class TransStat(Base):
    """AMR 실시간 상태 (배터리 포함).

    cur_zone_type: AWS RDS Casting public 스키마는 INTEGER (실측 확인 2026-04-27).
    smartcast 캐노니컬 (create_tables_v2.sql:291) 는 VARCHAR — 현재 비활성.
    SQLAlchemy ORM 이 RETURNING 절 때문에 INSERT 에 자동 포함하므로 활성 DB(RDS) 와 일치 필수.
    smartcast 재활성화 시 마이그레이션 OR 모델 분기 필요.
    """

    __tablename__ = "trans_stat"
    __table_args__ = ({"schema": SCHEMA},)

    res_id = Column(String, ForeignKey(f"{SCHEMA}.trans.res_id"), primary_key=True)
    item_id = Column(Integer, ForeignKey(f"{SCHEMA}.item.item_id"))
    cur_stat = Column(String)
    battery_pct = Column(Integer)
    cur_zone_type = Column(Integer)
    updated_at = Column(DateTime, server_default=func.now())


class LogErrTrans(Base):
    """AMR 에러 로그 (배터리 포함)."""

    __tablename__ = "log_err_trans"
    __table_args__ = ({"schema": SCHEMA},)

    err_id = Column(Integer, primary_key=True, autoincrement=True)
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"))
    task_txn_id = Column(Integer, ForeignKey(f"{SCHEMA}.trans_task_txn.trans_task_txn_id"))
    failed_stat = Column(String)
    err_msg = Column(String)
    battery_pct = Column(Integer)
    occured_at = Column(DateTime, server_default=func.now())
