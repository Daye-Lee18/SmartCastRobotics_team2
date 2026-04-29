#!/usr/bin/env python3
"""주물공장 PyQt5 모니터링 앱 진입점.

실행:
    cd monitoring
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    python main.py

환경 변수:
    CASTING_API_HOST, CASTING_API_PORT     (기본: 192.168.0.16:8000) — api_client 레거시 (Phase A-2 에서 제거 예정)
    MANAGEMENT_GRPC_HOST, MANAGEMENT_GRPC_PORT  (기본: localhost:50051) — V6 canonical Management 직결
"""

from __future__ import annotations

import logging
import os
import sys

from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import QApplication

# monitoring/ 를 sys.path 에 추가해서 app.* import 가능하게
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from config import APP_NAME  # noqa: E402

from app.main_window import MainWindow  # noqa: E402
from app.styles import ThemeManager  # noqa: E402


def _apply_korean_font(app: QApplication) -> None:
    """Pick an installed Korean-capable UI font before QSS is applied."""
    preferred = (
        "Noto Sans CJK KR",
        "Noto Sans KR",
        "NanumGothic",
        "Nanum Gothic",
        "Pretendard",
        "Apple SD Gothic Neo",
        "Malgun Gothic",
    )
    installed = set(QFontDatabase().families())
    for family in preferred:
        if family in installed:
            app.setFont(QFont(family, 10))
            logging.getLogger(__name__).info("UI font selected: %s", family)
            return

    logging.getLogger(__name__).warning(
        "No Korean UI font found. Install fonts-noto-cjk or fonts-nanum if Korean text is broken."
    )


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    _apply_korean_font(app)

    # 디자인 시스템 v2 (2026-04-26): 토큰 기반 라이트/다크 테마
    # Fusion 스타일 강제로 macOS 시스템 다크모드 영향 차단.
    theme_manager = ThemeManager()
    theme_manager.apply(app)

    window = MainWindow(theme_manager=theme_manager)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
