from __future__ import annotations

from dataclasses import dataclass

import management_pb2  # type: ignore

from rpc.robot_rpc import RobotRpcMixin
import enum

class TaskState(enum.Enum):
    IDLE = 1
    LOADING = 2

@dataclass
class _BatteryStatus:
    id: str
    host: str
    status: str
    battery: float
    voltage: float
    location: str
    task_state: int = 1
    task_id: str = ""
    loaded_item: str = ""


class _BatteryService:
    def __init__(self, statuses):
        self._statuses = statuses

    def get_all(self):
        return list(self._statuses)


class _Servicer(RobotRpcMixin):
    def __init__(self, statuses):
        self.amr_battery = _BatteryService(statuses)


def test_get_robot_status_uses_telemetry_fields() -> None:
    servicer = _Servicer(
        [
            _BatteryStatus(
                id="AMR1",
                host="dds",
                status="online",
                battery=87.5,
                voltage=7.31,
                location="PP",
                task_state=TaskState.LOADING.value,
                task_id="T-100",
                loaded_item="ITEM-9",
            )
        ]
    )

    response = servicer.GetRobotStatus(management_pb2.GetRobotStatusRequest(), context=None)

    assert len(response.robots) == 1
    robot = response.robots[0]
    assert robot.id == "AMR1"
    assert robot.location == "PP"
    assert robot.task_state == TaskState.LOADING.value
    assert robot.task_id == "T-100"
    assert robot.loaded_item == "ITEM-9"


def test_transition_amr_state_returns_deprecated_response() -> None:
    servicer = _Servicer([])

    response = servicer.TransitionAmrState(
        management_pb2.TransitionAmrStateRequest(robot_id="AMR1", new_state=TaskState.IDLE.value),
        context=None,
    )

    assert response.accepted is False
    assert response.reason == "deprecated: telemetry_only_mode"
