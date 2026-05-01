"""Master/resource models aligned to DB schema v21."""

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
    UniqueConstraint,
    func,
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
    pp_nm = Column(String, nullable=False, unique=True)
    extra_cost = Column(Numeric, server_default="0")


class Res(Base):
    __tablename__ = "res"
    __table_args__ = (
        CheckConstraint("res_type IN ('RA', 'CONV', 'AMR')", name="chk_res_type"),
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


class PatternStat(Base):
    __tablename__ = "pattern_stat"
    __table_args__ = (
        CheckConstraint("ptn_loc BETWEEN 1 AND 6", name="chk_ptn_loc_range"),
        {"schema": SCHEMA},
    )

    ptn_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), primary_key=True)
    ptn_loc = Column(Integer, nullable=False)
    registered_by = Column(Integer, ForeignKey(f"{SCHEMA}.user_account.user_id"))
    created_at = Column(DateTime, server_default=func.now())


class Trans(Base):
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
