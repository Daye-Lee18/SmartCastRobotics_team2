"""Equipment 트랜잭션 모델 — EquipTaskTxn, EquipStat, EquipErrLog.

생산 설비 (RA, CONV) 의 작업지시 + 실시간 상태 + 에러 로그.
이송 (AMR) 은 transport.py 에 별도.
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


class EquipTaskTxn(Base):
    """생산 설비 작업지시 트랜잭션 (RA/CONV)."""

    __tablename__ = "equip_task_txn"
    __table_args__ = (
        CheckConstraint("txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')", name="chk_equip_txn_stat"),
        {"schema": SCHEMA},
    )

    txn_id = Column(Integer, primary_key=True, autoincrement=True)
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"))
    task_type = Column(String)
    txn_stat = Column(String)
    item_id = Column(Integer, ForeignKey(f"{SCHEMA}.item.item_id"))
    strg_loc_id = Column(Integer, ForeignKey(f"{SCHEMA}.strg_location_stat.loc_id"))
    ship_loc_id = Column(Integer, ForeignKey(f"{SCHEMA}.ship_location_stat.loc_id"))
    req_at = Column(DateTime, server_default=func.now())
    start_at = Column(DateTime)
    end_at = Column(DateTime)


class EquipStat(Base):
    """생산 설비 실시간 상태."""

    __tablename__ = "equip_stat"
    __table_args__ = ({"schema": SCHEMA},)

    stat_id = Column(Integer, primary_key=True, autoincrement=True)
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"), nullable=False)
    item_id = Column(Integer, ForeignKey(f"{SCHEMA}.item.item_id"))
    txn_type = Column(String)
    cur_stat = Column(String)
    updated_at = Column(DateTime, server_default=func.now())
    err_msg = Column(String)


class EquipErrLog(Base):
    """생산 설비 에러 로그."""

    __tablename__ = "equip_err_log"
    __table_args__ = ({"schema": SCHEMA},)

    err_id = Column(Integer, primary_key=True, autoincrement=True)
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"))
    task_txn_id = Column(Integer, ForeignKey(f"{SCHEMA}.equip_task_txn.txn_id"))
    failed_stat = Column(String)
    err_msg = Column(String)
    occured_at = Column(DateTime, server_default=func.now())
