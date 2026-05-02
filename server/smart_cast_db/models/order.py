"""Order 도메인 모델 — Ord, OrdDetail, OrdPpMap, OrdPattern, OrdTxn, OrdStat, OrdLog."""

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
    func,
    relationship,
)
from .master import PatternMaster


class Ord(Base):
    """발주 마스터 (1:1 ord_detail)."""

    __tablename__ = "ord"
    __table_args__ = ({"schema": SCHEMA},)

    ord_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey(f"{SCHEMA}.user_account.user_id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("UserAccount")
    detail = relationship(
        "OrdDetail", uselist=False, back_populates="ord", cascade="all, delete-orphan"
    )
    pattern = relationship(
        "OrdPattern", uselist=False, back_populates="ord", cascade="all, delete-orphan"
    )
    pp_maps = relationship("OrdPpMap", back_populates="ord", cascade="all, delete-orphan")
    txns = relationship("OrdTxn", back_populates="ord", cascade="all, delete-orphan")
    stats = relationship("OrdStat", back_populates="ord", cascade="all, delete-orphan")
    items = relationship("Item", back_populates="ord", cascade="all, delete-orphan")


class OrdDetail(Base):
    """발주 상세 (1:1 with ord)."""

    __tablename__ = "ord_detail"
    __table_args__ = ({"schema": SCHEMA},)

    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), primary_key=True)
    prod_id = Column(Integer, ForeignKey(f"{SCHEMA}.product.prod_id"))
    diameter = Column(Numeric)
    thickness = Column(Numeric)
    material = Column(String(30))
    load_class = Column("load" if SCHEMA == "public" else "load_class", String(20))
    qty = Column(Integer)
    final_price = Column(Numeric)
    due_date = Column(Date)
    ship_addr = Column(String)

    ord = relationship("Ord", back_populates="detail")
    product = relationship("Product")


class OrdPpMap(Base):
    """발주↔후처리 N:M 매핑."""

    __tablename__ = "ord_pp_map"
    __table_args__ = ({"schema": SCHEMA},)

    map_id = Column(Integer, primary_key=True, autoincrement=True)
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), nullable=False)
    pp_id = Column(Integer, ForeignKey(f"{SCHEMA}.pp_options.pp_id"), nullable=False)

    ord = relationship("Ord", back_populates="pp_maps")
    pp_option = relationship("PpOption")


class OrdPattern(Base):
    """발주↔패턴 1:1 매핑."""

    __tablename__ = "ord_pattern"
    __table_args__ = ({"schema": SCHEMA},)

    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), primary_key=True)
    ptn_id = Column(Integer, ForeignKey(f"{SCHEMA}.pattern_master.ptn_id"), nullable=False)
    assigned_at = Column(DateTime, server_default=func.now())

    ord = relationship("Ord", back_populates="pattern")
    pattern_master = relationship(PatternMaster)


class OrdTxn(Base):
    """발주 비즈니스 트랜잭션 (RCVD/APPR/CNCL/REJT)."""

    __tablename__ = "ord_txn"
    __table_args__ = (
        CheckConstraint("txn_type IN ('RCVD', 'APPR', 'CNCL', 'REJT')", name="chk_ord_txn_type"),
        {"schema": SCHEMA},
    )

    txn_id = Column(Integer, primary_key=True, autoincrement=True)
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), nullable=False)
    txn_type = Column(String, server_default="RCVD")
    txn_at = Column(DateTime, server_default=func.now())

    ord = relationship("Ord", back_populates="txns")


class OrdStat(Base):
    """발주 상태 (RCVD→APPR→MFG→DONE→SHIP→COMP, 또는 REJT/CNCL)."""

    __tablename__ = "ord_stat"
    __table_args__ = (
        CheckConstraint(
            "ord_stat IN ('RCVD','APPR','MFG','DONE','SHIP','COMP','REJT','CNCL')",
            name="chk_ord_stat_value",
        ),
        {"schema": SCHEMA},
    )

    stat_id = Column(Integer, primary_key=True, autoincrement=True)
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), nullable=False)
    user_id = Column(Integer, ForeignKey(f"{SCHEMA}.user_account.user_id"))
    ord_stat = Column(String)
    updated_at = Column(DateTime, server_default=func.now())

    ord = relationship("Ord", back_populates="stats")
    user = relationship("UserAccount")


class OrdLog(Base):
    """발주 상태 전이 로그."""

    __tablename__ = "ord_log"
    __table_args__ = ({"schema": SCHEMA},)

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), nullable=False)
    prev_stat = Column(String)
    new_stat = Column(String)
    changed_by = Column(Integer, ForeignKey(f"{SCHEMA}.user_account.user_id"))
    logged_at = Column(DateTime, server_default=func.now())
