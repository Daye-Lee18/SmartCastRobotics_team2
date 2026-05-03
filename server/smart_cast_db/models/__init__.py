"""smartcast schema model exports aligned to create_tables.sql."""

from smart_cast_db.models._base import SCHEMA
from smart_cast_db.models.alert import Alert, AlertsStat
from smart_cast_db.models.equipment import EquipStat, EquipTaskTxn, LogDataEquip, LogErrEquip
from smart_cast_db.models.inspection import AiInferenceTxn, AiModel, InspStat, InspTaskTxn, PpTaskTxn
from smart_cast_db.models.item import ChgLocationStat, Item, ShipLocationStat, StrgLocationStat
from smart_cast_db.models.master import (
    Category,
    Equip,
    EquipLoadSpec,
    PatternMaster,
    PpOption,
    Product,
    ProductOrderPatternMaster,
    ProductOption,
    RaMotionStep,
    Res,
    Trans,
    TransTaskBatThreshold,
    Zone,
)
from smart_cast_db.models.models_mgmt import (
    LogActionAdmin,
    LogActionOperatorHandoffAcks,
    LogActionOperatorRfidScan,
    LogActionUser,
    LogEvent,
)
from smart_cast_db.models.order import Ord, OrdDetail, OrdLog, OrdPattern, OrdPpMap, OrdStat, OrdTxn
from smart_cast_db.models.rfid import RfidScanLog
from smart_cast_db.models.transport import (
    LogDataTrans,
    LogErrTrans,
    TatNavPoseMaster,
    TransStat,
    TransTaskTxn,
)
from smart_cast_db.models.user import UserAccount

# Compatibility aliases for remaining v21 callers.
ItemStat = Item
Pattern = OrdPattern
ChgLocStat = ChgLocationStat
StrgLocStat = StrgLocationStat
ShipLocStat = ShipLocationStat
TransCoord = TatNavPoseMaster
EquipErrLog = LogErrEquip
TransErrLog = LogErrTrans
HandoffAck = LogActionOperatorHandoffAcks
TransportTask = TransTaskTxn

__all__ = [
    "SCHEMA",
    "AiInferenceTxn",
    "AiModel",
    "Alert",
    "AlertsStat",
    "Category",
    "ChgLocStat",
    "ChgLocationStat",
    "Equip",
    "EquipErrLog",
    "EquipLoadSpec",
    "EquipStat",
    "EquipTaskTxn",
    "HandoffAck",
    "InspStat",
    "InspTaskTxn",
    "Item",
    "ItemStat",
    "LogActionAdmin",
    "LogActionOperatorHandoffAcks",
    "LogActionOperatorRfidScan",
    "LogActionUser",
    "LogDataEquip",
    "LogDataTrans",
    "LogErrEquip",
    "LogErrTrans",
    "LogEvent",
    "Ord",
    "OrdDetail",
    "OrdLog",
    "OrdPattern",
    "OrdPpMap",
    "OrdStat",
    "OrdTxn",
    "Pattern",
    "PatternMaster",
    "PpOption",
    "PpTaskTxn",
    "Product",
    "ProductOrderPatternMaster",
    "ProductOption",
    "RaMotionStep",
    "Res",
    "RfidScanLog",
    "ShipLocStat",
    "ShipLocationStat",
    "StrgLocStat",
    "StrgLocationStat",
    "TatNavPoseMaster",
    "Trans",
    "TransCoord",
    "TransErrLog",
    "TransStat",
    "TransTaskBatThreshold",
    "TransTaskTxn",
    "TransportTask",
    "UserAccount",
    "Zone",
]
