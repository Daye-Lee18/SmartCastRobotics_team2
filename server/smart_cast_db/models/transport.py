"""Transport models aligned to create_tables.sql."""

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
    Numeric,
    String,
    func,
    synonym,
)


class TransTaskTxn(Base):
    __tablename__ = "trans_task_txn"
    __table_args__ = (
        CheckConstraint("task_type IN ('ToPP', 'ToSTRG', 'ToSHIP', 'ToCHG')", name="chk_trans_task_type"),
        CheckConstraint("txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')", name="chk_trans_txn_stat"),
        {"schema": SCHEMA},
    )

    trans_task_txn_id = Column(Integer, primary_key=True, autoincrement=True)
    trans_id = Column(String(10), ForeignKey(f"{SCHEMA}.trans.res_id"))
    task_type = Column(String, nullable=False)
    txn_stat = Column(String, nullable=False)
    chg_loc_id = Column(Integer, ForeignKey(f"{SCHEMA}.chg_location_stat.loc_id"))
    item_id = Column(Integer, ForeignKey(f"{SCHEMA}.item.item_id"))
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"))
    req_at = Column(DateTime, server_default=func.now())
    start_at = Column(DateTime)
    end_at = Column(DateTime)

    txn_id = synonym("trans_task_txn_id")
    res_id = synonym("trans_id")
    item_stat_id = synonym("item_id")


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
    item_id = Column(Integer, ForeignKey(f"{SCHEMA}.item.item_id"))
    cur_stat = Column(String)
    battery_pct = Column(Integer)
    cur_zone_type = Column(Integer)
    updated_at = Column(DateTime, server_default=func.now())

    item_stat_id = synonym("item_id")
    cur_trans_coord_id = synonym("cur_zone_type")


class TatNavPoseMaster(Base):
    __tablename__ = "tat_nav_pose_master"
    __table_args__ = (
        CheckConstraint(
            "pose_nm IN ('ToINSP', 'ToSHIP', 'ToCAST', 'ToCHG1', 'ToCHG2', 'ToCHG3', 'ToSTRG', 'ToPICK', 'ToPP')",
            name="chk_tat_nav_pose_nm",
        ),
        CheckConstraint(
            "(pose_nm LIKE 'ToCHG%' AND loc_id IS NOT NULL) OR "
            "(pose_nm NOT LIKE 'ToCHG%' AND loc_id IS NULL)",
            name="chk_tat_nav_pose_chg_loc",
        ),
        {"schema": SCHEMA},
    )

    pose_id = Column(Integer, primary_key=True, autoincrement=True)
    pose_nm = Column(String, nullable=False, unique=True)
    zone_id = Column(Integer, ForeignKey(f"{SCHEMA}.zone.zone_id"), nullable=False)
    loc_id = Column(Integer, ForeignKey(f"{SCHEMA}.chg_location_stat.loc_id"))
    pose_x = Column(Numeric, nullable=False)
    pose_y = Column(Numeric, nullable=False)
    pose_theta = Column(Numeric, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")

    # Compatibility with older callers that used TransCoord.
    trans_coord_id = synonym("pose_id")
    chg_loc_id = synonym("loc_id")
    x = synonym("pose_x")
    y = synonym("pose_y")
    theta = synonym("pose_theta")


class LogDataTrans(Base):
    __tablename__ = "log_data_trans"
    __table_args__ = (
        CheckConstraint("status IS NULL OR status IN ('normal', 'warning', 'fault')", name="chk_log_data_trans_status"),
        {"schema": SCHEMA},
    )

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"), nullable=False)
    txn_id = Column(Integer, ForeignKey(f"{SCHEMA}.trans_task_txn.trans_task_txn_id"))
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
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"))
    task_txn_id = Column(Integer, ForeignKey(f"{SCHEMA}.trans_task_txn.trans_task_txn_id"))
    failed_stat = Column(String)
    err_msg = Column(String)
    battery_pct = Column(Integer)
    occured_at = Column(DateTime, server_default=func.now())
