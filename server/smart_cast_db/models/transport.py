"""Transport transaction/state/log models aligned to DB schema v21."""

from __future__ import annotations

from sqlalchemy.orm import synonym

from ._base import (
    SCHEMA,
    Base,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)


class TransTaskTxn(Base):
    __tablename__ = "trans_task_txn"
    __table_args__ = (
        CheckConstraint("task_type IN ('ToPP', 'ToSTRG', 'ToSHIP', 'ToCHG')", name="chk_trans_task_type"),
        CheckConstraint("txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')", name="chk_trans_txn_stat"),
        {"schema": SCHEMA},
    )

    txn_id = Column(Integer, primary_key=True, autoincrement=True)
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.trans.res_id"))
    task_type = Column(String, nullable=False)
    txn_stat = Column(String, nullable=False)
    chg_loc_id = Column(Integer, ForeignKey(f"{SCHEMA}.trans_coord.trans_coord_id"))
    item_stat_id = Column(Integer, ForeignKey(f"{SCHEMA}.item_stat.item_stat_id"))
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"))
    req_at = Column(DateTime, server_default=func.now())
    start_at = Column(DateTime)
    end_at = Column(DateTime)

    # Legacy compatibility
    trans_task_txn_id = synonym("txn_id")
    trans_id = synonym("res_id")
    item_id = synonym("item_stat_id")


class TransStat(Base):
    __tablename__ = "trans_stat"
    __table_args__ = (
        CheckConstraint(
            "cur_stat IS NULL OR cur_stat IN ('IDLE', 'ALLOC', 'CHG', 'TO_IDLE', 'MV_SRC', 'WAIT_LD', 'MV_DEST', 'WAIT_DLD', 'SUCC', 'FAIL')",
            name="chk_trans_cur_stat",
        ),
        CheckConstraint("battery_pct IS NULL OR battery_pct BETWEEN 0 AND 100", name="chk_trans_battery_pct"),
        {"schema": SCHEMA},
    )

    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.trans.res_id"), primary_key=True)
    item_stat_id = Column(Integer, ForeignKey(f"{SCHEMA}.item_stat.item_stat_id"))
    cur_stat = Column(String)
    battery_pct = Column(Integer)
    cur_trans_coord_id = Column(Integer, ForeignKey(f"{SCHEMA}.trans_coord.trans_coord_id"))
    updated_at = Column(DateTime, server_default=func.now())

    # Legacy compatibility
    item_id = synonym("item_stat_id")
    cur_zone_type = synonym("cur_trans_coord_id")


class LogDataTrans(Base):
    __tablename__ = "log_data_trans"
    __table_args__ = (
        CheckConstraint("status IS NULL OR status IN ('normal', 'warning', 'fault')", name="chk_log_data_trans_status"),
        {"schema": SCHEMA},
    )

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.trans.res_id"), nullable=False)
    txn_id = Column(Integer, ForeignKey(f"{SCHEMA}.trans_task_txn.txn_id"))
    sensor_type = Column(String(30), nullable=False)
    raw_value = Column(Numeric(10, 4), nullable=False)
    physical_value = Column(Numeric(10, 4))
    unit = Column(String(10))
    status = Column(String(10))
    logged_at = Column(DateTime, server_default=func.now())


class LogErrTrans(Base):
    __tablename__ = "log_err_trans"
    __table_args__ = ({"schema": SCHEMA},)

    err_id = Column(Integer, primary_key=True, autoincrement=True)
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.trans.res_id"))
    task_txn_id = Column(Integer, ForeignKey(f"{SCHEMA}.trans_task_txn.txn_id"))
    failed_stat = Column(String)
    err_msg = Column(String)
    battery_pct = Column(Integer)
    occured_at = Column(DateTime, server_default=func.now())
