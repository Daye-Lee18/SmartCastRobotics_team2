"""Item 도메인 + 위치 상태 모델 — Item, ChgLocationStat, StrgLocationStat,
ShipLocationStat.

Item 은 발주에서 파생된 개별 제품. 12개 cur_stat 라벨로 공정 단계를 추적한다.
위치 상태는 Item 이 어디에 있는지 (CHG=충전구역, STRG=적재, SHIP=출고) 를 표현.
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
    String,
    func,
    relationship,
)


class Item(Base):
    """생산된 모든 아이템의 실시간 공정 단계 + 불량 여부.

    cur_stat: 12개 라벨 (MM/POUR/DM/PP/ToINSP/INSP/PA/PICK/SHIP/ToPP/ToSTRG/ToSHIP)
    cur_res: 점유 자원 ID (PP 상태 시 NULL)
    is_defective: NULL=미검사, TRUE=불량, FALSE=양품
    """

    __tablename__ = "item"
    __table_args__ = ({"schema": SCHEMA},)

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"), nullable=False)
    equip_task_type = Column(String(10))
    trans_task_type = Column(String(10))
    cur_stat = Column(String(10))
    cur_res = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"))
    is_defective = Column(Boolean)
    updated_at = Column(DateTime, server_default=func.now())

    ord = relationship("Ord", back_populates="items")
    res = relationship("Res")


# -----------------------------------------------------------------------------
# Location State (chg / strg / ship)
# -----------------------------------------------------------------------------


class ChgLocationStat(Base):
    """충전 구역 (1x3) 위치 상태."""

    __tablename__ = "chg_location_stat"
    __table_args__ = (
        CheckConstraint(
            "status IN ('empty', 'occupied', 'reserved')",
            name="chk_chg_loc_status",
        ),
        {"schema": SCHEMA},
    )

    loc_id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(Integer, ForeignKey(f"{SCHEMA}.zone.zone_id"))
    res_id = Column(String, ForeignKey(f"{SCHEMA}.res.res_id"))
    loc_row = Column(Integer)
    loc_col = Column(Integer)
    status = Column(String)
    stored_at = Column(DateTime, server_default=func.now())


class StrgLocationStat(Base):
    """적재 구역 (3x6, 18칸) 위치 상태."""

    __tablename__ = "strg_location_stat"
    __table_args__ = (
        CheckConstraint(
            "status IN ('empty', 'occupied', 'reserved')",
            name="chk_strg_loc_status",
        ),
        CheckConstraint(
            "(item_id IS NOT NULL AND status = 'occupied') "
            "OR (item_id IS NULL AND status IN ('empty', 'reserved'))",
            name="chk_strg_item_status",
        ),
        {"schema": SCHEMA},
    )

    loc_id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(Integer, ForeignKey(f"{SCHEMA}.zone.zone_id"))
    item_id = Column(Integer, ForeignKey(f"{SCHEMA}.item.item_id"))
    loc_row = Column(Integer)
    loc_col = Column(Integer)
    status = Column(String)
    stored_at = Column(DateTime, server_default=func.now())


class ShipLocationStat(Base):
    """출고 구역 (1x5) 위치 상태."""

    __tablename__ = "ship_location_stat"
    __table_args__ = (
        CheckConstraint(
            "status IN ('empty', 'occupied', 'reserved')",
            name="chk_ship_loc_status",
        ),
        {"schema": SCHEMA},
    )

    loc_id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(Integer, ForeignKey(f"{SCHEMA}.zone.zone_id"))
    ord_id = Column(Integer, ForeignKey(f"{SCHEMA}.ord.ord_id"))
    item_id = Column(Integer, ForeignKey(f"{SCHEMA}.item.item_id"))
    loc_row = Column(Integer)
    loc_col = Column(Integer)
    status = Column(String)
    stored_at = Column(DateTime, server_default=func.now())
