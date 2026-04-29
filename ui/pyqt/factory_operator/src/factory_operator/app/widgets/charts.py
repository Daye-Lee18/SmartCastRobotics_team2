"""PyQtChart 기반 재사용 가능한 차트 위젯.

Next.js Recharts 컴포넌트를 PyQt5 로 재구현한 6종:
  1. WeeklyProductionChart  - 주간 생산 추이 (Line+Area)
  2. TemperatureChart       - 용해로 온도 실시간 (Line+Area)
  3. HourlyProductionChart  - 시간별 생산량/불량 (Bar, 스택)
  4. DefectRateChart        - 불량률 추이 (Line)
  5. DefectTypeDistChart    - 불량 유형 분포 (Pie)
  6. ProductionVsDefectsChart - 생산량 vs 불량 (Bar + Line 듀얼축)

모든 차트는 :meth:`update_data` 로 실시간 갱신 가능.
"""

from __future__ import annotations

from typing import Any

from PyQt5.QtChart import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QLineSeries,
    QPieSeries,
    QValueAxis,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QWidget

# 공통 색상 팔레트 (Tailwind 기반)
PALETTE = {
    "primary": "#3b82f6",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "purple": "#a855f7",
    "cyan": "#06b6d4",
    "pink": "#ec4899",
    "gray": "#6b7280",
}

CHART_BG = "#ffffff"
GRID_COLOR = "#e5e7eb"
TEXT_COLOR = "#374151"
TITLE_COLOR = "#111827"


def _styled_chart(title: str = "") -> QChart:
    """기본 스타일이 적용된 QChart 반환."""
    chart = QChart()
    if title:
        chart.setTitle(title)
        chart.setTitleBrush(QBrush(QColor(TITLE_COLOR)))
        title_font = QFont("Helvetica Neue", 11, QFont.Bold)
        chart.setTitleFont(title_font)
    chart.setBackgroundBrush(QBrush(QColor(CHART_BG)))
    chart.setBackgroundRoundness(8)
    chart.setAnimationOptions(QChart.SeriesAnimations)
    chart.legend().setLabelColor(QColor(TEXT_COLOR))
    chart.legend().setFont(QFont("Helvetica Neue", 9))
    chart.setMargins(chart.margins())
    return chart


def _styled_axis_x(axis, labels: list[str] | None = None) -> None:
    axis.setLabelsColor(QColor(TEXT_COLOR))
    axis.setLabelsFont(QFont("Helvetica Neue", 8))
    axis.setGridLineColor(QColor(GRID_COLOR))
    axis.setLinePen(QPen(QColor(GRID_COLOR), 1))
    if labels is not None and isinstance(axis, QBarCategoryAxis):
        axis.append(labels)


def _styled_axis_y(axis) -> None:
    axis.setLabelsColor(QColor(TEXT_COLOR))
    axis.setLabelsFont(QFont("Helvetica Neue", 8))
    axis.setGridLineColor(QColor(GRID_COLOR))
    axis.setLinePen(QPen(QColor(GRID_COLOR), 1))


class BaseChartWidget(QWidget):
    """모든 차트의 공통 컨테이너 (프레임 + 레이아웃)."""

    def __init__(self, title: str = "", height: int = 240) -> None:
        super().__init__()
        self.setObjectName("chartCard")
        self.setMinimumHeight(height)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._chart = _styled_chart(title)
        self._view = QChartView(self._chart)
        self._view.setRenderHint(QPainter.Antialiasing)
        self._view.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self._view)

    def chart(self) -> QChart:
        return self._chart


# ============================================================
# 1. Weekly Production Chart (Line)
# ============================================================
class WeeklyProductionChart(BaseChartWidget):
    """주간 생산 추이 — 생산량 + 불량률 라인 차트."""

    def __init__(self) -> None:
        super().__init__("주간 생산 추이")
        self._series_prod = QLineSeries()
        self._series_prod.setName("생산량 (개)")
        pen = QPen(QColor(PALETTE["primary"]))
        pen.setWidth(3)
        self._series_prod.setPen(pen)

        self._series_defect = QLineSeries()
        self._series_defect.setName("불량률 (%)")
        dpen = QPen(QColor(PALETTE["danger"]))
        dpen.setWidth(2)
        dpen.setStyle(Qt.DashLine)
        self._series_defect.setPen(dpen)

        self._chart.addSeries(self._series_prod)
        self._chart.addSeries(self._series_defect)

        self._axis_x = QBarCategoryAxis()
        self._chart.addAxis(self._axis_x, Qt.AlignBottom)
        self._series_prod.attachAxis(self._axis_x)
        self._series_defect.attachAxis(self._axis_x)
        _styled_axis_x(self._axis_x)

        self._axis_y_left = QValueAxis()
        self._axis_y_left.setTitleText("생산량")
        self._chart.addAxis(self._axis_y_left, Qt.AlignLeft)
        self._series_prod.attachAxis(self._axis_y_left)
        _styled_axis_y(self._axis_y_left)

        self._axis_y_right = QValueAxis()
        self._axis_y_right.setTitleText("불량률 (%)")
        self._chart.addAxis(self._axis_y_right, Qt.AlignRight)
        self._series_defect.attachAxis(self._axis_y_right)
        _styled_axis_y(self._axis_y_right)

    def update_data(self, data: list[dict[str, Any]]) -> None:
        """data: [{'day':'월','production':120,'defect_rate':2.5}, ...]"""
        self._series_prod.clear()
        self._series_defect.clear()

        labels: list[str] = []
        max_prod = 1.0
        max_def = 1.0
        for idx, row in enumerate(data):
            labels.append(str(row.get("day", f"D{idx}")))
            prod = float(row.get("production", 0))
            defect = float(row.get("defect_rate", 0))
            self._series_prod.append(idx, prod)
            self._series_defect.append(idx, defect)
            max_prod = max(max_prod, prod)
            max_def = max(max_def, defect)

        self._axis_x.clear()
        self._axis_x.append(labels)
        self._axis_y_left.setRange(0, max_prod * 1.15)
        self._axis_y_right.setRange(0, max(max_def * 1.3, 5))


# ============================================================
# 2. Temperature Chart (Line)
# ============================================================
class TemperatureChart(BaseChartWidget):
    """용해로 온도 실시간 — 현재 vs 목표."""

    def __init__(self) -> None:
        super().__init__("용해로 온도")
        self._actual = QLineSeries()
        self._actual.setName("현재 온도 (°C)")
        ap = QPen(QColor(PALETTE["danger"]))
        ap.setWidth(3)
        self._actual.setPen(ap)

        self._target = QLineSeries()
        self._target.setName("목표 온도 (°C)")
        tp = QPen(QColor(PALETTE["gray"]))
        tp.setWidth(2)
        tp.setStyle(Qt.DashLine)
        self._target.setPen(tp)

        self._chart.addSeries(self._actual)
        self._chart.addSeries(self._target)

        self._axis_x = QValueAxis()
        self._axis_x.setTitleText("시간 (분)")
        self._chart.addAxis(self._axis_x, Qt.AlignBottom)
        self._actual.attachAxis(self._axis_x)
        self._target.attachAxis(self._axis_x)
        _styled_axis_y(self._axis_x)

        self._axis_y = QValueAxis()
        self._axis_y.setTitleText("온도 (°C)")
        self._chart.addAxis(self._axis_y, Qt.AlignLeft)
        self._actual.attachAxis(self._axis_y)
        self._target.attachAxis(self._axis_y)
        _styled_axis_y(self._axis_y)

    def update_data(self, data: list[dict[str, Any]]) -> None:
        """data: [{'minute':0,'temperature':25,'target':1450}, ...]"""
        self._actual.clear()
        self._target.clear()

        min_x = 0.0
        max_x = 1.0
        max_y = 100.0
        for row in data:
            m = float(row.get("minute", 0))
            t = float(row.get("temperature", 0))
            tg = float(row.get("target", 1450))
            self._actual.append(m, t)
            self._target.append(m, tg)
            max_x = max(max_x, m)
            max_y = max(max_y, t, tg)

        self._axis_x.setRange(min_x, max_x)
        self._axis_y.setRange(0, max_y * 1.1)


# ============================================================
# 3. Hourly Production Chart (Bar stacked)
# ============================================================
class HourlyProductionChart(BaseChartWidget):
    """시간별 생산량/불량 스택 바 차트."""

    def __init__(self) -> None:
        super().__init__("시간별 생산량 / 불량")

        self._good_set = QBarSet("양품")
        self._good_set.setColor(QColor(PALETTE["success"]))
        self._bad_set = QBarSet("불량")
        self._bad_set.setColor(QColor(PALETTE["danger"]))

        self._series = QBarSeries()
        self._series.append(self._good_set)
        self._series.append(self._bad_set)
        self._chart.addSeries(self._series)

        self._axis_x = QBarCategoryAxis()
        self._chart.addAxis(self._axis_x, Qt.AlignBottom)
        self._series.attachAxis(self._axis_x)
        _styled_axis_x(self._axis_x)

        self._axis_y = QValueAxis()
        self._axis_y.setTitleText("수량")
        self._chart.addAxis(self._axis_y, Qt.AlignLeft)
        self._series.attachAxis(self._axis_y)
        _styled_axis_y(self._axis_y)

    def update_data(self, data: list[dict[str, Any]]) -> None:
        """data: [{'hour':'09:00','good':45,'bad':2}, ...]"""
        # QBarSet 은 clear 메서드가 없어서 재생성
        self._series.remove(self._good_set)
        self._series.remove(self._bad_set)

        self._good_set = QBarSet("양품")
        self._good_set.setColor(QColor(PALETTE["success"]))
        self._bad_set = QBarSet("불량")
        self._bad_set.setColor(QColor(PALETTE["danger"]))

        labels: list[str] = []
        max_y = 1.0
        for row in data:
            labels.append(str(row.get("hour", "")))
            good = int(row.get("good", 0))
            bad = int(row.get("bad", 0))
            self._good_set.append(good)
            self._bad_set.append(bad)
            max_y = max(max_y, good + bad)

        self._series.append(self._good_set)
        self._series.append(self._bad_set)

        self._axis_x.clear()
        self._axis_x.append(labels)
        self._axis_y.setRange(0, max_y * 1.2)


# ============================================================
# 4. Defect Rate Chart (Line)
# ============================================================
class DefectRateChart(BaseChartWidget):
    """불량률 추이 라인 차트."""

    def __init__(self) -> None:
        super().__init__("불량률 추이")
        self._series = QLineSeries()
        self._series.setName("불량률 (%)")
        pen = QPen(QColor(PALETTE["danger"]))
        pen.setWidth(3)
        self._series.setPen(pen)
        self._chart.addSeries(self._series)

        self._axis_x = QBarCategoryAxis()
        self._chart.addAxis(self._axis_x, Qt.AlignBottom)
        self._series.attachAxis(self._axis_x)
        _styled_axis_x(self._axis_x)

        self._axis_y = QValueAxis()
        self._axis_y.setTitleText("불량률 (%)")
        self._chart.addAxis(self._axis_y, Qt.AlignLeft)
        self._series.attachAxis(self._axis_y)
        _styled_axis_y(self._axis_y)

    def update_data(self, data: list[dict[str, Any]]) -> None:
        """data: [{'label':'월','rate':2.5}, ...]"""
        self._series.clear()
        labels: list[str] = []
        max_y = 5.0
        for idx, row in enumerate(data):
            labels.append(str(row.get("label", "")))
            rate = float(row.get("rate", 0))
            self._series.append(idx, rate)
            max_y = max(max_y, rate)
        self._axis_x.clear()
        self._axis_x.append(labels)
        self._axis_y.setRange(0, max_y * 1.3)


# ============================================================
# 5. Defect Type Distribution (Pie)
# ============================================================
class DefectTypeDistChart(BaseChartWidget):
    """불량 유형 분포 파이 차트."""

    def __init__(self) -> None:
        super().__init__("불량 유형 분포")
        self._series = QPieSeries()
        self._series.setHoleSize(0.4)
        self._chart.addSeries(self._series)

    def update_data(self, data: list[dict[str, Any]]) -> None:
        """data: [{'type':'기공','count':12}, ...]"""
        self._series.clear()
        colors = [
            PALETTE["danger"],
            PALETTE["warning"],
            PALETTE["purple"],
            PALETTE["primary"],
            PALETTE["cyan"],
            PALETTE["pink"],
        ]
        for idx, row in enumerate(data):
            label = str(row.get("type", ""))
            count = int(row.get("count", 0))
            slice_ = self._series.append(f"{label} ({count})", count)
            slice_.setBrush(QBrush(QColor(colors[idx % len(colors)])))
            slice_.setLabelVisible(True)
            slice_.setLabelColor(QColor(TEXT_COLOR))
            slice_.setLabelFont(QFont("Helvetica Neue", 9))


# ============================================================
# 6. Production vs Defects (Bar + Line dual axis)
# ============================================================
class ProductionVsDefectsChart(BaseChartWidget):
    """생산량 바 + 불량률 라인 (듀얼 축)."""

    def __init__(self) -> None:
        super().__init__("생산량 vs 불량률")

        self._prod_set = QBarSet("생산량")
        self._prod_set.setColor(QColor(PALETTE["primary"]))
        self._bar_series = QBarSeries()
        self._bar_series.append(self._prod_set)
        self._chart.addSeries(self._bar_series)

        self._line_series = QLineSeries()
        self._line_series.setName("불량률 (%)")
        lp = QPen(QColor(PALETTE["danger"]))
        lp.setWidth(3)
        self._line_series.setPen(lp)
        self._chart.addSeries(self._line_series)

        self._axis_x = QBarCategoryAxis()
        self._chart.addAxis(self._axis_x, Qt.AlignBottom)
        self._bar_series.attachAxis(self._axis_x)
        self._line_series.attachAxis(self._axis_x)
        _styled_axis_x(self._axis_x)

        self._axis_y_left = QValueAxis()
        self._axis_y_left.setTitleText("생산량")
        self._chart.addAxis(self._axis_y_left, Qt.AlignLeft)
        self._bar_series.attachAxis(self._axis_y_left)
        _styled_axis_y(self._axis_y_left)

        self._axis_y_right = QValueAxis()
        self._axis_y_right.setTitleText("불량률 (%)")
        self._chart.addAxis(self._axis_y_right, Qt.AlignRight)
        self._line_series.attachAxis(self._axis_y_right)
        _styled_axis_y(self._axis_y_right)

    def update_data(self, data: list[dict[str, Any]]) -> None:
        """data: [{'label':'09시','production':45,'defect_rate':2.1}, ...]"""
        self._bar_series.remove(self._prod_set)
        self._prod_set = QBarSet("생산량")
        self._prod_set.setColor(QColor(PALETTE["primary"]))
        self._line_series.clear()

        labels: list[str] = []
        max_prod = 1.0
        max_def = 1.0
        for idx, row in enumerate(data):
            labels.append(str(row.get("label", "")))
            prod = float(row.get("production", 0))
            rate = float(row.get("defect_rate", 0))
            self._prod_set.append(prod)
            self._line_series.append(idx, rate)
            max_prod = max(max_prod, prod)
            max_def = max(max_def, rate)

        self._bar_series.append(self._prod_set)
        self._axis_x.clear()
        self._axis_x.append(labels)
        self._axis_y_left.setRange(0, max_prod * 1.2)
        self._axis_y_right.setRange(0, max(max_def * 1.5, 5))


__all__ = [
    "WeeklyProductionChart",
    "TemperatureChart",
    "HourlyProductionChart",
    "DefectRateChart",
    "DefectTypeDistChart",
    "ProductionVsDefectsChart",
    "BaseChartWidget",
    "PALETTE",
]
