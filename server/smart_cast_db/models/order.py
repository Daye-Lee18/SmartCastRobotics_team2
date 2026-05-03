"""Order domain models aligned to create_tables.sql."""

from __future__ import annotations

from ._base import (
    SCHEMA,
    Base,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    relationship,
)


class Ord(Base):
    __tablename__ = "ord"
    __table_args__ = ({"schema": SCHEMA},)

    ord_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey(f"{SCHEMA}.user_account.user_id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("UserAccount")
    detail = relationship("OrdDetail", uselist=False, back_populates="ord", cascade="all, delete-orphan")
    pattern = relationship("OrdPattern", uselist=False, back_populates="ord", cascade="all, delete-orphan")
    pp_maps = relationship("OrdPpMap", back_populates="ord", cascade="all, delete-orphan")
    txns = relationship("OrdTxn", back_populates="ord", cascade="all, delete-orphan")
    stats = relationship("OrdStat", back_populates="ord", cascade="all, delete-orphan")
    items = relationship("Item", back_populates="ord", cascade="all, delete-orphan")


class OrdDetail(Base):
    __tablename__ = "ord_detail"
    __table_args__ = (
        CheckConstraint("qty > 0", name="chk_ord_detail_qty_gt_zero"),
        {"schema": SCHEMA},
    )

    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), primary_key=True)
    prod_id = Column(Integer, ForeignKey(f"{SCHEMA}.product.prod_id"))
    diameter = Column(Numeric)
    thickness = Column(Numeric)
    material = Column(String(30))
    load_class = Column(String(20))
    qty = Column(Integer, nullable=False)
    final_price = Column(Numeric, nullable=False)
    due_date = Column(Date, nullable=False)
    ship_addr = Column(String, nullable=False)

    ord = relationship("Ord", back_populates="detail")
    product = relationship("Product")


class OrdPpMap(Base):
    __tablename__ = "ord_pp_map"
    __table_args__ = (
        UniqueConstraint("ord_id", "pp_id", name="uq_ord_pp_map_ord_pp"),
        {"schema": SCHEMA},
    )

    map_id = Column(Integer, primary_key=True, autoincrement=True)
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), nullable=False)
    pp_id = Column(Integer, ForeignKey(f"{SCHEMA}.pp_options.pp_id"), nullable=False)

    ord = relationship("Ord", back_populates="pp_maps")
    pp_option = relationship("PpOption")


class OrdPattern(Base):
    __tablename__ = "ord_pattern"
    __table_args__ = ({"schema": SCHEMA},)

    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), primary_key=True)
    ptn_id = Column(Integer, ForeignKey(f"{SCHEMA}.pattern_master.ptn_id"), nullable=False)
    assigned_at = Column(DateTime, server_default=func.now())

    ord = relationship("Ord", back_populates="pattern")
    pattern_master = relationship("PatternMaster")


class OrdTxn(Base):
    __tablename__ = "ord_txn"
    __table_args__ = (
        CheckConstraint("txn_type IN ('RCVD', 'APPR', 'CNCL', 'REJT')", name="chk_ord_txn_type"),
        {"schema": SCHEMA},
    )

    txn_id = Column(Integer, primary_key=True, autoincrement=True)
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), nullable=False)
    txn_type = Column(String, nullable=False, server_default="RCVD")
    txn_at = Column(DateTime, server_default=func.now())

    ord = relationship("Ord", back_populates="txns")


class OrdStat(Base):
    __tablename__ = "ord_stat"
    __table_args__ = (
        CheckConstraint(
            "ord_stat IN ('RCVD', 'APPR', 'MFG', 'DONE', 'SHIPPING', 'COMP', 'REJT', 'CNCL')",
            name="chk_ord_stat_value",
        ),
        CheckConstraint("gp_qty >= 0", name="chk_ord_stat_gp_qty_nonneg"),
        CheckConstraint("dp_qty >= 0", name="chk_ord_stat_dp_qty_nonneg"),
        {"schema": SCHEMA},
    )

    stat_id = Column(Integer, primary_key=True, autoincrement=True)
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey(f"{SCHEMA}.user_account.user_id"))
    ord_stat = Column(String, nullable=False)
    gp_qty = Column(Integer, nullable=False, server_default="0")
    dp_qty = Column(Integer, nullable=False, server_default="0")
    updated_at = Column(DateTime, server_default=func.now())

    ord = relationship("Ord", back_populates="stats")
    user = relationship("UserAccount")


class OrdLog(Base):
    __tablename__ = "ord_log"
    __table_args__ = (
        CheckConstraint(
            "prev_stat IS NULL OR prev_stat IN ('RCVD', 'APPR', 'MFG', 'DONE', 'SHIP', 'COMP', 'REJT', 'CNCL')",
            name="chk_ord_log_prev_stat",
        ),
        CheckConstraint(
            "new_stat IN ('RCVD', 'APPR', 'MFG', 'DONE', 'SHIP', 'COMP', 'REJT', 'CNCL')",
            name="chk_ord_log_new_stat",
        ),
        {"schema": SCHEMA},
    )

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), nullable=False)
    prev_stat = Column(String)
    new_stat = Column(String, nullable=False)
    changed_by = Column(Integer, ForeignKey(f"{SCHEMA}.user_account.user_id"))
    logged_at = Column(DateTime, server_default=func.now())
