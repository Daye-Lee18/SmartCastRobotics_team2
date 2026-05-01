"""AMR telemetry/handoff cache tests."""

import pytest
from services.core.legacy.amr_state_machine import AmrStateMachine, TaskState


@pytest.fixture
def sm():
    machine = AmrStateMachine()
    machine.register("AMR-001")
    return machine


class TestCache:
    """최소 cache 동작 검증."""

    def test_transition_updates_cache(self, sm: AmrStateMachine):
        assert sm.transition("AMR-001", TaskState.MOVE_TO_SOURCE, task_id="T-1")
        assert sm.get("AMR-001").state == TaskState.MOVE_TO_SOURCE
        assert sm.get("AMR-001").task_id == "T-1"

    def test_handoff_releases_to_idle(self, sm: AmrStateMachine):
        sm.transition("AMR-001", TaskState.UNLOADING, task_id="T-1", loaded_item="ITEM-42")
        ok, reason = sm.confirm_handoff("AMR-001")
        ctx = sm.get("AMR-001")
        assert ok is True
        assert reason == "released"
        assert ctx.state == TaskState.IDLE
        assert ctx.task_id == ""
        assert ctx.loaded_item == ""


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
