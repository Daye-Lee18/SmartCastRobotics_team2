"""RA (Robot Arm) task 별 cur_stat 시퀀스 하드코딩.

Confluence 32342045 inline comment (2026-04-18, 이다예):
  "규정이가 RA task 마다 하드 코딩한 것으로 cur_stat 업데이트 필요합니다."

equip_stat.cur_stat 은 로봇 동작의 세밀 단계를 기록한다. FMS 는 RA task 진행 중
다음 상수 시퀀스에 따라 equip_stat.cur_stat 을 갱신한다.

task_type (equip_task_txn.task_type) 별 전이 시퀀스:

  MM (Mold Making)         : MV_SRC → GRASP → MV_DEST → RELEASE → RETURN
  POUR (Pouring)           : MV_SRC → GRASP → MV_DEST → POURING → RELEASE → RETURN
  DM (Demolding)           : MV_SRC → GRASP → MV_DEST → RELEASE → RETURN
  PP (Post-processing 대상 준비): MV_SRC → GRASP → MV_DEST → RELEASE → RETURN
  PA_GP (Putaway good)     : MV_SRC → GRASP → MV_DEST → RELEASE → RETURN
  PA_DP (Putaway defective): MV_SRC → GRASP → MV_DEST → RELEASE → RETURN
  PICK (for SHIP)          : MV_SRC → GRASP → MV_DEST → RELEASE → RETURN
  SHIP (배달)              : MV_SRC → GRASP → MV_DEST → RELEASE → RETURN

CONV task_type:
  ToINSP (컨베이어 이동): ON → OFF
  IDLE: OFF
  ERR: ERR

모든 task 종료 시 cur_stat 은 다시 'IDLE' 로 리셋.
"""

from __future__ import annotations

# RA cur_stat 표준 전이 단계
RA_DEFAULT_SEQUENCE: tuple[str, ...] = (
    "MV_SRC",  # pick 위치로 이동
    "GRASP",  # gripper 잡기
    "MV_DEST",  # place 위치로 이동
    "RELEASE",  # gripper 놓기
    "RETURN",  # 기본 위치 복귀
)

# POUR 는 용탕 주입 단계가 추가됨
RA_POUR_SEQUENCE: tuple[str, ...] = (
    "MV_SRC",
    "GRASP",
    "MV_DEST",
    "POURING",  # 용탕 주입 (POUR 전용)
    "RELEASE",
    "RETURN",
)

# task_type → cur_stat 시퀀스 매핑
RA_TASK_STAT_SEQUENCES: dict[str, tuple[str, ...]] = {
    "MM": RA_DEFAULT_SEQUENCE,
    "POUR": RA_POUR_SEQUENCE,
    "DM": RA_DEFAULT_SEQUENCE,
    "PP": RA_DEFAULT_SEQUENCE,
    "PA_GP": RA_DEFAULT_SEQUENCE,
    "PA_DP": RA_DEFAULT_SEQUENCE,
    "PICK": RA_DEFAULT_SEQUENCE,
    "SHIP": RA_DEFAULT_SEQUENCE,
}

# CONV 관련 단순 상수
CONV_TASK_STATES: dict[str, str] = {
    "ToINSP": "ON",
    "IDLE": "OFF",
    "ERR": "ERR",
}

# 공통 비작업 상태
STATE_IDLE = "IDLE"
STATE_ERR = "ERR"


def next_state(task_type: str, current: str | None) -> str | None:
    """task_type 과 현재 cur_stat 을 받아 다음 상태를 반환.

    - current is None → 시퀀스의 첫 상태.
    - current 가 마지막이면 IDLE 로 복귀.
    - 매핑 없는 task_type → None (호출자가 로그만 남기고 현 상태 유지).

    CONV task (ToINSP 등) 는 첫 진입에서 ON, 다음 호출에서 IDLE 로 종료
    (단일-단계 task — 컨베이어가 아이템을 검사 영역으로 운반하는 1회 동작).
    """
    if task_type in CONV_TASK_STATES:
        # 단일 단계 task: None → 정의된 상태 → IDLE 종료
        if current is None:
            return CONV_TASK_STATES[task_type]
        return STATE_IDLE

    seq = RA_TASK_STAT_SEQUENCES.get(task_type)
    if seq is None:
        return None

    if current is None:
        return seq[0]
    try:
        idx = seq.index(current)
    except ValueError:
        # 현 상태가 시퀀스에 없음 → 시작부터
        return seq[0]
    # 마지막 단계 후에는 IDLE
    if idx + 1 >= len(seq):
        return STATE_IDLE
    return seq[idx + 1]


def validate_sequence(task_type: str, current: str) -> bool:
    """현 상태가 해당 task_type 시퀀스에 속하는지 검증."""
    if task_type in CONV_TASK_STATES:
        return current in set(CONV_TASK_STATES.values())
    seq = RA_TASK_STAT_SEQUENCES.get(task_type, ())
    return current in set(seq) or current == STATE_IDLE
