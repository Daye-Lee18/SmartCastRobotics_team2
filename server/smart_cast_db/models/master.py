"""Master/resource models aligned to create_tables.sql."""

from __future__ import annotations

from sqlalchemy import text

from ._base import (
    SCHEMA,
    Base,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    relationship,
)


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

    category = relationship("Category")
    options = relationship("ProductOption", back_populates="product", cascade="all, delete-orphan")


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

    product = relationship("Product", back_populates="options")


class PpOption(Base):
    __tablename__ = "pp_options"
    __table_args__ = ({"schema": SCHEMA},)

    pp_id = Column(Integer, primary_key=True, autoincrement=True)
    pp_nm = Column(String, nullable=False, unique=True)
    extra_cost = Column(Numeric, server_default="0")


class Res(Base):
    __tablename__ = "res"
    __table_args__ = (
        CheckConstraint("res_type IN ('RA', 'CONV', 'TAT')", name="chk_res_type"),
        {"schema": SCHEMA},
    )

    res_id = Column(String(10), primary_key=True)
    res_type = Column(String, nullable=False)
    model_nm = Column(String, nullable=False)


class Zone(Base):
    __tablename__ = "zone"
    __table_args__ = (
        CheckConstraint(
            "zone_nm IN ('CAST', 'PP', 'INSP', 'STRG', 'PICK', 'SHIP', 'CHG')",
            name="chk_zone_nm",
        ),
        {"schema": SCHEMA},
    )

    zone_id = Column(Integer, primary_key=True, autoincrement=True)
    zone_nm = Column(String, nullable=False, unique=True)


class Equip(Base):
    __tablename__ = "equip"
    __table_args__ = ({"schema": SCHEMA},)

    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"), primary_key=True)
    zone_id = Column(Integer, ForeignKey(f"{SCHEMA}.zone.zone_id"))

    res = relationship("Res")
    zone = relationship("Zone")


class EquipLoadSpec(Base):
    __tablename__ = "equip_load_spec"
    __table_args__ = ({"schema": SCHEMA},)

    load_spec_id = Column(Integer, primary_key=True, autoincrement=True)
    load_class = Column(String(20))
    press_f = Column(Numeric(10, 2))
    press_t = Column(Numeric(5, 2))
    tol_val = Column(Numeric(5, 2))


class Trans(Base):
    __tablename__ = "trans"
    __table_args__ = (
        CheckConstraint("slot_count > 0", name="chk_trans_slot_count_gt_zero"),
        {"schema": SCHEMA},
    )

    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"), primary_key=True)
    slot_count = Column(Integer)
    max_load_kg = Column(Numeric)

    res = relationship("Res")


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


class PatternMaster(Base):
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


class RaMotionStep(Base):
    __tablename__ = "ra_motion_step"
    __table_args__ = (
        CheckConstraint(
            "task_type IN ('MM', 'POUR', 'DM', 'PA_GP', 'PA_DP', 'PICK', 'SHIP')",
            name="chk_ra_motion_task_type",
        ),
        CheckConstraint("tool_type IN ('PAT', 'MAT')", name="chk_ra_motion_tool_type"),
        CheckConstraint(
            "pose_nm IS NULL OR pose_nm IN ('HOME', 'TAT_HANDOFF', 'DEFECT_HOVER', 'DEFECT_DROP', 'SLOT_PATH')",
            name="chk_ra_motion_pose_nm",
        ),
        CheckConstraint(
            "command_type IN ('MOVE_ANGLES', 'MOVE_Z', 'GRIP_OPEN', 'GRIP_CLOSE', 'WAIT')",
            name="chk_ra_motion_command_type",
        ),
        CheckConstraint(
            "("
            "(command_type = 'MOVE_ANGLES' AND "
            "j1 IS NOT NULL AND j2 IS NOT NULL AND j3 IS NOT NULL AND "
            "j4 IS NOT NULL AND j5 IS NOT NULL AND j6 IS NOT NULL AND delta_z IS NULL) OR "
            "(command_type = 'MOVE_Z' AND "
            "delta_z IS NOT NULL AND "
            "j1 IS NULL AND j2 IS NULL AND j3 IS NULL AND "
            "j4 IS NULL AND j5 IS NULL AND j6 IS NULL) OR "
            "(command_type IN ('GRIP_OPEN', 'GRIP_CLOSE', 'WAIT') AND "
            "delta_z IS NULL AND "
            "j1 IS NULL AND j2 IS NULL AND j3 IS NULL AND "
            "j4 IS NULL AND j5 IS NULL AND j6 IS NULL)"
            ")",
            name="chk_ra_step_payload",
        ),
        UniqueConstraint(
            "task_type",
            "pattern_no",
            "loc_id",
            "pose_nm",
            "step_ord",
            name="uq_ra_motion_step_order",
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
