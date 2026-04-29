"""사이드바 스타일 — 좌측 내비게이션 + 로고 + 버전 푸터."""

from __future__ import annotations

from app.styles.tokens import Tokens


def _sidebar(t: Tokens) -> str:
    c = t.color
    typo = t.typography
    sp = t.spacing
    return f"""
#sidebar {{
    background-color: {c.sidebar_bg};
    border-right: 1px solid {c.sidebar_border};
}}
#sidebarLogo {{
    background-color: {c.sidebar_bg_top};
    color: {c.sidebar_accent};
    font-size: {typo.size_lg}px;
    font-weight: 700;
    padding: {sp.xl}px {sp.md}px;
    border-bottom: 1px solid {c.sidebar_border};
    letter-spacing: 0.5px;
}}
#sidebarNav {{
    background-color: {c.sidebar_bg};
    border: none;
    color: {c.sidebar_text};
    font-size: {typo.size_md}px;
    outline: none;
    padding: {sp.xs}px 0;
}}
#sidebarNav::item {{
    padding: {sp.md}px {sp.lg}px;
    border-left: 3px solid transparent;
    margin: 1px 0;
    color: {c.sidebar_text};
}}
#sidebarNav::item:hover {{
    background-color: {c.sidebar_hover};
    color: {c.sidebar_text_active};
    border-left: 3px solid {c.sidebar_text_muted};
}}
#sidebarNav::item:selected {{
    background-color: {c.sidebar_active};
    color: {c.sidebar_text_active};
    border-left: 3px solid {c.sidebar_accent};
    font-weight: 600;
}}
#sidebarVersion {{
    color: {c.sidebar_text_muted};
    font-size: {typo.size_xs}px;
    padding: {sp.sm}px {sp.md}px;
    background-color: {c.sidebar_bg_top};
    border-top: 1px solid {c.sidebar_border};
}}
"""
