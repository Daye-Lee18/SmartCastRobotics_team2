"""AMR State Machine 단위 테스트."""

import pytest
from services.amr_state_machine import AmrStateMachine, TaskState


@pytest.fixture
def sm():
    machine = AmrStateMachine()
    machine.register("AMR-001")
    return machine


class TestTransitions:
    """유효/무효 전이 검증."""

    def test_idle_to_move_to_source(self, sm: AmrStateMachine):
        assert sm.transition("AMR-001", TaskState.MOVE_TO_SOURCE, task_id="T-1")
        assert sm.get("AMR-001").state == TaskState.MOVE_TO_SOURCE
        assert sm.get("AMR-001").task_id == "T-1"

    def test_full_cycle(self, sm: AmrStateMachine):
        """IDLE → ... → UNLOAD_COMPLETED → IDLE 전체 순환."""
        steps = [
            TaskState.MOVE_TO_SOURCE,
            TaskState.AT_SOURCE,
            TaskState.LOADING,
            TaskState.LOAD_COMPLETED,
            TaskState.MOVE_TO_DEST,
            TaskState.AT_DESTINATION,
            TaskState.UNLOADING,
            TaskState.UNLOAD_COMPLETED,
            TaskState.IDLE,
        ]
        for step in steps:
            kwargs = {}
            if step == TaskState.MOVE_TO_SOURCE:
                kwargs = {"task_id": "T-1", "loaded_item": ""}
            if step == TaskState.LOADING:
                kwargs = {"loaded_item": "ITEM-42"}
            assert sm.transition("AMR-001", step, **kwargs), f"전이 실패: → {step.name}"
        ctx = sm.get("AMR-001")
        assert ctx.state == TaskState.IDLE
        assert ctx.task_id == ""
        assert ctx.loaded_item == ""

    def test_invalid_transition_rejected(self, sm: AmrStateMachine):
        """IDLE → AT_SOURCE 는 무효."""
        assert not sm.transition("AMR-001", TaskState.AT_SOURCE)
        assert sm.get("AMR-001").state == TaskState.IDLE

    def test_any_state_to_failed(self, sm: AmrStateMachine):
        """임의 상태에서 FAILED 전이 가능."""
        sm.transition("AMR-001", TaskState.MOVE_TO_SOURCE, task_id="T-1")
        assert sm.transition("AMR-001", TaskState.FAILED)
        assert sm.get("AMR-001").state == TaskState.FAILED

    def test_failed_to_idle(self, sm: AmrStateMachine):
        """FAILED → IDLE 복구."""
        sm.transition("AMR-001", TaskState.MOVE_TO_SOURCE, task_id="T-1")
        sm.transition("AMR-001", TaskState.FAILED)
        assert sm.transition("AMR-001", TaskState.IDLE)
        assert sm.get("AMR-001").state == TaskState.IDLE

    def test_failed_to_move_rejected(self, sm: AmrStateMachine):
        """FAILED → MOVE_TO_SOURCE 는 무효 (IDLE 거쳐야 함)."""
        sm.transition("AMR-001", TaskState.MOVE_TO_SOURCE)
        sm.transition("AMR-001", TaskState.FAILED)
        assert not sm.transition("AMR-001", TaskState.MOVE_TO_SOURCE)


class TestRegistration:
    """등록/미등록 로봇 동작."""

    def test_unregistered_returns_idle(self, sm: AmrStateMachine):
        ctx = sm.get("AMR-999")
        assert ctx.state == TaskState.IDLE

    def test_transition_auto_registers(self, sm: AmrStateMachine):
        assert sm.transition("AMR-002", TaskState.MOVE_TO_SOURCE)
        assert sm.get("AMR-002").state == TaskState.MOVE_TO_SOURCE

    def test_get_all(self, sm: AmrStateMachine):
        sm.register("AMR-002")
        all_states = sm.get_all()
        assert "AMR-001" in all_states
        assert "AMR-002" in all_states


class TestForceReset:
    """강제 리셋."""

    def test_force_reset_clears_task(self, sm: AmrStateMachine):
        sm.transition("AMR-001", TaskState.MOVE_TO_SOURCE, task_id="T-1", loaded_item="ITEM-1")
        sm.force_reset("AMR-001")
        ctx = sm.get("AMR-001")
        assert ctx.state == TaskState.IDLE
        assert ctx.task_id == ""
        assert ctx.loaded_item == ""
