"""Orders 도메인 mixin — 발주/패턴/최근주문/승인주문.

Pink GUI #1, #3 (패턴 등록 — 자동 매핑 후 운영자 수동 호출 거의 없음).
"""

from __future__ import annotations

from typing import Any

from app import mock_data

from ._base import _ORD_STAT_TO_LEGACY_STATUS


class OrdersMixin:
    """발주 및 패턴 등록 endpoints."""

    # ===== smartcast schema =====
    def get_smartcast_orders(self) -> list[dict[str, Any]] | None:
        """모든 발주 (관리자용)."""
        return self._get("/api/orders", mock_value=[])

    def lookup_orders_by_email(self, email: str) -> list[dict[str, Any]] | None:
        """Pink GUI #1 — 이메일로 발주 조회 (없으면 빈 배열)."""
        from urllib.parse import quote

        return self._get(f"/api/orders/lookup?email={quote(email)}", mock_value=[])

    def register_pattern(self, ord_id: int, ptn_loc: int) -> dict[str, Any] | None:
        """Pink GUI #3 — 패턴 위치 등록 (1-6).

        2026-04-27: 자동 매핑 (R/S/O→1/2/3) 도입 후 운영자 수동 호출 빈도 ↓.
        """
        return self._post("/api/production/patterns", {"ptn_id": ord_id, "ptn_loc": ptn_loc})

    def get_patterns(self) -> list[dict[str, Any]] | None:
        return self._get("/api/production/patterns", mock_value=[])

    def get_recent_orders(self) -> list[dict[str, Any]]:
        data = self._get("/api/orders", mock_value=mock_data.RECENT_ORDERS)
        if isinstance(data, list) and data:
            normalized: list[dict[str, Any]] = []
            for item in data[:10]:
                normalized.append(
                    {
                        "id": item.get("id", item.get("order_number", "")),
                        "customer": item.get("customer", item.get("customer_name", "")),
                        "amount": item.get("amount", item.get("total_price", 0)),
                        "due_date": item.get("due_date", item.get("delivery_date", "")),
                        "status": item.get("status", ""),
                    }
                )
            return normalized
        return mock_data.RECENT_ORDERS

    def get_approved_and_running_orders(self) -> list[dict[str, Any]]:
        """생산 계획 화면에서 볼 주문 목록.

        - approved: 생산 승인되지 않은 대기 주문 (참고용)
        - in_production: 승인 완료 → ProductionJob 존재, 우선순위 계산 대상

        Returns: 정규화된 주문 리스트 (id, company_name, total_amount,
                 requested_delivery, status 등).
        """
        data = self._get("/api/orders", mock_value=[])
        if not isinstance(data, list):
            return []

        target_statuses = {"approved", "in_production"}
        result: list[dict[str, Any]] = []
        for item in data:
            raw_status = (
                item.get("status") or item.get("latest_stat") or item.get("latestStat") or ""
            )
            status = str(raw_status).lower()
            if str(raw_status).upper() in _ORD_STAT_TO_LEGACY_STATUS:
                status = _ORD_STAT_TO_LEGACY_STATUS[str(raw_status).upper()]
            if status not in target_statuses:
                continue
            detail = item.get("detail") if isinstance(item.get("detail"), dict) else {}
            ord_id = item.get("ord_id", item.get("ordId", item.get("id", "")))
            result.append(
                {
                    # Management gRPC StartProduction expects numeric smartcast ord_id strings.
                    "id": str(ord_id).replace("ord_", ""),
                    "company_name": (
                        item.get("company_name")
                        or item.get("companyName")
                        or item.get("user_co_nm")
                        or item.get("userCoNm")
                        or "-"
                    ),
                    "customer_name": (
                        item.get("customer_name")
                        or item.get("customerName")
                        or item.get("user_nm")
                        or item.get("userNm")
                        or "-"
                    ),
                    "total_amount": (
                        item.get("total_amount")
                        or item.get("totalAmount")
                        or detail.get("final_price")
                        or detail.get("finalPrice")
                        or 0
                    ),
                    "requested_delivery": (
                        item.get("requested_delivery")
                        or item.get("requestedDelivery")
                        or detail.get("due_date")
                        or detail.get("dueDate")
                        or ""
                    ),
                    "confirmed_delivery": (
                        item.get("confirmed_delivery")
                        or item.get("confirmedDelivery")
                        or detail.get("due_date")
                        or detail.get("dueDate")
                        or ""
                    ),
                    "created_at": item.get("created_at") or item.get("createdAt") or "",
                    "status": status,
                }
            )
        return result
