"""Item/location models aligned to create_tables.sql."""

from __future__ import annotations

from sqlalchemy import case
from sqlalchemy.ext.hybrid import hybrid_property

from ._base import (
    SCHEMA,
    Base,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    relationship,
    synonym,
)


class Item(Base):
    __tablename__ = "item"
    __table_args__ = (
        Index("idx_item_ord", "ord_id"),
        {"schema": SCHEMA},
    )

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), nullable=False)
    equip_task_type = Column(String(10))
    trans_task_type = Column(String(10))
    cur_stat = Column(String(10))
    cur_res = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"))
    is_defective = Column(Boolean)
    updated_at = Column(DateTime, server_default=func.now())

    # Compatibility for older v21 callers.
    item_stat_id = synonym("item_id")
    flow_stat = synonym("cur_stat")
    zone_nm = synonym("cur_res")

    ord = relationship("Ord", back_populates="items")

    @hybrid_property
    def result(self) -> bool | None:
        """Legacy v21 inspection result compatibility.

        v21:  True=GP, False=DP, None=pending
        v23:  is_defective False=GP, True=DP, None=pending
        """
        if self.is_defective is None:
            return None
        return not self.is_defective

    @result.setter
    def result(self, value: bool | None) -> None:
        if value is None:
            self.is_defective = None
        else:
            self.is_defective = not bool(value)

    @result.expression
    def result(cls):
        return case(
            (cls.is_defective.is_(None), None),
            (cls.is_defective.is_(True), False),
            else_=True,
        )


class ChgLocationStat(Base):
    __tablename__ = "chg_location_stat"
    __table_args__ = (
        CheckConstraint("status IN ('empty', 'occupied', 'reserved')", name="chk_chg_loc_status"),
        CheckConstraint(
            "(res_id IS NOT NULL AND status = 'occupied') OR "
            "(res_id IS NULL AND status IN ('empty', 'reserved'))",
            name="chk_chg_res_status",
        ),
        {"schema": SCHEMA},
    )

    loc_id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(Integer, ForeignKey(f"{SCHEMA}.zone.zone_id"))
    res_id = Column(String, ForeignKey(f"{SCHEMA}.res.res_id"))
    loc_row = Column(Integer)
    loc_col = Column(Integer)
    status = Column(String, nullable=False)
    stored_at = Column(DateTime, server_default=func.now())


class StrgLocationStat(Base):
    __tablename__ = "strg_location_stat"
    __table_args__ = (
        CheckConstraint("status IN ('empty', 'occupied', 'reserved')", name="chk_strg_loc_status"),
        CheckConstraint(
            "(item_id IS NOT NULL AND status = 'occupied') OR "
            "(item_id IS NULL AND status IN ('empty', 'reserved'))",
            name="chk_strg_item_status",
        ),
        {"schema": SCHEMA},
    )

    loc_id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(Integer, ForeignKey(f"{SCHEMA}.zone.zone_id"))
    item_id = Column(Integer, ForeignKey(f"{SCHEMA}.item.item_id"))
    loc_row = Column(Integer)
    loc_col = Column(Integer)
    status = Column(String, nullable=False)
    stored_at = Column(DateTime, server_default=func.now())

    item_stat_id = synonym("item_id")


class ShipLocationStat(Base):
    __tablename__ = "ship_location_stat"
    __table_args__ = (
        CheckConstraint("status IN ('empty', 'occupied', 'reserved')", name="chk_ship_loc_status"),
        {"schema": SCHEMA},
    )

    loc_id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(Integer, ForeignKey(f"{SCHEMA}.zone.zone_id"))
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"))
    item_id = Column(Integer, ForeignKey(f"{SCHEMA}.item.item_id"))
    loc_row = Column(Integer)
    loc_col = Column(Integer)
    status = Column(String, nullable=False)
    stored_at = Column(DateTime, server_default=func.now())

    item_stat_id = synonym("item_id")
