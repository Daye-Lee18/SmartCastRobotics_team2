"""생산 공정 워크플로우 — equip/trans task_type 의 다음 단계 매핑.

Confluence 32342045 ord 승인 시퀀스 (DDL 본문 위쪽):
    equip_task_txn (CAST_MM/POUR/DM/PP)  ← 별도 레이어 불필요
        → inspection_ord (자동 생성, result 저장 필요)
            → equip_task_txn (PUTAWAY 자동)
                → shipment_ord (사람 입력, date/qty 결정)
                    → trans_task_txn (SHIP)

본 모듈은 자동 진행 시퀀서가 task 완료(SUCC) 시 어떤 후속 task 를 만들어야
하는지 결정한다. 사람 의사결정이 필요한 단계 (shipment_ord) 는 매핑 안 함.
"""

from __future__ import annotations

# RA 자동 진행 체인: equip_task_txn task_type → 다음 task_type (None=인간 결정 대기)
RA_NEXT_TASK: dict[str, str | None] = {
    "MM": "POUR",  # 주형 제작 → 주탕
    "POUR": "DM",  # 주탕 → 탈형
    "DM": "PP",  # 탈형 → 후처리 라인 진입 (실제 후처리는 사람)
    "PP": "ToINSP",  # 후처리 (CONV 시작 트리거)
    "PA_GP": None,  # 양품 적재 → 종료 (sample 출고 결정 대기)
    "PA_DP": None,  # 불량품 처리 → 종료
    "PICK": "SHIP",  # 출고 픽업 → 배달
    "SHIP": None,  # 배달 → 종료 (ord_stat=COMP 후속)
}

# CONV 후 다음: ToINSP 종료 시 INSP task 자동 생성
CONV_NEXT_INSPECTION = True

# AMR 이송 자동 체인 (trans_task_txn task_type → 다음)
TRANS_NEXT_TASK: dict[str, str | None] = {
    "ToPP": None,  # 후처리 도착 → 사람 ACK 대기 (SPEC-AMR-001)
    "ToINSP": None,  # INSP 영역 도착 → 검사 트리거
    "ToSTRG": None,  # 적재 도착 → PA task 트리거
    "ToSHIP": None,  # 출고 도착 → 종료
    "ToCHG": None,  # 충전 도착 → 충전 시작
}

# 각 task 의 자동 진행 단계 사이 sleep (초). 실기 환경의 작업 시간을 어림 시뮬레이션.
STEP_DELAY_SECONDS = 1.0

# 시퀀서 polling 주기 (초)
POLL_INTERVAL_SECONDS = 2.0

# 오류 시뮬레이션 (env FMS_ERROR_RATE 으로 override 가능, 기본 0.0 = 비활성)
# 0.05 = task 단계마다 5% 확률로 FAIL. equip_err_log/trans_err_log INSERT.
ERROR_RATE_DEFAULT = 0.0

# 사람 ACK 대기 task_type (SPEC-AMR-001) — 시퀀서가 자동 진행하지 않음
HANDOFF_WAIT_TASK_TYPES: frozenset[str] = frozenset({"ToPP"})
