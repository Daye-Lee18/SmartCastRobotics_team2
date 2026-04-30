"""Task Allocator — 거리·capability·배터리 기반 로봇 배정 스코어링."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AllocationResult:
    robot_id: str
    score: float
    rationale: str


class TaskAllocator:
    """가용 AMR/Cobot 중 최적 1대를 선택한다.

    스코어 가중치(예):
        0.45 거리 (task 목적지 ↔ 로봇 현재 pos_x/y)
        0.25 배터리 잔량 (낮을수록 감점)
        0.20 capability 매칭 (AMR vs Cobot)
        0.10 최근 할당 분산 (동일 로봇 연속 할당 감점)

    TODO:
    - equipment 테이블 쿼리 (type, status, pos, battery)
    - Task 목적지 좌표 로딩
    - 배터리 30% 미만 자동 충전 Task 우선 삽입
    """

    def allocate(self, task_id: str) -> AllocationResult:
        raise NotImplementedError("TaskAllocator.allocate: 미구현")
