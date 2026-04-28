"""Logistics 도메인 mixin — 이송/창고/출고/AMR.

물류 페이지 + 적재 페이지 + AMR 카드.
"""

from __future__ import annotations

from typing import Any

from app import mock_data

from ._base import _normalize_rack_id, _normalize_rack_status


class LogisticsMixin:
    """이송 작업, 창고, 출고, AMR endpoints."""

    def get_transport_tasks(self) -> list[dict[str, Any]] | None:
        data = self._get("/api/logistics/tasks", mock_value=mock_data.TRANSPORT_TASKS)
        if isinstance(data, list):
            normalized: list[dict[str, Any]] = []
            for item in data:
                normalized.append(
                    {
                        "id": item.get("id", item.get("task_id", "")),
                        "type": item.get("type", item.get("task_type", "")),
                        "priority": item.get("priority", "normal"),
                        "from": item.get("from", item.get("source", item.get("from_location", ""))),
                        "to": item.get("to", item.get("destination", item.get("to_location", ""))),
                        "amr": item.get(
                            "amr", item.get("assigned_robot", item.get("robot_id", ""))
                        ),
                        "status": item.get("status", "-"),
                        "cargo": item.get("cargo", item.get("loaded_item", "")),
                    }
                )
            return normalized
        return data

    def get_warehouse_racks(self) -> list[dict[str, Any]]:
        data = self._get("/api/logistics/warehouse", mock_value=mock_data.WAREHOUSE_RACKS)
        if isinstance(data, list) and data:
            normalized: list[dict[str, Any]] = []
            for item in data:
                normalized.append(
                    {
                        "id": _normalize_rack_id(item),
                        "status": _normalize_rack_status(str(item.get("status", "empty"))),
                        "content": item.get(
                            "content", item.get("item_name", item.get("itemName", ""))
                        ),
                        "qty": item.get("qty", item.get("quantity", 0)),
                        "zone": item.get("zone", ""),
                        "rack_number": item.get("rack_number", item.get("rackNumber", "")),
                    }
                )
            return normalized
        return mock_data.WAREHOUSE_RACKS

    def get_outbound_orders(self) -> list[dict[str, Any]]:
        data = self._get("/api/logistics/outbound-orders", mock_value=mock_data.OUTBOUND_ORDERS)
        if isinstance(data, list) and data:
            normalized: list[dict[str, Any]] = []
            for item in data:
                normalized.append(
                    {
                        "id": item.get("id", item.get("order_id", "")),
                        "product": item.get("product", item.get("product_name", "")),
                        "qty": item.get("qty", item.get("quantity", 0)),
                        "customer": item.get("customer", item.get("destination", "")),
                        "policy": item.get("policy", "FIFO"),
                        "status": item.get("status", "pending"),
                    }
                )
            return normalized
        return mock_data.OUTBOUND_ORDERS

    def get_amr_status(self) -> list[dict[str, Any]] | None:
        # 우선 전용 엔드포인트 시도, 없으면 equipment 에서 amr 타입만 추출
        equipment = self._get("/api/production/equipment", mock_value=None)
        if isinstance(equipment, list):
            amrs = [e for e in equipment if e.get("type") == "amr"]
            if amrs:
                return [
                    {
                        "id": amr.get("id", ""),
                        "status": amr.get("status", "-"),
                        "battery": amr.get("battery", 0) or 0,
                        "location": amr.get("install_location", "-"),
                        "current_task": "-",
                    }
                    for amr in amrs
                ]
        # fallback
        return mock_data.AMR_STATUS if self._fallback else None
