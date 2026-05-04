"""Equipment task/state/log models aligned to create_tables.sql."""

from __future__ import annotations

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
    synonym,
)


class EquipTaskTxn(Base):
    __tablename__ = "equip_task_txn"
    __table_args__ = (
        CheckConstraint(
            "task_type IN ('MM', 'POUR', 'DM', 'PP', 'PA_GP', 'PA_DP', 'PICK', 'SHIP', 'ToINSP', 'ToPAWait')",
            name="chk_equip_task_type",
        ),
        CheckConstraint("txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')", name="chk_equip_txn_stat"),
        {"schema": SCHEMA},
    )

    txn_id = Column(Integer, primary_key=True, autoincrement=True)
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"))
    task_type = Column(String, nullable=False)
    txn_stat = Column(String, nullable=False)
    item_id = Column(Integer, ForeignKey(f"{SCHEMA}.item.item_id"))
    strg_loc_id = Column(Integer, ForeignKey(f"{SCHEMA}.strg_location_stat.loc_id"))
    ship_loc_id = Column(Integer, ForeignKey(f"{SCHEMA}.ship_location_stat.loc_id"))
    req_at = Column(DateTime, server_default=func.now())
    start_at = Column(DateTime)
    end_at = Column(DateTime)

    item_stat_id = synonym("item_id")


class EquipStat(Base):
    __tablename__ = "equip_stat"
    __table_args__ = (
        CheckConstraint(
            "cur_stat IS NULL OR cur_stat IN ('IDLE', 'ALLOC', 'FAIL', 'MV_SRC', 'GRASP', 'MV_DEST', 'RELEASE', 'TO_IDLE', 'ON', 'OFF')",
            name="chk_equip_cur_stat",
        ),
        {"schema": SCHEMA},
    )

    stat_id = Column(Integer, primary_key=True, autoincrement=True)
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"), nullable=False, unique=True)
    item_id = Column(Integer, ForeignKey(f"{SCHEMA}.item.item_id"))
    txn_type = Column(String)
    cur_stat = Column(String)
    updated_at = Column(DateTime, server_default=func.now())
    err_msg = Column(String)

    item_stat_id = synonym("item_id")


class LogDataEquip(Base):
    __tablename__ = "log_data_equip"
    __table_args__ = (
        CheckConstraint("status IS NULL OR status IN ('normal', 'warning', 'fault')", name="chk_log_data_equip_status"),
        {"schema": SCHEMA},
    )

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"), nullable=False)
    txn_id = Column(Integer, ForeignKey(f"{SCHEMA}.equip_task_txn.txn_id"))
    sensor_type = Column(String(30), nullable=False)
    raw_value = Column(Numeric(10, 4), nullable=False)
    physical_value = Column(Numeric(10, 4))
    unit = Column(String(10))
    status = Column(String(10))
    logged_at = Column(DateTime, server_default=func.now())


class LogErrEquip(Base):
    __tablename__ = "log_err_equip"
    __table_args__ = ({"schema": SCHEMA},)

    err_id = Column(Integer, primary_key=True, autoincrement=True)
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"))
    task_txn_id = Column(Integer, ForeignKey(f"{SCHEMA}.equip_task_txn.txn_id"))
    failed_stat = Column(String)
    err_msg = Column(String)
    occured_at = Column(DateTime, server_default=func.now())
