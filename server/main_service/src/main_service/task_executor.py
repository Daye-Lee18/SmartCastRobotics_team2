"""
task_executor.py
- 역할: Orchestrator로부터 할당된 Task를 받아 Adapter를 통해 물리적으로 실행하고 결과를 State Manager에 보고함.
- 핵심 로직: 시퀀스 분해 -> 순차 실행 -> 상태 전이 관리 (이벤트 발행은 State Manager 책임)
- Naming: Pydantic Naming Convention 가이드 준수 (Input/Result 접미사)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Protocol, List, Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator

# ==========================================
# 1. ENUM & CONSTANTS
# ==========================================

class TaskStat(str, Enum):
    """DB Schema (equip_task_txn / trans_task_txn) 의 txn_stat 컬럼과 매칭"""
    QUE = "QUE"
    PROC = "PROC"
    SUCC = "SUCC"
    FAIL = "FAIL"

class TaskType(str, Enum):
    """DB Schema 의 task_type 컬럼과 매칭 (최신 명칭: MAT/PAT/TAT)"""
    # MAT (Casting)
    MM = "MM"
    POUR = "POUR"
    DM = "DM"
    # PAT (Logistics)
    PA_GP = "PA_GP"
    PA_DP = "PA_DP"
    PICK = "PICK"
    SHIP = "SHIP"
    # TAT (AMR)
    ToPP = "ToPP"
    ToSTRG = "ToSTRG"
    ToSHIP = "ToSHIP"
    ToCHG = "ToCHG"
    # CONV
    ToINSP = "ToINSP"
    ToPAWait = "ToPAWait"

# ==========================================
# 2. PYDANTIC MODELS (Naming Convention 준수)
# ==========================================

class CommandStep(BaseModel):
    """분해된 물리 시퀀스의 단위 단계 (인메모리 정의)"""
    step_id: int = Field(gt=0)
    action: str = Field(min_length=1)
    params: Dict[str, Any] = Field(default_factory=dict)
    timeout_sec: int = Field(default=30, ge=1)

class TaskExecutorInput(BaseModel):
    task_id: str  # min_length 제거
    res_id: str   # min_length 제거
    task_type: TaskType
    item_id: Optional[str] = None
    
    @field_validator("task_id", "res_id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not v.strip():  # None/빈문자열/공백만 체크
            raise ValueError("ID cannot be empty")
        return v.strip()

class ExecutionResult(BaseModel):
    """실행 완료 후 반환되는 결과값 ([동사][명사]Result 규칙)"""
    task_id: str
    final_status: TaskStat
    steps_executed: int = Field(ge=0)
    error_code: Optional[str] = None
    completed_at: datetime = Field(default_factory=datetime.now)

class UpdateTaskStatusInput(BaseModel):
    """State Manager 로 보낼 상태 업데이트 요청 ([동사][명사]Input 규칙)"""
    task_id: str
    new_stat: TaskStat
    error_code: Optional[str] = None

# ==========================================
# 3. PROTOCOLS (Interfaces)
# ==========================================

class IAdapter(Protocol):
    """Adapter 인터페이스 ([명사] 규칙)"""
    async def send_command(self, robot_id: str, action: str, params: Dict) -> bool: ...

class IStateManager(Protocol):
    """State Manager 인터페이스 (이벤트 발행 책임 분리)"""
    async def update_task_status(self, req: UpdateTaskStatusInput) -> bool: ...

# ==========================================
# 4. TASK EXECUTOR IMPLEMENTATION
# ==========================================

class TaskExecutor:
    """
    Task Executor
    
    [FB3 반영] 논리적 Task 를 물리적 시퀀스로 분해하여 실행
    [FB4 반영] Task 단위(txn_stat) 상태 관리에 집중
    [FB5 반영] 이벤트 발행은 State Manager 책임이므로 Executor 는 호출하지 않음
    """

    def __init__(self, adapter: IAdapter, state_manager: IStateManager):
        self.adapter = adapter
        self.state_manager = state_manager
        self.logger = logging.getLogger(__name__)
        
        # [Unit Test Scope] 시퀀스 분해 맵 (하드코딩된 가상 데이터)
        # 실제 운영 시에는 DB(ra_motion_step) 조회 또는 State Manager 를 통해 동적 획득 가능
        self._sequence_map: Dict[TaskType, List[CommandStep]] = {
            # === MAT (Casting Robot) ===
            TaskType.MM: [
                CommandStep(step_id=1, action="MOLD_P1_PICK", params={"speed": 50}),
                CommandStep(step_id=2, action="GRIPPER_CLOSE", params={"speed": 50}),
                CommandStep(step_id=3, action="MOLD_P1_PATTERNING", params={"speed": 50}),
                CommandStep(step_id=4, action="MOLD_P1_DROP", params={"speed": 50}),
                CommandStep(step_id=5, action="GRIPPER_OPEN", params={"speed": 50}),
                CommandStep(step_id=6, action="GO_HOME", params={}),
            ],
            TaskType.POUR: [
                CommandStep(step_id=1, action="POURING_PICK_READY", params={"speed": 50}),
                CommandStep(step_id=2, action="POURING_PICK", params={"speed": 50}),
                CommandStep(step_id=3, action="GRIPPER_CLOSE", params={"speed": 50}),
                CommandStep(step_id=4, action="POURING_TILT", params={"speed": 50}),
                CommandStep(step_id=5, action="GRIPPER_OPEN", params={"speed": 50}),
                CommandStep(step_id=6, action="GO_HOME", params={}),
            ],
            TaskType.DM: [
                CommandStep(step_id=1, action="DEMOLD_APPROACH", params={"speed": 50}),
                CommandStep(step_id=2, action="DEMOLD_PICK", params={"speed": 50}),
                CommandStep(step_id=3, action="GRIPPER_CLOSE", params={"speed": 50}),
                CommandStep(step_id=4, action="DEMOLD_DROP", params={"speed": 50}),
                CommandStep(step_id=5, action="GRIPPER_OPEN", params={"speed": 50}),
                CommandStep(step_id=6, action="GO_HOME", params={}),
            ],
            
            # === PAT (Logistics Robot) ===
            TaskType.PA_GP: [
                CommandStep(step_id=1, action="APPROACH", params={"floor": 3, "cell": 1, "speed": 30}),
                CommandStep(step_id=2, action="GRIPPER_CLOSE", params={"speed": 50}),
                CommandStep(step_id=3, action="PLACE", params={"floor": 3, "cell": 1, "speed": 30}),
                CommandStep(step_id=4, action="GRIPPER_OPEN", params={"speed": 50}),
                CommandStep(step_id=5, action="GO_HOME", params={}),
            ],
            TaskType.PA_DP: [
                CommandStep(step_id=1, action="APPROACH", params={"floor": 1, "cell": 1, "speed": 30}),
                CommandStep(step_id=2, action="GRIPPER_CLOSE", params={"speed": 50}),
                CommandStep(step_id=3, action="DEFECT_DROP", params={"speed": 30}),
                CommandStep(step_id=4, action="GRIPPER_OPEN", params={"speed": 50}),
                CommandStep(step_id=5, action="GO_HOME", params={}),
            ],
            TaskType.PICK: [
                CommandStep(step_id=1, action="APPROACH", params={"floor": 3, "cell": 1, "speed": 30}),
                CommandStep(step_id=2, action="GRIPPER_CLOSE", params={"speed": 50}),
                CommandStep(step_id=3, action="PLACE", params={"floor": 3, "cell": 1, "speed": 30}),
                CommandStep(step_id=4, action="GRIPPER_OPEN", params={"speed": 50}),
                CommandStep(step_id=5, action="GO_HOME", params={}),
            ],
            # ✅ 추가된 SHIP 시퀀스
            TaskType.SHIP: [
                CommandStep(step_id=1, action="APPROACH", params={"floor": 1, "cell": 1, "speed": 30}),
                CommandStep(step_id=2, action="GRIPPER_CLOSE", params={"speed": 50}),
                CommandStep(step_id=3, action="PLACE", params={"zone": "SHIP", "speed": 30}),
                CommandStep(step_id=4, action="GRIPPER_OPEN", params={"speed": 50}),
                CommandStep(step_id=5, action="GO_HOME", params={}),
            ],
            # === TAT (AMR) ===
            TaskType.ToPP: [
                CommandStep(step_id=1, action="ToCAST1", params={}),  # Casting Waiting
                CommandStep(step_id=2, action="ToPP1", params={}),    # PP Zone
                CommandStep(step_id=3, action="ToCHG1", params={}),   # Charging
            ],
            TaskType.ToSTRG: [
                CommandStep(step_id=1, action="ToINSP", params={}),   # Conveyor Waiting
                CommandStep(step_id=2, action="ToSTRG1", params={}),  # STRG Zone
                CommandStep(step_id=3, action="ToCHG1", params={}),   # Charging
            ],
            TaskType.ToSHIP: [
                CommandStep(step_id=1, action="ToSTRG1", params={}),  # STRG Zone (PICK 후)
                CommandStep(step_id=2, action="ToSHIP", params={}),   # SHIP Zone
                CommandStep(step_id=3, action="ToCHG1", params={}),   # Charging
            ],
            TaskType.ToCHG: [
                CommandStep(step_id=1, action="ToCHG1", params={}),   # Charging Zone
            ],
            
            # === CONV (Conveyor Belt) ===
            TaskType.ToINSP: [
                CommandStep(step_id=1, action="CONV_RUN", params={"duration_sec": 4}),
            ],
            TaskType.ToPAWait: [
                CommandStep(step_id=1, action="CONV_RUN", params={"duration_sec": 4}),
            ],
        }

    async def execute_task(self, input_data: TaskExecutorInput) -> ExecutionResult:
        """
        메인 실행 파이프라인
        
        1. 전처리 및 상태 업데이트 (QUE -> PROC)
        2. 시퀀스 분해
        3. 단계별 Adapter 호출 및 모니터링
        4. 최종 결과 보고 (SUCC/FAIL) -> State Manager 업데이트 요청 후 종료
        """
        self.logger.info(f"[Executor] Start Task: {input_data.task_id} ({input_data.task_type.value})")

        # 1. 전처리: 실행 가능 여부 확인 (Mock)
        # 실제 구현 시에는 res_stat 확인 등 수행
        if not await self._pre_check(input_data):
            return await self._handle_error(input_data, "PRECHECK_FAILED", 0)

        # [FB4 반영] 상태 전이: QUE -> PROC
        await self.state_manager.update_task_status(
            UpdateTaskStatusInput(task_id=input_data.task_id, new_stat=TaskStat.PROC)
        )

        # 2. 시퀀스 분해
        try:
            sequence = self._breakdown_sequence(input_data.task_type)
        except ValueError as e:
            return await self._handle_error(input_data, str(e), 0)

        executed_steps = 0
        
        # 3. 순차 실행
        try:
            for step in sequence:
                # 단계 실행
                success = await self._execute_step(input_data.res_id, step)
                if not success:
                    raise RuntimeError(f"Adapter failed at step {step.step_id}")
                
                executed_steps += 1
                self.logger.info(f"[Executor] Step {step.step_id} completed")
            
            # [FB4 반영] 성공 상태 전이: PROC -> SUCC
            await self.state_manager.update_task_status(
                UpdateTaskStatusInput(task_id=input_data.task_id, new_stat=TaskStat.SUCC)
            )
            return ExecutionResult(
                task_id=input_data.task_id,
                final_status=TaskStat.SUCC,
                steps_executed=executed_steps
            )

        except Exception as e:
            # [FB4 반영] 실패 상태 전이: PROC -> FAIL
            return await self._handle_error(input_data, str(e), executed_steps)

    async def _pre_check(self, input_data: TaskExecutorInput) -> bool:
        """실행 전 조건 확인 (Mock)"""
        # TODO: 실제 구현 시 res_id 의 상태 (IDLE 등) 체크
        return True

    def _breakdown_sequence(self, task_type: TaskType) -> List[CommandStep]:
        """[FB3] Task Type 기준 시퀀스 분해"""
        seq = self._sequence_map.get(task_type)
        if not seq:
            raise ValueError(f"No sequence defined for task_type: {task_type.value}")
        return seq.copy()

    async def _execute_step(self, res_id: str, step: CommandStep) -> bool:
        """단일 단계 실행 및 Adapter 호출"""
        return await self.adapter.send_command(
            robot_id=res_id,
            action=step.action,
            params=step.params
        )

    async def _handle_error(self, input_data: TaskExecutorInput, error_msg: str, steps: int) -> ExecutionResult:
        """에러 처리 및 상태 업데이트"""
        self.logger.error(f"[Executor] Task {input_data.task_id} failed: {error_msg}")
        await self.state_manager.update_task_status(
            UpdateTaskStatusInput(task_id=input_data.task_id, new_stat=TaskStat.FAIL, error_code=error_msg)
        )
        return ExecutionResult(
            task_id=input_data.task_id,
            final_status=TaskStat.FAIL,
            steps_executed=steps,
            error_code=error_msg
        )
