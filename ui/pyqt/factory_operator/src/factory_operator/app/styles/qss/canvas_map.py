"""다크 캔버스 + 팩토리 맵 페이지 + 사이드바 토글/테마 토글 + 탭/프로그레스바."""

from __future__ import annotations

from app.styles.tokens import Tokens


def _canvas(t: Tokens) -> str:
    c = t.color
    r = t.radius
    return f"""
#cameraView, #factoryMap, #darkCanvas {{
    background-color: {c.canvas_bg};
    border: 1px solid {c.canvas_border};
    border-radius: {r.lg}px;
    color: #f1f5f9;
}}
"""


def _factory_map(t: Tokens) -> str:
    c = t.color
    typo = t.typography
    sp = t.spacing
    r = t.radius
    return f"""
#factoryMapPage {{
    background-color: {c.canvas_bg};
}}
#factoryMapPage QLabel {{
    color: #e5e7eb;
}}
#mapTitle {{
    color: #f9fafb;
    font-size: {typo.size_2xl}px;
    font-weight: 700;
    background-color: transparent;
}}
#mapHint {{
    color: #9ca3af;
    font-size: {typo.size_xs}px;
    background-color: transparent;
}}
#mapLegendText {{
    color: #cbd5e1;
    font-size: {typo.size_sm}px;
    background-color: transparent;
}}

QToolButton#sidebarToggle {{
    background-color: {c.bg_muted};
    color: {c.text_secondary};
    border: none;
    border-right: 1px solid {c.border};
    font-size: {typo.size_xs}px;
    padding: 0;
}}
QToolButton#sidebarToggle:hover {{
    background-color: {c.border};
    color: {c.text_primary};
}}

QToolButton#sidebarThemeToggle {{
    background-color: transparent;
    color: {c.sidebar_text};
    border: none;
    border-top: 1px solid {c.sidebar_border};
    padding: {sp.sm + 2}px {sp.md + 2}px;
    font-size: {typo.size_sm}px;
    text-align: center;
}}
QToolButton#sidebarThemeToggle:hover {{
    background-color: {c.sidebar_hover};
    color: {c.sidebar_text_active};
}}

QTabWidget::pane {{
    border: 1px solid {c.border};
    border-radius: {r.lg}px;
    background-color: {c.bg_card};
    top: -1px;
}}
QTabBar::tab {{
    background-color: {c.bg_muted};
    color: {c.text_secondary};
    padding: {sp.sm}px {sp.lg}px;
    border: 1px solid {c.border};
    border-bottom: none;
    border-top-left-radius: {r.md}px;
    border-top-right-radius: {r.md}px;
    font-size: {typo.size_sm}px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    background-color: {c.bg_card};
    color: {c.text_primary};
    font-weight: 600;
}}
QTabBar::tab:hover {{
    background-color: {c.bg_elevated};
    color: {c.text_primary};
}}

QProgressBar {{
    background-color: {c.bg_muted};
    border: 1px solid {c.border};
    border-radius: {r.md}px;
    text-align: center;
    color: {c.text_primary};
    font-size: {typo.size_xs}px;
    height: 14px;
}}
QProgressBar::chunk {{
    background-color: {c.brand};
    border-radius: {r.sm}px;
}}
"""
