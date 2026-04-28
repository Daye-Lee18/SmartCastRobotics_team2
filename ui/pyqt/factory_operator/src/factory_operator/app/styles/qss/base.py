"""기본 위젯 스타일 — QWidget/QLabel/메뉴/툴팁 + 메인 페이지 + 스크롤바.

토큰을 받아 QSS 문자열을 반환하는 섹션 함수 모음.
"""

from __future__ import annotations

from app.styles.tokens import Tokens


def _global(t: Tokens) -> str:
    c = t.color
    typo = t.typography
    sp = t.spacing
    r = t.radius
    return f"""
QWidget {{
    background-color: {c.bg_app};
    color: {c.text_primary};
    font-family: {typo.family};
    font-size: {typo.size_base}px;
}}
QLabel {{ background-color: transparent; color: {c.text_primary}; }}
QFrame {{ background-color: transparent; }}
QToolTip {{
    background-color: {c.text_primary};
    color: {c.bg_card};
    border: 1px solid {c.border_strong};
    border-radius: {r.md}px;
    padding: {sp.xs}px {sp.sm}px;
    font-size: {typo.size_sm}px;
}}
QMenu {{
    background-color: {c.bg_card};
    color: {c.text_primary};
    border: 1px solid {c.border};
    border-radius: {r.md}px;
    padding: {sp.xs}px;
}}
QMenu::item {{ padding: {sp.xs}px {sp.md}px; border-radius: {r.sm}px; }}
QMenu::item:selected {{ background-color: {c.brand_subtle}; color: {c.text_primary}; }}
"""


def _main(t: Tokens) -> str:
    c = t.color
    typo = t.typography
    sp = t.spacing
    return f"""
QMainWindow {{ background-color: {c.bg_app}; }}
QStackedWidget > QWidget {{ background-color: {c.bg_app}; }}
#pageTitle {{
    color: {c.text_primary};
    font-size: {typo.size_2xl}px;
    font-weight: 700;
    padding: {sp.xs}px 0 {sp.sm}px 0;
    background-color: transparent;
}}
#sectionTitle {{
    color: {c.text_secondary};
    font-size: {typo.size_md}px;
    font-weight: 600;
    padding: {sp.md}px 0 {sp.xs}px 0;
    background-color: transparent;
}}
#pageSubtitle {{
    color: {c.text_muted};
    font-size: {typo.size_sm}px;
    background-color: transparent;
}}
"""


def _scrollbar(t: Tokens) -> str:
    c = t.color
    r = t.radius
    return f"""
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: {c.bg_app};
    width: 10px; margin: 0;
    border-radius: {r.sm}px;
}}
QScrollBar::handle:vertical {{
    background: {c.border_strong};
    min-height: 30px; border-radius: {r.sm}px;
}}
QScrollBar::handle:vertical:hover {{ background: {c.text_muted}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ height: 0; background: none; }}

QScrollBar:horizontal {{
    background: {c.bg_app};
    height: 10px; margin: 0;
    border-radius: {r.sm}px;
}}
QScrollBar::handle:horizontal {{
    background: {c.border_strong};
    min-width: 30px; border-radius: {r.sm}px;
}}
QScrollBar::handle:horizontal:hover {{ background: {c.text_muted}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ width: 0; background: none; }}
"""
