from __future__ import annotations

from enum import Enum


class OrdTxnType(str, Enum):
    RCVD = "RCVD"
    APPR = "APPR"
    CNCL = "CNCL"
    REJT = "REJT"


class OrdStat(str, Enum):
    RCVD = "RCVD"
    APPR = "APPR"
    MFG  = "MFG"
    DONE = "DONE"
    SHIP = "SHIP"
    SHIPPING = "SHIPPING"
    COMP = "COMP"
    REJT = "REJT"
    CNCL = "CNCL"


class EquipTaskType(str, Enum):
    MM     = "MM"
    POUR   = "POUR"
    DM     = "DM"
    PP     = "PP"
    ToINSP = "ToINSP"
    INSP   = "INSP"
    PA_GP  = "PA_GP"
    PA_DP  = "PA_DP"
    PICK   = "PICK"
    SHIP   = "SHIP"


class ZoneNm(str, Enum):
    CAST = "CAST"
    PP   = "PP"
    INSP = "INSP"
    STRG = "STRG"
    PICK = "PICK"
    SHIP = "SHIP"
    CHG  = "CHG"


class PoseNm(str, Enum):
    HOME         = "HOME"
    TAT_HANDOFF  = "TAT_HANDOFF"
    DEFECT_HOVER = "DEFECT_HOVER"
    DEFECT_DROP  = "DEFECT_DROP"
    SLOT_PATH    = "SLOT_PATH"


class TransTaskType(str, Enum):
    ToPP   = "ToPP"
    ToSTRG = "ToSTRG"
    ToSHIP = "ToSHIP"
    ToCHG  = "ToCHG"


class TxnStat(str, Enum):
    QUE  = "QUE"
    PROC = "PROC"
    SUCC = "SUCC"
    FAIL = "FAIL"


class EquipStat(str, Enum):
    IDLE    = "IDLE"
    ALLOC   = "ALLOC"
    FAIL    = "FAIL"
    MV_SRC  = "MV_SRC"
    GRASP   = "GRASP"
    MV_DEST = "MV_DEST"
    RELEASE = "RELEASE"
    TO_IDLE = "TO_IDLE"
    ON      = "ON"
    OFF     = "OFF"


class TransStat(str, Enum):
    IDLE     = "IDLE"
    ALLOC    = "ALLOC"
    CHG      = "CHG"
    TO_IDLE  = "TO_IDLE"
    MV_SRC   = "MV_SRC"
    WAIT_LD  = "WAIT_LD"
    MV_DEST  = "MV_DEST"
    WAIT_DLD = "WAIT_DLD"
    SUCC     = "SUCC"
    FAIL     = "FAIL"


class LocStatus(str, Enum):
    EMPTY    = "empty"
    OCCUPIED = "occupied"
    RESERVED = "reserved"


class AlertSeverity(str, Enum):
    INFO     = "info"
    WARNING  = "warning"
    CRITICAL = "critical"


class RfidParseStatus(str, Enum):
    OK         = "ok"
    BAD_FORMAT = "bad_format"
    DUPLICATE  = "duplicate"


class AdminActionType(str, Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class EventType(str, Enum):
    TASK_COMPLETED = "TASK_COMPLETED"
    ITEM_STATUS_CHANGED = "ITEM_STATUS_CHANGED"
    TASK_ASSIGNED = "TASK_ASSIGNED"
