from __future__ import annotations

from app.routes import websocket
from smart_cast_db.database import SessionLocal
from smart_cast_db.models import Ord, OrdStat, Res, Trans, TransCoord, TransStat, UserAccount, Zone


def test_snapshot_projects_zone_name_from_cur_trans_coord_id(postgresql_smartcast_empty) -> None:
    with SessionLocal() as db:
        user = UserAccount(
            co_nm="TEST",
            user_nm="tester",
            role="customer",
            phone="010-0000-0000",
            email="websocket-test@example.com",
            password="secret",
        )
        db.add(user)
        db.flush()

        ord_row = Ord(user_id=user.user_id)
        db.add(ord_row)
        db.flush()

        zone = Zone(zone_nm="CHG")
        db.add(zone)
        db.flush()

        coord = TransCoord(zone_id=zone.zone_id, x=1, y=2, theta=3)
        db.add(coord)
        db.flush()

        res = Res(res_id="AMR1", res_type="AMR", model_nm="TEST-AMR")
        db.add(res)
        db.flush()

        db.add(Trans(res_id=res.res_id, slot_count=1, max_load_kg=100))
        db.add(
            TransStat(
                res_id=res.res_id,
                cur_stat="MV_SRC",
                battery_pct=88,
                cur_trans_coord_id=coord.trans_coord_id,
            )
        )
        db.add(OrdStat(ord_id=ord_row.ord_id, ord_stat="MFG"))
        db.commit()

    snapshot = websocket._snapshot()
    assert snapshot["trans"][0]["res_id"] == "AMR1"
    assert snapshot["trans"][0]["cur_zone_type"] == "CHG"
    assert snapshot["trans"][0]["battery_pct"] == 88
