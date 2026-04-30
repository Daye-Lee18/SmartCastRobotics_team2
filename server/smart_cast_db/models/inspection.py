"""Inspection / Post-process 트랜잭션 모델 — PpTaskTxn, InspTaskTxn.

후처리 작업 (operator 가 수동 진행) + 품질 검사 (CONV1 + AI 자동).
"""

from __future__ import annotations

from ._base import (
    SCHEMA,
    Base,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)


class PpTaskTxn(Base):
    """후처리 작업 트랜잭션."""

    __tablename__ = "pp_task_txn"
    __table_args__ = (
        CheckConstraint("txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')", name="chk_pp_txn_stat"),
        {"schema": SCHEMA},
    )

    txn_id = Column(Integer, primary_key=True, autoincrement=True)
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), nullable=False)
    map_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord_pp_map.map_id"))
    pp_nm = Column(String)
    item_id = Column(Integer, ForeignKey(f"{SCHEMA}.item.item_id"))
    operator_id = Column(Integer, ForeignKey(f"{SCHEMA}.user_account.user_id"))
    txn_stat = Column(String)
    req_at = Column(DateTime, server_default=func.now())
    start_at = Column(DateTime)
    end_at = Column(DateTime)


class InspTaskTxn(Base):
    """품질 검사 작업 트랜잭션 (CONV1 + AI)."""

    __tablename__ = "insp_task_txn"
    __table_args__ = (
        CheckConstraint("txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')", name="chk_insp_txn_stat"),
        {"schema": SCHEMA},
    )

    txn_id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey(f"{SCHEMA}.item.item_id"))
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"))
    txn_stat = Column(String)
    result = Column(Boolean)  # NULL=미검사, FALSE=DP, TRUE=GP
    req_at = Column(DateTime, server_default=func.now())
    start_at = Column(DateTime)
    end_at = Column(DateTime)
