"""상태/톤 배지 + 알림 목록 + 토스트 알림."""

from __future__ import annotations

from app.styles.tokens import Tokens


def _badges_alerts(t: Tokens) -> str:
    c = t.color
    typo = t.typography
    sp = t.spacing
    r = t.radius
    return f"""
QLabel[status="ok"] {{
    color: {c.ok}; background-color: {c.ok_subtle}; border: 1px solid {c.ok};
    border-radius: {r.full}px; padding: 2px {sp.sm}px;
    font-weight: 600; font-size: {typo.size_xs}px;
}}
QLabel[status="warn"] {{
    color: {c.warn}; background-color: {c.warn_subtle}; border: 1px solid {c.warn};
    border-radius: {r.full}px; padding: 2px {sp.sm}px;
    font-weight: 600; font-size: {typo.size_xs}px;
}}
QLabel[status="danger"] {{
    color: {c.danger}; background-color: {c.danger_subtle}; border: 1px solid {c.danger};
    border-radius: {r.full}px; padding: 2px {sp.sm}px;
    font-weight: 600; font-size: {typo.size_xs}px;
}}
QLabel[status="defect"] {{
    color: {c.defect}; background-color: {c.defect_subtle}; border: 1px solid {c.defect};
    border-radius: {r.full}px; padding: 2px {sp.sm}px;
    font-weight: 600; font-size: {typo.size_xs}px;
}}
QLabel[status="info"] {{
    color: {c.info}; background-color: {c.info_subtle}; border: 1px solid {c.info};
    border-radius: {r.full}px; padding: 2px {sp.sm}px;
    font-weight: 600; font-size: {typo.size_xs}px;
}}
QLabel[status="muted"] {{
    color: {c.text_muted}; background-color: {c.bg_muted}; border: 1px solid {c.border_strong};
    border-radius: {r.full}px; padding: 2px {sp.sm}px;
    font-weight: 500; font-size: {typo.size_xs}px;
}}

QLabel[tone="ok"]      {{ color: {c.ok};     font-weight: 600; }}
QLabel[tone="warn"]    {{ color: {c.warn};   font-weight: 600; }}
QLabel[tone="danger"]  {{ color: {c.danger}; font-weight: 600; }}
QLabel[tone="muted"]   {{ color: {c.text_muted}; }}
QLabel[tone="primary"] {{ color: {c.brand_accent};  font-weight: 600; }}

#alertList {{
    background-color: {c.bg_card};
    border: 1px solid {c.border};
    border-radius: {r.lg}px;
    font-size: {typo.size_base}px;
    padding: {sp.xs}px;
    color: {c.text_primary};
}}
#alertList::item {{
    padding: {sp.sm}px {sp.md}px;
    border-bottom: 1px solid {c.border};
    color: {c.text_primary};
    border-radius: {r.sm}px;
}}
#alertList::item:hover {{ background-color: {c.bg_elevated}; }}

#toastNotification[severity="info"] {{
    background-color: {c.info}; color: {c.brand_text_on};
    border-radius: {r.lg}px; padding: {sp.md}px {sp.lg}px;
    font-size: {typo.size_md}px; font-weight: 600;
}}
#toastNotification[severity="warning"] {{
    background-color: {c.warn}; color: {c.brand_text_on};
    border-radius: {r.lg}px; padding: {sp.md}px {sp.lg}px;
    font-size: {typo.size_md}px; font-weight: 600;
}}
#toastNotification[severity="critical"], #toastNotification[severity="error"] {{
    background-color: {c.danger}; color: {c.brand_text_on};
    border-radius: {r.lg}px; padding: {sp.md}px {sp.lg}px;
    font-size: {typo.size_md}px; font-weight: 600;
}}
"""


def _alerts_list(t: Tokens) -> str:
    c = t.color
    typo = t.typography
    return f"""
#alertItem {{
    border-radius: {t.radius.sm}px;
    border-left: 4px solid {c.border_strong};
    background-color: {c.bg_muted};
}}
#alertItem[severity="critical"] {{ background-color: {c.danger_subtle}; border-left-color: {c.danger}; }}
#alertItem[severity="error"]    {{ background-color: {c.danger_subtle}; border-left-color: {c.danger}; }}
#alertItem[severity="warning"]  {{ background-color: {c.warn_subtle};   border-left-color: {c.warn}; }}
#alertItem[severity="info"]     {{ background-color: {c.info_subtle};   border-left-color: {c.info}; }}
#alertItem[severity="success"]  {{ background-color: {c.ok_subtle};     border-left-color: {c.ok}; }}

#alertIcon {{
    background-color: transparent;
    font-size: {typo.size_lg}px;
    font-weight: 700;
}}
#alertIcon[severity="critical"], #alertIcon[severity="error"] {{ color: {c.danger}; }}
#alertIcon[severity="warning"]  {{ color: {c.warn}; }}
#alertIcon[severity="info"]     {{ color: {c.info}; }}
#alertIcon[severity="success"]  {{ color: {c.ok}; }}

#alertLevelBadge {{
    background-color: transparent;
    font-size: {typo.size_xs}px;
    font-weight: 700;
}}
#alertLevelBadge[severity="critical"], #alertLevelBadge[severity="error"] {{ color: {c.danger}; }}
#alertLevelBadge[severity="warning"]  {{ color: {c.warn}; }}
#alertLevelBadge[severity="info"]     {{ color: {c.info}; }}
#alertLevelBadge[severity="success"]  {{ color: {c.ok}; }}

#alertMessage {{
    background-color: transparent;
    color: {c.text_primary};
    font-size: {typo.size_sm}px;
}}
"""


def _toast(t: Tokens) -> str:
    c = t.color
    typo = t.typography
    return f"""
#toastContainer {{
    background-color: {c.text_primary};
    border-radius: {t.radius.lg}px;
    border-left: 5px solid {c.border_strong};
}}
#toastContainer[severity="critical"], #toastContainer[severity="error"] {{ border-left-color: {c.danger}; }}
#toastContainer[severity="warning"]  {{ border-left-color: {c.warn}; }}
#toastContainer[severity="info"]     {{ border-left-color: {c.info}; }}
#toastContainer[severity="success"]  {{ border-left-color: {c.ok}; }}

#toastIcon {{
    background-color: transparent;
    font-size: {typo.size_xl}px;
    font-weight: 700;
}}
#toastIcon[severity="critical"], #toastIcon[severity="error"] {{ color: {c.danger}; }}
#toastIcon[severity="warning"]  {{ color: {c.warn}; }}
#toastIcon[severity="info"]     {{ color: {c.info}; }}
#toastIcon[severity="success"]  {{ color: {c.ok}; }}

#toastTitle {{
    background-color: transparent;
    font-size: {typo.size_xs}px;
    font-weight: 700;
}}
#toastTitle[severity="critical"], #toastTitle[severity="error"] {{ color: {c.danger}; }}
#toastTitle[severity="warning"]  {{ color: {c.warn}; }}
#toastTitle[severity="info"]     {{ color: {c.info}; }}
#toastTitle[severity="success"]  {{ color: {c.ok}; }}

#toastMessage {{
    background-color: transparent;
    color: {c.bg_card};
    font-size: {typo.size_base}px;
}}
"""
