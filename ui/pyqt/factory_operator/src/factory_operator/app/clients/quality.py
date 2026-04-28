"""Quality 도메인 mixin — 검사/sorter/vision/defect/standards.

Pink GUI #6 (검사 요약), 품질 페이지의 차트/표.
"""

from __future__ import annotations

from typing import Any

from app import mock_data


class QualityMixin:
    """검사 + 시각화 endpoints."""

    def get_inspection_summary(self) -> list[dict[str, Any]] | None:
        """Pink GUI #6 — 발주별 GP/DP/미검사 카운트."""
        return self._get("/api/quality/summary", mock_value=[])

    def complete_inspection(self, txn_id: int, result: bool) -> dict[str, Any]:
        """POST /api/quality/inspections/{txn_id}/result?result=<bool>.

        result=True → GP (양품), False → DP (불량). insp_task_txn SUCC + end_at + item.is_defective.
        """
        path = f"/api/quality/inspections/{txn_id}/result?result={'true' if result else 'false'}"
        rsp = self._post(path, payload={})
        return rsp if isinstance(rsp, dict) else {}

    def get_inspection_tasks(self) -> list[dict[str, Any]]:
        """GET /api/quality/inspections — insp_task_txn 목록 (PROC 포함)."""
        data = self._get("/api/quality/inspections", mock_value=[])
        return data if isinstance(data, list) else []

    def get_quality_inspections(self) -> list[dict[str, Any]] | None:
        data = self._get("/api/quality/inspections", mock_value=mock_data.INSPECTIONS)
        if isinstance(data, list):
            normalized = []
            for item in data:
                normalized.append(
                    {
                        "inspected_at": item.get("inspected_at", item.get("timestamp", "")),
                        "product": item.get("product", item.get("product_name", "")),
                        "result": str(item.get("result", "")).upper(),
                        "defect_type": item.get("defect_type", "") or "",
                        "inspector": item.get("inspector", item.get("inspected_by", "")),
                        "note": item.get("note", item.get("comment", "")) or "",
                    }
                )
            return normalized
        return data

    def get_defect_stats(self) -> dict[str, Any] | None:
        data = self._get("/api/quality/stats", mock_value=mock_data.QUALITY_STATS)
        if isinstance(data, dict) and self._fallback:
            for key, value in mock_data.QUALITY_STATS.items():
                data.setdefault(key, value)
        return data

    def get_defect_rate_trend(self) -> list[dict[str, Any]]:
        return (
            self._get("/api/quality/trend", mock_value=mock_data.DEFECT_RATE_TREND)
            or mock_data.DEFECT_RATE_TREND
        )

    def get_defect_type_dist(self) -> list[dict[str, Any]]:
        return (
            self._get("/api/quality/defect-types", mock_value=mock_data.DEFECT_TYPE_DIST)
            or mock_data.DEFECT_TYPE_DIST
        )

    def get_production_vs_defects(self) -> list[dict[str, Any]]:
        return (
            self._get("/api/quality/vs-defects", mock_value=mock_data.PRODUCTION_VS_DEFECTS)
            or mock_data.PRODUCTION_VS_DEFECTS
        )

    def get_vision_feed(self) -> dict[str, Any]:
        data = self._get("/api/quality/vision-feed", mock_value=mock_data.VISION_FEED)
        if isinstance(data, dict) and data:
            merged = dict(mock_data.VISION_FEED)
            merged.update(data)
            return merged
        return mock_data.VISION_FEED

    def get_sorter_state(self) -> dict[str, Any]:
        data = self._get("/api/quality/sorter", mock_value=mock_data.SORTER_STATE)
        if isinstance(data, dict) and data:
            merged = dict(mock_data.SORTER_STATE)
            merged.update(data)
            return merged
        return mock_data.SORTER_STATE

    def get_inspection_standards(self) -> list[dict[str, Any]]:
        data = self._get("/api/quality/standards", mock_value=mock_data.INSPECTION_STANDARDS)
        if isinstance(data, list) and data:
            normalized: list[dict[str, Any]] = []
            for item in data:
                normalized.append(
                    {
                        "product": item.get("product", item.get("product_name", "")),
                        "target": item.get("target", item.get("target_dimension", "-")),
                        "tolerance": item.get("tolerance", item.get("tolerance_range", "-")),
                        "threshold": item.get("threshold", item.get("decision_threshold", "-")),
                    }
                )
            return normalized
        return mock_data.INSPECTION_STANDARDS
