"""도메인 위젯 — AMR 카드 / 배터리 바 / 컨베이어 카드 / 불량 패널."""

from __future__ import annotations

from app.styles.tokens import Tokens


def _amr_card(t: Tokens) -> str:
    c = t.color
    typo = t.typography
    sp = t.spacing
    r = t.radius
    return f"""
#amrIdLabel {{
    background-color: transparent;
    color: {c.text_primary};
    font-size: {typo.size_lg}px;
    font-weight: 700;
}}

#amrStatusBadge {{
    border-radius: {r.full}px;
    font-size: {typo.size_xs}px;
    font-weight: 700;
    padding: 2px {sp.sm + 2}px;
    background-color: {c.bg_muted};
    color: {c.text_secondary};
    border: 1px solid {c.border_strong};
}}
#amrStatusBadge[severity="idle"] {{
    background-color: {c.bg_muted}; color: {c.text_secondary}; border-color: {c.border_strong};
}}
#amrStatusBadge[severity="moving"] {{
    background-color: {c.ok_subtle}; color: {c.ok}; border-color: {c.ok};
}}
#amrStatusBadge[severity="waiting"] {{
    background-color: {c.warn_subtle}; color: {c.warn}; border-color: {c.warn};
}}
#amrStatusBadge[severity="loading"] {{
    background-color: {c.brand_subtle}; color: {c.brand_accent}; border-color: {c.brand};
}}
#amrStatusBadge[severity="done"] {{
    background-color: {c.info_subtle}; color: {c.info}; border-color: {c.info};
}}
#amrStatusBadge[severity="failed"] {{
    background-color: {c.danger_subtle}; color: {c.danger}; border-color: {c.danger};
}}

#amrInfoTitle {{
    background-color: transparent;
    color: {c.text_muted};
    font-size: 10px;
}}
#amrInfoValue {{
    background-color: transparent;
    color: {c.text_primary};
    font-size: {typo.size_sm}px;
    font-weight: 600;
}}
"""


def _battery_bar(t: Tokens) -> str:
    c = t.color
    return f"""
#batteryBar {{
    background-color: {c.bg_muted};
    border: 1px solid {c.border};
    border-radius: 9px;
    text-align: center;
    font-size: 10px;
    font-weight: 700;
    color: {c.text_primary};
}}
#batteryBar::chunk {{
    border-radius: 8px;
    background-color: {c.ok};
}}
#batteryBar[level="high"]::chunk {{ background-color: {c.ok}; }}
#batteryBar[level="mid"]::chunk  {{ background-color: {c.warn}; }}
#batteryBar[level="low"]::chunk  {{ background-color: {c.danger}; }}
"""


def _conveyor_card(t: Tokens) -> str:
    c = t.color
    typo = t.typography
    sp = t.spacing
    r = t.radius
    return f"""
#convCardTitle {{
    background-color: transparent;
    color: {c.text_primary};
    font-size: {typo.size_lg}px;
    font-weight: 700;
}}

#convStateBadge {{
    border-radius: {r.full}px;
    font-size: 10px;
    font-weight: 700;
    padding: 2px {sp.md}px;
    background-color: {c.bg_muted};
    color: {c.text_secondary};
    border: 1px solid {c.border_strong};
}}
#convStateBadge[severity="idle"]    {{ background-color: {c.bg_muted};      color: {c.text_secondary}; border-color: {c.border_strong}; }}
#convStateBadge[severity="ok"]      {{ background-color: {c.ok_subtle};    color: {c.ok};     border-color: {c.ok}; }}
#convStateBadge[severity="warn"]    {{ background-color: {c.warn_subtle};  color: {c.warn};   border-color: {c.warn}; }}
#convStateBadge[severity="info"]    {{ background-color: {c.info_subtle};  color: {c.info};   border-color: {c.info}; }}
#convStateBadge[severity="defect"]  {{ background-color: {c.defect_subtle};color: {c.defect}; border-color: {c.defect}; }}
#convStateBadge[severity="danger"]  {{ background-color: {c.danger_subtle};color: {c.danger}; border-color: {c.danger}; }}
#convStateBadge[severity="offline"] {{ background-color: {c.bg_muted};      color: {c.text_muted}; border-color: {c.border}; }}

#convMetricLabel {{
    background-color: transparent;
    color: {c.text_muted};
    font-size: 10px;
}}
#convMetricValue {{
    background-color: transparent;
    color: {c.text_primary};
    font-size: {typo.size_md}px;
    font-weight: 700;
}}
#convMetricValue[state="on"]  {{ color: {c.ok}; }}
#convMetricValue[state="off"] {{ color: {c.text_muted}; }}

#convTofValue {{
    background-color: transparent;
    color: {c.text_secondary};
    font-size: {typo.size_base}px;
    font-weight: 600;
}}
"""


def _defect_panels(t: Tokens) -> str:
    c = t.color
    typo = t.typography
    r = t.radius
    return f"""
#rankBadge {{
    border-radius: 13px;
    font-weight: 700;
    font-size: {typo.size_sm}px;
    background-color: {c.bg_muted};
    color: {c.text_primary};
}}
#rankBadge[rank="1"] {{ background-color: #fbbf24; color: #78350f; }}
#rankBadge[rank="2"] {{ background-color: #cbd5e1; color: #1e293b; }}
#rankBadge[rank="3"] {{ background-color: #fdba74; color: #7c2d12; }}

#defectName {{
    background-color: transparent;
    color: {c.text_primary};
    font-size: {typo.size_base}px;
    font-weight: 600;
}}

#defectStandardCard {{
    background-color: {c.bg_muted};
    border: 1px solid {c.border};
    border-radius: {r.md}px;
}}
#defectStandardName {{
    background-color: transparent;
    color: {c.text_primary};
    font-size: {typo.size_sm}px;
    font-weight: 700;
    border: none;
}}
#defectStandardLabel {{
    background-color: transparent;
    color: {c.text_muted};
    font-size: 9px;
    border: none;
}}
#defectStandardValue {{
    background-color: transparent;
    color: {c.text_secondary};
    font-size: {typo.size_xs}px;
    border: none;
}}
"""
