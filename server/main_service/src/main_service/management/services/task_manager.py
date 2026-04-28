"""Task Manager — smartcast v2 기반 단건 생산 개시 (SPEC-C2 Iteration 3).

canonical 아키텍처: Interface POST /api/production/start 가 Management gRPC StartProduction
으로 proxy 되며, legacy PyQt schedule 페이지는 `order_ids=[...]` 로 동일 RPC 호출.

입력 형식 (StartProductionRequest dual-input):
- `ord_id` (smartcast Interface proxy 경로, 단건)
- `order_ids` (legacy PyQt schedule 경로, 다중 주문 시작)

동작:
- ord_id > 0 → smartcast v2 로직 단건 처리
- order_ids 비어있지 않음 → 각 원소를 int 로 변환해 smartcast v2 로직 반복

smartcast v2 트랜잭션 (Interface production.py:94 와 동일 경계):
    OrdStat(MFG) + Item(cur_stat='QUE', cur_res='RA1', equip_task_type='MM')
    + EquipTaskTxn(res_id='RA1', task_type='MM', txn_stat='QUE')
    단일 `db.commit()` 으로 atomic.

@MX:ANCHOR: SPEC-C2 Phase C-2 산출물. Management write 경로의 단일 진입점.
@MX:REASON: Interface proxy 와 legacy PyQt 가 모두 본 함수를 호출. 스키마/트랜잭션 규약 변경은 SPEC-C2 수정 후에만 가능.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass

from app.database import SessionLocal
from app.models import (
    EquipTaskTxn,
    Item,
    Ord,
    OrdStat,
    Pattern,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StartProductionResult:
    """단건 smartcast v2 생산 개시 결과 — proto StartProductionResult 와 1:1."""

    ord_id: int
    item_id: int
    equip_task_txn_id: int
    message: str


class TaskManagerError(ValueError):
    """TaskManager 도메인 오류 — gRPC INVALID_ARGUMENT 로 매핑."""


class TaskManager:
    """smartcast v2 ORM 기반 생산 개시."""

    def start_production_single(self, ord_id: int) -> StartProductionResult:
        """단일 발주의 smartcast v2 생산 개시.

        선행 조건:
            - ord_id 가 smartcast `ord` 테이블에 존재
            - `pattern` 테이블에 ord_id 키의 패턴 등록됨
        효과 (atomic):
            - OrdStat INSERT (ord_stat='MFG')
            - Item INSERT (cur_stat='QUE', cur_res='RA1', equip_task_type='MM')
            - EquipTaskTxn INSERT (res_id='RA1', task_type='MM', txn_stat='QUE')
        """
        if not ord_id or ord_id <= 0:
            raise TaskManagerError(f"invalid ord_id: {ord_id}")

        with SessionLocal() as db:
            ord_obj = db.get(Ord, ord_id)
            if ord_obj is None:
                raise TaskManagerError(f"ord_id={ord_id} not found")
            if db.get(Pattern, ord_id) is None:
                raise TaskManagerError(
                    f"pattern for ord_id={ord_id} not registered",
                )

            db.add(OrdStat(ord_id=ord_id, ord_stat="MFG"))

            new_item = Item(
                ord_id=ord_id,
                equip_task_type="MM",
                trans_task_type=None,
                cur_stat="QUE",
                cur_res="RA1",
            )
            db.add(new_item)
            db.flush()  # new_item.item_id 확보

            txn = EquipTaskTxn(
                res_id="RA1",
                task_type="MM",
                txn_stat="QUE",
                item_id=new_item.item_id,
            )
            db.add(txn)
            db.commit()

            db.refresh(new_item)
            db.refresh(txn)

            result = StartProductionResult(
                ord_id=ord_id,
                item_id=new_item.item_id,
                equip_task_txn_id=txn.txn_id,
                message="Production started: RA1/MM task queued.",
            )
            logger.info(
                "start_production_single: ord_id=%d item=%d txn=%d",
                ord_id,
                new_item.item_id,
                txn.txn_id,
            )
            return result

    def start_production_batch(self, order_ids: Iterable[str]) -> list[StartProductionResult]:
        """Legacy 다중 시작 (PyQt schedule 페이지 경로).

        order_ids 각 원소를 int 변환 → start_production_single 반복.
        변환 실패/존재하지 않음/패턴 미등록 시 해당 건 skip + warning.
        """
        results: list[StartProductionResult] = []
        for raw in order_ids:
            try:
                parsed = int(str(raw).strip())
            except ValueError:
                logger.warning("start_production_batch: invalid order_id=%r skip", raw)
                continue
            try:
                results.append(self.start_production_single(parsed))
            except TaskManagerError as exc:
                logger.warning(
                    "start_production_batch: ord_id=%d skip reason=%s",
                    parsed,
                    exc,
                )
        return results

    def list_items(
        self,
        order_id: str | None,
        stage: str | None,
        limit: int,
    ) -> list[Item]:
        """smartcast Item 목록 조회 (ListItems RPC 핸들러 용).

        Args:
            order_id: ord_id (int 문자열). None 이면 전체.
            stage: smartcast Item.cur_stat 필터. None 이면 전체.
            limit: 상한 (기본 100).
        """
        with SessionLocal() as db:
            q = db.query(Item)
            if order_id:
                try:
                    q = q.filter(Item.ord_id == int(order_id))
                except (TypeError, ValueError):
                    logger.warning("list_items: invalid order_id=%r — 필터 무시", order_id)
            if stage:
                q = q.filter(Item.cur_stat == stage)
            return q.order_by(Item.item_id.asc()).limit(limit or 100).all()
