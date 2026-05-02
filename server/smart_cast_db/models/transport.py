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
    String,
    relationship,
    func,
)
from sqlalchemy import BigInteger, text
from sqlalchemy.dialects.postgresql import JSONB


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


class TransportTask(Base):
    """이송 작업 (smartcast.transport_tasks)."""

    __tablename__ = "transport_tasks"
    __table_args__ = ({"schema": SCHEMA},)

    id = Column(String, primary_key=True, index=True)
    from_name = Column(String, nullable=False)
    from_coord = Column(String, nullable=True, default="")
    to_name = Column(String, nullable=False)
    to_coord = Column(String, nullable=True, default="")
    item_id = Column(String, nullable=True, default="")
    item_name = Column(String, nullable=True, default="")
    quantity = Column(Integer, nullable=False, default=1)
    priority = Column(String, nullable=False, default="medium")
    status = Column(String, nullable=False, default="unassigned")
    assigned_robot_id = Column(String, nullable=True, default="")
    requested_at = Column(String, nullable=False)
    completed_at = Column(String, nullable=True)


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
