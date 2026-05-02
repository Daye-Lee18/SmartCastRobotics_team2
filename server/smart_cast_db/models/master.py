"""Master 데이터 모델 — Category, Product, ProductOption, PpOption,
Zone, PatternMaster, RaMotionStep, Res, Equip, EquipLoadSpec, Trans.

마스터 데이터 = 트랜잭션이 참조하는 정적 정의. seed 로 채워지고 자주 바뀌지 않음.
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
    Numeric,
    String,
    UniqueConstraint,
    func,
    relationship,
)
from sqlalchemy import text

# -----------------------------------------------------------------------------
# 표준 제품 (Category / Product / ProductOption / PpOption)
# -----------------------------------------------------------------------------


class Category(Base):
    __tablename__ = "category"
    __table_args__ = (
        CheckConstraint("cate_cd IN ('CMH', 'RMH', 'EMH')", name="chk_cate_cd"),
        {"schema": SCHEMA},
    )

    cate_cd = Column(String, primary_key=True)
    cate_nm = Column(String, nullable=False, unique=True)


class Product(Base):
    __tablename__ = "product"
    __table_args__ = ({"schema": SCHEMA},)

    prod_id = Column(Integer, primary_key=True, autoincrement=True)
    cate_cd = Column(String, ForeignKey(f"{SCHEMA}.category.cate_cd"), nullable=False)
    base_price = Column(Numeric, nullable=False)
    img_url = Column(String(400))

    category = relationship("smart_cast_db.models.master.Category")
    options = relationship(
        "smart_cast_db.models.master.ProductOption",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class ProductOption(Base):
    __tablename__ = "product_option"
    __table_args__ = ({"schema": SCHEMA},)

    prod_opt_id = Column(Integer, primary_key=True, autoincrement=True)
    prod_id = Column(Integer, ForeignKey(f"{SCHEMA}.product.prod_id"), nullable=False)
    mat_type = Column(String(20), nullable=False)
    diameter = Column(Numeric, nullable=False)
    thickness = Column(Numeric, nullable=False)
    material = Column(String(30), nullable=False)
    load_class = Column(String(20), nullable=False)

    product = relationship("smart_cast_db.models.master.Product", back_populates="options")


class PpOption(Base):
    __tablename__ = "pp_options"
    __table_args__ = ({"schema": SCHEMA},)

    pp_id = Column(Integer, primary_key=True, autoincrement=True)
    pp_nm = Column(String, unique=True)
    extra_cost = Column(Numeric)


# -----------------------------------------------------------------------------
# Operator (zone, pattern master)
# -----------------------------------------------------------------------------


class Zone(Base):
    """공정 6구역 (CAST/PP/INSP/STRG/SHIP/CHG)."""

    __tablename__ = "zone"
    __table_args__ = (
        CheckConstraint(
            "zone_nm IN ('CAST', 'PP', 'INSP', 'STRG', 'SHIP', 'CHG')",
            name="chk_zone_nm",
        ),
        {"schema": SCHEMA},
    )

    zone_id = Column(Integer, primary_key=True, autoincrement=True)
    zone_nm = Column(String, unique=True)


class PatternMaster(Base):
    """모션 패턴 마스터 (MM pattern 1~3)."""

    __tablename__ = "pattern_master"
    __table_args__ = (
        CheckConstraint("ptn_id BETWEEN 1 AND 3", name="chk_ptn_id_range"),
        CheckConstraint("task_type IN ('MM')", name="chk_pattern_task_type"),
        {"schema": SCHEMA},
    )

    ptn_id = Column(Integer, primary_key=True)
    ptn_nm = Column(String, nullable=False, unique=True)
    task_type = Column(String, nullable=False)
    description = Column(String)
    is_active = Column(Boolean, nullable=False, server_default=text("TRUE"))


# -----------------------------------------------------------------------------
# 설비 마스터 (res, equip, trans)
# -----------------------------------------------------------------------------


class Res(Base):
    """전체 설비 마스터 (RA/CONV/TAT)."""

    __tablename__ = "res"
    __table_args__ = (
        CheckConstraint("res_type IN ('RA', 'CONV', 'TAT')", name="chk_res_type"),
        {"schema": SCHEMA},
    )

    res_id = Column(String(10), primary_key=True)
    res_type = Column(String, nullable=False)
    model_nm = Column(String, nullable=False)


class Equip(Base):
     """생산 설비 (RA, CONV) — zone에 배치."""
    __tablename__ = "equip"
    __table_args__ = ({"schema": SCHEMA},)

    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"), primary_key=True)
    zone_id = Column(Integer, ForeignKey(f"{SCHEMA}.zone.zone_id"))

    res = relationship("Res")
    zone = relationship("Zone")


class EquipLoadSpec(Base):
     """하중 등급별 정밀 제어 수치."""
    __tablename__ = "equip_load_spec"
    __table_args__ = ({"schema": SCHEMA},)

    load_spec_id = Column(Integer, primary_key=True, autoincrement=True)
    load_class = Column(String(20))
    press_f = Column(Numeric(10, 2))
    press_t = Column(Numeric(5, 2))
    tol_val = Column(Numeric(5, 2))



class Trans(Base):
    """이송 자원 (TAT)."""

    __tablename__ = "trans"
    __table_args__ = (
        CheckConstraint("slot_count > 0", name="chk_trans_slot_count_gt_zero"),
        {"schema": SCHEMA},
    )

    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"), primary_key=True)
    slot_count = Column(Integer)
    max_load_kg = Column(Numeric)
    home_coord_id = Column(Integer, ForeignKey(f"{SCHEMA}.trans_coord.trans_coord_id"))

    res = relationship("Res")


class RaMotionStep(Base):
    """RA 모션 시퀀스 정의.

    PAT/MAT 공통 테이블로 쓰되, tool_type 으로 실제 툴을 구분한다.
    """

    __tablename__ = "ra_motion_step"
    __table_args__ = (
        CheckConstraint(
            "task_type IN ('MM', 'POUR', 'DM', 'PA_GP', 'PA_DP', 'PICK', 'SHIP')",
            name="chk_ra_motion_task_type",
        ),
        CheckConstraint("tool_type IN ('PAT', 'MAT')", name="chk_ra_motion_tool_type"),
        CheckConstraint(
            "command_type IN ('MOVE_ANGLES', 'MOVE_Z', 'GRIP_OPEN', 'GRIP_CLOSE', 'WAIT')",
            name="chk_ra_motion_command_type",
        ),
        CheckConstraint(
            "pose_nm IN ('HOME', 'TAT_HANDOFF', 'DEFECT_HOVER', 'DEFECT_DROP', 'SLOT_PATH')",
            name="chk_ra_motion_pose_nm",
        ),
        {"schema": SCHEMA},
    )

    step_id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(String, nullable=False)
    tool_type = Column(String, nullable=False, server_default=text("'MAT'"))
    pattern_no = Column(Integer, ForeignKey(f"{SCHEMA}.pattern_master.ptn_id"))
    loc_id = Column(Integer, ForeignKey(f"{SCHEMA}.strg_location_stat.loc_id"))
    pose_nm = Column(String)
    step_ord = Column(Integer, nullable=False)
    command_type = Column(String, nullable=False)
    j1 = Column(Numeric)
    j2 = Column(Numeric)
    j3 = Column(Numeric)
    j4 = Column(Numeric)
    j5 = Column(Numeric)
    j6 = Column(Numeric)
    delta_z = Column(Numeric)
    speed = Column(Integer)
    delay_sec = Column(Numeric)


class TransTaskBatThreshold(Base):
    __tablename__ = "trans_task_bat_threshold"
    __table_args__ = (
        CheckConstraint("task_type IN ('ToPP', 'ToSTRG', 'ToSHIP', 'ToCHG')", name="chk_trans_bat_task"),
        CheckConstraint("bat_low_threshold BETWEEN 0 AND 100", name="chk_bat_low_threshold"),
        {"schema": SCHEMA},
    )

    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.trans.res_id"), primary_key=True)
    task_type = Column(String(10), primary_key=True)
    bat_low_threshold = Column(Integer)


class TransCoord(Base):
    __tablename__ = "trans_coord"
    __table_args__ = (
        UniqueConstraint("zone_id", "chg_loc_id", name="uq_trans_coord_zone_chg_loc"),
        {"schema": SCHEMA},
    )

    trans_coord_id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(Integer, ForeignKey(f"{SCHEMA}.zone.zone_id"), nullable=False)
    chg_loc_id = Column(Integer, ForeignKey(f"{SCHEMA}.chg_loc_stat.loc_id"))
    x = Column(Numeric, nullable=False)
    y = Column(Numeric, nullable=False)
    theta = Column(Numeric, nullable=False)


class RaMotionStep(Base):
    __tablename__ = "ra_motion_step"
    __table_args__ = (
        CheckConstraint(
            "task_type IN ('MM', 'POUR', 'DM', 'PA_GP', 'PA_DP', 'PICK', 'SHIP')",
            name="chk_ra_motion_task_type",
        ),
        CheckConstraint("pattern_no BETWEEN 1 AND 6", name="chk_ra_motion_pattern_no"),
        CheckConstraint(
            "pose_nm IN ('HOME', 'AMR_HANDOFF', 'DEFECT_HOVER', 'DEFECT_DROP', 'SLOT_PATH')",
            name="chk_ra_motion_pose_nm",
        ),
        CheckConstraint(
            "command_type IN ('MOVE_ANGLES', 'MOVE_Z', 'GRIP_OPEN', 'GRIP_CLOSE', 'WAIT')",
            name="chk_ra_motion_command_type",
        ),
        CheckConstraint(
            "command_type <> 'MOVE_ANGLES' OR ("
            "j1 IS NOT NULL AND j2 IS NOT NULL AND j3 IS NOT NULL AND "
            "j4 IS NOT NULL AND j5 IS NOT NULL AND j6 IS NOT NULL AND "
            "delta_z IS NULL"
            ")",
            name="chk_ra_motion_move_angles_payload",
        ),
        CheckConstraint(
            "command_type <> 'MOVE_Z' OR ("
            "j1 IS NULL AND j2 IS NULL AND j3 IS NULL AND "
            "j4 IS NULL AND j5 IS NULL AND j6 IS NULL AND "
            "delta_z IS NOT NULL"
            ")",
            name="chk_ra_motion_move_z_payload",
        ),
        CheckConstraint(
            "command_type NOT IN ('GRIP_OPEN', 'GRIP_CLOSE', 'WAIT') OR ("
            "j1 IS NULL AND j2 IS NULL AND j3 IS NULL AND "
            "j4 IS NULL AND j5 IS NULL AND j6 IS NULL AND "
            "delta_z IS NULL"
            ")",
            name="chk_ra_motion_passive_payload",
        ),
        CheckConstraint(
            "("
            "(task_type = 'MM' AND pattern_no IS NOT NULL AND loc_id IS NULL) OR "
            "(task_type IN ('POUR', 'DM', 'PA_DP') AND pattern_no IS NULL) OR "
            "(task_type IN ('PA_GP', 'PICK', 'SHIP') AND pattern_no IS NULL AND loc_id IS NOT NULL)"
            ")",
            name="chk_ra_motion_task_context",
        ),
        UniqueConstraint(
            "task_type",
            "pattern_no",
            "loc_id",
            "pose_nm",
            "step_ord",
            name="uq_ra_motion_step_order",
        ),
        # NOTE:
        # DB schema v21 requires `UNIQUE NULLS NOT DISTINCT` here.
        # SQLAlchemy's portable UniqueConstraint cannot express that exactly,
        # so Alembic/raw DDL must manage the canonical unique index.
        {"schema": SCHEMA},
    )

    step_id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(String, nullable=False)
    pattern_no = Column(Integer)
    loc_id = Column(Integer, ForeignKey(f"{SCHEMA}.strg_loc_stat.loc_id"))
    pose_nm = Column(String)
    step_ord = Column(Integer, nullable=False)
    command_type = Column(String, nullable=False)
    j1 = Column(Numeric)
    j2 = Column(Numeric)
    j3 = Column(Numeric)
    j4 = Column(Numeric)
    j5 = Column(Numeric)
    j6 = Column(Numeric)
    delta_z = Column(Numeric)
    speed = Column(Integer)
    delay_sec = Column(Numeric)
