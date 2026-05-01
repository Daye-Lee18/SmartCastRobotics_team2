"""Item/location models aligned to DB schema v21."""

from __future__ import annotations

from sqlalchemy import Index
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
    String,
    func,
    relationship,
)


class ItemStat(Base):
    __tablename__ = "item_stat"
    __table_args__ = (
        CheckConstraint(
            "flow_stat IN ('CREATED', 'CAST', 'WAIT_PP', 'PP', 'WAIT_INSP', 'INSP', 'WAIT_PA', 'PA', 'STORED', 'PICK', 'READY_TO_SHIP', 'DISCARDED', 'HOLD')",
            name="chk_item_stat_flow_stat",
        ),
        Index("idx_item_stat_ord_flow", "ord_id", "flow_stat"),
        {"schema": SCHEMA},
    )

    item_stat_id = Column(Integer, primary_key=True, autoincrement=True)
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), nullable=False)
    flow_stat = Column(String, nullable=False)
    zone_nm = Column(String(20), ForeignKey(f"{SCHEMA}.zone.zone_nm"))
    result = Column(Boolean)
    updated_at = Column(DateTime, server_default=func.now())

    # Legacy import compatibility. Old code still refers to Item.item_id.
    item_id = synonym("item_stat_id")

    ord = relationship("Ord", back_populates="items")


class ChgLocStat(Base):
    __tablename__ = "chg_loc_stat"
    __table_args__ = (
        CheckConstraint("status IN ('empty', 'occupied', 'reserved')", name="chk_chg_loc_status"),
        CheckConstraint(
            "(res_id IS NOT NULL AND status = 'occupied') OR (res_id IS NULL AND status IN ('empty', 'reserved'))",
            name="chk_chg_loc_res_status",
        ),
        {"schema": SCHEMA},
    )

    loc_id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(Integer, ForeignKey(f"{SCHEMA}.zone.zone_id"))
    trans_coord_id = Column(Integer, ForeignKey(f"{SCHEMA}.trans_coord.trans_coord_id"))
    res_id = Column(String, ForeignKey(f"{SCHEMA}.res.res_id"))
    loc_row = Column(Integer)
    loc_col = Column(Integer)
    status = Column(String, nullable=False)
    stored_at = Column(DateTime, server_default=func.now())


class StrgLocStat(Base):
    __tablename__ = "strg_loc_stat"
    __table_args__ = (
        CheckConstraint("status IN ('empty', 'occupied', 'reserved')", name="chk_strg_loc_status"),
        CheckConstraint(
            "(item_stat_id IS NOT NULL AND status = 'occupied') OR (item_stat_id IS NULL AND status IN ('empty', 'reserved'))",
            name="chk_strg_item_status",
        ),
        {"schema": SCHEMA},
    )

    loc_id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(Integer, ForeignKey(f"{SCHEMA}.zone.zone_id"))
    item_stat_id = Column(Integer, ForeignKey(f"{SCHEMA}.item_stat.item_stat_id"))
    loc_row = Column(Integer)
    loc_col = Column(Integer)
    status = Column(String, nullable=False)
    stored_at = Column(DateTime, server_default=func.now())

    # Legacy compatibility
    item_id = synonym("item_stat_id")

class ShipLocStat(Base):
    __tablename__ = "ship_loc_stat"
    __table_args__ = (
        CheckConstraint("status IN ('empty', 'occupied', 'reserved')", name="chk_ship_loc_status"),
        CheckConstraint(
            "(item_stat_id IS NOT NULL AND status = 'occupied') OR (item_stat_id IS NULL AND status IN ('empty', 'reserved'))",
            name="chk_ship_item_status",
        ),
        {"schema": SCHEMA},
    )

    loc_id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(Integer, ForeignKey(f"{SCHEMA}.zone.zone_id"))
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"))
    item_stat_id = Column(Integer, ForeignKey(f"{SCHEMA}.item_stat.item_stat_id"))
    loc_row = Column(Integer)
    loc_col = Column(Integer)
    status = Column(String, nullable=False)
    stored_at = Column(DateTime, server_default=func.now())

    # Legacy compatibility
    item_id = synonym("item_stat_id")
