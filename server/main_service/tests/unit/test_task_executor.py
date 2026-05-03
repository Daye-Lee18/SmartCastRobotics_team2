"""
test_task_executor.py
- Structure: Task Executor Unit Test Plan (PDF ver. 030526)
- Groups: S-51 ~ S-55, FB1, Input Validation, Coverage
- Naming: Pydantic Naming Convention 가이드 준수
"""

import pytest
from unittest.mock import AsyncMock
import asyncio
from datetime import datetime

from main_service.task_executor import (
    TaskExecutor,
    TaskExecutorInput,
    ExecutionResult,
    TaskStat,
    TaskType,
    CommandStep,
    UpdateTaskStatusInput
)

# ==========================================
# 1. FIXTURES & MOCKS
# ==========================================

@pytest.fixture
def mock_adapter():
    """Adapter Mock: send_command 는 항상 성공"""
    adapter = AsyncMock()
    adapter.send_command = AsyncMock(return_value=True)
    return adapter

@pytest.fixture
def mock_state_manager():
    """State Manager Mock: update_task_status 는 항상 성공"""
    sm = AsyncMock()
    sm.update_task_status = AsyncMock(return_value=True)
    return sm

@pytest.fixture
def executor(mock_adapter, mock_state_manager):
    """TaskExecutor 인스턴스 생성"""
    return TaskExecutor(
        adapter=mock_adapter,
        state_manager=mock_state_manager
    )

@pytest.fixture
def valid_input():
    """MAT(MM) 작업용 기본 입력값"""
    return TaskExecutorInput(
        task_id="TASK-MM-001",
        res_id="MAT",
        task_type=TaskType.MM,
        item_id="ITEM-100"
    )

# ==========================================
# [그룹 1] 시퀀스 분해 검증 (S-51)
# ==========================================

@pytest.mark.asyncio
async def test_s51_sequence_breakdown_all_task_types(executor):
    """[S-51] 12 가지 작업 유형 모두를 장비별 실행 단계로 변환할 수 있어야 함
    
    실제 공정 시나리오:
    - 주문이 들어왔을 때, 시스템이 MM, ToPP 등 12 가지 작업 유형을 모두 인식해야 함.
    검증 목적:
    - 모든 TaskType 이 _sequence_map 에 정의되어 있고, CommandStep 리스트를 정상 반환하는지.
    """
    for task_type in TaskType:
        seq = executor._breakdown_sequence(task_type)
        assert len(seq) > 0, f"{task_type.value} is missing sequence"
        assert all(isinstance(step, CommandStep) for step in seq)

@pytest.mark.asyncio
async def test_s51_mat_mm_sequence_structure(executor):
    """[S-51] MAT(주형제작) 의 시퀀스 구조 검증
    
    실제 공정 시나리오:
    - 주형제작 (MM): 패턴 위치 이동 → 집기 → 주형 이동 → 성형 → 원위치 → 복귀 (6 단계)
    검증 목적:
    - MAT 로봇이 CASTING_WAYPOINTS 키와 일치하는 6 단계 시퀀스로 분해되는지.
    """
    seq = executor._breakdown_sequence(TaskType.MM)
    assert len(seq) == 6
    assert seq[0].action == "MOLD_P1_PICK"
    assert seq[2].action == "MOLD_P1_PATTERNING"
    assert seq[5].action == "GO_HOME"

@pytest.mark.asyncio
async def test_s51_pat_gp_sequence_structure(executor):
    """[S-51] PAT(양품적치) 의 시퀀스 구조 검증
    
    실제 공정 시나리오:
    - 양품 적치 (PA_GP): 선반 접근 → 집기 → 적치 → 복귀
    검증 목적:
    - PAT 로봇이 LOGISTICS_WAYPOINTS 키와 floor/cell 파라미터를 포함해 분해되는지.
    """
    seq = executor._breakdown_sequence(TaskType.PA_GP)
    assert len(seq) == 5
    assert seq[0].action == "APPROACH"
    assert seq[0].params["floor"] == 3

@pytest.mark.asyncio
async def test_s51_amr_sequence_structure(executor):
    """[S-51] AMR(후처리이송) 의 시퀀스 구조 검증
    
    실제 공정 시나리오:
    - 후처리이송 (ToPP): Casting 대기 → PP 구역 → 충전 이동
    검증 목적:
    - AMR 이 DOCK_STATIONS 키 (ToCAST1, ToPP1, ToCHG1) 를 순서대로 분해하는지.
    """
    seq = executor._breakdown_sequence(TaskType.ToPP)
    assert len(seq) == 3
    assert seq[0].action == "ToCAST1"
    assert seq[1].action == "ToPP1"

@pytest.mark.asyncio
async def test_s51_conv_sequence_structure(executor):
    """[S-51] Conveyor(검사이송) 의 시퀀스 구조 검증
    
    실제 공정 시나리오:
    - 검사이송 (ToINSP): 컨베이어 가동 후 자동 정지
    검증 목적:
    - Conveyor 가 시간 기반 명령 (CONV_RUN) 을 정확히 분해하는지.
    """
    seq = executor._breakdown_sequence(TaskType.ToINSP)
    assert len(seq) == 1
    assert seq[0].action == "CONV_RUN"
    assert seq[0].params["duration_sec"] == 4

# ==========================================
# [그룹 2] 상태 전이 검증 (S-52)
# ==========================================

@pytest.mark.asyncio
async def test_s52_status_update_success_flow(executor, mock_state_manager, valid_input):
    """[S-52] 정상 실행 시 상태 전이 (QUE → PROC → SUCC) 검증
    
    실제 공정 시나리오:
    - 작업 할당 (QUE) → 로봇 시작 (PROC) → 작업 완료 (SUCC)
    검증 목적:
    - state_manager.update_task_status() 가 PROC → SUCC 순으로 호출되는지.
    """
    result = await executor.execute_task(valid_input)
    assert result.final_status == TaskStat.SUCC
    
    calls = mock_state_manager.update_task_status.call_args_list
    assert len(calls) == 2
    assert calls[0][0][0].new_stat == TaskStat.PROC
    assert calls[1][0][0].new_stat == TaskStat.SUCC

@pytest.mark.asyncio
async def test_s52_status_update_failure_flow(executor, mock_adapter, mock_state_manager, valid_input):
    """[S-52] 실패 시 상태 전이 (QUE → PROC → FAIL) 검증
    
    실제 공정 시나리오:
    - 작업 중 그리퍼 오류 발생 시, 즉시 FAIL 상태로 전환
    검증 목적:
    - 예외 발생 시 PROC → FAIL 로 전이되고 error_code 가 전달되는지.
    """
    mock_adapter.send_command.side_effect = [True, False, True]
    
    result = await executor.execute_task(valid_input)
    assert result.final_status == TaskStat.FAIL
    
    calls = mock_state_manager.update_task_status.call_args_list
    assert len(calls) == 2
    assert calls[0][0][0].new_stat == TaskStat.PROC
    assert calls[1][0][0].new_stat == TaskStat.FAIL

# ==========================================
# [그룹 3] 작업 완료 보고 검증 (S-53)
# ==========================================

@pytest.mark.asyncio
async def test_s53_task_completion_result(executor, valid_input):
    """[S-53] 작업 완료 시 ExecutionResult 반환 검증
    
    실제 공정 시나리오:
    - 주형제작 완료 시, 다음 공정 (탈형) 을 깨울 수 있는 정확한 결과 반환
    검증 목적:
    - ExecutionResult 의 모든 필드가 실제 실행 내용과 일치하는지.
    """
    result = await executor.execute_task(valid_input)
    
    assert isinstance(result, ExecutionResult)
    assert result.task_id == valid_input.task_id
    assert result.final_status == TaskStat.SUCC
    assert result.steps_executed == 6
    assert result.error_code is None

@pytest.mark.asyncio
async def test_s53_task_completion_all_equipment_types(executor):
    """[S-53] 모든 장비 유형별 작업 완료 검증
    
    실제 공정 시나리오:
    - MAT, PAT, TAT, CONV 모두 작업 완료 시 동일한 형식으로 결과 보고
    검증 목적:
    - 4 가지 장비 유형 모두 final_status=SUCC 와 올바른 steps_executed 를 반환하는지.
    """
    # MAT
    res = await executor.execute_task(TaskExecutorInput(task_id="T1", res_id="MAT", task_type=TaskType.MM, item_id="I"))
    assert res.final_status == TaskStat.SUCC and res.steps_executed == 6
    
    # PAT
    res = await executor.execute_task(TaskExecutorInput(task_id="T2", res_id="PAT", task_type=TaskType.PA_GP, item_id="I"))
    assert res.final_status == TaskStat.SUCC and res.steps_executed == 5
    
    # TAT
    res = await executor.execute_task(TaskExecutorInput(task_id="T3", res_id="TAT1", task_type=TaskType.ToPP, item_id="I"))
    assert res.final_status == TaskStat.SUCC and res.steps_executed == 3
    
    # CONV
    res = await executor.execute_task(TaskExecutorInput(task_id="T4", res_id="CONV1", task_type=TaskType.ToINSP, item_id="I"))
    assert res.final_status == TaskStat.SUCC and res.steps_executed == 1

# ==========================================
# [그룹 4] 예외 처리 검증 (S-54)
# ==========================================

@pytest.mark.asyncio
async def test_s54_error_handling_adapter_failure(executor, mock_adapter, mock_state_manager, valid_input):
    """[S-54] Adapter 실패 시 즉시 중단 및 에러 처리 검증
    
    실제 공정 시나리오:
    - 로봇팔이 패턴을 집는 도중 모터 과부하 발생 → 즉시 중단 및 FAIL 보고
    검증 목적:
    - send_command 실패 시 루프가 중단되고 steps_executed 가 실패 지점까지만 카운트되는지.
    """
    mock_adapter.send_command.side_effect = [True, False, True]
    
    result = await executor.execute_task(valid_input)
    
    assert result.final_status == TaskStat.FAIL
    assert result.steps_executed == 1  # 1 단계 완료 후 2 단계 실패
    assert "Adapter failed" in result.error_code

@pytest.mark.asyncio
async def test_s54_error_handling_precondition_failure(executor, mock_state_manager, valid_input):
    """[S-54] 전처리 실패 시 PROC 진입 방지 검증
    
    실제 공정 시나리오:
    - 작업 시작 전 금형이 제자리에 없음 → 작업 시작 자체를 막고 FAIL 보고
    검증 목적:
    - _pre_check() 실패 시 PROC 상태로 전이되지 않고 바로 FAIL 로 처리되는지.
    """
    async def fake_pre_check(*args): return False
    
    original = executor._pre_check
    executor._pre_check = fake_pre_check
    
    try:
        result = await executor.execute_task(valid_input)
        
        assert result.final_status == TaskStat.FAIL
        assert "PRECHECK_FAILED" in result.error_code
        
        # PROC 로 전이되지 않음 (FAIL 만 1 회)
        assert mock_state_manager.update_task_status.call_count == 1
        assert mock_state_manager.update_task_status.call_args_list[0][0][0].new_stat == TaskStat.FAIL
    finally:
        executor._pre_check = original

# ==========================================
# [그룹 5] Adapter 명령 전달 검증 (S-55)
# ==========================================

@pytest.mark.asyncio
async def test_s55_adapter_command_dispatch_mat(executor, mock_adapter, valid_input):
    """[S-55] MAT 작업 시 Adapter 에 올바른 명령 전달 검증
    
    실제 공정 시나리오:
    - MM 작업 시 로봇팔에 MOLD_P1_PICK → GRIPPER_CLOSE → ... 순서로 명령 전달
    검증 목적:
    - adapter.send_command() 가 올바른 action 과 params 로 호출되는지.
    """
    await executor.execute_task(valid_input)
    
    assert mock_adapter.send_command.call_count == 6
    
    first_call = mock_adapter.send_command.call_args_list[0]
    assert first_call.kwargs["robot_id"] == "MAT"
    assert first_call.kwargs["action"] == "MOLD_P1_PICK"
    assert "speed" in first_call.kwargs["params"]

@pytest.mark.asyncio
async def test_s55_adapter_command_dispatch_tat(executor, mock_adapter):
    """[S-55] AMR 작업 시 Adapter 에 도킹 명령 전달 검증
    
    실제 공정 시나리오:
    - ToPP 작업 시 AMR 에 ToCAST1(도킹) → ToPP1(도킹) → ToCHG1(도킹) 명령 전달
    검증 목적:
    - AMR 이 DOCK_STATIONS 테이블 키를 기반으로 정확한 도킹 좌표를 받는지.
    """
    input_data = TaskExecutorInput(task_id="T-AMR", res_id="TAT1", task_type=TaskType.ToPP, item_id="I-AMR")
    await executor.execute_task(input_data)
    
    assert mock_adapter.send_command.call_count == 3
    
    calls = mock_adapter.send_command.call_args_list
    assert calls[0].kwargs["action"] == "ToCAST1"
    assert calls[1].kwargs["action"] == "ToPP1"

@pytest.mark.asyncio
async def test_s55_adapter_command_dispatch_conv(executor, mock_adapter):
    """[S-55] Conveyor 작업 시 Adapter 에 시간 기반 명령 전달 검증
    
    실제 공정 시나리오:
    - ToINSP 작업 시 Conveyor 에 CONV_RUN 명령과 duration_sec=4 파라미터 전달
    검증 목적:
    - Conveyor 가 시간 기반 제어를 위해 정확한 파라미터를 받는지.
    """
    input_data = TaskExecutorInput(task_id="T-CONV", res_id="CONV1", task_type=TaskType.ToINSP, item_id="I-CONV")
    await executor.execute_task(input_data)
    
    assert mock_adapter.send_command.call_count == 1
    
    call = mock_adapter.send_command.call_args_list[0]
    assert call.kwargs["action"] == "CONV_RUN"
    assert call.kwargs["params"]["duration_sec"] == 4

# ==========================================
# [그룹 6] Orchestrator 연동 검증 (FB1)
# ==========================================

class MockOrchestrator:
    """[FB1] Orchestrator 가 Executor 를 호출하는 가상 시나리오"""
    def __init__(self, executor):
        self.executor = executor

    async def request_production(self, task_data: dict) -> ExecutionResult:
        """가상 데이터를 생성하여 Executor 에게 요청"""
        input_data = TaskExecutorInput(
            task_id=task_data["txn_id"],
            res_id=task_data["res_id"],
            task_type=task_data["task_type"],
            item_id=task_data["item_id"]
        )
        return await self.executor.execute_task(input_data)

@pytest.mark.asyncio
async def test_fb1_orchestrator_integration_mat(executor, mock_adapter):
    """[FB1] Orchestrator 로부터 MAT 작업 가상 데이터 수신 및 실행 검증
    
    실제 공정 시나리오:
    - Orchestrator 가 "주문 #1001 의 주형제작 시작" 명령을 내려 → Task Executor 가 실행 → 완료 보고
    검증 목적:
    - MockOrchestrator 를 통해 입력→실행→보고의 전체 파이프라인이 끊김 없이 동작하는지.
    """
    orchestrator = MockOrchestrator(executor)
    
    mock_task_data = {
        "txn_id": "TXN-MM-001",
        "res_id": "MAT",
        "task_type": "MM",
        "item_id": "ITM-MM-001"
    }
    
    result = await orchestrator.request_production(mock_task_data)
    
    assert result.task_id == "TXN-MM-001"
    assert result.final_status == TaskStat.SUCC

@pytest.mark.asyncio
async def test_fb1_orchestrator_integration_all_types(executor):
    """[FB1] 모든 TaskType 에 대해 Orchestrator 연동 검증
    
    실제 공정 시나리오:
    - 다양한 작업 유형 (MM, PA_GP, ToSTRG, ToINSP) 에 대해 Orchestrator 가 할당 → Executor 실행
    검증 목적:
    - 모든 TaskType 에 대해 Orchestrator 연동 시나리오가 일관되게 동작하는지.
    """
    orchestrator = MockOrchestrator(executor)
    
    test_cases = [
        {"txn_id": "T1", "res_id": "MAT", "task_type": "POUR", "item_id": "I1"},
        {"txn_id": "T2", "res_id": "PAT", "task_type": "PA_GP", "item_id": "I2"},
        {"txn_id": "T3", "res_id": "TAT1", "task_type": "ToSTRG", "item_id": "I3"},
        {"txn_id": "T4", "res_id": "CONV1", "task_type": "ToINSP", "item_id": "I4"},
    ]
    
    for task_data in test_cases:
        result = await orchestrator.request_production(task_data)
        assert result.task_id == task_data["txn_id"]
        assert result.final_status == TaskStat.SUCC

# ==========================================
# [그룹 7] 입력값 검증 (Naming Convention)
# ==========================================

@pytest.mark.asyncio
async def test_input_validation_empty_task_id():
    """[입력값 검증] 빈 task_id 입력 시 예외 처리
    
    실제 공정 시나리오:
    - 작업 지시서에 task_id 가 누락된 경우, 시스템이 작업을 시작하기 전에 유효성 검사로 차단
    검증 목적:
    - 빈 task_id 입력 시 ValueError 가 발생하여 잘못된 요청이 실행되지 않는지.
    """
    with pytest.raises(ValueError, match="ID cannot be empty"):
        TaskExecutorInput(task_id="", res_id="MAT", task_type=TaskType.MM, item_id="I1")

@pytest.mark.asyncio
async def test_input_validation_empty_res_id():
    """[입력값 검증] 빈 res_id 입력 시 예외 처리
    
    실제 공정 시나리오:
    - 어떤 장비 (res_id) 에 작업을 할당할지 명시되지 않은 경우, 시스템이 할당을 거부
    검증 목적:
    - 빈 res_id 입력 시 유효성 검사가 동작하는지.
    """
    with pytest.raises(ValueError, match="ID cannot be empty"):
        TaskExecutorInput(task_id="T1", res_id="", task_type=TaskType.MM, item_id="I1")

# ==========================================
# [그룹 8] 전체 커버리지 최종 검증
# ==========================================

@pytest.mark.asyncio
async def test_coverage_all_task_types_executable(executor):
    """[커버리지] 모든 작업 유형이 실제 실행 가능한 상태로 준비되었는지 검증
    
    실제 공정 시나리오:
    - 신규 작업 유형 추가 시, 누락 없이 모든 유형이 실행 가능한지 최종 점검
    검증 목적:
    - 12 개 TaskType 모두 _sequence_map 에 정의되어 있고, 실제 execute_task() 호출 시 SUCC 를 반환하는지.
    """
    task_configs = [
        # MAT (Casting)
        ("MAT", TaskType.MM, 6),
        ("MAT", TaskType.POUR, 6),
        ("MAT", TaskType.DM, 6),
        # PAT (Logistics)
        ("PAT", TaskType.PA_GP, 5),
        ("PAT", TaskType.PA_DP, 5),
        ("PAT", TaskType.PICK, 5),
        # TAT (AMR)
        ("TAT1", TaskType.ToPP, 3),
        ("TAT1", TaskType.ToSTRG, 3),
        ("TAT1", TaskType.ToSHIP, 3),
        ("TAT1", TaskType.ToCHG, 1),
        # CONV
        ("CONV1", TaskType.ToINSP, 1),
        ("CONV1", TaskType.ToPAWait, 1),
    ]
    
    for res_id, task_type, expected_steps in task_configs:
        input_data = TaskExecutorInput(
            task_id=f"T-{task_type.value}",
            res_id=res_id,
            task_type=task_type,
            item_id="I-COV"
        )
        result = await executor.execute_task(input_data)
        
        assert result.final_status == TaskStat.SUCC, f"{task_type.value} failed"
        assert result.steps_executed == expected_steps, f"{task_type.value} step count mismatch"
