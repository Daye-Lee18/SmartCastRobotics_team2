from __future__ import annotations

from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.routes import dashboard, debug, quality
from smart_cast_db.database import SessionLocal, get_db
from smart_cast_db.models import (
    Equip,
    InspStat,
    InspTaskTxn,
    ItemStat,
    Ord,
    OrdDetail,
    OrdPpMap,
    OrdStat,
    PpOption,
    PpTaskTxn,
    Res,
    UserAccount,
    Zone,
)


@pytest.fixture
def client(postgresql_smartcast_empty):
    app = FastAPI()
    app.include_router(dashboard.router)
    app.include_router(quality.router)
    app.include_router(debug.router)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def route_seed(postgresql_smartcast_empty):
    with SessionLocal() as db:
        user = UserAccount(
            co_nm="TEST",
            user_nm="tester",
            role="customer",
            phone="010-0000-0000",
            email="route-test@example.com",
            password="secret",
        )
        db.add(user)
        db.flush()

        ord_row = Ord(user_id=user.user_id)
        db.add(ord_row)
        db.flush()

        db.add(
            OrdDetail(
                ord_id=ord_row.ord_id,
                qty=3,
                final_price=1000,
                due_date=date(2026, 5, 10),
                ship_addr="Busan",
            )
        )
        db.add(OrdStat(ord_id=ord_row.ord_id, user_id=user.user_id, ord_stat="MFG"))

        db.add_all([Zone(zone_nm="PP"), Zone(zone_nm="INSP")])
        db.flush()

        item_gp = ItemStat(ord_id=ord_row.ord_id, flow_stat="PP", zone_nm="PP", result=True)
        item_dp = ItemStat(ord_id=ord_row.ord_id, flow_stat="INSP", zone_nm="INSP", result=False)
        item_pending = ItemStat(ord_id=ord_row.ord_id, flow_stat="WAIT_INSP", zone_nm="INSP", result=None)
        db.add_all([item_gp, item_dp, item_pending])
        db.flush()

        res = Res(res_id="RA1", res_type="RA", model_nm="TEST-RA")
        db.add(res)
        db.flush()
        db.add(Equip(res_id=res.res_id))

        pp_option = PpOption(pp_nm="POLISH", extra_cost=100)
        db.add(pp_option)
        db.flush()

        ord_pp_map = OrdPpMap(ord_id=ord_row.ord_id, pp_id=pp_option.pp_id)
        db.add(ord_pp_map)
        db.flush()

        db.add(
            PpTaskTxn(
                ord_id=ord_row.ord_id,
                item_stat_id=item_pending.item_stat_id,
                map_id=ord_pp_map.map_id,
                pp_nm=pp_option.pp_nm,
                txn_stat="QUE",
            )
        )

        insp_txn = InspTaskTxn(item_stat_id=item_pending.item_stat_id, txn_stat="QUE", res_id="RA1")
        db.add(insp_txn)
        db.flush()

        db.commit()

        return {
            "ord_id": ord_row.ord_id,
            "item_gp_id": item_gp.item_stat_id,
            "item_dp_id": item_dp.item_stat_id,
            "item_pending_id": item_pending.item_stat_id,
            "insp_txn_id": insp_txn.txn_id,
            "rfid_payload": f"order_{ord_row.ord_id}_item_20260501_{item_pending.item_stat_id}",
        }


def test_dashboard_stats_uses_item_stat_canonical_counts(client, route_seed):
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    payload = response.json()

    assert payload["total_orders"] == 1
    assert payload["orders_in_production"] == 1
    assert payload["total_items"] == 3
    assert payload["good_items"] == 1
    assert payload["defective_items"] == 1
    assert payload["defect_rate_pct"] == 50.0


def test_quality_inspections_filters_and_projects_legacy_item_id(client, route_seed):
    response = client.get(
        f"/api/quality/inspections?ord_id={route_seed['ord_id']}&item_id={route_seed['item_pending_id']}"
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1

    row = rows[0]
    assert row["txn_id"] == route_seed["insp_txn_id"]
    assert row["item_id"] == route_seed["item_pending_id"]
    assert row["txn_stat"] == "QUE"
    assert row["result"] is None


def test_quality_update_inspection_result_updates_canonical_item_stat(client, route_seed):
    response = client.post(f"/api/quality/inspections/{route_seed['insp_txn_id']}/result?result=true")
    assert response.status_code == 200
    payload = response.json()
    assert payload["item_id"] == route_seed["item_pending_id"]
    assert payload["txn_stat"] == "SUCC"
    assert payload["result"] is True

    with SessionLocal() as db:
        txn = db.get(InspTaskTxn, route_seed["insp_txn_id"])
        stat = db.get(InspStat, route_seed["insp_txn_id"])
        item = db.get(ItemStat, route_seed["item_pending_id"])

        assert txn is not None and txn.item_stat_id == route_seed["item_pending_id"]
        assert stat is not None and stat.item_stat_id == route_seed["item_pending_id"]
        assert stat.final_result == "GP"
        assert item is not None and item.result is True


def test_debug_lookup_and_sim_rfid_scan_use_item_stat_payload_matching(client, route_seed):
    lookup = client.get(f"/api/debug/items/by-rfid?payload={route_seed['rfid_payload']}")
    assert lookup.status_code == 200
    lookup_payload = lookup.json()
    assert lookup_payload["item"]["item_id"] == route_seed["item_pending_id"]
    assert lookup_payload["pp_options"][0]["txn_stat"] == "QUE"

    scan = client.post(
        "/api/debug/sim/rfid-scan",
        json={
            "reader_id": "ESP-CONV-01",
            "zone": "postprocessing",
            "raw_payload": route_seed["rfid_payload"],
        },
    )
    assert scan.status_code == 200
    scan_payload = scan.json()
    assert scan_payload["matched"] is True
    assert scan_payload["item"]["item_id"] == route_seed["item_pending_id"]
