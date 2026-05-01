"""DB schema v21 model exports.

This package now treats schema v21 as the canonical source of truth. A few
legacy aliases remain exported to soften the transition in higher layers.
"""

from smart_cast_db.models._base import SCHEMA
from smart_cast_db.models.equipment import EquipStat, EquipTaskTxn, LogDataEquip, LogErrEquip
from smart_cast_db.models.inspection import (
    AiInferenceTxn,
    AiModel,
    InspStat,
    InspTaskTxn,
    PickItemMap,
    PickTxn,
    PpTaskTxn,
)
from smart_cast_db.models.item import ChgLocStat, ItemStat, ShipLocStat, StrgLocStat
from smart_cast_db.models.master import (
    Category,
    Equip,
    EquipLoadSpec,
    PatternStat,
    PpOption,
    Product,
    ProductOption,
    RaMotionStep,
    Res,
    Trans,
    TransCoord,
    TransTaskBatThreshold,
    Zone,
)
from smart_cast_db.models.models_mgmt import (
    AlertsStat,
    LogActionAdmin,
    LogActionOperatorHandoffAcks,
    LogActionOperatorRfidScan,
    LogActionUser,
    LogEvent,
)
from smart_cast_db.models.order import Ord, OrdDetail, OrdLog, OrdPpMap, OrdStat, OrdTxn
from smart_cast_db.models.transport import LogDataTrans, LogErrTrans, TransStat, TransTaskTxn
from smart_cast_db.models.user import UserAccount

# Transitional aliases for legacy import paths.
Item = ItemStat
Pattern = PatternStat
ChgLocationStat = ChgLocStat
StrgLocationStat = StrgLocStat
ShipLocationStat = ShipLocStat
EquipErrLog = LogErrEquip
TransErrLog = LogErrTrans
Alert = AlertsStat
HandoffAck = LogActionOperatorHandoffAcks
RfidScanLog = LogActionOperatorRfidScan
TransportTask = TransTaskTxn

__all__ = [
    "SCHEMA",
    "AiInferenceTxn",
    "AiModel",
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
    "OrdPpMap",
    "OrdStat",
    "OrdTxn",
    "Pattern",
    "PatternStat",
    "PickItemMap",
    "PickTxn",
    "PpOption",
    "PpTaskTxn",
    "Product",
    "ProductOption",
    "RaMotionStep",
    "Res",
    "RfidScanLog",
    "ShipLocStat",
    "ShipLocationStat",
    "StrgLocStat",
    "StrgLocationStat",
    "Trans",
    "TransCoord",
    "TransErrLog",
    "TransStat",
    "TransTaskBatThreshold",
    "TransTaskTxn",
    "TransportTask",
    "UserAccount",
    "Zone",
    "Alert",
]
