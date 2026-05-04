from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.routes.production import items as production_items
from smart_cast_db.database import SessionLocal, get_db
from smart_cast_db.models import (
    Equip,
    EquipTaskTxn,
    ItemStat,
    Ord,
    OrdPpMap,
    PpOption,
    PpTaskTxn,
    Res,
    UserAccount,
    Zone,
)


@pytest.fixture
def client(postgresql_smartcast_empty):
    app = FastAPI()
    app.include_router(production_items.router)

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
def production_seed(postgresql_smartcast_empty):
    with SessionLocal() as db:
        user = UserAccount(
            co_nm="TEST",
            user_nm="tester",
            role="customer",
            phone="010-0000-0000",
            email="production-items-test@example.com",
            password="secret",
        )
        db.add(user)
        db.flush()

        ord_row = Ord(user_id=user.user_id)
        db.add(ord_row)
        db.flush()

        zone_cast = Zone(zone_nm="CAST")
        zone_pp = Zone(zone_nm="PP")
        db.add_all([zone_cast, zone_pp])
        db.flush()

        item = ItemStat(
            ord_id=ord_row.ord_id,
            flow_stat="PP",
            zone_nm=zone_pp.zone_nm,
            result=True,
        )
        db.add(item)
        db.flush()

        res = Res(res_id="RA1", res_type="RA", model_nm="TEST-RA")
        db.add(res)
        db.flush()
        db.add(Equip(res_id=res.res_id, zone_id=zone_pp.zone_id))
        db.flush()

        pp_option = PpOption(pp_nm="POLISH", extra_cost=5000)
        db.add(pp_option)
        db.flush()

        ord_pp_map = OrdPpMap(ord_id=ord_row.ord_id, pp_id=pp_option.pp_id)
        db.add(ord_pp_map)
        db.flush()

        db.add(
            PpTaskTxn(
                ord_id=ord_row.ord_id,
                item_stat_id=item.item_stat_id,
                map_id=ord_pp_map.map_id,
                pp_nm=pp_option.pp_nm,
                txn_stat="PROC",
            )
        )
        db.add(
            EquipTaskTxn(
                res_id=res.res_id,
                task_type="PP",
                txn_stat="PROC",
                item_stat_id=item.item_stat_id,
                ord_id=ord_row.ord_id,
            )
        )
        db.commit()

        return {
            "ord_id": ord_row.ord_id,
            "item_stat_id": item.item_stat_id,
            "zone_nm": zone_pp.zone_nm,
            "pp_nm": pp_option.pp_nm,
        }


def test_production_item_routes_project_legacy_fields_from_canonical_source(client, production_seed):
    response = client.get(f"/api/production/items?ord_id={production_seed['ord_id']}")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1

    row = rows[0]
    assert row["item_id"] == production_seed["item_stat_id"]
    assert row["ord_id"] == production_seed["ord_id"]
    assert row["flow_stat"] == "PP"
    assert row["zone_nm"] == production_seed["zone_nm"]
    assert row["result"] is True
    assert row["cur_stat"] == "PP"
    assert row["cur_res"] == production_seed["zone_nm"]
    assert row["is_defective"] is False

    response = client.get(f"/api/production/items/{production_seed['item_stat_id']}/pp")
    assert response.status_code == 200
    payload = response.json()

    assert payload["item_id"] == production_seed["item_stat_id"]
    assert payload["ord_id"] == production_seed["ord_id"]
    assert [row["pp_nm"] for row in payload["pp_options"]] == [production_seed["pp_nm"]]
    assert len(payload["pp_task_status"]) == 1
    assert payload["pp_task_status"][0]["item_id"] == production_seed["item_stat_id"]
    assert payload["pp_task_status"][0]["txn_stat"] == "PROC"
