"""Master 데이터 모델 — Category, Product, ProductOption, PpOption,
Zone, Pattern, Res, Equip, EquipLoadSpec, Trans.

마스터 데이터 = 트랜잭션이 참조하는 정적 정의. seed 로 채워지고 자주 바뀌지 않음.
"""

from __future__ import annotations

from ._base import (
    SCHEMA,
    Base,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    Numeric,
    String,
    relationship,
)

# -----------------------------------------------------------------------------
# 표준 제품 (Category / Product / ProductOption / PpOption)
# -----------------------------------------------------------------------------


class Category(Base):
    """제품 카테고리 (CMH/RMH/EMH)."""

    __tablename__ = "category"
    __table_args__ = (
        CheckConstraint("cate_cd IN ('CMH', 'RMH', 'EMH')", name="chk_cate_cd"),
        {"schema": SCHEMA},
    )

    cate_cd = Column(String, primary_key=True)
    cate_nm = Column(String, nullable=False, unique=True)


class Product(Base):
    """표준 주조 제품."""

    __tablename__ = "product"
    __table_args__ = ({"schema": SCHEMA},)

    prod_id = Column(Integer, primary_key=True, autoincrement=True)
    cate_cd = Column(String, ForeignKey(f"{SCHEMA}.category.cate_cd"), nullable=False)
    base_price = Column(Numeric, nullable=False)
    img_url = Column(String(400))

    category = relationship("Category")
    options = relationship("ProductOption", back_populates="product", cascade="all, delete-orphan")


class ProductOption(Base):
    """제품별 옵션 (재질/하중등급)."""

    __tablename__ = "product_option"
    __table_args__ = ({"schema": SCHEMA},)

    prod_opt_id = Column(Integer, primary_key=True, autoincrement=True)
    prod_id = Column(Integer, ForeignKey(f"{SCHEMA}.product.prod_id"))
    mat_type = Column(String(20))
    load_class = Column(String(20))

    product = relationship("Product", back_populates="options")


class PpOption(Base):
    """후처리 옵션 마스터."""

    __tablename__ = "pp_options"
    __table_args__ = ({"schema": SCHEMA},)

    pp_id = Column(Integer, primary_key=True, autoincrement=True)
    pp_nm = Column(String, unique=True)
    extra_cost = Column(Numeric)


# -----------------------------------------------------------------------------
# Operator (zone, pattern)
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


class Pattern(Base):
    """패턴 위치 (1-6번, 발주 1:1)."""

    __tablename__ = "pattern"
    __table_args__ = (
        CheckConstraint("ptn_loc BETWEEN 1 AND 6", name="chk_ptn_loc_range"),
        {"schema": SCHEMA},
    )

    ptn_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), primary_key=True)
    ptn_loc = Column(Integer)


# -----------------------------------------------------------------------------
# 설비 마스터 (res, equip, trans)
# -----------------------------------------------------------------------------


class Res(Base):
    """전체 설비 마스터 (RA/CONV/AMR)."""

    __tablename__ = "res"
    __table_args__ = (
        CheckConstraint("res_type IN ('RA', 'CONV', 'AMR')", name="chk_res_type"),
        {"schema": SCHEMA},
    )

    res_id = Column(String(10), primary_key=True)
    res_type = Column(String)
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
    """이송 자원 (AMR)."""

    __tablename__ = "trans"
    __table_args__ = ({"schema": SCHEMA},)

    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"), primary_key=True)
    slot_count = Column(Integer)
    max_load_kg = Column(Numeric)

    res = relationship("Res")
