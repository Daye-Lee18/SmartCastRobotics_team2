"""Orders 도메인 mixin — 발주/패턴/최근주문/승인주문.

Pink GUI #1, #3 (패턴 등록 — 자동 매핑 후 운영자 수동 호출 거의 없음).
"""

from __future__ import annotations

from typing import Any

from app import mock_data


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

        backend `/api/production/schedule/jobs` 가 이미 다음 조건으로 필터링한다.
        - ord_stat == MFG
        - 아직 item_stat / equip_task_txn 이 없는 큐 후보만

        Returns: 정규화된 주문 리스트 (id, company_name, total_amount,
                 requested_delivery, status 등).
        """
        data = self._get("/api/production/schedule/jobs", mock_value=[])
        if not isinstance(data, list):
            return []

        result: list[dict[str, Any]] = []
        for item in data:
            ord_id = item.get("order_id", item.get("orderId", item.get("id", "")))
            result.append(
                {
                    "id": str(ord_id).replace("ord_", ""),
                    "company_name": item.get("company_name") or item.get("companyName") or "-",
                    "customer_name": item.get("customer_name") or item.get("customerName") or "-",
                    "total_amount": item.get("total_amount") or item.get("totalAmount") or 0,
                    "requested_delivery": item.get("requested_delivery") or item.get("requestedDelivery") or "",
                    "confirmed_delivery": item.get("confirmed_delivery") or item.get("confirmedDelivery") or "",
                    "created_at": item.get("created_at") or item.get("createdAt") or "",
                    "status": "in_production",
                }
            )
        return result
