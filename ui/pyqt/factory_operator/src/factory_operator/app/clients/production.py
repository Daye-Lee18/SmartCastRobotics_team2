"""Production 도메인 mixin — 라인 투입/items/equip/stages/metrics/equipment/schedule.

Pink GUI #5 (생산 시작), #4 (item별 후처리), 운영자 페이지의 advance/스케줄러.

2026-04-27: 동명 메서드 critical 픽스 — start_production_one (단건 라인 투입) +
start_production_batch (배치 큐 등록) 로 분리. ApiClient.start_production 사라짐.
"""

from __future__ import annotations

from typing import Any

from app import mock_data


class ProductionMixin:
    """생산 lifecycle + item + equip + scheduling endpoints."""

    # ===== Lifecycle =====
    def start_production_one(self, ord_id: int) -> dict[str, Any] | None:
        """단건 라인 투입 — POST /api/production/start.

        2026-04-27: 이전 'start_production' 동명 메서드 버그 픽스. 두 endpoint
        의미가 완전히 다르므로 메서드명 분리:
          - start_production_one(ord_id: int)   → /api/production/start (Item + EquipTaskTxn 생성)
          - start_production_batch(order_ids)    → /api/production/schedule/start (ord_stat MFG 큐 등록만)

        backend 동작: ord_stat=MFG + Item(QUE, RA1, MM) + EquipTaskTxn(RA1, MM, QUE) 생성.
        선행 조건: pattern 등록 (자동 매핑됨).
        """
        return self._post("/api/production/start", {"ord_id": ord_id})

    # ===== Items =====
    def get_smartcast_items(self, ord_id: int | None = None) -> list[dict[str, Any]] | None:
        path = "/api/production/items"
        if ord_id is not None:
            path = f"{path}?ord_id={ord_id}"
        return self._get(path, mock_value=[])

    def get_item_pp_requirements(self, item_id: int) -> dict[str, Any] | None:
        """Pink GUI #4 — item별 필요 후처리 + 진행 상태."""
        return self._get(f"/api/production/items/{item_id}/pp", mock_value=None)

    # ===== Equip tasks (Gap 5, 2026-04-27) =====
    def get_equip_tasks(self) -> list[dict[str, Any]]:
        """전체 equip_task_txn 목록. (필터링은 클라이언트에서.)"""
        data = self._get("/api/production/equip-tasks", mock_value=[])
        return data if isinstance(data, list) else []

    def get_active_equip_task_for_item(self, item_id: int) -> dict[str, Any] | None:
        """item 의 활성 equip_task_txn(QUE/PROC) 1건 반환. 없으면 None."""
        rows = self.get_equip_tasks()
        active = [
            r
            for r in rows
            if r.get("item_id") == item_id and str(r.get("txn_stat", "")).upper() in ("QUE", "PROC")
        ]
        if not active:
            return None
        # 가장 최근 (txn_id 최대) 1건
        active.sort(key=lambda r: int(r.get("txn_id", 0)), reverse=True)
        return active[0]

    def advance_equip_task(self, txn_id: int) -> dict[str, Any]:
        """POST /api/production/equip-tasks/{txn_id}/advance.

        IDLE 도달 시 backend 가 자동으로 후속 task (POUR/DM/ToPP) 생성.
        Response: {txn_id, prev_stat, new_stat, txn_stat, item_cur_stat, auto: {...}}
        """
        result = self._post(f"/api/production/equip-tasks/{txn_id}/advance", payload={})
        return result if isinstance(result, dict) else {}

    # ===== Production views (legacy) =====
    def get_production_metrics(self) -> list[dict[str, Any]] | None:
        return self._get("/api/production/metrics", mock_value=[])

    def get_equipment(self) -> list[dict[str, Any]] | None:
        data = self._get("/api/production/equipment", mock_value=mock_data.EQUIPMENT)
        # 필드 정규화: utilization 이 없으면 mock 기본값 사용
        if isinstance(data, list):
            normalized = []
            for item in data:
                normalized.append(
                    {
                        "id": item.get("id", ""),
                        "name": item.get("name", ""),
                        "status": item.get("status", "-"),
                        "utilization": item.get("utilization") or self._calc_util(item),
                        "last_checked": item.get("last_maintenance", item.get("last_checked", "")),
                    }
                )
            return normalized
        return data

    def get_equipment_raw(self) -> list[dict[str, Any]] | None:
        """공장 맵용: 정규화 없이 pos_x/pos_y/type 포함한 raw equipment 반환."""
        data = self._get("/api/production/equipment", mock_value=None)
        if data:
            return data  # type: ignore[return-value]
        # mock 데이터에 좌표 추가 (mock_data 의 EQUIPMENT 에는 좌표가 없음)
        return self._mock_equipment_with_positions()

    @staticmethod
    def _mock_equipment_with_positions() -> list[dict[str, Any]]:
        """좌표가 포함된 mock equipment (공장 맵 데모용).

        AMR 좌표는 시간 기반 순환으로 이동 시뮬레이션.
        """
        import math
        import time

        t = time.time() * 0.15  # 느린 순환 속도

        # AMR-001 원형 순환
        amr1_x = 10 + 10 * (0.5 + 0.5 * math.sin(t))
        amr1_y = 5 + 2.5 * math.cos(t)

        # AMR-002 horizontal ping-pong
        amr2_x = 4 + 8 * (0.5 + 0.5 * math.sin(t * 0.7 + 1.2))
        amr2_y = 7

        # AMR-003 는 충전소 근처에서 정지
        amr3_x = 1
        amr3_y = 10

        return [
            {
                "id": "FRN-001",
                "name": "용해로 #1",
                "type": "furnace",
                "status": "running",
                "pos_x": 2,
                "pos_y": 1,
            },
            {
                "id": "FRN-002",
                "name": "용해로 #2",
                "type": "furnace",
                "status": "idle",
                "pos_x": 4,
                "pos_y": 1,
            },
            {
                "id": "MLD-001",
                "name": "조형기 #1",
                "type": "mold_press",
                "status": "running",
                "pos_x": 8,
                "pos_y": 1,
            },
            {
                "id": "ARM-001",
                "name": "로봇암 #1 (주탕)",
                "type": "robot_arm",
                "status": "idle",
                "pos_x": 12,
                "pos_y": 2,
            },
            {
                "id": "ARM-002",
                "name": "로봇암 #2 (탈형)",
                "type": "robot_arm",
                "status": "idle",
                "pos_x": 16,
                "pos_y": 2,
            },
            {
                "id": "ARM-003",
                "name": "로봇암 #3 (후처리)",
                "type": "robot_arm",
                "status": "running",
                "pos_x": 20,
                "pos_y": 2,
            },
            {
                "id": "CVR-001",
                "name": "컨베이어 #1",
                "type": "conveyor",
                "status": "running",
                "pos_x": 24,
                "pos_y": 3,
            },
            {
                "id": "CAM-001",
                "name": "검사 카메라 #1",
                "type": "camera",
                "status": "running",
                "pos_x": 25,
                "pos_y": 3,
            },
            {
                "id": "SRT-001",
                "name": "분류기 #1",
                "type": "sorter",
                "status": "running",
                "pos_x": 28,
                "pos_y": 3,
            },
            {
                "id": "AMR-001",
                "name": "AMR #1",
                "type": "amr",
                "status": "running",
                "pos_x": amr1_x,
                "pos_y": amr1_y,
                "battery": 78,
            },
            {
                "id": "AMR-002",
                "name": "AMR #2",
                "type": "amr",
                "status": "running",
                "pos_x": amr2_x,
                "pos_y": amr2_y,
                "battery": 64,
            },
            {
                "id": "AMR-003",
                "name": "AMR #3",
                "type": "amr",
                "status": "charging",
                "pos_x": amr3_x,
                "pos_y": amr3_y,
                "battery": 12,
            },
        ]

    def get_process_stages(self) -> list[dict[str, Any]] | None:
        data = self._get("/api/production/stages", mock_value=mock_data.PROCESS_STAGES)
        if isinstance(data, list):
            normalized = []
            for item in data:
                normalized.append(
                    {
                        "name": item.get("label", item.get("stage", "")),
                        "status": item.get("status", "-"),
                        "progress": item.get("progress", 0),
                        "started_at": item.get("start_time", "-") or "-",
                        "equipment": item.get("equipment_id", "-"),
                    }
                )
            return normalized
        return data

    def get_order_item_progress(self) -> list[dict[str, Any]]:
        """주문 → 제품 개당(item) 단위 실시간 공정 위치.

        반환 항목: order_id, product, item, stage
        stage 는 ['대기','주탕','탈형','후처리','검사','적재'] 중 하나.
        """
        data = self._get(
            "/api/production/order-item-progress",
            mock_value=mock_data.ORDER_ITEM_PROGRESS,
        )
        if isinstance(data, list):
            normalized = []
            for it in data:
                normalized.append(
                    {
                        "order_id": it.get("order_id", it.get("order", "")),
                        "product": it.get("product", it.get("product_name", "")),
                        "item": it.get("item", it.get("item_id", "")),
                        "stage": it.get("stage", it.get("current_stage", "대기")),
                    }
                )
            return normalized
        return []

    # ===== Production Scheduling (생산 계획) =====
    # Web에서 "생산 승인" 버튼을 누르면 in_production 상태 + ProductionJob 레코드 생성됨.
    # 그 이후 PyQt5 생산 계획 페이지에서 우선순위 계산/순서 조정/실제 착수를 수행한다.

    def get_production_jobs(self) -> list[dict[str, Any]]:
        """생산 작업 목록 조회 (웹에서 승인된 order로부터 생성된 ProductionJob들).

        Returns: ProductionJob 딕셔너리 리스트 (id, order_id, priority_score,
                 priority_rank, status, estimated_completion 등).
        """
        data = self._get("/api/production/schedule/jobs", mock_value=[])
        return data if isinstance(data, list) else []

    def calculate_priority(self, order_ids: list[str]) -> dict[str, Any]:
        """선택 주문들의 우선순위를 계산 (dry-run, DB 상태 변경 없음).

        Returns:
            {"results": [PriorityResult, ...]} 형식. 각 PriorityResult는
            order_id, total_score, rank, factors, recommendation_reason,
            delay_risk, ready_status, blocking_reasons 등 포함.

        Raises:
            requests.RequestException: 네트워크/서버 에러 (UI에서 잡아서 표시)
        """
        result = self._post(
            "/api/production/schedule/calculate",
            {"order_ids": order_ids},
        )
        return result if isinstance(result, dict) else {"results": []}

    def start_production_batch(self, order_ids: list[str]) -> list[dict[str, Any]]:
        """배치 큐 등록 — POST /api/production/schedule/start.

        2026-04-27: 이전 'start_production' 동명 메서드 버그 픽스. 의미상 라인
        투입(Item 생성)과 다르므로 메서드명 분리. 자세한 비교는 start_production_one 참조.

        backend 동작: ord_stat=MFG transition 만. Item/EquipTaskTxn 생성 안 함.
        실제 라인 투입은 운영 모니터링 페이지의 라인 투입 버튼이 별도로 호출.

        Returns:
            가상 ProductionJob shape 리스트 (id, order_id, started_at, ...).
            백엔드가 리스트가 아닌 응답을 주면 빈 리스트 반환.

        Raises:
            requests.RequestException: 네트워크/서버 에러.
        """
        result = self._post(
            "/api/production/schedule/start",
            {"order_ids": order_ids},
        )
        return result if isinstance(result, list) else []

    def create_priority_log(
        self,
        order_id: str,
        old_rank: int,
        new_rank: int,
        reason: str,
    ) -> dict[str, Any] | None:
        """우선순위 수동 변경 이력 기록."""
        return self._post(
            "/api/production/schedule/priority-log",
            {
                "order_id": order_id,
                "old_rank": old_rank,
                "new_rank": new_rank,
                "reason": reason,
            },
        )
