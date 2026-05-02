"""Transport 도메인 모델 — TransTaskTxn, TransStat, LogErrTrans, TatNavPoseMaster,
TransportTask, HandoffAck.

AMR 이송 작업 + 실시간 상태 (배터리 포함) + 에러 로그.
생산 설비 (RA/CONV) 는 equipment.py 에 별도.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ._base import (
    SCHEMA,
    Base,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    Integer,
    Numeric,
    String,
    relationship,
    func,
)
from sqlalchemy import BigInteger, text
from sqlalchemy.dialects.postgresql import JSONB


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




class HandoffAck(Base):
    """후처리존 인수인계 확인 이벤트 (smartcast.handoff_acks)."""

    __tablename__ = "handoff_acks"
    __table_args__ = ({"schema": SCHEMA},)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ack_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True)
    task_id = Column(
        String,
        ForeignKey(f"{SCHEMA}.transport_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    zone = Column(String, nullable=False, index=True)
    amr_id = Column(String, nullable=True)
    ack_source = Column(
        String, nullable=False
    )  # 'esp32_button' | 'debug_endpoint' | 'gui_override'
    operator_id = Column(String, nullable=True)
    button_device_id = Column(String, nullable=True)
    orphan_ack = Column(Boolean, nullable=False, default=False)
    idempotency_key = Column(String, nullable=True)
    extra = Column("metadata", JSONB, nullable=True)  # 'metadata' 충돌 회피


class TatNavPoseMaster(Base):
    """TAT 네비게이션 목적지 마스터.

    nav2_params.yaml 의 실제 운용 포즈만 저장하고, *_WAIT 포즈는 제외한다.
    """

    __tablename__ = "tat_nav_pose_master"
    __table_args__ = (
        CheckConstraint(
            "pose_nm IN ('ToINSP', 'ToSHIP', 'ToCAST', 'ToCHG1', 'ToCHG2', 'ToCHG3', 'ToSTRG', 'ToPICK', 'ToPP')",
            name="chk_tat_nav_pose_nm",
        ),
        CheckConstraint(
            "(pose_nm LIKE 'ToCHG%' AND loc_id IS NOT NULL) OR (pose_nm NOT LIKE 'ToCHG%' AND loc_id IS NULL)",
            name="chk_tat_nav_pose_loc",
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
    is_active = Column(Boolean, nullable=False, server_default=text("TRUE"))

    zone = relationship("Zone")
    chg_location = relationship("ChgLocationStat")
