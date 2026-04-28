"""Monitoring 도메인 mixin — dashboard/alerts/timeseries/charts.

대시보드 KPI/주간 차트, 알림, 시간별 생산량/온도/공정 파라미터 이력.
"""

from __future__ import annotations

from typing import Any

from app import mock_data


class MonitoringMixin:
    """대시보드 + 알림 + 시계열 endpoints."""

    # ===== Dashboard =====
    def get_dashboard_stats(self) -> dict[str, Any] | None:
        data = self._get("/api/dashboard/stats", mock_value=mock_data.DASHBOARD_STATS)
        if isinstance(data, dict) and self._fallback:
            # 백엔드에 없는 필드를 mock 값으로 보충
            for key, value in mock_data.DASHBOARD_STATS.items():
                data.setdefault(key, value)
        return data

    def get_dashboard_stats_v2(self) -> dict[str, Any] | None:
        """smartcast 대시보드 stats (timescaledb_enabled 포함)."""
        return self._get("/api/dashboard/stats", mock_value=None)

    def get_alerts(self) -> list[dict[str, Any]] | None:
        return self._get("/api/alerts", mock_value=mock_data.ALERTS)

    # ===== TimescaleDB v2 =====
    def get_hourly_production_v2(self, hours: int = 24) -> list[dict[str, Any]] | None:
        """시간대별 생산 카운트 (timescale 자동 분기)."""
        return self._get(f"/api/production/hourly?hours={hours}", mock_value=[])

    def get_err_log_trend(self, hours: int = 24) -> list[dict[str, Any]] | None:
        """err_log 시간대별 트렌드."""
        return self._get(f"/api/quality/trend?hours={hours}", mock_value=[])

    # ===== Charts (v0.2) =====
    def get_weekly_production(self) -> list[dict[str, Any]]:
        return (
            self._get("/api/production/weekly", mock_value=mock_data.WEEKLY_PRODUCTION)
            or mock_data.WEEKLY_PRODUCTION
        )

    def get_temperature_history(self) -> list[dict[str, Any]]:
        return (
            self._get("/api/production/temperature", mock_value=mock_data.TEMPERATURE_HISTORY)
            or mock_data.TEMPERATURE_HISTORY
        )

    def get_hourly_production(self) -> list[dict[str, Any]]:
        return (
            self._get("/api/production/hourly", mock_value=mock_data.HOURLY_PRODUCTION)
            or mock_data.HOURLY_PRODUCTION
        )

    def get_process_parameter_history(self) -> list[dict[str, Any]]:
        """공정별 파라미터 이력 (8공정 × 여러 지표)."""
        data = self._get(
            "/api/production/parameter-history",
            mock_value=mock_data.PROCESS_PARAM_HISTORY,
        )
        if isinstance(data, list) and data:
            return data  # type: ignore[return-value]
        return mock_data.PROCESS_PARAM_HISTORY

    def get_live_parameters(self) -> dict[str, Any]:
        """실시간 공정 파라미터 (온도/압력/각도/냉각 진행)."""
        data = self._get("/api/production/live", mock_value=mock_data.LIVE_PARAMETERS)
        if isinstance(data, dict):
            merged = dict(mock_data.LIVE_PARAMETERS)
            merged.update(data)
            return merged
        return mock_data.LIVE_PARAMETERS
