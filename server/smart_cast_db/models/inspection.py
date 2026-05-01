"""Inspection/post-process/pick models aligned to DB schema v21."""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import synonym

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
    UniqueConstraint,
    func,
)


class PpTaskTxn(Base):
    __tablename__ = "pp_task_txn"
    __table_args__ = (
        CheckConstraint("txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')", name="chk_pp_txn_stat"),
        {"schema": SCHEMA},
    )

    txn_id = Column(Integer, primary_key=True, autoincrement=True)
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), nullable=False)
    item_stat_id = Column(Integer, ForeignKey(f"{SCHEMA}.item_stat.item_stat_id"))
    map_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord_pp_map.map_id"))
    pp_nm = Column(String, ForeignKey(f"{SCHEMA}.pp_options.pp_nm"))
    operator_id = Column(Integer, ForeignKey(f"{SCHEMA}.user_account.user_id"))
    txn_stat = Column(String, nullable=False)
    req_at = Column(DateTime, server_default=func.now())
    start_at = Column(DateTime)
    end_at = Column(DateTime)

    # Legacy compatibility
    item_id = synonym("item_stat_id")


class AiModel(Base):
    __tablename__ = "ai_model"
    __table_args__ = (
        CheckConstraint("model_type IN ('YOLO', 'PATCHCORE')", name="chk_ai_model_type"),
        CheckConstraint("target_cls IS NULL OR target_cls IN ('CMH', 'RMH', 'EMH')", name="chk_ai_target_cls"),
        CheckConstraint(
            "(model_type = 'YOLO' AND target_cls IS NULL) OR (model_type = 'PATCHCORE' AND target_cls IS NOT NULL)",
            name="chk_ai_model_target_cls",
        ),
        UniqueConstraint("model_nm", "model_type", "target_cls", name="uq_ai_model_name_type_target"),
        {"schema": SCHEMA},
    )

    model_id = Column(Integer, primary_key=True, autoincrement=True)
    model_nm = Column(String(50), nullable=False)
    model_type = Column(String(20), nullable=False)
    target_cls = Column(String(5))
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime, server_default=func.now())


class InspTaskTxn(Base):
    __tablename__ = "insp_task_txn"
    __table_args__ = (
        CheckConstraint("txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')", name="chk_insp_txn_stat"),
        {"schema": SCHEMA},
    )

    txn_id = Column(Integer, primary_key=True, autoincrement=True)
    item_stat_id = Column(Integer, ForeignKey(f"{SCHEMA}.item_stat.item_stat_id"), nullable=False)
    txn_stat = Column(String(10), nullable=False)
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.equip.res_id"))
    req_at = Column(DateTime, server_default=func.now())
    start_at = Column(DateTime)
    end_at = Column(DateTime)

    # Legacy compatibility
    item_id = synonym("item_stat_id")


class AiInferenceTxn(Base):
    __tablename__ = "ai_inference_txn"
    __table_args__ = (
        CheckConstraint(
            "step_type IN ('CLASSIFICATION', 'ANOMALY_DETECTION')",
            name="chk_ai_inference_step_type",
        ),
        CheckConstraint("txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')", name="chk_ai_inference_txn_stat"),
        {"schema": SCHEMA},
    )

    inference_id = Column(Integer, primary_key=True, autoincrement=True)
    insp_txn_id = Column(Integer, ForeignKey(f"{SCHEMA}.insp_task_txn.txn_id"), nullable=False)
    model_id = Column(Integer, ForeignKey(f"{SCHEMA}.ai_model.model_id"), nullable=False)
    step_type = Column(String(30), nullable=False)
    txn_stat = Column(String(10), nullable=False)
    req_at = Column(DateTime, server_default=func.now())
    start_at = Column(DateTime)
    end_at = Column(DateTime)


class InspStat(Base):
    __tablename__ = "insp_stat"
    __table_args__ = (
        CheckConstraint("predicted_class IS NULL OR predicted_class IN ('CMH', 'RMH', 'EMH')", name="chk_insp_predicted_class"),
        CheckConstraint("final_result IS NULL OR final_result IN ('GP', 'DP')", name="chk_insp_final_result"),
        {"schema": SCHEMA},
    )

    insp_txn_id = Column(Integer, ForeignKey(f"{SCHEMA}.insp_task_txn.txn_id"), primary_key=True)
    item_stat_id = Column(Integer, ForeignKey(f"{SCHEMA}.item_stat.item_stat_id"), nullable=False)
    yolo_inference_id = Column(Integer, ForeignKey(f"{SCHEMA}.ai_inference_txn.inference_id"))
    patchcore_inference_id = Column(Integer, ForeignKey(f"{SCHEMA}.ai_inference_txn.inference_id"))
    predicted_class = Column(String(5))
    yolo_confidence = Column(Numeric)
    anomaly_score = Column(Numeric)
    anomaly_threshold = Column(Numeric)
    final_result = Column(String(2))
    result_json = Column(JSONB)
    updated_at = Column(DateTime, server_default=func.now())

    # Legacy compatibility
    item_id = synonym("item_stat_id")


class PickTxn(Base):
    __tablename__ = "pick_txn"
    __table_args__ = (
        CheckConstraint("txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')", name="chk_pick_txn_stat"),
        CheckConstraint("req_qty > 0", name="chk_pick_req_qty_gt_zero"),
        CheckConstraint("picked_qty >= 0", name="chk_pick_picked_qty_nonneg"),
        CheckConstraint("picked_qty <= req_qty", name="chk_pick_picked_qty_le_req_qty"),
        {"schema": SCHEMA},
    )

    txn_id = Column(Integer, primary_key=True, autoincrement=True)
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), nullable=False)
    txn_stat = Column(String(10), nullable=False)
    req_qty = Column(Integer, nullable=False)
    picked_qty = Column(Integer, nullable=False, server_default="0")
    req_at = Column(DateTime, server_default=func.now())
    start_at = Column(DateTime)
    end_at = Column(DateTime)


class PickItemMap(Base):
    __tablename__ = "pick_item_map"
    __table_args__ = (
        CheckConstraint("pick_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')", name="chk_pick_item_map_stat"),
        {"schema": SCHEMA},
    )

    pick_txn_id = Column(Integer, ForeignKey(f"{SCHEMA}.pick_txn.txn_id"), primary_key=True)
    item_stat_id = Column(Integer, ForeignKey(f"{SCHEMA}.item_stat.item_stat_id"), primary_key=True)
    equip_txn_id = Column(Integer, ForeignKey(f"{SCHEMA}.equip_task_txn.txn_id"))
    pick_stat = Column(String(10), nullable=False)
    mapped_at = Column(DateTime, server_default=func.now())

    # Legacy compatibility
    item_id = synonym("item_stat_id")
