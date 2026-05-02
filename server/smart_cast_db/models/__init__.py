"""smartcast schema 모델 export.

Confluence page 32342045 v59 (2026-04-18) 기준 27 테이블 + equip_load_spec.
2026-04-27: backend/app/models/models.py (553 LOC, 29 클래스) 를 도메인별 8 파일로 분할.

SPEC-C5 (2026-04-23): TransportTask/HandoffAck 를 public → smartcast 로 이관.
Alert/RfidScanLog 은 public 에 유지.

도메인별 파일 (소스):
    _base.py        SCHEMA + 공통 SQLAlchemy import
    user.py         UserAccount
    order.py        Ord, OrdDetail, OrdPpMap, OrdPattern, OrdTxn, OrdStat, OrdLog
    master.py       Category, Product, ProductOption, PpOption, Zone, PatternMaster,
                    Res, Equip, EquipLoadSpec, Trans (마스터 데이터)
    item.py         Item + ChgLocationStat, StrgLocationStat, ShipLocationStat
    equipment.py    EquipTaskTxn, EquipStat, LogErrEquip (생산 설비 트랜잭션)
    transport.py    TransTaskTxn, TransStat, LogErrTrans, TransportTask,
                    HandoffAck, TatNavPoseMaster (이송 트랜잭션)
    rfid.py         RfidScanLog (RFID 로그)
    inspection.py   PpTaskTxn, InspTaskTxn (후처리/검사 트랜잭션)

공용 import 경로: `from smart_cast_db.models import Ord, Item, ...`.
"""

from smart_cast_db.models._base import SCHEMA
from smart_cast_db.models.equipment import EquipStat, EquipTaskTxn, LogErrEquip
from smart_cast_db.models.inspection import InspTaskTxn, PpTaskTxn
from smart_cast_db.models.item import (
    ChgLocationStat,
    Item,
    ShipLocationStat,
    StrgLocationStat,
)
from smart_cast_db.models.alert import Alert
from smart_cast_db.models.master import (
    Category,
    Equip,
    EquipLoadSpec,
    PpOption,
    Product,
    ProductOption,
    PatternMaster,
    RaMotionStep,
    Res,
    Trans,
    Zone,
)

from smart_cast_db.models.order import (
    Ord,
    OrdDetail,
    OrdLog,
    OrdPpMap,
    OrdPattern,
    OrdStat,
    OrdTxn,
)
from smart_cast_db.models.rfid import RfidScanLog
from smart_cast_db.models.transport import LogErrTrans, TransStat, TransTaskTxn
from smart_cast_db.models.transport import HandoffAck, TatNavPoseMaster, TransportTask
from smart_cast_db.models.user import UserAccount

__all__ = [
    "SCHEMA",
    "Category",
    "ChgLocationStat",
    "Equip",
    "LogErrEquip",
    "EquipLoadSpec",
    "EquipStat",
    "EquipTaskTxn",
    "InspTaskTxn",
    "Item",
    "Ord",
    "OrdDetail",
    "OrdLog",
    "OrdPpMap",
    "OrdPattern",
    "OrdStat",
    "OrdTxn",
    "PatternMaster",
    "RaMotionStep",
    "PpOption",
    "PpTaskTxn",
    "Product",
    "ProductOption",
    "Res",
    "ShipLocationStat",
    "StrgLocationStat",
    "Trans",
    "TatNavPoseMaster",
    "LogErrTrans",
    "TransStat",
    "TransTaskTxn",
    "UserAccount",
    "Zone",
    "Alert",
    "HandoffAck",
    "RfidScanLog",
    "TransportTask",
]
