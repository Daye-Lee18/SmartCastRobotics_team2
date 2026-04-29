"""가상 카메라 뷰 - PASS/FAIL 오버레이 + 스캔라인 애니메이션.

실제 카메라 피드 대신 시뮬레이션 렌더.
Vision 시스템 결과에 따라 오버레이 색상과 텍스트 변경.
"""

from __future__ import annotations

from PyQt5.QtCore import QRectF, Qt, QTimer
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt5.QtWidgets import QFrame, QSizePolicy

RESULT_STYLE = {
    "pass": {"overlay": "#10b981", "label": "PASS", "border": "#059669"},
    "fail": {"overlay": "#ef4444", "label": "FAIL", "border": "#991b1b"},
    "checking": {"overlay": "#3b82f6", "label": "CHECKING", "border": "#1e40af"},
    "idle": {"overlay": "#9ca3af", "label": "STANDBY", "border": "#4b5563"},
}


class CameraLiveView(QFrame):
    """가상 카메라 라이브 뷰.

    - 스캔라인 60fps 애니메이션
    - PASS/FAIL 오버레이 박스
    - 신뢰도 표시
    - 검사 시각
    """

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("cameraView")
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._result = "checking"
        self._product_id = "-"
        self._confidence = 0.0
        self._inspected_at = "-"
        self._defect_type = ""
        # Stage A — 실제 Jetson 프레임 (있으면 시뮬레이션 대신 표시)
        self._pixmap: QPixmap | None = None
        self._frame_sequence: int = 0
        self._frame_received_at: str = ""

        # 스캔라인 애니메이션
        self._scan_y_ratio = 0.0
        self._scan_dir = 1
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60fps
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def set_result(
        self,
        result: str,
        product_id: str = "-",
        confidence: float = 0.0,
        inspected_at: str = "-",
        defect_type: str = "",
    ) -> None:
        self._result = result.lower() if result else "idle"
        self._product_id = product_id
        self._confidence = confidence
        self._inspected_at = inspected_at
        self._defect_type = defect_type
        self.update()

    def set_frame_bytes(
        self,
        data: bytes,
        encoding: str = "jpeg",
        sequence: int = 0,
        received_at: str = "",
    ) -> None:
        """Stage A — Jetson 실제 프레임 바이트를 설정.

        JPEG/PNG 바이트를 QPixmap 으로 디코딩해 보관. paintEvent 가 배경으로 그린다.
        data 가 비어있거나 디코딩 실패 시 pixmap 을 None 으로 돌려 시뮬레이션 모드.
        """
        if not data:
            self._pixmap = None
            self._frame_sequence = 0
            self._frame_received_at = ""
            self.update()
            return
        img = QImage.fromData(data, encoding.upper() if encoding else "JPEG")
        if img.isNull():
            self._pixmap = None
        else:
            self._pixmap = QPixmap.fromImage(img)
        self._frame_sequence = int(sequence)
        self._frame_received_at = received_at or ""
        self.update()

    def _tick(self) -> None:
        self._scan_y_ratio += 0.015 * self._scan_dir
        if self._scan_y_ratio >= 1.0:
            self._scan_y_ratio = 1.0
            self._scan_dir = -1
        elif self._scan_y_ratio <= 0.0:
            self._scan_y_ratio = 0.0
            self._scan_dir = 1
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802, ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        rect = QRectF(0, 0, w, h)

        # 배경: 어두운 그라디언트
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0.0, QColor("#0f172a"))
        bg.setColorAt(1.0, QColor("#1e293b"))
        painter.fillRect(rect, QBrush(bg))

        # Stage A — 실제 프레임 우선 렌더 (있으면 시뮬레이션 실루엣 생략)
        if self._pixmap is not None and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                int(w),
                int(h),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            px = (w - scaled.width()) / 2
            py = (h - scaled.height()) / 2
            painter.drawPixmap(int(px), int(py), scaled)
            # 코너 브래킷/스캔라인/결과 오버레이는 그대로 유지 — 아래로 진행
            self._draw_overlay(painter, w, h)
            painter.end()
            return

        # 중앙에 가상 제품 실루엣 (원형)
        cx, cy = w / 2, h / 2
        r = min(w, h) * 0.22
        product_rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)

        grad = QRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 1.4)
        grad.setColorAt(0.0, QColor("#6b7280"))
        grad.setColorAt(1.0, QColor("#374151"))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor("#1f2937"), 2))
        painter.drawEllipse(product_rect)

        # 하이라이트
        hl = QRadialGradient(cx - r * 0.4, cy - r * 0.4, r * 0.4)
        hl.setColorAt(0.0, QColor(255, 255, 255, 80))
        hl.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(hl))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(cx - r * 0.7, cy - r * 0.7, r * 0.6, r * 0.6))

        # 격자 오버레이 (검사 영역)
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1, Qt.DotLine))
        for i in range(1, 8):
            px = w * i / 8
            py = h * i / 8
            painter.drawLine(int(px), 0, int(px), h)
            painter.drawLine(0, int(py), w, int(py))

        # 스캔라인 (긴 녹색 가로줄)
        scan_y = int(h * self._scan_y_ratio)
        scan_grad = QLinearGradient(0, scan_y - 6, 0, scan_y + 6)
        scan_grad.setColorAt(0.0, QColor(34, 197, 94, 0))
        scan_grad.setColorAt(0.5, QColor(34, 197, 94, 180))
        scan_grad.setColorAt(1.0, QColor(34, 197, 94, 0))
        painter.fillRect(QRectF(0, scan_y - 6, w, 12), QBrush(scan_grad))

        # 코너 브래킷 (카메라 ROI 표시)
        style = RESULT_STYLE.get(self._result, RESULT_STYLE["idle"])
        pen = QPen(QColor(style["overlay"]), 3)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        inset = 24
        clen = 22
        # top-left
        painter.drawLine(inset, inset, inset + clen, inset)
        painter.drawLine(inset, inset, inset, inset + clen)
        # top-right
        painter.drawLine(w - inset, inset, w - inset - clen, inset)
        painter.drawLine(w - inset, inset, w - inset, inset + clen)
        # bottom-left
        painter.drawLine(inset, h - inset, inset + clen, h - inset)
        painter.drawLine(inset, h - inset, inset, h - inset - clen)
        # bottom-right
        painter.drawLine(w - inset, h - inset, w - inset - clen, h - inset)
        painter.drawLine(w - inset, h - inset, w - inset, h - inset - clen)

        # 결과 라벨 (우상단)
        label = style["label"]
        label_w = 88
        label_h = 30
        label_x = w - label_w - 16
        label_y = 16
        painter.setBrush(QBrush(QColor(style["overlay"])))
        painter.setPen(QPen(QColor(style["border"]), 2))
        painter.drawRoundedRect(QRectF(label_x, label_y, label_w, label_h), 6, 6)
        painter.setPen(QPen(QColor("#ffffff")))
        painter.setFont(QFont("Helvetica Neue", 12, QFont.Bold))
        painter.drawText(
            QRectF(label_x, label_y, label_w, label_h),
            Qt.AlignCenter,
            label,
        )

        # 하단 정보 (반투명 검정 바)
        info_h = 54
        painter.fillRect(QRectF(0, h - info_h, w, info_h), QBrush(QColor(0, 0, 0, 160)))
        painter.setPen(QPen(QColor("#e5e7eb")))
        painter.setFont(QFont("Helvetica Neue", 10))
        painter.drawText(
            QRectF(16, h - info_h + 6, w - 32, 16),
            Qt.AlignLeft,
            f"제품: {self._product_id}",
        )
        conf_text = f"신뢰도: {self._confidence:.1f}%"
        painter.drawText(
            QRectF(16, h - info_h + 22, w - 32, 16),
            Qt.AlignLeft,
            conf_text,
        )
        painter.drawText(
            QRectF(16, h - info_h + 38, w - 32, 16),
            Qt.AlignLeft,
            f"시각: {self._inspected_at}",
        )

        # 불량 유형 (FAIL 일 때만)
        if self._result == "fail" and self._defect_type:
            painter.setPen(QPen(QColor("#fca5a5")))
            painter.setFont(QFont("Helvetica Neue", 10, QFont.Bold))
            painter.drawText(
                QRectF(16, h - info_h + 22, w - 32, 16),
                Qt.AlignRight,
                f"⚠ {self._defect_type}",
            )

        painter.end()

    def _draw_overlay(self, painter: QPainter, w: int, h: int) -> None:
        """실제 프레임 위에 브래킷·PASS/FAIL 라벨·하단 정보 오버레이."""
        style = RESULT_STYLE.get(self._result, RESULT_STYLE["idle"])
        # 코너 브래킷
        pen = QPen(QColor(style["overlay"]), 3)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        inset, clen = 24, 22
        painter.drawLine(inset, inset, inset + clen, inset)
        painter.drawLine(inset, inset, inset, inset + clen)
        painter.drawLine(w - inset, inset, w - inset - clen, inset)
        painter.drawLine(w - inset, inset, w - inset, inset + clen)
        painter.drawLine(inset, h - inset, inset + clen, h - inset)
        painter.drawLine(inset, h - inset, inset, h - inset - clen)
        painter.drawLine(w - inset, h - inset, w - inset - clen, h - inset)
        painter.drawLine(w - inset, h - inset, w - inset, h - inset - clen)

        # 결과 라벨 (우상단)
        label_w, label_h = 88, 30
        label_x, label_y = w - label_w - 16, 16
        painter.setBrush(QBrush(QColor(style["overlay"])))
        painter.setPen(QPen(QColor(style["border"]), 2))
        painter.drawRoundedRect(QRectF(label_x, label_y, label_w, label_h), 6, 6)
        painter.setPen(QPen(QColor("#ffffff")))
        painter.setFont(QFont("Helvetica Neue", 12, QFont.Bold))
        painter.drawText(QRectF(label_x, label_y, label_w, label_h), Qt.AlignCenter, style["label"])

        # 하단 정보 바
        info_h = 54
        painter.fillRect(QRectF(0, h - info_h, w, info_h), QBrush(QColor(0, 0, 0, 160)))
        painter.setPen(QPen(QColor("#e5e7eb")))
        painter.setFont(QFont("Helvetica Neue", 10))
        painter.drawText(
            QRectF(16, h - info_h + 6, w - 32, 16),
            Qt.AlignLeft,
            f"카메라: LIVE · seq {self._frame_sequence}",
        )
        painter.drawText(
            QRectF(16, h - info_h + 22, w - 32, 16),
            Qt.AlignLeft,
            f"신뢰도: {self._confidence:.1f}%",
        )
        painter.drawText(
            QRectF(16, h - info_h + 38, w - 32, 16),
            Qt.AlignLeft,
            f"수신: {self._frame_received_at or '-'}",
        )


__all__ = ["CameraLiveView"]
