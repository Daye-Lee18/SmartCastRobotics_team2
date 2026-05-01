from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.routes import logistics
from smart_cast_db.database import SessionLocal, get_db
from smart_cast_db.models import (
    ChgLocStat,
    ItemStat,
    Ord,
    Res,
    ShipLocStat,
    StrgLocStat,
    Trans,
    TransCoord,
    TransStat,
    TransTaskTxn,
    UserAccount,
    Zone,
)


@pytest.fixture
def client(postgresql_smartcast_empty):
    app = FastAPI()
    app.include_router(logistics.router)

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
def logistics_seed(postgresql_smartcast_empty):
    with SessionLocal() as db:
        user = UserAccount(
            co_nm="TEST",
            user_nm="tester",
            role="customer",
            phone="010-0000-0000",
            email="logistics-test@example.com",
            password="secret",
        )
        db.add(user)
        db.flush()

        ord_row = Ord(user_id=user.user_id)
        db.add(ord_row)
        db.flush()

        zone_chg = Zone(zone_nm="CHG")
        zone_strg = Zone(zone_nm="STRG")
        zone_ship = Zone(zone_nm="SHIP")
        db.add_all([zone_chg, zone_strg, zone_ship])
        db.flush()

        item = ItemStat(ord_id=ord_row.ord_id, flow_stat="STORED", zone_nm="STRG")
        db.add(item)
        db.flush()

        res = Res(res_id="AMR1", res_type="AMR", model_nm="TEST-AMR")
        db.add(res)
        db.flush()

        trans = Trans(res_id="AMR1", slot_count=1, max_load_kg=100)
        db.add(trans)
        db.flush()

        coord = TransCoord(zone_id=zone_chg.zone_id, x=1, y=2, theta=3)
        db.add(coord)
        db.flush()

        trans.home_coord_id = coord.trans_coord_id

        trans_task = TransTaskTxn(
            res_id=res.res_id,
            task_type="ToPP",
            txn_stat="PROC",
            chg_loc_id=coord.trans_coord_id,
            item_stat_id=item.item_stat_id,
            ord_id=ord_row.ord_id,
        )
        db.add(trans_task)

        trans_stat = TransStat(
            res_id=res.res_id,
            item_stat_id=item.item_stat_id,
            cur_stat="MV_SRC",
            battery_pct=77,
            cur_trans_coord_id=coord.trans_coord_id,
        )
        db.add(trans_stat)

        db.add(
            ChgLocStat(
                zone_id=zone_chg.zone_id,
                trans_coord_id=coord.trans_coord_id,
                res_id=res.res_id,
                loc_row=1,
                loc_col=1,
                status="occupied",
            )
        )
        db.add(
            StrgLocStat(
                zone_id=zone_strg.zone_id,
                item_stat_id=item.item_stat_id,
                loc_row=2,
                loc_col=1,
                status="occupied",
            )
        )
        db.add(
            ShipLocStat(
                zone_id=zone_ship.zone_id,
                ord_id=ord_row.ord_id,
                item_stat_id=item.item_stat_id,
                loc_row=3,
                loc_col=1,
                status="occupied",
            )
        )
        db.commit()

        return {
            "ord_id": ord_row.ord_id,
            "item_stat_id": item.item_stat_id,
            "res_id": res.res_id,
            "coord_id": coord.trans_coord_id,
            "zone_nm": zone_chg.zone_nm,
            "txn_id": trans_task.txn_id,
        }


def test_trans_tasks_returns_legacy_compatible_projection(client, logistics_seed):
    response = client.get("/api/logistics/trans-tasks")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1

    row = rows[0]
    assert row["txn_id"] == logistics_seed["txn_id"]
    assert row["res_id"] == logistics_seed["res_id"]
    assert row["trans_task_txn_id"] == logistics_seed["txn_id"]
    assert row["trans_id"] == logistics_seed["res_id"]
    assert row["item_id"] == logistics_seed["item_stat_id"]
    assert row["ord_id"] == logistics_seed["ord_id"]


def test_trans_tasks_filters_by_trans_id_query_param(client, logistics_seed):
    ok = client.get(f"/api/logistics/trans-tasks?trans_id={logistics_seed['res_id']}")
    assert ok.status_code == 200
    assert len(ok.json()) == 1

    miss = client.get("/api/logistics/trans-tasks?trans_id=AMR999")
    assert miss.status_code == 200
    assert miss.json() == []


def test_tasks_alias_matches_trans_tasks(client, logistics_seed):
    trans_tasks = client.get("/api/logistics/trans-tasks")
    tasks_alias = client.get("/api/logistics/tasks")
    assert trans_tasks.status_code == 200
    assert tasks_alias.status_code == 200
    assert tasks_alias.json() == trans_tasks.json()


def test_trans_stats_projects_zone_from_coord(client, logistics_seed):
    response = client.get("/api/logistics/trans-stats")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1

    row = rows[0]
    assert row["res_id"] == logistics_seed["res_id"]
    assert row["item_id"] == logistics_seed["item_stat_id"]
    assert row["cur_trans_coord_id"] == logistics_seed["coord_id"]
    assert row["cur_zone_type"] == logistics_seed["zone_nm"]
    assert row["battery_pct"] == 77
    assert row["cur_stat"] == "MV_SRC"


def test_warehouse_and_locations_project_item_stat_ids(client, logistics_seed):
    warehouse = client.get("/api/logistics/warehouse")
    assert warehouse.status_code == 200
    warehouse_rows = warehouse.json()
    assert len(warehouse_rows) == 1
    assert warehouse_rows[0]["item_id"] == logistics_seed["item_stat_id"]

    locations = client.get("/api/logistics/locations")
    assert locations.status_code == 200
    payload = locations.json()

    assert payload["chg"][0]["res_id"] == logistics_seed["res_id"]
    assert payload["strg"][0]["item_id"] == logistics_seed["item_stat_id"]
    assert payload["ship"][0]["item_id"] == logistics_seed["item_stat_id"]
    assert payload["ship"][0]["ord_id"] == logistics_seed["ord_id"]
