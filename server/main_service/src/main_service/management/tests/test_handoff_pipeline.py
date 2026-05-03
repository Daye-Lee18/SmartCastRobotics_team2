from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

from sqlalchemy import text

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_MGMT_DIR = os.path.dirname(_THIS_DIR)
_APP_DIR = os.path.dirname(_MGMT_DIR)
_SERVER_DIR = os.path.abspath(os.path.join(_THIS_DIR, "../../../../../"))

for p in (_MGMT_DIR, _APP_DIR, _SERVER_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import smart_cast_db.models  # noqa: F401
import smart_cast_db.models.models_legacy  # noqa: F401
from smart_cast_db.database import Base, SessionLocal, engine
from smart_cast_db.models import (
    Equip,
    EquipStat,
    EquipTaskTxn,
    InspTaskTxn,
    ItemStat,
    Ord,
    OrdPpMap,
    PpOption,
    PpTaskTxn,
    Res,
    Trans,
    TransStat,
    TransTaskTxn,
    UserAccount,
    Zone,
)
from smart_cast_db.models.models_legacy import HandoffAck

from services.legacy.handoff_pipeline import apply_handoff, apply_tof1, apply_tof2


def _truncate_all() -> None:
    with engine.begin() as conn:
        names = ", ".join(t.fullname for t in reversed(Base.metadata.sorted_tables))
        if names:
            conn.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))


def _seed_common(db) -> dict[str, Zone]:
    zones = {name: Zone(zone_nm=name) for name in ("CHG", "PP", "INSP")}
    db.add(
        UserAccount(
            user_id=1,
            co_nm="TEST",
            user_nm="tester",
            role="operator",
            email="operator@example.com",
            password="pw",
        )
    )
    db.add_all(zones.values())
    db.flush()

    db.add_all(
        [
            Res(res_id="AMR1", res_type="AMR", model_nm="TEST-AMR"),
            Res(res_id="CONV-01", res_type="CONV", model_nm="TEST-CONV"),
        ]
    )
    db.flush()
    db.add(Trans(res_id="AMR1", slot_count=1))
    db.add(Equip(res_id="CONV-01", zone_id=zones["INSP"].zone_id))
    db.flush()
    return zones


def _seed_order_and_item(db, *, ord_id: int, flow_stat: str, zone_nm: str) -> ItemStat:
    db.add(Ord(ord_id=ord_id, user_id=1))
    db.flush()
    item = ItemStat(ord_id=ord_id, flow_stat=flow_stat, zone_nm=zone_nm)
    db.add(item)
    db.flush()
    return item


def _seed_trans_waiting_for_handoff(db, *, item: ItemStat, ord_id: int, req_at: datetime) -> TransTaskTxn:
    db.add(TransStat(res_id="AMR1", item_stat_id=item.item_stat_id, cur_stat="WAIT_DLD"))
    txn = TransTaskTxn(
        res_id="AMR1",
        task_type="ToPP",
        txn_stat="PROC",
        item_stat_id=item.item_stat_id,
        ord_id=ord_id,
        req_at=req_at,
    )
    db.add(txn)
    db.flush()
    return txn


def _seed_pp_maps(db, *, ord_id: int) -> None:
    shot = PpOption(pp_nm="SHOT", extra_cost=1000)
    grind = PpOption(pp_nm="GRIND", extra_cost=2000)
    db.add_all([shot, grind])
    db.flush()
    db.add_all(
        [
            OrdPpMap(ord_id=ord_id, pp_id=shot.pp_id),
            OrdPpMap(ord_id=ord_id, pp_id=grind.pp_id),
        ]
    )
    db.flush()


def _assert_schema_ready() -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS smartcast"))
    Base.metadata.create_all(engine)


def setup_function() -> None:
    _assert_schema_ready()
    _truncate_all()


def test_apply_handoff_uses_transport_canonical_fields_and_creates_pp_queue() -> None:
    with SessionLocal() as db:
        _seed_common(db)
        item = _seed_order_and_item(db, ord_id=1, flow_stat="WAIT_PP", zone_nm="PP")
        _seed_pp_maps(db, ord_id=1)
        txn = _seed_trans_waiting_for_handoff(
            db, item=item, ord_id=1, req_at=datetime.now() - timedelta(minutes=5)
        )

        result = apply_handoff(
            db,
            button_device_id="BTN-1",
            ack_source="esp32_button",
            via="pytest",
            idempotency_key="handoff-1",
            operator_id=1,
        )

        db.flush()
        db.refresh(txn)
        db.refresh(item)

        assert result.released is True
        assert result.orphan is False
        assert result.task_id == txn.txn_id
        assert result.amr_id == txn.res_id
        assert result.item_id == item.item_stat_id

        assert txn.txn_stat == "SUCC"
        assert db.get(TransStat, "AMR1").cur_stat == "SUCC"
        assert item.flow_stat == "PP"
        assert item.zone_nm == "PP"

        pp_rows = db.query(PpTaskTxn).filter(PpTaskTxn.ord_id == 1).order_by(PpTaskTxn.txn_id.asc()).all()
        assert len(pp_rows) == 2
        assert {row.item_stat_id for row in pp_rows} == {item.item_stat_id}
        assert {row.pp_nm for row in pp_rows} == {"SHOT", "GRIND"}
        assert all(row.txn_stat == "QUE" for row in pp_rows)

        ack = db.query(HandoffAck).one()
        assert ack.amr_id == "AMR1"
        assert ack.extra["trans_task_txn_id"] == txn.txn_id


def test_apply_handoff_without_pp_maps_routes_item_to_wait_insp() -> None:
    with SessionLocal() as db:
        _seed_common(db)
        item = _seed_order_and_item(db, ord_id=2, flow_stat="WAIT_PP", zone_nm="PP")
        _seed_trans_waiting_for_handoff(
            db, item=item, ord_id=2, req_at=datetime.now() - timedelta(minutes=1)
        )

        result = apply_handoff(
            db,
            button_device_id="BTN-2",
            ack_source="debug_endpoint",
            via="pytest",
            idempotency_key="handoff-2",
        )

        db.flush()
        db.refresh(item)

        assert result.released is True
        assert result.pp_task_txn_ids == []
        assert result.item_cur_stat == "WAIT_INSP"
        assert item.flow_stat == "WAIT_INSP"
        assert item.zone_nm == "INSP"


def test_apply_tof1_marks_pp_tasks_done_and_creates_equip_task() -> None:
    with SessionLocal() as db:
        _seed_common(db)
        item = _seed_order_and_item(db, ord_id=3, flow_stat="PP", zone_nm="PP")
        db.add_all([PpOption(pp_nm="SHOT", extra_cost=1000), PpOption(pp_nm="GRIND", extra_cost=2000)])
        db.flush()
        db.add_all(
            [
                PpTaskTxn(ord_id=3, item_stat_id=item.item_stat_id, pp_nm="SHOT", txn_stat="QUE"),
                PpTaskTxn(ord_id=3, item_stat_id=item.item_stat_id, pp_nm="GRIND", txn_stat="PROC"),
            ]
        )
        db.flush()

        result = apply_tof1(db, res_id="CONV-01", item_id=item.item_stat_id, operator_id=1)

        db.flush()
        db.refresh(item)

        assert result.ok is True
        assert result.item_id == item.item_stat_id
        assert result.equip_task_txn_id is not None
        assert item.flow_stat == "WAIT_INSP"
        assert item.zone_nm == "INSP"

        pp_rows = db.query(PpTaskTxn).filter(PpTaskTxn.ord_id == 3).order_by(PpTaskTxn.txn_id.asc()).all()
        assert all(row.txn_stat == "SUCC" for row in pp_rows)
        assert all(row.operator_id == 1 for row in pp_rows)

        equip_txn = db.query(EquipTaskTxn).filter(EquipTaskTxn.ord_id == 3).one()
        assert equip_txn.res_id == "CONV-01"
        assert equip_txn.task_type == "ToINSP"
        assert equip_txn.txn_stat == "PROC"
        assert equip_txn.item_stat_id == item.item_stat_id

        equip_stat = db.query(EquipStat).filter(EquipStat.res_id == "CONV-01").one()
        assert equip_stat.item_stat_id == item.item_stat_id
        assert equip_stat.cur_stat == "ON"


def test_apply_tof2_marks_equip_task_done_and_creates_insp_task() -> None:
    with SessionLocal() as db:
        _seed_common(db)
        item = _seed_order_and_item(db, ord_id=4, flow_stat="WAIT_INSP", zone_nm="INSP")
        txn = EquipTaskTxn(
            res_id="CONV-01",
            task_type="ToINSP",
            txn_stat="PROC",
            item_stat_id=item.item_stat_id,
            ord_id=4,
            start_at=datetime.now() - timedelta(seconds=30),
        )
        db.add(txn)
        db.flush()

        result = apply_tof2(db, res_id="CONV-01", item_id=item.item_stat_id)

        db.flush()
        db.refresh(txn)
        db.refresh(item)

        assert result.ok is True
        assert result.equip_task_txn_succ_id == txn.txn_id
        assert result.item_id == item.item_stat_id
        assert item.flow_stat == "INSP"
        assert item.zone_nm == "INSP"
        assert txn.txn_stat == "SUCC"

        insp = db.query(InspTaskTxn).filter(InspTaskTxn.item_stat_id == item.item_stat_id).one()
        assert insp.res_id == "CONV-01"
        assert insp.txn_stat == "PROC"

        equip_stat = db.query(EquipStat).filter(EquipStat.res_id == "CONV-01").one()
        assert equip_stat.item_stat_id == item.item_stat_id
        assert equip_stat.cur_stat == "OFF"
