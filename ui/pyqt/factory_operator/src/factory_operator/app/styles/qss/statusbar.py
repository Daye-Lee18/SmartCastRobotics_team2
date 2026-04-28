"""상단 상태바 — QStatusBar 본체 + 시계/항목 라벨/사유박스/컨베이어 라벨/상태 도트."""

from __future__ import annotations

from app.styles.tokens import Tokens


def _statusbar(t: Tokens) -> str:
    c = t.color
    typo = t.typography
    sp = t.spacing
    r = t.radius
    return f"""
QStatusBar {{
    background-color: {c.bg_card};
    color: {c.text_muted};
    font-size: {typo.size_xs}px;
    border-top: 1px solid {c.border};
    min-height: 28px;
}}
QStatusBar QLabel {{
    padding: 0 {sp.sm + 2}px;
    color: {c.text_muted};
    background-color: transparent;
}}

#statusBarClock {{
    color: {c.text_primary};
    font-family: {typo.family_mono};
    font-weight: 700;
    padding: 0 {sp.md + 2}px;
}}

#itemFieldLabel {{
    color: {c.text_secondary};
    font-weight: 600;
}}

#reasonBox {{
    color: {c.text_secondary};
    background-color: {c.bg_muted};
    padding: {sp.md - 2}px {sp.md}px;
    border-radius: {r.md}px;
    border: 1px solid {c.border};
    font-size: {typo.size_sm}px;
}}

#convBarLabel {{
    color: {c.text_muted};
    font-size: {typo.size_xs}px;
    font-weight: 700;
}}
#convStatusText {{
    color: {c.text_secondary};
    font-size: {typo.size_sm}px;
    font-weight: 600;
}}
#convMetaText {{
    color: {c.text_muted};
    font-size: {typo.size_xs}px;
}}

QLabel#statusDot {{
    font-size: {typo.size_sm}px;
    background-color: transparent;
}}
QLabel#statusDot[status="online"]   {{ color: {c.ok}; }}
QLabel#statusDot[status="offline"]  {{ color: {c.border_strong}; }}
QLabel#statusDot[status="warn"]     {{ color: {c.warn}; }}
QLabel#statusDot[status="danger"]   {{ color: {c.danger}; }}
"""
