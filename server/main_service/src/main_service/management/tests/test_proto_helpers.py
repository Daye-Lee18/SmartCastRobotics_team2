from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import management_pb2  # type: ignore

from rpc.proto_helpers import item_to_proto
from smart_cast_db.models import ItemStat


def test_item_to_proto_uses_canonical_item_stat_fields() -> None:
    item = ItemStat(
        item_stat_id=17,
        ord_id=501,
        flow_stat="WAIT_INSP",
        zone_nm="INSP",
        updated_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
    )

    proto = item_to_proto(item)

    assert isinstance(proto, management_pb2.Item)
    assert proto.id == 17
    assert proto.order_id == "501"
    assert proto.cur_stage == 1  # WAIT_INSP -> legacy QUE
    assert proto.curr_res == "INSP"
    assert proto.mfg_at.iso8601 == "2026-05-01T12:00:00+00:00"


def test_item_to_proto_accepts_legacy_list_items_projection() -> None:
    item = SimpleNamespace(
        item_id=23,
        ord_id=777,
        cur_stat="PP",
        cur_res="PP",
        updated_at=datetime(2026, 5, 1, 13, 30, tzinfo=timezone.utc),
    )

    proto = item_to_proto(item)

    assert isinstance(proto, management_pb2.Item)
    assert proto.id == 23
    assert proto.order_id == "777"
    assert proto.cur_stage == 5  # PP
    assert proto.curr_res == "PP"
    assert proto.mfg_at.iso8601 == "2026-05-01T13:30:00+00:00"
